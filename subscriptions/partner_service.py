"""
Partners: set and removed by an admin on the Permissions page
(api/routes/admin/permissions.py), the same way as Staff.

What being a partner gives:
  - a 50% Builder Bonus rate on their referrals' payments
    (CommissionService, via User.is_partner);
  - Premium, free, for 6 calendar months from the day they became a
    partner (User.partner_since -> User.partner_premium_until).

While that free Premium lasts:
  - the partner's account is kept active even without a payment: the
    per-request status sync (api/utils/sub_utils.py) and the daily expiry
    job (api/main.py) both check partner_premium_active before moving anyone
    to Free, and the expiry job doesn't charge them a renewal;
  - any Stripe subscription they already pay for is paused (Stripe's
    pause_collection, invoices voided) until the free Premium ends, when
    Stripe resumes billing by itself.
When it ends, end_expired_partner_premium puts the account back on whatever
they actually pay for (or Free). They stay a partner, so the 50% rate
continues until an admin removes it. Removing partner status ends the free
Premium and resumes any paused Stripe billing at once.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import stripe
from sqlalchemy.orm import Session

from database.pg_models import User

logger = logging.getLogger(__name__)

PARTNER_PREMIUM_MONTHS = 6
# Stripe subscriptions in these states are billing the partner and get paused.
BILLING_STRIPE_STATUSES = ("active", "trialing", "past_due")


def _as_utc(dt: datetime | None) -> datetime | None:
    """Treat a naive datetime as UTC so it can be compared with aware ones."""
    # 1. Nothing to convert.
    if dt is None:
        return None
    # 2. Naive times are stored as UTC in this app; mark them so.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def add_calendar_months(dt: datetime, months: int) -> datetime:
    """The same day `months` calendar months later, clamped to the last day
    of a shorter month (31 August + 6 months = 28/29 February)."""
    from calendar import monthrange
    # 1. Work out the target year and month.
    years, month_index = divmod(dt.month - 1 + months, 12)
    year, month = dt.year + years, month_index + 1
    # 2. Keep the same day, or the month's last day if it is shorter.
    return dt.replace(year=year, month=month, day=min(dt.day, monthrange(year, month)[1]))


def partner_premium_active(user: User | None, now: datetime | None = None) -> bool:
    """True while a partner's free Premium lasts: they are a partner and
    partner_premium_until is still in the future."""
    # 1. Only partners have free Premium.
    if user is None or not getattr(user, "is_partner", False):
        return False
    # 2. It lasts until partner_premium_until (exclusive).
    until = _as_utc(getattr(user, "partner_premium_until", None))
    return until is not None and (now or datetime.now(timezone.utc)) < until


def _keep_active(user: User) -> None:
    """Give the partner Premium access while it lasts: an active status
    that runs at least until their free Premium ends."""
    # 1. Active, so every subscriber-only feature opens.
    user.subscription_status = "active"
    # 2. Their access runs at least until the free Premium ends.
    until = _as_utc(user.partner_premium_until)
    expires = _as_utc(getattr(user, "subscription_expires_at", None))
    if expires is None or expires < until:
        user.subscription_expires_at = until


def _billing_stripe_subscriptions(user: User) -> list:
    """The user's Stripe subscriptions that are billing them now (empty if
    they have no Stripe customer or Stripe isn't configured)."""
    # 1. No Stripe customer: nothing on Stripe to pause or resume.
    api_key = os.getenv("STRIPE_SECRET_KEY")
    if not getattr(user, "stripe_customer_id", None) or not api_key:
        return []
    # 2. Every subscription of theirs, kept only if it is billing.
    listing = stripe.Subscription.list(customer=user.stripe_customer_id, status="all", limit=20, api_key=api_key)
    subs = listing.get("data", []) if isinstance(listing, dict) else getattr(listing, "data", [])
    return [s for s in subs if (s.get("status") if isinstance(s, dict) else getattr(s, "status", None)) in BILLING_STRIPE_STATUSES]


def pause_stripe_billing(user: User) -> int:
    """Pause billing on the partner's Stripe subscriptions until their free
    Premium ends: invoices in that time are voided (not charged) and Stripe
    resumes billing by itself at partner_premium_until. Returns how many
    subscriptions were paused; a Stripe error is logged, not raised, so
    making someone a partner never fails because of it."""
    # 1. Nothing to pause unless the free Premium is running.
    until = _as_utc(user.partner_premium_until)
    if until is None:
        return 0
    paused = 0
    try:
        # 2. Pause each subscription that is billing them, until the end date.
        for sub in _billing_stripe_subscriptions(user):
            sub_id = sub["id"] if isinstance(sub, dict) else sub.id
            stripe.Subscription.modify(
                sub_id,
                pause_collection={"behavior": "void", "resumes_at": int(until.timestamp())},
                metadata={"paused_for": "partner_premium"},
                api_key=os.getenv("STRIPE_SECRET_KEY"),
            )
            paused += 1
            logger.info("[partner] paused Stripe subscription %s for user %s until %s", sub_id, user.id, until)
    except Exception as e:
        # 3. Log and carry on: the admin sees the count in the response.
        logger.error("[partner] could not pause Stripe billing for user %s: %s", user.id, e)
    return paused


