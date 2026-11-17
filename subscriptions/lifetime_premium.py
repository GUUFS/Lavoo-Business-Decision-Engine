"""
Premium forever (User.lifetime_premium).

An account with this flag is a Premium member for good, without paying:
  - the per-request status sync (api/utils/sub_utils.py) keeps it active,
    whatever its payments say;
  - the checkup limits (decision_engine/checkup_limits.py) treat it as
    Premium;
  - the daily expiry job (api/main.py) neither charges it a renewal nor
    moves it to Free.
It is not the partner deal (subscriptions/partner_service.py): no 50%
Builder Bonus rate and no end date. The flag is set in the database (the
migration a3c5e7f9b1d2 sets it for the first account) or by
grant_lifetime_premium.
"""
import logging

from sqlalchemy.orm import Session

from database.pg_models import User

logger = logging.getLogger(__name__)

# Shown as the plan name ("Lifetime") wherever the app prints the plan.
LIFETIME_PLAN = "lifetime"

# Accounts made Premium forever by the owner. Their flag is switched on the
# first time the status sync sees them, so an account that signs up after
# the migration ran is covered too. Lower case.
LIFETIME_PREMIUM_EMAILS = frozenset({"teamholyhustle@gmail.com"})


def lifetime_premium_active(user: User | None) -> bool:
    """True when the account is Premium forever (the flag, or its email is
    on LIFETIME_PREMIUM_EMAILS)."""
    # 1. No user: not lifetime.
    if user is None:
        return False
    # 2. The flag, or an email the owner named.
    return bool(getattr(user, "lifetime_premium", False)
                or (user.email or "").strip().lower() in LIFETIME_PREMIUM_EMAILS)


def lifetime_premium_user_ids(db: Session) -> set[int]:
    """Ids of every Premium-forever account (the expiry job skips them)."""
    from sqlalchemy import func, or_

    # 1. Accounts with the flag set, or an email the owner named.
    rows = db.query(User.id).filter(or_(
        User.lifetime_premium.is_(True),
        func.lower(User.email).in_(LIFETIME_PREMIUM_EMAILS),
    )).all()
    # 2. Just the ids.
    return {row[0] for row in rows}


def _keep_active(user: User) -> bool:
    """Make the account active on the lifetime plan. Returns True when
    something changed (so the caller only writes when it has to)."""
    changed = False
    # 0. The flag itself (an email on the list gets it here the first time).
    if not getattr(user, "lifetime_premium", False):
        user.lifetime_premium = True
        changed = True
    # 1. Active, so every subscriber-only feature opens.
    if user.subscription_status != "active":
        user.subscription_status = "active"
        changed = True
    # 2. The plan reads "lifetime" (the upgrade page shows its own card).
    if user.subscription_plan != LIFETIME_PLAN:
        user.subscription_plan = LIFETIME_PLAN
        changed = True
    # 3. No end date: access never runs out.
    if getattr(user, "subscription_expires_at", None) is not None:
        user.subscription_expires_at = None
        changed = True
    return changed


def enforce_lifetime_premium(db: Session, user: User) -> bool:
    """Called by the status sync: if the account is Premium forever, make
    sure it is active and return True (the caller then leaves it alone)."""
    # 1. Not lifetime: the normal sync decides.
    if not lifetime_premium_active(user):
        return False
    # 2. Lifetime: keep it active, writing only when something changed.
    if _keep_active(user):
        db.commit()
    return True


def grant_lifetime_premium(db: Session, user: User) -> None:
    """Make the account a Premium member forever."""
    # 1. Set the flag.
    user.lifetime_premium = True
    # 2. Active on the lifetime plan straight away.
    _keep_active(user)
    db.commit()
    logger.info("[lifetime] user %s is Premium forever", user.id)
