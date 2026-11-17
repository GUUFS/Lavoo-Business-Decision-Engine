"""
Founding prices: who pays the founding price and who pays the standard one.

The rule: anyone who pays before the founding end date pays the founding
price, on every plan. There is no limit on how many people get it.
  - The end date is SystemSettings.founding_monthly_ends_at, set by the
    admin on the Settings page (default: founding prices end after
    31 January 2027, i.e. at 2027-02-01 00:00 UTC).
  - Monthly: the founding monthly price on every payment before the end
    date, and the standard price after it.
  - Quarterly and yearly: the founding price on the FIRST quarterly payment
    and the FIRST yearly payment made before the end date. Every renewal
    after that is standard.
  - After the end date, everyone pays the standard price.
  - These rules apply to Stripe and Flutterwave payments alike.
Anyone who pays a founding price is marked as a founding member
(User.is_founding_member), which the daily Stripe sweep below uses.

Stripe keeps charging a subscription the price it was created with, so after
each paid invoice `after_stripe_payment` checks whether the NEXT payment
should be standard and, if so, moves the subscription to the standard price
(no charge now; the next invoice is at the new price). A daily sweep
(`sweep_founding_subscriptions`) catches anything a missed webhook skipped.
"""
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import stripe
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.pg_models import Subscriptions, SystemSettings, User
from subscriptions.plan_prices import (
    CURRENCIES, FOUNDING, PERIODS, STANDARD, TIERS,
    get_all_plan_prices, get_price_id, identify_price_id, normalise_price_type, normalise_tier,
)

logger = logging.getLogger(__name__)

# Founding prices are charged up to the end of 31 January 2027.
DEFAULT_ENDS_AT = datetime(2027, 2, 1, tzinfo=timezone.utc)
# Old name, kept so existing imports still work.
DEFAULT_MONTHLY_ENDS_AT = DEFAULT_ENDS_AT

# A payment started at the founding price just before the end date can
# finish a little after it (e.g. a slow Flutterwave bank transfer). Within
# this window it is still accepted at the founding price.
LATE_PAYMENT_GRACE = timedelta(hours=2)

PAID_STATUSES = ("completed", "active", "paid", "successful", "succeeded")


@dataclass
class FoundingRules:
    ends_at: datetime
    member_count: int

    @property
    def monthly_ends_at(self) -> datetime:
        # Old name, kept so existing callers still work.
        return self.ends_at

    def is_open(self, now: datetime) -> bool:
        return now < self.ends_at


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def get_rules(db: Session) -> FoundingRules:
    """When founding prices end, plus how many founding members there are."""
    settings = db.query(SystemSettings).first()
    count = db.query(func.count(User.id)).filter(User.is_founding_member.is_(True)).scalar() or 0
    ends_at = _as_utc(settings.founding_monthly_ends_at) if settings else None
    return FoundingRules(ends_at=ends_at or DEFAULT_ENDS_AT, member_count=count)


def founding_status(db: Session, now: Optional[datetime] = None) -> dict:
    """For the pricing pages and the admin Settings page."""
    now = now or datetime.now(timezone.utc)
    rules = get_rules(db)
    return {
        "available": rules.is_open(now),
        "ends_at": rules.ends_at.isoformat(),
        "monthly_ends_at": rules.ends_at.isoformat(),  # old name
        "members": rules.member_count,
    }


def _has_paid_founding(db: Session, user_id: int, period: str) -> bool:
    """Has this user already made a founding-price payment for this period?"""
    return db.query(Subscriptions.id).filter(
        Subscriptions.user_id == user_id,
        Subscriptions.subscription_plan == period,
        Subscriptions.price_type == FOUNDING,
        Subscriptions.status.in_(PAID_STATUSES),
    ).first() is not None


