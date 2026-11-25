"""
Saved cards and automatic renewal: only with the customer's say-so.

THE RULE
  A card is kept, and a plan renewed automatically, ONLY when the customer
  ticked "Save my card and renew automatically" on their latest payment.
  That choice is stored on the user as `auto_renew`. Their latest payment's
  choice always wins: ticking it turns renewal on, leaving it unticked turns
  it off and forgets any card saved before.

WHERE IT IS USED
  - Stripe checkouts (subscriptions/stripe.py) and Flutterwave verification
    (subscriptions/flutterwave.py) call remember_card_choice() after a payment.
  - Lavoo's daily expiry job (api/main.py) renews only users with
    auto_renew on.
  - sweep_unconsented() runs with that job: anyone with auto_renew off who
    still has a card on file (cards saved before this rule existed) has it
    forgotten, the card removed from Stripe, and every Stripe subscription
    set to end at the end of the period already paid for, so Stripe can't
    renew it by itself either.
  - stop_old_price_renewals() runs with it too: a Stripe subscription
    renews BY ITSELF at the price it was created on. One created on a price
    Lavoo no longer sells (e.g. an old $1 price) would keep charging that
    price forever, so it is set to end at the end of its paid period and
    the admin is told. The customer subscribes again at today's price.

Nothing here charges anyone.
"""
import logging
import os
from datetime import UTC, datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from database.pg_models import User

logger = logging.getLogger(__name__)

# The card details kept on the user while a card is saved.
_CARD_FIELDS = ("stripe_payment_method_id", "card_last4", "card_brand", "card_exp_month",
                "card_exp_year", "card_saved_at", "flutterwave_card_token")


def _forget_card_fields(user: User) -> None:
    """Clear every saved-card detail on the user (nothing is sent anywhere)."""
    for name in _CARD_FIELDS:
        if hasattr(user, name):
            setattr(user, name, None)


def remember_card_choice(user: User, save_card: bool, *, stripe_payment_method=None,
                         stripe_payment_method_id: str | None = None, flutterwave_card: dict | None = None) -> None:
    """Record the customer's choice from the payment they just made.

    save_card=True: keep the card (a Stripe PaymentMethod, or Flutterwave's
    card info with its token) and turn automatic renewal on.
    save_card=False: forget any saved card and turn automatic renewal off.
    The caller commits."""
    # 1. Not saving: forget everything and stop renewals.
    if not save_card:
        _forget_card_fields(user)
        user.auto_renew = False
        # The daily sweep checks Stripe for this customer again.
        user.renewals_stopped_at = None
        logger.info("[card-consent] user %s did not save their card: auto-renewal off", user.id)
        return
    # 2. Saving a Stripe card.
    if stripe_payment_method_id:
        user.stripe_payment_method_id = stripe_payment_method_id
        card = getattr(stripe_payment_method, "card", None)
        if card is not None:
            user.card_last4, user.card_brand = card.last4, card.brand
            user.card_exp_month, user.card_exp_year = card.exp_month, card.exp_year
        user.card_saved_at = datetime.now(UTC)
    # 3. Saving a Flutterwave card (its token is what renewals charge).
    if flutterwave_card and flutterwave_card.get("token"):
        user.flutterwave_card_token = flutterwave_card["token"]
        if flutterwave_card.get("last_4digits"):
            user.card_last4 = flutterwave_card["last_4digits"]
        if flutterwave_card.get("type"):
            user.card_brand = str(flutterwave_card["type"]).title()
        user.card_saved_at = datetime.now(UTC)
    # 4. Renewal on.
    user.auto_renew = True
    logger.info("[card-consent] user %s saved their card: auto-renewal on", user.id)


