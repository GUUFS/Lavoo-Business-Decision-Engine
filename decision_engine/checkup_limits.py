"""
Weekly checkup limits for the Decision Engine.

  - Pro:     1 checkup per week
  - Premium: 2 checkups per week

The limit is the same on every billing period (monthly, quarterly, yearly).
A "week" is the last 7 days (rolling), so a checkup comes back exactly 7
days after it was started. Admins have no limit.

Every checkup that starts is recorded in checkup_usage (CheckupUsage):
  1. reserve_checkup()   - before the analysis runs: refuses with HTTP 429
                           if the user has none left, otherwise records one
                           with status 'started'.
  2. confirm_checkup()   - after the analysis is saved: status 'completed',
                           linked to the analysis.
  3. release_checkup()   - if the analysis fails or the user leaves: status
                           'failed' or 'cancelled', which don't count.
Deleting an analysis later does NOT give the checkup back, because the
usage record is separate from the analysis. Admin checkups are recorded
too (never limited), so the admin Engine Health page sees every checkup.
"""
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database.pg_models import CheckupUsage, Subscriptions, User

CHECKUPS_PER_WEEK = {"pro": 1, "premium": 2}
WINDOW = timedelta(days=7)
# Payment statuses that mean "this subscription payment went through"
# (Stripe and Flutterwave each use their own words).
PAID_STATUSES = ("completed", "active", "paid", "successful", "succeeded")
# Checkup statuses that use up one of the week's checkups.
COUNTED_STATUSES = ("started", "completed")


def user_plan_tier(db: Session, user: User) -> str:
    """'pro' or 'premium' for a subscriber: the plan on their latest
    successful payment. Older payments without a saved plan are matched
    against the Stripe prices; accounts with no payment at all (beta or
    permanent accounts) use the plan they picked, or Pro."""
    latest = (
        db.query(Subscriptions)
        .filter(Subscriptions.user_id == user.id, Subscriptions.status.in_(PAID_STATUSES))
        .order_by(Subscriptions.created_at.desc())
        .first()
    )
    tier = None
    if latest is not None:
        tier = latest.plan_tier
        if not tier:
            from subscriptions.plan_prices import resolve_tier
            try:
                tier = resolve_tier(latest.amount, latest.currency, latest.subscription_plan)
            except Exception:
                tier = None
    tier = (tier or getattr(user, "preferred_plan_tier", None) or "pro").lower()
    return tier if tier in CHECKUPS_PER_WEEK else "pro"


def checkup_allowance(db: Session, user: User, now: datetime | None = None) -> dict:
    """How many checkups the user has left this week.

    Returns {tier, limit, used, remaining, next_available_at, unlimited}.
    next_available_at is when the next checkup frees up (ISO time), or None
    if they have one available now. Admins get unlimited=True."""
    now = now or datetime.now(UTC)
    if getattr(user, "is_admin", False):
        return {"tier": "admin", "limit": None, "used": 0, "remaining": None,
                "next_available_at": None, "unlimited": True}

    tier = user_plan_tier(db, user)
    limit = CHECKUPS_PER_WEEK[tier]
    # Checkups started in the last 7 days, oldest first.
    recent = [
        row[0] for row in
        db.query(CheckupUsage.created_at)
        .filter(
            CheckupUsage.user_id == user.id,
            CheckupUsage.created_at > now - WINDOW,
            CheckupUsage.status.in_(COUNTED_STATUSES),
        )
        .order_by(CheckupUsage.created_at.asc())
        .all()
    ]
    used = len(recent)
    remaining = max(0, limit - used)
    # When full, the oldest checkup in the window is the next to free up.
    next_available = (recent[used - limit] + WINDOW) if remaining == 0 and used else None
    return {
        "tier": tier, "limit": limit, "used": used, "remaining": remaining,
        "next_available_at": next_available.isoformat() if next_available else None,
        "unlimited": False,
    }


def _limit_message(allowance: dict) -> str:
    """The text shown to a user who has used this week's checkups."""
    plan = allowance["tier"].capitalize()
    count = allowance["limit"]
    plural = "checkup" if count == 1 else "checkups"
    when = ""
    if allowance["next_available_at"]:
        when_dt = datetime.fromisoformat(allowance["next_available_at"])
        when = f" Your next checkup is available on {when_dt.strftime('%a %d %b at %H:%M')} UTC."
    upgrade = " Upgrade to Premium for 2 checkups a week." if allowance["tier"] == "pro" else ""
    return f"{plan} includes {count} {plural} a week, and you've used yours.{when}{upgrade}"


def reserve_checkup(db: Session, user: User) -> CheckupUsage:
    """Record a checkup for `user`, or raise HTTP 429 if they have none left
    this week. Returns the usage row. Admins are recorded but never refused.

    The user's row is locked while checking and recording, so two checkups
    started at the same moment can't both slip under the limit."""
    # Lock this user's row until commit: a second request waits here.
    db.query(User).filter(User.id == user.id).with_for_update().first()
    allowance = checkup_allowance(db, user)
    if not allowance["unlimited"] and allowance["remaining"] <= 0:
        db.rollback()  # releases the lock
        raise HTTPException(status_code=429, detail={
            "code": "checkup_limit_reached",
            "message": _limit_message(allowance),
            **allowance,
        })
    usage = CheckupUsage(user_id=user.id, created_at=datetime.now(UTC), status="started")
    db.add(usage)
    db.commit()  # releases the lock
    return usage


def confirm_checkup(db: Session, usage: CheckupUsage | None, analysis_id: int | None) -> None:
    """Mark a checkup completed and link it to the analysis it produced."""
    _finish(db, usage, status="completed", analysis_id=analysis_id)


def release_checkup(db: Session, usage: CheckupUsage | None, error: str | None = None,
                    cancelled: bool = False) -> None:
    """Give a checkup back because its analysis failed (status 'failed',
    with the error) or the user left before it finished ('cancelled')."""
    db.rollback()  # clear any half-finished work from the failed analysis
    _finish(db, usage, status="cancelled" if cancelled else "failed",
            error=(error or "")[:2000] or None)


def _finish(db: Session, usage: CheckupUsage | None, **fields) -> None:
    """Save a checkup's final status. Never raises: recording the outcome
    must not break the response the user is waiting for."""
    if usage is None:
        return
    try:
        db.query(CheckupUsage).filter(CheckupUsage.id == usage.id).update(
            {**fields, "finished_at": datetime.now(UTC)}
        )
        db.commit()
    except Exception:
        db.rollback()