def price_type_for(
    db: Session,
    user: Optional[User],
    period: str,
    now: Optional[datetime] = None,
    grace: bool = False,
    rules: Optional[FoundingRules] = None,
) -> str:
    """'founding' or 'standard': the price set this user's next payment for
    this billing period should be charged at. `user` None means a new payer.

    grace: also allow the founding price for LATE_PAYMENT_GRACE after the end
    date. Only for accepting a payment that was started at the founding price
    just before the end date (see subscriptions/flutterwave.py)."""
    now = now or datetime.now(timezone.utc)
    rules = rules or get_rules(db)
    period = (period or "").lower()

    cutoff = rules.ends_at + (LATE_PAYMENT_GRACE if grace else timedelta(0))
    if now >= cutoff:
        return STANDARD

    if period == "monthly":
        return FOUNDING

    # Quarterly and yearly: founding price on the first payment only.
    if user and _has_paid_founding(db, user.id, period):
        return STANDARD
    return FOUNDING


def mark_founding_member(db: Session, user: User) -> bool:
    """Make this user a founding member (they just paid a founding price).
    Locks the settings row so two payments at the same moment can't get the
    same founding number. Returns True if they were newly marked."""
    if getattr(user, "is_founding_member", False):
        return False
    db.query(SystemSettings).with_for_update().first()
    highest = db.query(func.max(User.founding_number)).scalar() or 0
    user.is_founding_member = True
    user.founding_number = highest + 1
    user.founding_member_at = datetime.now(timezone.utc)
    db.flush()
    logger.info(f"[founding] user {user.id} is founding member #{user.founding_number}")
    return True


def record_payment(db: Session, user: User, subscription: Subscriptions,
                   plan_tier: Optional[str], price_type: Optional[str]) -> None:
    """Save the plan and price set on a payment row, and make the payer a
    founding member if they paid a founding price."""
    if plan_tier:
        subscription.plan_tier = normalise_tier(plan_tier)
    if price_type:
        subscription.price_type = normalise_price_type(price_type)
        if subscription.price_type == FOUNDING:
            mark_founding_member(db, user)


def effective_prices(db: Session, user: Optional[User] = None) -> dict:
    """What this user (or a new payer, if None) would pay right now:
    {tier: {currency: {period: amount or None}}}."""
    rules = get_rules(db)
    all_prices = get_all_plan_prices()
    types = {period: price_type_for(db, user, period, rules=rules) for period in PERIODS}
    return {
        tier: {
            currency: {period: all_prices[types[period]][tier][currency][period] for period in PERIODS}
            for currency in CURRENCIES
        }
        for tier in TIERS
    }


# ----------------------------------------------------------------------------
# Stripe: move founding subscriptions to the standard price when it's due
# ----------------------------------------------------------------------------

def _field(obj, key):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    try:
        return obj[key]
    except Exception:
        return getattr(obj, key, None)


def describe_stripe_subscription(stripe_sub) -> dict:
    """The price on a Stripe subscription and what it is:
    {item_id, price_id, info (from identify_price_id or None), period_end}."""
    items = _field(_field(stripe_sub, "items"), "data") or []
    item = items[0] if items else None
    price = _field(item, "price")
    price_id = price if isinstance(price, str) else _field(price, "id")
    # Basil API: billing periods live on the item; older API: on the subscription.
    period_end = _field(item, "current_period_end") or _field(stripe_sub, "current_period_end")
    return {
        "item_id": _field(item, "id"),
        "price_id": price_id,
        "info": identify_price_id(price_id),
        "period_end": period_end,
    }