def stop_stripe_renewals(user: User) -> int | None:
    """Set every live Stripe subscription of this customer to end at the end
    of the period already paid for, and remove their saved cards from Stripe.
    Returns how many subscriptions were changed, or None if Stripe couldn't
    be reached (tried again next day). Never raises."""
    customer_id = getattr(user, "stripe_customer_id", None)
    if not customer_id:
        return 0
    if not os.getenv("STRIPE_SECRET_KEY"):
        return None
    changed = 0
    try:
        import stripe
        key = os.getenv("STRIPE_SECRET_KEY")
        # 1. Each subscription that would renew by itself.
        for status in ("active", "trialing", "past_due"):
            for sub in stripe.Subscription.list(customer=customer_id, status=status, limit=100, api_key=key).auto_paging_iter():
                if not sub.get("cancel_at_period_end"):
                    stripe.Subscription.modify(sub["id"], cancel_at_period_end=True, api_key=key)
                    changed += 1
        # 2. The saved cards.
        for pm in stripe.PaymentMethod.list(customer=customer_id, type="card", limit=100, api_key=key).auto_paging_iter():
            try:
                stripe.PaymentMethod.detach(pm["id"], api_key=key)
            except Exception as exc:
                logger.warning("[card-consent] could not remove card %s: %s", pm["id"], exc)
    except Exception as exc:
        logger.error("[card-consent] could not stop Stripe renewals for user %s: %s", user.id, exc)
        return None
    return changed


def sweep_unconsented(db: Session) -> dict:
    """For everyone with auto-renewal off who still has a card on file, or a
    Stripe customer not checked yet: stop Stripe's own renewals, remove the
    card from Stripe and forget it here. Each Stripe customer is checked once
    (renewals_stopped_at), again only after they turn renewal off on a later
    payment. Returns {"users": n, "stripe_subscriptions": n}. Run daily."""
    # 1. Who still has a card on file, or a Stripe customer not yet checked.
    users = db.query(User).filter(
        User.auto_renew.is_(False),
        or_(User.stripe_payment_method_id.isnot(None), User.flutterwave_card_token.isnot(None),
            (User.stripe_customer_id.isnot(None)) & (User.renewals_stopped_at.is_(None))),
    ).all()
    changed = 0
    for user in users:
        # 2. Stripe first (so nothing renews), then forget the card here.
        stopped = stop_stripe_renewals(user)
        _forget_card_fields(user)
        # 3. Marked done only when Stripe answered (otherwise tried again tomorrow).
        if stopped is not None:
            changed += stopped
            user.renewals_stopped_at = datetime.now(UTC)
    db.commit()
    if users:
        logger.info("[card-consent] forgot %s unconsented card(s); %s Stripe subscription(s) set to end",
                    len(users), changed)
    return {"users": len(users), "stripe_subscriptions": changed}


def stop_old_price_renewals(db: Session) -> int:
    """Stripe charges a renewal at the price ON the subscription, not at
    Lavoo's current price. For every customer with auto-renewal on, any live
    Stripe subscription on a price that isn't in today's price list
    (founding.identify_price_id knows them all) is set to end at the end of
    the period already paid for, and the admin is emailed. Returns how many
    were stopped. Never raises. Run daily."""
    key = os.getenv("STRIPE_SECRET_KEY")
    if not key:
        return 0
    import stripe

    from subscriptions.founding import describe_stripe_subscription
    stopped: list[str] = []
    # 1. Only customers who agreed to renewal (everyone else's renewals are
    #    already stopped by sweep_unconsented).
    users = db.query(User).filter(User.auto_renew.is_(True), User.stripe_customer_id.isnot(None)).all()
    for user in users:
        try:
            for status in ("active", "trialing", "past_due"):
                subs = stripe.Subscription.list(customer=user.stripe_customer_id, status=status, limit=100, api_key=key)
                for sub in subs.auto_paging_iter():
                    # 2. On a price Lavoo still sells, or already ending: leave it.
                    desc = describe_stripe_subscription(sub)
                    if desc["info"] is not None or sub.get("cancel_at_period_end"):
                        continue
                    # 3. An old price: let it end, don't renew it.
                    stripe.Subscription.modify(sub["id"], cancel_at_period_end=True, api_key=key)
                    stopped.append(f"user {user.id}: subscription {sub['id']} on unknown price {desc['price_id']}")
        except Exception as exc:
            logger.error("[card-consent] could not check old prices for user %s: %s", user.id, exc)
    # 4. Tell the admin which ones.
    if stopped:
        logger.warning("[card-consent] stopped %s renewal(s) on old prices: %s", len(stopped), stopped)
        from subscriptions.commission_service import CommissionService
        CommissionService._alert_admin(
            "Stripe renewals on old prices stopped",
            "These Stripe subscriptions were on a price Lavoo no longer sells, so they would have renewed at "
            "that old price. Each now ends at the end of the period already paid for; the customer can "
            "subscribe again at today's price:\n\n" + "\n".join(stopped),
        )
    return len(stopped)
