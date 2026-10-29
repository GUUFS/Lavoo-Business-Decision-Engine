
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from database.pg_models import Commission, Referral, CommissionSummary, User, NotificationType, Subscriptions
from api.services.notification_service import NotificationService
from emailing.email_service import email_service
import os
import logging

logger = logging.getLogger(__name__)

COMMISSION_RATE_PARTNER  = Decimal("0.50")   # 50% — paid internally to partners/staff on their own real referrals, under the same 6-month/one-time rules as everyone else (see _eligibility_for_payment)
COMMISSION_RATE_STAFF_POOL = Decimal("0.30")  # 30% flat — a referral-less signup auto-assigned to staff (see Referral.via_staff_pool); overrides everything below regardless of that staff member's own plan

# Builder Bonus Rewards rates, keyed by the REFERRER's own current plan —
# not the referral's. Eligibility (whether a given payment pays out at all)
# is separate — see _commission_eligibility below.
COMMISSION_RATE_PREMIUM = Decimal("0.40")    # 40% — referrer is actively on Premium
COMMISSION_RATE_PRO     = Decimal("0.25")    # 25% — referrer is actively on Pro
COMMISSION_RATE_STARTER = Decimal("0.10")    # 10% — referrer is on the free Starter plan; ONE-TIME only, see below

# Legacy aliases kept for anything that still imports the old names directly.
COMMISSION_RATE_STANDARD = COMMISSION_RATE_PREMIUM
COMMISSION_RATE_FREE = COMMISSION_RATE_STARTER

# A monthly or quarterly referral keeps paying the referrer on every payment
# that clears within this many days of the referral's FIRST successful
# payment — roughly 6 months. A yearly referral never uses this window: it
# pays once, on that first payment, and never again (see _commission_eligibility).
RECURRING_WINDOW_DAYS = 183

# Awarded to the SUBSCRIBER themselves (not a referrer) EVERY time one of
# their subscription payments succeeds — initial purchase or renewal alike,
# not just the first ever. Which amount depends on which plan they paid
# for, told apart by the actual amount charged (see PLAN_PRICES below):
# there's no separate "tier" column on Subscriptions, and the checkout flow
# itself doesn't pass a tier through yet — the home page's pricing section
# (lib/currency.ts's LAVOO_PRICING on the frontend) already prices both
# tiers for every currency/billing-period, which is what PLAN_PRICES
# mirrors here.
PLAN_CHOPS = {"pro": 1500, "premium": 3000}

# Mirrors lib/currency.ts's LAVOO_PRICING on the frontend — each tier's
# actual discounted "price" per currency/billing-period (never "regular",
# which is only ever shown struck-through, never charged). Keep both files
# in sync by hand if either changes; there's no shared source between a
# Python backend and a TypeScript frontend to enforce it automatically.
PLAN_PRICES = {
    "pro": {
        "GBP": {"monthly": Decimal("22.49"), "quarterly": Decimal("60.00"), "yearly": Decimal("269.78")},
        "USD": {"monthly": Decimal("29.95"), "quarterly": Decimal("84.25"), "yearly": Decimal("336.98")},
        "NGN": {"monthly": Decimal("34000"), "quarterly": Decimal("22680"), "yearly": Decimal("20160")},
    },
    "premium": {
        "GBP": {"monthly": Decimal("29.58"), "quarterly": Decimal("78.98"), "yearly": Decimal("354.96")},
        "USD": {"monthly": Decimal("36.95"), "quarterly": Decimal("110.85"), "yearly": Decimal("443.40")},
        "NGN": {"monthly": Decimal("45000"), "quarterly": Decimal("28080"), "yearly": Decimal("24960")},
    },
}
# A charged amount is matched to a plan within this tolerance — covers minor
# rounding (e.g. minor-unit conversion) without being loose enough to
# confuse two genuinely different price points.
PLAN_PRICE_MATCH_TOLERANCE = Decimal("0.50")

# A payment is "real" for chops/stats purposes under a different word per
# provider (Flutterwave writes "successful", Stripe "completed") — same set
# already used in api/main.py, api/utils/sub_utils.py, and
# api/routes/admin/revenue.py; duplicated here rather than imported since
# none of those are modules this one already depends on.
PAID_SUBSCRIPTION_STATUSES = ('completed', 'active', 'paid', 'successful', 'succeeded')

# Keep legacy alias so any other callsite referencing COMMISSION_RATE still works
COMMISSION_RATE = COMMISSION_RATE_STANDARD