def resume_stripe_billing(user: User) -> int:
    """Resume billing on Stripe subscriptions that were paused for the
    partner's free Premium (used when partner status is removed early).
    Returns how many were resumed; errors are logged, not raised."""
    resumed = 0
    try:
        # 1. Only subscriptions we paused for partner Premium are resumed.
        for sub in _billing_stripe_subscriptions(user):
            meta = (sub.get("metadata") if isinstance(sub, dict) else getattr(sub, "metadata", None)) or {}
            paused = sub.get("pause_collection") if isinstance(sub, dict) else getattr(sub, "pause_collection", None)
            if not paused or meta.get("paused_for") != "partner_premium":
                continue
            # 2. Clear the pause and our marker; Stripe bills from the next cycle.
            sub_id = sub["id"] if isinstance(sub, dict) else sub.id
            stripe.Subscription.modify(sub_id, pause_collection="", metadata={"paused_for": ""},
                                       api_key=os.getenv("STRIPE_SECRET_KEY"))
            resumed += 1
            logger.info("[partner] resumed Stripe subscription %s for user %s", sub_id, user.id)
    except Exception as e:
        # 3. Log and carry on.
        logger.error("[partner] could not resume Stripe billing for user %s: %s", user.id, e)
    return resumed


def grant_partner(db: Session, user: User, now: datetime | None = None) -> dict:
    """Make the user a partner. A new partner's join day is today and their
    free Premium runs 6 calendar months from it; making an existing partner
    a partner again changes nothing (their 6 months don't restart).
    Returns {"stripe_paused": n, "is_new": bool}: how many Stripe
    subscriptions were paused, and whether they just became a partner (the
    caller emails new partners only)."""
    now = now or datetime.now(timezone.utc)
    # 1. A new partner: today is their join day; Premium for 6 months from it.
    is_new = not user.is_partner or user.partner_since is None
    if is_new:
        user.partner_since = now
        user.partner_premium_until = add_calendar_months(now, PARTNER_PREMIUM_MONTHS)
    user.is_partner = True
    # 2. While the free Premium runs, their account is active Premium.
    if partner_premium_active(user, now):
        _keep_active(user)
    db.commit()
    # 3. Stop Stripe charging them for the free months (new partners only;
    #    an existing partner's subscriptions were paused when they joined).
    stripe_paused = pause_stripe_billing(user) if is_new and partner_premium_active(user, now) else 0
    logger.info("[partner] user %s is a partner; free Premium until %s", user.id, user.partner_premium_until)
    return {"stripe_paused": stripe_paused, "is_new": is_new}


def revoke_partner(db: Session, user: User) -> dict:
    """Remove partner status: the 50% rate and any free Premium left end
    now, Stripe billing paused for it resumes, and the account goes back to
    what they actually pay for. Returns {"stripe_resumed": n}."""
    from api.utils.sub_utils import sync_user_subscription

    # 1. Resume any Stripe billing paused for the free Premium.
    stripe_resumed = resume_stripe_billing(user)
    # 2. Clear partner status and the free Premium.
    user.is_partner = False
    user.partner_since = None
    user.partner_premium_until = None
    db.commit()
    # 3. Back to what they actually pay for: active if they pay, Free if not.
    sync_user_subscription(db, user)
    logger.info("[partner] user %s is no longer a partner", user.id)
    return {"stripe_resumed": stripe_resumed}


def enforce_partner_premium(db: Session, user: User, now: datetime | None = None) -> bool:
    """Called by the status sync: if the user's free partner Premium is
    still running, make sure they are active and return True (the caller
    then leaves their status alone)."""
    # 1. Not on free partner Premium: the normal sync decides.
    if not partner_premium_active(user, now):
        return False
    # 2. On it: keep them active (only write when something changed).
    if user.subscription_status != "active":
        _keep_active(user)
        db.commit()
    return True


def end_expired_partner_premium(db: Session, now: datetime | None = None) -> int:
    """Daily job: partners whose free Premium has ended and who are still
    shown as active go back to what they actually pay for (or Free). Stripe
    resumes any paused billing by itself on the same date. Returns how many
    accounts were checked."""
    from api.utils.sub_utils import sync_user_subscription

    now = now or datetime.now(timezone.utc)
    # 1. Partners whose free Premium has ended but who are still active.
    ended = (
        db.query(User)
        .filter(
            User.is_partner.is_(True),
            User.partner_premium_until.isnot(None),
            User.partner_premium_until <= now,
            User.subscription_status == "active",
        )
        .all()
    )
    # 2. Re-check each against their real payments, at the same `now`.
    for user in ended:
        sync_user_subscription(db, user, now)
    if ended:
        logger.info("[partner] free Premium ended for %d partner(s)", len(ended))
    return len(ended)


def partner_premium_user_ids(db: Session, now: datetime | None = None) -> set[int]:
    """Ids of partners whose free Premium is still running (the expiry job
    must neither charge nor downgrade them)."""
    now = now or datetime.now(timezone.utc)
    # 1. Partners whose free Premium ends after `now`.
    rows = (
        db.query(User.id)
        .filter(User.is_partner.is_(True), User.partner_premium_until > now)
        .all()
    )
    # 2. Just the ids.
    return {row[0] for row in rows}