def move_to_standard_if_due(db: Session, stripe_sub, rules: Optional[FoundingRules] = None) -> bool:
    """If this subscription is on a founding price and its next payment
    should be standard, move it to the standard price for the same plan,
    period and currency. Nothing is charged now; the next invoice is at the
    standard price. Returns True if it was moved."""
    sub_id = _field(stripe_sub, "id")
    if not sub_id or _field(stripe_sub, "status") in ("canceled", "incomplete_expired"):
        return False
    desc = describe_stripe_subscription(stripe_sub)
    info = desc["info"]
    if not info or info["price_type"] != FOUNDING:
        return False

    if info["period"] == "monthly":
        rules = rules or get_rules(db)
        if not desc["period_end"]:
            logger.warning(f"[founding] {sub_id}: no period end on the subscription; not moved")
            return False
        next_payment_at = datetime.fromtimestamp(int(desc["period_end"]), tz=timezone.utc)
        if next_payment_at < rules.monthly_ends_at:
            return False
    # Quarterly/yearly: the founding price was for the first payment only,
    # which has now been made, so every renewal is standard.

    standard_id = get_price_id(info["tier"], info["period"], info["currency"], STANDARD)
    if not standard_id:
        message = (
            f"Stripe subscription {sub_id} should move to the standard {info['tier']} "
            f"{info['period']} {info['currency']} price, but no standard price is set "
            f"(STRIPE_{info['tier'].upper()}_{info['period'].upper()}_STANDARD_PRICE_ID_{info['currency']}). "
            f"It will keep renewing at the founding price until this is set."
        )
        logger.error(f"[founding] {message}")
        from subscriptions.commission_service import CommissionService
        CommissionService._alert_admin("⚠️ Standard price missing for a founding subscription", message)
        return False

    stripe.Subscription.modify(
        sub_id,
        items=[{"id": desc["item_id"], "price": standard_id}],
        proration_behavior="none",
        metadata={"price_type": STANDARD},
        api_key=os.getenv("STRIPE_SECRET_KEY"),
    )
    logger.info(f"[founding] {sub_id} moved to standard price {standard_id} from its next payment")
    return True


def after_stripe_payment(db: Session, user: User, subscription: Optional[Subscriptions],
                         stripe_sub=None, sub_id: Optional[str] = None) -> None:
    """Call after a Stripe subscription payment is recorded: saves the plan
    and price set on the payment row, marks founding members, and moves the
    subscription to the standard price if its next payment should be.
    Never raises: a problem here must not undo a recorded payment."""
    try:
        if stripe_sub is None or not _field(stripe_sub, "items"):
            sub_id = sub_id or _field(stripe_sub, "id") or _field(stripe_sub, "subscription_id")
            if not sub_id:
                return
            stripe_sub = stripe.Subscription.retrieve(sub_id, api_key=os.getenv("STRIPE_SECRET_KEY"))

        info = describe_stripe_subscription(stripe_sub)["info"]
        meta = _field(stripe_sub, "metadata") or {}
        plan_tier = info["tier"] if info else _field(meta, "plan_tier")
        price_type = info["price_type"] if info else _field(meta, "price_type")
        if subscription is not None:
            record_payment(db, user, subscription, plan_tier, price_type)

        move_to_standard_if_due(db, stripe_sub)
    except Exception as e:
        logger.error(f"[founding] after_stripe_payment failed for user {getattr(user, 'id', None)}: {e}", exc_info=True)


def sweep_founding_subscriptions(db: Session) -> int:
    """Daily safety net: move every founding member's Stripe subscription
    that is due for the standard price (for example after the monthly
    founding end date, or if a webhook was missed). Returns how many moved."""
    rules = get_rules(db)
    moved = 0
    api_key = os.getenv("STRIPE_SECRET_KEY")
    founders = db.query(User).filter(
        User.is_founding_member.is_(True),
        User.stripe_customer_id.isnot(None),
    ).all()
    for user in founders:
        try:
            subs = stripe.Subscription.list(customer=user.stripe_customer_id, status="active", api_key=api_key)
            for stripe_sub in _field(subs, "data") or []:
                if move_to_standard_if_due(db, stripe_sub, rules=rules):
                    moved += 1
        except Exception as e:
            logger.error(f"[founding] sweep failed for user {user.id}: {e}")
    if moved:
        logger.info(f"[founding] sweep moved {moved} subscription(s) to standard prices")
    return moved