class CommissionService:

    # When the settlement job last emailed about commissions stuck waiting.
    _last_waiting_alert: "datetime | None" = None
    _last_waiting_alert_flutterwave: "datetime | None" = None

    @staticmethod
    def _resolve_referrer_tier(referrer_id: int, db: Session) -> str:
        """Which Builder Bonus tier a referrer is in RIGHT NOW: 'partner',
        'premium', 'pro' or 'starter'. Checked fresh on every call — this is
        what makes eligibility a per-payment check rather than something
        locked in at the referral's first payment: a referrer who lapses
        from Pro back to Starter between two of a referral's payments earns
        the Pro rate on the payments that cleared while they were still
        subscribed, and nothing on the ones that cleared after they lapsed.

        Partners AND staff (is_partner OR is_staff — an admin-assignable
        role, independent of is_partner) are 'partner' regardless of their
        own subscription — assigning the Staff role on the admin
        Permissions page is what's supposed to grant this, so it has to
        actually change the rate, not just show a badge.

        Otherwise: 'starter' unless User.subscription_status is 'active', in
        which case the referrer's own most recent active Subscriptions row
        is matched against PLAN_PRICES (via _resolve_plan_tier) to tell Pro
        from Premium. An active referrer whose amount doesn't match either
        price point (legacy pricing, a manual adjustment) is treated as
        'starter' rather than guessed at — same fail-safe as
        _resolve_plan_tier itself.
        """
        referrer = db.query(User).filter(User.id == referrer_id).first()
        if not referrer:
            return "starter"
        if getattr(referrer, "is_partner", False) or getattr(referrer, "is_staff", False):
            return "partner"
        if (referrer.subscription_status or "").lower() != "active":
            return "starter"

        own_sub = (
            db.query(Subscriptions)
            .filter(
                Subscriptions.user_id == referrer_id,
                Subscriptions.subscription_status == "active",
            )
            .order_by(Subscriptions.created_at.desc())
            .first()
        )
        if not own_sub:
            return "starter"
        tier = CommissionService._resolve_plan_tier(Decimal(str(own_sub.amount)), own_sub.currency)
        return tier or "starter"

    @staticmethod
    def _get_rate_for_referrer(referrer_id: int, db: Session) -> Decimal:
        """Display-only: the rate a referrer currently earns on an eligible
        payment, for showing on the earnings page. Does NOT by itself mean
        every payment pays this rate — see _commission_eligibility for the
        first-payment/6-month-window/yearly-one-time rules that decide
        whether a given payment is eligible at all."""
        tier = CommissionService._resolve_referrer_tier(referrer_id, db)
        return {
            "partner": COMMISSION_RATE_PARTNER,
            "premium": COMMISSION_RATE_PREMIUM,
            "pro": COMMISSION_RATE_PRO,
            "starter": COMMISSION_RATE_STARTER,
        }[tier]

    @staticmethod
    def _eligibility_for_payment(
        referrer_id: int,
        via_staff_pool: bool,
        referred_user_id: int,
        billing_period: "str | None",
        payment_time: datetime,
        db: Session,
        exclude_subscription_id: "int | None" = None,
    ) -> "tuple[bool, Decimal]":
        """Core eligibility/rate decision, built from primitives so it can be
        called both AFTER a payment row exists (calculate_commission, via
        _commission_eligibility below) and BEFORE one does — when
        Flutterwave's split has to be configured on the charge request
        itself, ahead of the charge succeeding (see
        flutterwave_split.get_split_config_for_referred_user). Returns
        (eligible, rate).

        Rules (see commission_service.py module docstring area for the
        rates themselves):
          - via_staff_pool: flat 30%, always eligible, no window — this is a
            no-referral-code signup auto-assigned to a staff member from a
            rotating pool (set at signup, before any payment exists), not a
            real Builder Bonus referral, so none of the rules below apply to
            it.
          - Every other referrer — partner/staff (50%), Premium (40%), Pro
            (25%) alike — is a real referral and follows the SAME
            eligibility rules, just at a different rate:
              - Starter referrer: 10%, but ONLY on the referral's first-ever
                successful payment. Never again from that referral,
                regardless of billing period.
              - Referral on a YEARLY plan: the tier rate, but ONLY on the
                referral's first-ever successful payment — a yearly referral
                pays its referrer exactly once, even when it renews a year
                later.
              - Referral on monthly/quarterly (or unknown — treated as
                monthly/quarterly, the more common case): the tier rate on
                every payment that clears within RECURRING_WINDOW_DAYS of
                the referral's first successful payment. Checked fresh per
                payment against the referrer's CURRENT tier — see
                _resolve_referrer_tier — so a partner/staff referrer loses
                nothing by this: the ONLY referrer tier currently exempt
                from re-checking was partner/staff before this rule existed,
                and that exemption is gone.
        """
        if via_staff_pool:
            return True, COMMISSION_RATE_STAFF_POOL

        tier = CommissionService._resolve_referrer_tier(referrer_id, db)

        # Is this the referred user's first-ever successful payment?
        earlier_filters = [
            Subscriptions.user_id == referred_user_id,
            Subscriptions.status.in_(PAID_SUBSCRIPTION_STATUSES),
            Subscriptions.created_at < payment_time,
        ]
        if exclude_subscription_id is not None:
            earlier_filters.append(Subscriptions.id != exclude_subscription_id)
        earlier_payment = db.query(Subscriptions.id).filter(*earlier_filters).first()
        is_first_payment = earlier_payment is None

        if tier == "starter":
            return is_first_payment, COMMISSION_RATE_STARTER

        # partner/staff, premium and pro all follow the same window/one-time
        # rules below — only the rate differs. A staff member's own personal
        # referral is a real Builder Bonus referral like anyone else's; only
        # the staff-pool auto-assignment above is exempt from these rules.
        rate = {
            "partner": COMMISSION_RATE_PARTNER,
            "premium": COMMISSION_RATE_PREMIUM,
            "pro": COMMISSION_RATE_PRO,
        }[tier]
        billing_period = (billing_period or "monthly").lower()

        if billing_period == "yearly":
            return is_first_payment, rate

        # monthly/quarterly: recurring within RECURRING_WINDOW_DAYS of the
        # referral's first successful payment (which may be this payment itself).
        first_payment_row = (
            db.query(Subscriptions.created_at)
            .filter(
                Subscriptions.user_id == referred_user_id,
                Subscriptions.status.in_(PAID_SUBSCRIPTION_STATUSES),
            )
            .order_by(Subscriptions.created_at.asc())
            .first()
        )
        first_payment_date = first_payment_row[0] if first_payment_row else payment_time
        within_window = (payment_time - first_payment_date) <= timedelta(days=RECURRING_WINDOW_DAYS)
        return within_window, rate

    @staticmethod
    def _commission_eligibility(subscription, referral, db: Session) -> "tuple[bool, Decimal]":
        """calculate_commission's entry point into _eligibility_for_payment
        — see that method's docstring for the actual rules."""
        return CommissionService._eligibility_for_payment(
            referrer_id=referral.referrer_id,
            via_staff_pool=referral.via_staff_pool,
            referred_user_id=subscription.user_id,
            billing_period=getattr(subscription, "subscription_plan", None),
            payment_time=subscription.created_at,
            db=db,
            exclude_subscription_id=subscription.id,
        )

    @staticmethod
    def _resolve_plan_tier(amount: Decimal, currency: str) -> "str | None":
        """Tell a Pro payment from a Premium one by matching the amount
        actually charged against PLAN_PRICES — see that constant's comment
        for why there's nothing more direct to check yet. Returns None if
        nothing matches closely enough (an old/legacy price point, a beta
        discount, a manually-adjusted amount, …) so the caller can skip
        awarding rather than guess at which tier it was."""
        currency = (currency or "USD").upper()
        for tier, by_currency in PLAN_PRICES.items():
            periods = by_currency.get(currency)
            if not periods:
                continue
            for period_price in periods.values():
                if abs(amount - period_price) <= PLAN_PRICE_MATCH_TOLERANCE:
                    return tier
        return None

    @staticmethod
    def _award_plan_signup_chops(subscription, db: Session) -> None:
        """Pay the subscriber themselves chops once per successful
        subscription payment — initial purchase and every renewal each
        earn it once, but never twice for the SAME payment. Amount depends
        on which plan (Pro vs Premium) they actually paid for, resolved via
        _resolve_plan_tier; skipped entirely if that can't be determined.

        Idempotency: Subscriptions.chops_awarded is the guard, checked and
        set on the SAME row this payment created/updated — not derived from
        status or counted some other indirect way. This is what makes a
        webhook redelivery for the same payment event safe even on the one
        path (_create_active_subscription_record in stripe.py, for an
        incomplete -> active transition) that reuses an existing row and
        calls calculate_commission again on it: the second call sees
        chops_awarded already True and does nothing.
        """
        if (subscription.status or "").lower() not in PAID_SUBSCRIPTION_STATUSES:
            return

        if getattr(subscription, "chops_awarded", False):
            return

        tier = CommissionService._resolve_plan_tier(
            Decimal(str(subscription.amount)), subscription.currency
        )
        if tier is None:
            logger.info(
                f"[PLAN SIGNUP CHOPS] subscription={subscription.id} amount="
                f"{subscription.amount} {subscription.currency} didn't match a known "
                f"Pro/Premium price point — skipping chops"
            )
            return

        user = db.query(User).filter(User.id == subscription.user_id).first()
        if not user:
            return

        chops = PLAN_CHOPS[tier]
        user.total_chops = (user.total_chops or 0) + chops
        subscription.chops_awarded = True
        db.flush()
        logger.info(
            f"[PLAN SIGNUP CHOPS] Awarded {chops} chops ({tier}) to user {user.id} "
            f"for subscription={subscription.id} ({subscription.amount} {subscription.currency})"
        )

    @staticmethod
    def calculate_commission(subscription, db: Session, already_settled: bool = False):
        """
        Calculate and create a Commission record when a referred user makes
        a payment. Regular users receive 40% of the subscription amount.
        Partners/staff receive 50% (screen always shows 40%).

        already_settled=True means the actual charge this Commission is
        for was placed with a Flutterwave split (see flutterwave_split.py)
        — the referrer's share already landed in their own account at
        payment time, so this row is a read-only history/earnings-page
        record, not something owed. It's created with status='auto_settled'
        and paid_at set immediately, skipping the pending -> approved ->
        payout pipeline entirely (no "Request Payout" action applies to it).
        already_settled=False (the default, and the only behaviour that
        existed before Flutterwave splits) means the referrer has no
        verified payout account to split to yet — this Commission starts
        'pending' and is only ever paid via the existing manual
        approve/payout flow once they add one.
        """
        try:
            # Award the subscriber's own plan chops (every successful
            # payment, not just the first) before anything referral-
            # specific — this must fire for every subscriber, not just
            # referred ones, which the early-return right below would
            # otherwise skip entirely.
            CommissionService._award_plan_signup_chops(subscription, db)

            # Check if user was referred
            referral = db.query(Referral).filter(
                Referral.referred_user_id == subscription.user_id
            ).first()

            if not referral:
                logger.info(f"No referral found for user {subscription.user_id}")
                return None

            # Check if commission already exists
            existing = db.query(Commission).filter(
                Commission.subscription_id == subscription.id
            ).first()

            if existing:
                logger.info(f"Commission already exists for subscription {subscription.id}")
                return existing

            # Determine eligibility and rate — see _commission_eligibility's
            # own docstring for the full first-payment/6-month-window/
            # yearly-one-time rules this payment is checked against.
            eligible, actual_rate = CommissionService._commission_eligibility(subscription, referral, db)
            if not eligible:
                logger.info(
                    f"[BUILDER BONUS] skipped | subscription={subscription.id} "
                    f"referred_user={subscription.user_id} referrer={referral.referrer_id} — "
                    f"not eligible (outside recurring window, past the one-time yearly/Starter "
                    f"payment, or referrer not actively subscribed)"
                )
                return None

            # Calculate commission amount
            original_amount = Decimal(str(subscription.amount))
            commission_amount = original_amount * actual_rate

            # Create commission — always store the actual rate used
            now = datetime.now(timezone.utc)
            commission = Commission(
                user_id=referral.referrer_id,
                referred_user_id=subscription.user_id,
                subscription_id=subscription.id,
                amount=commission_amount,
                original_amount=original_amount,
                currency=subscription.currency,
                commission_rate=actual_rate * 100,
                status='auto_settled' if already_settled else 'pending',
                created_at=now,
                paid_at=now if already_settled else None,
            )

            db.add(commission)
            db.flush()

            # Automated payout, no admin click, the moment the money is
            # earned — per explicit direction: "the admin does not have to
            # click to send the user the money... the moment the money
            # lands." already_settled (Flutterwave subaccount split) already
            # covers same-currency NGN charges to a referrer with a
            # Flutterwave subaccount — this covers everything else a
            # subaccount split structurally cannot: a Stripe (USD/GBP)
            # commission owed to a referrer whose only real payout method is
            # Flutterwave/NGN, converted via a live FX rate and sent as a
            # plain transfer, right here, synchronously.
            settled_now = already_settled
            payout_id = None
            if not already_settled:
                payout_id = CommissionService._attempt_immediate_payout(commission, db)
                if payout_id:
                    commission.status = 'auto_settled'
                    commission.paid_at = now
                    commission.payout_id = payout_id
                    settled_now = True
                    db.flush()

            # Update monthly summary — a settled commission (subaccount
            # split OR the immediate-payout path above) counts straight into
            # paid_commissions, not pending_commissions, since nothing is
            # owed on it (see _update_monthly_summary).
            CommissionService._update_monthly_summary(
                referral.referrer_id,
                commission_amount,
                db,
                already_settled=settled_now,
            )

            db.flush()
            # db.refresh(commission) # We can use flush + already in session

            logger.info(
                f"[BUILDER BONUS] created | subscription={subscription.id} referred_user={subscription.user_id} "
                f"referrer={referral.referrer_id} amount={commission_amount} {subscription.currency} "
                f"rate={actual_rate * 100}% status={commission.status} settled_now={settled_now} "
                f"commission_id={commission.id} payout_id={payout_id}"
            )

            # Notify referrer about builder bonus in real time
            cur = getattr(subscription, "currency", "USD") or "USD"
            bonus_message = (
                f"You earned a {cur} {commission_amount:.2f} builder bonus from a "
                f"referral's subscription payment — sent straight to your account."
                if settled_now else
                f"You earned a {cur} {commission_amount:.2f} builder bonus "
                f"from a referral's subscription payment."
            )
            logger.info(f"[BUILDER BONUS] notification sent to user={referral.referrer_id} | \"{bonus_message}\"")
            NotificationService.create_notification(
                db=db,
                user_id=referral.referrer_id,
                type=NotificationType.COMMISSION_EARNED.value,
                title="🎉 Builder Bonus Earned!",
                message=bonus_message,
                link="/dashboard/earnings",
            )

            return commission

        except Exception as e:
            logger.error(f"❌ Commission creation error: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def reverse_commission_for_subscription(subscription: "Subscriptions", reason: str, db: Session) -> None:
        """Revoke paid access and claw back any commission tied to a
        subscription that got refunded or disputed (a chargeback) —
        called from the Stripe webhook handlers for charge.refunded and
        charge.dispute.created. Before this, a refund/chargeback left
        Lavoo's own records completely unaware: the subscriber kept Pro
        access, and a referrer who'd already been auto-paid kept the
        commission, on money Lavoo no longer has.

        reason: 'refund' or 'dispute' — only affects the status string
        recorded, not the clawback logic itself.

        What this does NOT do: reach into Stripe/Flutterwave and pull
        money back out of a referrer's account — that's not something
        either provider's API lets us do unilaterally. For a commission
        already paid out, this instead records a negative Commission row
        (status='clawback', excluded from every payout-eligibility query
        elsewhere in this file — it's pure bookkeeping) so the loss is
        visible on the referrer's own earnings totals and nets against
        whatever they earn next, and alerts the admin so a human knows a
        real payout needs manual recovery.
        """
        from api.utils.sub_utils import sync_user_subscription

        subscription.status = "refunded" if reason == "refund" else "disputed"
        subscription.subscription_status = "Payment failed"
        db.flush()

        user = db.query(User).filter(User.id == subscription.user_id).first()
        if user:
            # Recomputes the user's CURRENT plan/status from their latest
            # still-valid subscription (this one no longer qualifies,
            # having just been marked refunded/disputed above) — correctly
            # leaves them on Pro if some OTHER subscription of theirs is
            # still genuinely active, instead of blindly downgrading.
            sync_user_subscription(db, user)

        commission = db.query(Commission).filter(Commission.subscription_id == subscription.id).first()
        if not commission:
            logger.info(f"[CHARGEBACK] subscription={subscription.id} {reason} — no commission was ever created for it, nothing to claw back")
            return

        if commission.status in ("pending", "approved"):
            commission.status = "reversed"
            db.flush()
            logger.info(f"[CHARGEBACK] commission={commission.id} reversed (was never paid) for subscription={subscription.id} {reason}")
            return

        if commission.status in ("paid", "auto_settled"):
            # Flip the ORIGINAL commission's status before anything else so
            # a redelivered webhook for the same refund/dispute (normal
            # at-least-once behavior, not an edge case) sees "already
            # clawed_back" here instead of still "paid"/"auto_settled" —
            # without this, a retry would fall through to this same branch
            # again and create a SECOND negative clawback row for the one
            # real refund, double-counting the loss on the referrer's
            # earnings totals.
            commission.status = "clawed_back"
            clawback = Commission(
                user_id=commission.user_id,
                referred_user_id=commission.referred_user_id,
                subscription_id=commission.subscription_id,
                amount=-commission.amount,
                currency=commission.currency,
                commission_rate=commission.commission_rate,
                status="clawback",
                created_at=datetime.now(timezone.utc),
            )
            db.add(clawback)
            db.flush()
            referrer = db.query(User).filter(User.id == commission.user_id).first()
            reason_past = "refunded" if reason == "refund" else "disputed (charged back)"
            msg = (
                f"Commission #{commission.id} ({commission.amount} {commission.currency}, already paid to "
                f"{referrer.email if referrer else commission.user_id}) is being clawed back — the underlying "
                f"subscription (id={subscription.id}) was {reason_past}. A negative commission "
                f"(#{clawback.id}, {clawback.amount} {clawback.currency}) has been recorded and will net "
                f"against this referrer's future earnings, but the original payout already left Lavoo's "
                f"account — manual recovery (contacting the referrer, adjusting a future payout) may be needed."
            )
            logger.warning(f"[CHARGEBACK] {msg}")
            CommissionService._alert_admin(f"⚠️ Commission clawback needed — subscription #{subscription.id} {reason_past}", msg)
            return

        logger.info(f"[CHARGEBACK] commission={commission.id} status={commission.status} for subscription={subscription.id} {reason} — no action needed (already {commission.status})")

    @staticmethod
    def _attempt_immediate_payout(
        commission: "Commission", db: Session, notify_admin: bool = True,
        balance_override: "Decimal | None" = None,
    ) -> "int | None":
        """Pay a freshly-created commission out immediately, no admin
        approval step, when the referrer's only usable payout method is a
        verified Flutterwave bank account — covering exactly the case a
        Flutterwave subaccount split structurally cannot: a commission in a
        currency the referrer can't be split into at charge time (a Stripe
        USD/GBP charge, when the referrer only has NGN banking), converted
        via a live FX rate and sent as a plain transfer instead.

        Returns the new Payout's id on a confirmed successful transfer,
        None on anything else (no Flutterwave account configured yet, rate
        lookup failed, transfer failed) — the commission is left exactly as
        the caller already has it (status='pending') for the existing
        manual approve/payout flow to pick up later, same as before this
        existed. Never raises: a payout failure here must never take down
        the commission record it's trying to settle, let alone the
        subscription payment that's already been charged for real.

        balance_override: when a caller is settling several commissions in
        one batch (settle_pending_flutterwave_commissions), it tracks one
        running balance across the whole batch and passes it here instead
        of letting each commission re-query Flutterwave independently.
        Confirmed in production this isn't optional: two commissions
        processed 5 seconds apart each saw the same live "available"
        balance (neither transfer had settled on Flutterwave's side yet),
        both passed their own fresh check, and Flutterwave's own ledger
        could only honor one — the other came back a real, visible
        "Insufficient funds" failure on Flutterwave's dashboard.
        """
        logger.info(
            f"[BUILDER BONUS] immediate payout check | commission={commission.id} "
            f"referrer={commission.user_id} amount={commission.amount} {commission.currency}"
        )
        try:
            from database.pg_models import Payout, PayoutAccount
            from subscriptions.flutterwave_split import get_flutterwave_fx_rate
            from subscriptions.payout_service import PayoutService

            payout_account = (
                db.query(PayoutAccount)
                .filter(
                    PayoutAccount.user_id == commission.user_id,
                    PayoutAccount.payment_method == "flutterwave",
                    PayoutAccount.bank_name.isnot(None),
                    PayoutAccount.account_number.isnot(None),
                    PayoutAccount.bank_code.isnot(None),
                )
                .order_by(PayoutAccount.updated_at.desc().nullslast(), PayoutAccount.created_at.desc())
                .first()
            )
            if not payout_account:
                # No Flutterwave bank account — the referrer may be paid
                # through Stripe Connect instead (e.g. a UK referrer whose
                # referred user paid in NGN via Flutterwave). Previously this
                # direction simply didn't exist and the commission sat
                # 'pending' until someone paid it by hand.
                return CommissionService._attempt_stripe_immediate_payout(commission, db, notify_admin=notify_admin)

            logger.info(
                f"[BUILDER BONUS] immediate payout method found | commission={commission.id} "
                f"payout_account={payout_account.id} bank={payout_account.bank_name} "
                f"account=***{payout_account.account_number[-4:]}"
            )

            commission_currency = (commission.currency or "USD").upper()
            commission_amount = Decimal(str(commission.amount))
            fx_rate = None

            if commission_currency == "NGN":
                payout_amount = commission_amount
                logger.info(f"[BUILDER BONUS] no conversion needed | commission={commission.id} already NGN")
            else:
                logger.info(f"[BUILDER BONUS] fetching FX rate | commission={commission.id} {commission_currency}->NGN")
                fx_rate = get_flutterwave_fx_rate(commission_currency, "NGN")
                if fx_rate is None:
                    logger.warning(
                        f"[BUILDER BONUS] Could not fetch {commission_currency}->NGN rate for "
                        f"commission {commission.id} — leaving pending for manual payout"
                    )
                    return None
                payout_amount = (commission_amount * fx_rate).quantize(Decimal("0.01"))
                logger.info(
                    f"[BUILDER BONUS] FX rate fetched | commission={commission.id} rate={fx_rate} "
                    f"{commission_amount} {commission_currency} -> {payout_amount} NGN"
                )

            # Check the live Flutterwave balance before creating anything —
            # same pattern as the Stripe path above. Without this, an
            # unfunded cycle would create a Payout row, have
            # process_flutterwave_payout's own pre-flight check reject it,
            # and mark it 'failed' — a messier trail than simply not
            # attempting yet, and (via the broad except below) an admin
            # alert on every single retry cycle instead of a rate-limited one.
            if balance_override is not None:
                available_amount = balance_override
            else:
                available = PayoutService.get_platform_flutterwave_available("NGN")
                available_amount = available["available"] if available is not None else None

            if available_amount is None or available_amount < payout_amount:
                msg = (
                    f"Commission #{commission.id} ({payout_amount} NGN"
                    + (f", converted from {commission_amount} {commission_currency}" if fx_rate else "")
                    + f") is waiting: the platform's available Flutterwave NGN balance is "
                    + (f"{available_amount}" if available_amount is not None else "unknown (balance check failed)")
                    + ". It will be paid automatically once funded."
                )
                logger.warning(f"[BUILDER BONUS] flutterwave payout waiting for balance | {msg}")
                if notify_admin:
                    CommissionService._alert_admin(f"⚠️ Referral payout waiting for Flutterwave balance — commission #{commission.id}", msg)
                return None

            # Reuse the commission's own prior failed attempt, if it has one,
            # instead of creating an unrelated new Payout row. Previously a
            # retry always inserted a fresh row with no link back to the
            # attempt that failed — two rows for what is really one payout's
            # history, unlike a dashboard retry of an existing transfer
            # (reconcile_flutterwave_payouts), which already updates the
            # same row in place. commission.payout_id is set below on EVERY
            # attempt now (success or failure) specifically so this lookup
            # has something to find next time.
            existing_payout = (
                db.query(Payout).filter(Payout.id == commission.payout_id).first()
                if commission.payout_id else None
            )
            if existing_payout is not None and existing_payout.status == "failed":
                payout = existing_payout
                payout.amount = payout_amount
                payout.currency = "NGN"
                payout.status = "pending"
                payout.provider = "flutterwave"
                payout.payment_method = "flutterwave"
                payout.recipient_name = payout_account.account_name
                payout.account_details = (
                    f"Bank: {payout_account.bank_name}, "
                    f"Account: ****{payout_account.account_number[-4:] if payout_account.account_number else 'N/A'}"
                )
                payout.original_currency = commission_currency if commission_currency != "NGN" else None
                payout.original_amount = commission_amount if commission_currency != "NGN" else None
                payout.fx_rate = fx_rate
                payout.failure_reason = None
                payout.requested_at = datetime.now(timezone.utc)
                logger.info(f"[BUILDER BONUS] reusing failed payout {payout.id} for retry | commission={commission.id}")
            else:
                payout = Payout(
                    user_id=commission.user_id,
                    amount=payout_amount,
                    currency="NGN",
                    status="pending",
                    provider="flutterwave",
                    payment_method="flutterwave",
                    recipient_name=payout_account.account_name,
                    account_details=(
                        f"Bank: {payout_account.bank_name}, "
                        f"Account: ****{payout_account.account_number[-4:] if payout_account.account_number else 'N/A'}"
                    ),
                    original_currency=commission_currency if commission_currency != "NGN" else None,
                    original_amount=commission_amount if commission_currency != "NGN" else None,
                    fx_rate=fx_rate,
                    requested_at=datetime.now(timezone.utc),
                )
                db.add(payout)
            db.flush()
            commission.payout_id = payout.id

            PayoutService.process_flutterwave_payout(payout, db, manage_transaction=False)
            # process_flutterwave_payout sets payout.status='processing' on a
            # confirmed-accepted transfer request and commits internally; any
            # failure raises, caught below. Flutterwave transfers are async
            # (webhook confirms final completion), so 'processing' here means
            # "successfully handed to Flutterwave," which is the correct
            # point to mark this commission auto_settled — same trust
            # boundary the existing admin-approved payout flow already uses.
            logger.info(
                f"[BUILDER BONUS] immediate payout initiated | commission={commission.id} "
                f"payout={payout.id} amount={payout_amount} NGN "
                f"(from {commission_amount} {commission_currency}"
                + (f" @ rate {fx_rate}" if fx_rate else "") + ")"
            )
            return payout.id

        except Exception as e:
            logger.error(f"[BUILDER BONUS] Immediate payout attempt failed for commission {commission.id}: {e}", exc_info=True)
            # Commit here, not just flush: the caller (settle_pending_commission)
            # rolls back on a None return, which would otherwise undo the
            # failed Payout row and commission.payout_id link this attempt
            # just set up — exactly the state a retry needs to reconcile
            # against the SAME payout instead of creating an unrelated new
            # one. A commit failing here is itself best-effort; it must not
            # turn an already-handled payout failure into a crash.
            try:
                db.commit()
            except Exception as commit_err:
                logger.error(f"[BUILDER BONUS] could not persist failed payout state for commission {commission.id}: {commit_err}")
                db.rollback()
            # Only a log line before this — a real transfer failure (bad IP
            # whitelist, insufficient balance, bad account) went completely
            # unnoticed until someone happened to dig through logs (which is
            # exactly how this class of incident was found). The commission
            # itself is safe either way (falls back to the manual payout
            # queue, per this function's contract), but a human should know
            # promptly rather than discover it by accident. Best-effort and
            # isolated in its own try/except: a failure to send this alert
            # must not turn an already-handled payout failure into a crash.
            # Gated on notify_admin: the periodic retry job passes False and
            # sends its own rate-limited (6-hour) summary alert instead — an
            # unhandled error here (bad bank details, Flutterwave API down)
            # would otherwise re-email on every 10-minute retry cycle for as
            # long as the underlying cause persists.
            if notify_admin:
                try:
                    admin_email = os.getenv("ADMIN_ALERT_EMAIL", os.getenv("SUPPORT_EMAIL", "support@lavoo.io"))
                    email_service._send_email(
                        to_email=admin_email,
                        to_name="Lavoo Admin",
                        subject=f"⚠️ Immediate Flutterwave payout failed — commission #{commission.id}",
                        html_content=(
                            f"<p>An automatic immediate payout attempt failed for "
                            f"commission #{commission.id} (referrer user_id={commission.user_id}, "
                            f"amount={commission.amount} {commission.currency}).</p>"
                            f"<p>Error: {e}</p>"
                            f"<p>The commission is safe and has fallen back to the manual "
                            f"payout queue — nothing is lost — but this may indicate a "
                            f"systemic issue (e.g. the server's IP no longer whitelisted "
                            f"in the Flutterwave dashboard) affecting every referrer's "
                            f"immediate payouts, not just this one.</p>"
                        ),
                        text_content=(
                            f"Immediate Flutterwave payout failed for commission #{commission.id} "
                            f"(referrer user_id={commission.user_id}, amount={commission.amount} "
                            f"{commission.currency}). Error: {e}. The commission itself is safe "
                            f"(manual payout queue), but this may be a systemic issue."
                        ),
                    )
                except Exception as alert_err:
                    logger.error(f"[BUILDER BONUS] Failed to send payout-failure alert email: {alert_err}")
            return None

    @staticmethod
    def _alert_admin(subject: str, body: str) -> None:
        """Best-effort email to the admin; never raises."""
        try:
            admin_email = os.getenv("ADMIN_ALERT_EMAIL", os.getenv("SUPPORT_EMAIL", "support@lavoo.io"))
            email_service._send_email(
                to_email=admin_email, to_name="Lavoo Admin",
                subject=subject, html_content=f"<p>{body}</p>", text_content=body,
            )
        except Exception as alert_err:
            logger.error(f"[BUILDER BONUS] Failed to send admin alert '{subject}': {alert_err}")

    @staticmethod
    def _attempt_stripe_immediate_payout(commission: "Commission", db: Session, notify_admin: bool = True) -> "int | None":
        """
        Pay a commission to a referrer who is paid through Stripe Connect.
        Example: a UK referrer whose referred user paid in Naira.

        Steps: convert the amount to the referrer's Stripe currency, check we
        have enough Stripe balance, then send one Stripe transfer.

        Returns the payout id if it worked, or None if not. It never raises.
        On None the commission stays 'pending', and the retry job tries it
        again later (for example once the Stripe balance has been topped up).
        """
        try:
            from sqlalchemy import text
            import stripe
            from database.pg_models import Payout, PayoutAccount
            from subscriptions.flutterwave_split import get_flutterwave_fx_rate
            from subscriptions.payout_service import PayoutService

            stripe_account = (
                db.query(PayoutAccount)
                .filter(
                    PayoutAccount.user_id == commission.user_id,
                    PayoutAccount.stripe_account_id.isnot(None),
                    PayoutAccount.is_verified.is_(True),
                )
                .first()
            )
            if not stripe_account:
                logger.info(
                    f"[BUILDER BONUS] immediate payout skipped | commission={commission.id} "
                    f"referrer={commission.user_id} has neither a Flutterwave bank account nor a "
                    f"verified Stripe Connect account — leaving pending for manual payout"
                )
                return None

            # LOCK: only one process may pay this commission at a time.
            # Two things can try to pay the same commission together, for
            # example a web request and the 10-minute retry job (or two copies
            # of the server). The lock makes the second one wait. By the time
            # it gets its turn, the first has finished and the commission is
            # already paid, so the second sees that below and stops.
            # 7302 = our "commission payout" lock group. The commission id
            # picks the exact lock inside that group. The lock frees itself
            # when this database transaction ends.
            db.execute(text("SELECT pg_advisory_xact_lock(7302, :cid)"), {"cid": int(commission.id)})
            # Reload the commission: another process may have paid it while we waited.
            db.refresh(commission)
            if commission.payout_id is not None or (commission.status or "").lower() != "pending":
                logger.info(f"[BUILDER BONUS] stripe payout skipped | commission={commission.id} already handled (status={commission.status})")
                return None

            account = stripe.Account.retrieve(stripe_account.stripe_account_id, api_key=os.getenv("STRIPE_SECRET_KEY"))
            account = account.to_dict() if hasattr(account, "to_dict") else dict(account)
            transfers_active = (account.get("capabilities") or {}).get("transfers") == "active"
            if not transfers_active:
                logger.warning(
                    f"[BUILDER BONUS] stripe payout skipped | commission={commission.id} connected account "
                    f"{stripe_account.stripe_account_id} cannot receive transfers yet — leaving pending"
                )
                return None
            target_currency = (account.get("default_currency") or "gbp").upper()

            commission_currency = (commission.currency or "USD").upper()
            commission_amount = Decimal(str(commission.amount))
            fx_rate = None
            if commission_currency == target_currency:
                payout_amount = commission_amount
            else:
                fx_rate = get_flutterwave_fx_rate(commission_currency, target_currency)
                if fx_rate is None:
                    logger.warning(
                        f"[BUILDER BONUS] Could not fetch {commission_currency}->{target_currency} rate for "
                        f"commission {commission.id} — leaving pending"
                    )
                    return None
                payout_amount = (commission_amount * fx_rate).quantize(Decimal("0.01"))
            logger.info(
                f"[BUILDER BONUS] stripe payout amount | commission={commission.id} "
                f"{commission_amount} {commission_currency} -> {payout_amount} {target_currency}"
                + (f" @ {fx_rate}" if fx_rate else "")
            )

            amount_minor = int(payout_amount * 100)
            if amount_minor < 1:
                logger.warning(f"[BUILDER BONUS] stripe payout skipped | commission={commission.id} converts to less than 0.01 {target_currency}")
                return None

            # Ask Stripe if this commission was already paid, before sending.
            # Our own database can be behind Stripe (for example the money was
            # sent but saving it here failed), so we trust Stripe's record.
            transfer_group = f"LAVOO-COMMISSION-{commission.id}"
            prior_transfer = None      # a transfer that is still in place
            reversed_transfer = None   # a transfer Stripe took back
            try:
                found = stripe.Transfer.list(
                    destination=stripe_account.stripe_account_id, transfer_group=transfer_group,
                    limit=5, api_key=os.getenv("STRIPE_SECRET_KEY"),
                )
                for t in found.data:
                    t = t.to_dict() if hasattr(t, "to_dict") else dict(t)
                    if t.get("reversed"):
                        reversed_transfer = reversed_transfer or t
                    else:
                        prior_transfer = t
                        break
            except Exception as lookup_err:
                # If we can't check, we can't be sure it wasn't paid, so don't send.
                logger.warning(f"[BUILDER BONUS] could not check Stripe for an existing transfer for commission {commission.id}: {lookup_err} — leaving pending")
                return None

            if reversed_transfer and not prior_transfer:
                # It was paid once and then taken back (by a person, usually on
                # purpose). Do NOT send it again automatically. A human decides.
                logger.warning(
                    f"[BUILDER BONUS] commission {commission.id} was already sent (transfer "
                    f"{reversed_transfer.get('id')}) and Stripe reversed it — not sending again. "
                    f"Review it and pay manually if it is still owed."
                )
                return None

            available = None if prior_transfer else PayoutService.get_platform_stripe_available(target_currency)
            if available is not None and available < amount_minor:
                msg = (
                    f"Commission #{commission.id} ({payout_amount} {target_currency}) is waiting: the platform's "
                    f"available Stripe {target_currency} balance is {available / 100:.2f}. Add funds to the Stripe "
                    f"balance (Dashboard > Balances > Add to balance) or wait for pending funds to settle; it will "
                    f"then be paid automatically."
                )
                logger.warning(f"[BUILDER BONUS] stripe payout waiting for balance | {msg}")
                if notify_admin:
                    CommissionService._alert_admin(f"⚠️ Referral payout waiting for Stripe balance — commission #{commission.id}", msg)
                return None

            # Reuse the commission's own prior failed attempt, if it has one,
            # rather than creating an unrelated new Payout row — same
            # reasoning as the Flutterwave path above: a retry should
            # reconcile against the SAME payout, not look like a second,
            # disconnected one.
            existing_payout = (
                db.query(Payout).filter(Payout.id == commission.payout_id).first()
                if commission.payout_id else None
            )
            if existing_payout is not None and existing_payout.status == "failed":
                payout = existing_payout
                payout.status = "pending"
                payout.failure_reason = None
                payout.requested_at = datetime.now(timezone.utc)
            else:
                payout = Payout(user_id=commission.user_id, status="pending", requested_at=datetime.now(timezone.utc))
                db.add(payout)
            payout.amount = payout_amount
            payout.currency = target_currency
            payout.provider = "stripe"
            payout.payment_method = "stripe"
            payout.recipient_email = None
            payout.account_details = f"Stripe Connect: {stripe_account.stripe_account_id}"
            payout.original_currency = commission_currency if commission_currency != target_currency else None
            payout.original_amount = commission_amount if commission_currency != target_currency else None
            payout.fx_rate = fx_rate
            if prior_transfer:
                # Record what Stripe actually sent, not what we'd compute today.
                payout.amount = (Decimal(str(prior_transfer.get("amount", amount_minor))) / 100).quantize(Decimal("0.01"))
                payout.currency = str(prior_transfer.get("currency") or target_currency).upper()
            db.flush()
            commission.payout_id = payout.id

            PayoutService.process_stripe_transfer_payout(
                payout, db, manage_transaction=False,
                transfer_group=transfer_group,
                idempotency_key=f"lavoo-commission-{commission.id}",
                existing_transfer=prior_transfer,
            )

            try:
                NotificationService.create_notification(
                    db=db, user_id=commission.user_id,
                    type=NotificationType.PAYOUT_COMPLETED.value,
                    title="💸 Builder Bonus sent",
                    message=(
                        f"{payout_amount} {target_currency} from your referral was sent to your Stripe account. "
                        f"Stripe will pay it out to your bank on your account's payout schedule."
                    ),
                    link="/l/earnings",
                )
            except Exception as notif_err:
                logger.warning(f"[BUILDER BONUS] payout notification failed (payout itself succeeded): {notif_err}")

            logger.info(f"[BUILDER BONUS] stripe payout complete | commission={commission.id} payout={payout.id}")
            return payout.id

        except Exception as e:
            logger.error(f"[BUILDER BONUS] Stripe payout attempt failed for commission {commission.id}: {e}", exc_info=True)
            # Commit here, not just flush: the caller (settle_pending_commission)
            # rolls back on a None return, which would otherwise undo the
            # failed Payout row and commission.payout_id link this attempt
            # just set up — see the matching comment in
            # _attempt_immediate_payout's except block.
            try:
                db.commit()
            except Exception as commit_err:
                logger.error(f"[BUILDER BONUS] could not persist failed Stripe payout state for commission {commission.id}: {commit_err}")
                db.rollback()
            if notify_admin:
                CommissionService._alert_admin(
                    f"⚠️ Referral payout via Stripe failed — commission #{commission.id}",
                    f"Commission #{commission.id} (referrer user_id={commission.user_id}, {commission.amount} "
                    f"{commission.currency}) could not be sent via Stripe: {e}. It is still pending and will be "
                    f"retried automatically.",
                )
            return None

    @staticmethod
    def settle_pending_commission(
        commission: "Commission", db: Session, notify_admin: bool = True,
        balance_override: "Decimal | None" = None,
    ) -> "int | None":
        """
        Pay an EXISTING pending commission now (through whichever route the
        referrer has) and do the bookkeeping the create-time path does
        implicitly: link it to the payout, mark it auto_settled, and move it
        from pending to paid in the monthly summary (which had counted it as
        pending when it was created). Commits on success, rolls back otherwise.
        Returns the payout id or None.

        balance_override is forwarded to _attempt_immediate_payout — see its
        docstring. Irrelevant (and harmless) when the referrer has no
        Flutterwave account, since that path is never reached.
        """
        from database.pg_models import Payout
        from subscriptions.payout_service import PayoutService
        try:
            payout_id = CommissionService._attempt_immediate_payout(
                commission, db, notify_admin=notify_admin, balance_override=balance_override,
            )
            if not payout_id:
                db.rollback()
                return None
            commission.status = 'auto_settled'
            commission.paid_at = datetime.now(timezone.utc)
            commission.payout_id = payout_id
            db.flush()  # session has autoflush off; the summary update reads by payout_id
            PayoutService._update_summary_on_payout(db.get(Payout, payout_id), db)
            db.commit()
            return payout_id
        except Exception as e:
            db.rollback()
            logger.error(f"[BUILDER BONUS] settle_pending_commission failed for {commission.id}: {e}", exc_info=True)
            return None

    @staticmethod
    def settle_pending_stripe_commissions(db: Session, lookback_days: int = 30, limit: int = 25) -> dict:
        """
        Retry commissions that are waiting to be paid through Stripe Connect —
        typically because the platform's Stripe balance was empty when they
        were earned. Runs from a background job; with an empty balance a cycle
        makes no Stripe transfer and creates no payout rows (the balance is
        checked before anything is created), so it is safe to run often.
        """
        from database.pg_models import PayoutAccount, Payout
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        rows = (
            db.query(Commission)
            .join(PayoutAccount, PayoutAccount.user_id == Commission.user_id)
            .outerjoin(Payout, Payout.id == Commission.payout_id)
            .filter(
                Commission.status == 'pending',
                # A prior attempt that failed still has payout_id set (so the
                # retry reconciles against that SAME Payout row instead of
                # creating an unrelated new one) — only a payout_id pointing
                # at something OTHER than a failed attempt means this
                # commission is genuinely spoken for already.
                (Commission.payout_id.is_(None)) | (Payout.status == 'failed'),
                Commission.created_at >= cutoff,
                PayoutAccount.stripe_account_id.isnot(None),
                PayoutAccount.is_verified.is_(True),
                # leave anyone with a usable Flutterwave bank account to that route
                (PayoutAccount.bank_code.is_(None)) | (PayoutAccount.payment_method != 'flutterwave'),
            )
            .order_by(Commission.created_at)
            .limit(limit)
            .all()
        )
        counts = {"checked": len(rows), "settled": 0, "waiting": 0}
        for commission in rows:
            cid = commission.id
            if CommissionService.settle_pending_commission(commission, db, notify_admin=False):
                counts["settled"] += 1
                logger.info(f"[settle-job] commission {cid} paid via Stripe")
            else:
                counts["waiting"] += 1

        # One reminder per 6 hours at most — the job runs every 10 minutes and
        # a persistently empty balance must not become an email every cycle.
        if counts["waiting"]:
            now = datetime.now(timezone.utc)
            last = CommissionService._last_waiting_alert
            if last is None or now - last > timedelta(hours=6):
                CommissionService._last_waiting_alert = now
                CommissionService._alert_admin(
                    f"⏳ {counts['waiting']} referral payout(s) waiting to be sent via Stripe",
                    f"{counts['waiting']} pending commission(s) could not be paid to Stripe-connected referrers. "
                    f"Most often the available Stripe balance is too low (Dashboard > Balances > Add to balance). "
                    f"They are retried every 10 minutes and paid automatically once the cause clears. "
                    f"One exception: a transfer that Stripe reversed is never re-sent automatically, so it "
                    f"needs a manual decision. The [BUILDER BONUS] log lines say which case each one is.",
                )
        return counts

    @staticmethod
    def settle_pending_flutterwave_commissions(db: Session, lookback_days: int = 30, limit: int = 25) -> dict:
        """
        The Flutterwave-side counterpart to settle_pending_stripe_commissions
        above — retries commissions waiting to be paid through a referrer's
        Flutterwave bank account (typically a USD/GBP commission converted to
        NGN via live FX rate), usually because the platform's Flutterwave
        wallet was empty when they were earned. Same shape, same safety
        properties: checks the balance before creating anything, so an
        unfunded cycle makes no transfer and leaves no failed rows behind.

        Tracks ONE running balance across the whole batch rather than
        letting each commission re-query Flutterwave independently —
        confirmed in production that two commissions processed seconds
        apart can both see the same live "available" balance (neither
        transfer has settled on Flutterwave's side yet), both pass their
        own fresh check, and Flutterwave's own ledger can only honor one.
        """
        from database.pg_models import PayoutAccount, Payout
        from subscriptions.payout_service import PayoutService
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        rows = (
            db.query(Commission)
            .join(PayoutAccount, PayoutAccount.user_id == Commission.user_id)
            .outerjoin(Payout, Payout.id == Commission.payout_id)
            .filter(
                Commission.status == 'pending',
                # Same reasoning as settle_pending_stripe_commissions above:
                # a prior failed attempt keeps commission.payout_id set (so
                # the retry reconciles against that SAME row) — only a
                # payout_id pointing at something other than a failed
                # attempt means this one is genuinely already spoken for.
                (Commission.payout_id.is_(None)) | (Payout.status == 'failed'),
                Commission.created_at >= cutoff,
                PayoutAccount.payment_method == 'flutterwave',
                PayoutAccount.bank_name.isnot(None),
                PayoutAccount.account_number.isnot(None),
                PayoutAccount.bank_code.isnot(None),
            )
            .order_by(Commission.created_at)
            .limit(limit)
            .all()
        )
        counts = {"checked": len(rows), "settled": 0, "waiting": 0}
        if rows:
            available = PayoutService.get_platform_flutterwave_available("NGN")
            remaining = available["available"] if available is not None else Decimal("0")
        for commission in rows:
            cid = commission.id
            payout_id = CommissionService.settle_pending_commission(
                commission, db, notify_admin=False, balance_override=remaining,
            )
            if payout_id:
                counts["settled"] += 1
                sent = db.get(Payout, payout_id)
                remaining -= Decimal(str(sent.amount)) if sent else Decimal("0")
                logger.info(f"[settle-job] commission {cid} paid via Flutterwave | remaining_budget={remaining}")
            else:
                counts["waiting"] += 1

        # Same 6-hour reminder cadence as the Stripe job, kept as a separate
        # timestamp so a quiet Flutterwave wallet and a quiet Stripe balance
        # don't suppress each other's alerts.
        if counts["waiting"]:
            now = datetime.now(timezone.utc)
            last = CommissionService._last_waiting_alert_flutterwave
            if last is None or now - last > timedelta(hours=6):
                CommissionService._last_waiting_alert_flutterwave = now
                CommissionService._alert_admin(
                    f"⏳ {counts['waiting']} referral payout(s) waiting to be sent via Flutterwave",
                    f"{counts['waiting']} pending commission(s) could not be paid to referrers whose only "
                    f"payout method is a Flutterwave bank account. Most often the live Flutterwave NGN "
                    f"balance is too low — check the admin Revenue page's Platform Balance card. "
                    f"They are retried every 10 minutes and paid automatically once funded. The "
                    f"[BUILDER BONUS] log lines say what each one is waiting on.",
                )
        return counts

    @staticmethod
    def _update_monthly_summary(user_id: int, amount: Decimal, db: Session, already_settled: bool = False):
        """Update or create monthly commission summary.

        already_settled routes `amount` into paid_commissions instead of
        pending_commissions — a Flutterwave-split commission has nothing
        owed on it, so it must not appear as payout-requestable balance.
        """
        now = datetime.now(timezone.utc)

        summary = db.query(CommissionSummary).filter(
            CommissionSummary.user_id == user_id,
            CommissionSummary.year == now.year,
            CommissionSummary.month == now.month
        ).first()

        if summary:
            summary.total_commissions += amount
            if already_settled:
                summary.paid_commissions += amount
            else:
                summary.pending_commissions += amount
            summary.commission_count += 1
            summary.updated_at = now
        else:
            summary = CommissionSummary(
                user_id=user_id,
                year=now.year,
                month=now.month,
                total_commissions=amount,
                pending_commissions=Decimal("0.00") if already_settled else amount,
                paid_commissions=amount if already_settled else Decimal("0.00"),
                commission_count=1,
                currency='USD'
            )
            db.add(summary)
    
    @staticmethod
    def approve_commission(commission_id: int, db: Session):
        """Approve a pending commission"""
        commission = db.query(Commission).filter(
            Commission.id == commission_id
        ).first()
        
        if not commission:
            raise ValueError(f"Commission {commission_id} not found")
        
        if commission.status != 'pending':
            raise ValueError(f"Commission is not pending (status: {commission.status})")
        
        commission.status = 'approved'
        commission.approved_at = datetime.now(timezone.utc)
        
        # Update summary
        now = datetime.now(timezone.utc)
        summary = db.query(CommissionSummary).filter(
            CommissionSummary.user_id == commission.user_id,
            CommissionSummary.year == now.year,
            CommissionSummary.month == now.month
        ).first()
        
        if summary:
            summary.pending_commissions -= commission.amount
            # Note: Not moved to paid yet, that happens on actual payout
        
        db.flush()
        # db.refresh(commission)
        
        logger.info(f"✅ Commission {commission_id} approved")
        return commission
    
    @staticmethod
    def auto_approve_commissions(db: Session, days_old: int = 0):
        """
        Auto-approve commissions that are X days old
        Useful for automated approval after verification period
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        commissions = db.query(Commission).filter(
            Commission.status == 'pending',
            Commission.created_at <= cutoff_date
        ).all()
        
        count = 0
        for commission in commissions:
            commission.status = 'approved'
            commission.approved_at = datetime.now(timezone.utc)
            count += 1
        
        db.flush()
        
        logger.info(f"✅ Auto-approved {count} commissions")
        return count
    
    @staticmethod
    def get_user_earnings(user_id: int, db: Session):
        """Get comprehensive earnings data for a user, broken down by
        currency — summing every status across every currency into one
        number and hardcoding "currency": "USD" regardless of what was
        actually summed (the previous version) blends NGN/USD/GBP
        commissions together and mislabels the result whenever a referrer
        has commissions in more than one currency."""

        def sum_by_currency(*filters):
            rows = db.query(
                Commission.currency,
                func.coalesce(func.sum(Commission.amount), 0)
            ).filter(Commission.user_id == user_id, *filters).group_by(Commission.currency).all()
            return {(row[0] or 'USD'): float(row[1] or 0) for row in rows}

        total_by_ccy = sum_by_currency()
        count_by_ccy = {
            (row[0] or 'USD'): row[1]
            for row in db.query(Commission.currency, func.count(Commission.id))
                .filter(Commission.user_id == user_id).group_by(Commission.currency).all()
        }
        available_by_ccy = sum_by_currency(Commission.status == 'approved', Commission.payout_id.is_(None))
        pending_by_ccy = sum_by_currency(Commission.status == 'pending')
        paid_by_ccy = sum_by_currency(Commission.status.in_(('paid', 'auto_settled')))

        return {
            "total_earned_by_currency": total_by_ccy,
            "commission_count_by_currency": count_by_ccy,
            "available_for_payout_by_currency": available_by_ccy,
            "pending_approval_by_currency": pending_by_ccy,
            "already_paid_by_currency": paid_by_ccy,
        }