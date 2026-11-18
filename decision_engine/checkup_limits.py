"""
Checkup limits for the Decision Engine.

  - Pro:     1 checkup per WEEK   (resets Monday 00:00 UTC)
  - Premium: 10 checkups per MONTH (resets on the 1st, 00:00 UTC)

The limit is the same on every billing period (monthly, quarterly, yearly).
A week is Monday 00:00 to Sunday 23:59 UTC; a month is a calendar month.
Everyone on the same plan resets at the same moment (midnight UTC is 01:00
in Lagos, 00:00 in London in winter). Admins and Staff have no limit.

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

# Each plan: (how many checkups, per "week" or "month").
CHECKUP_LIMITS = {"pro": (1, "week"), "premium": (10, "month")}
# Payment statuses that mean "this subscription payment went through"
# (Stripe and Flutterwave each use their own words).
PAID_STATUSES = ("completed", "active", "paid", "successful", "succeeded")
# Checkup statuses that use up one of the week's checkups.
COUNTED_STATUSES = ("started", "completed")


def user_plan_tier(db: Session, user: User) -> str:
    """'pro' or 'premium' for a subscriber: the plan on their latest
    successful payment. Older payments without a saved plan are matched
    against the Stripe prices; accounts with no payment at all (beta or
    permanent accounts) use the plan they picked, or Pro. A partner on
    their free 6 months of Premium (subscriptions/partner_service.py) is
    Premium whatever they pay for, and so is a Premium-forever account
    (subscriptions/lifetime_premium.py)."""
    from subscriptions.lifetime_premium import lifetime_premium_active
    from subscriptions.partner_service import partner_premium_active
    # 1. Free Premium (forever, or a partner's 6 months) beats any payment.
    if lifetime_premium_active(user) or partner_premium_active(user):
        return "premium"
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
    return tier if tier in CHECKUP_LIMITS else "pro"


def week_start(now: datetime) -> datetime:
    """Monday 00:00 UTC of the week `now` falls in."""
    now = now.astimezone(UTC)
    monday = now - timedelta(days=now.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def period_bounds(period: str, now: datetime) -> tuple[datetime, datetime]:
    """(start, next start) of the week or calendar month `now` falls in, UTC."""
    # 1. A week: Monday to next Monday.
    if period == "week":
        start = week_start(now)
        return start, start + timedelta(days=7)
    # 2. A month: the 1st to the 1st of next month.
    now = now.astimezone(UTC)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    following = start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
    return start, following


def checkup_allowance(db: Session, user: User, now: datetime | None = None) -> dict:
    """How many checkups the user has left this week (Pro) or month (Premium).

    Returns {tier, limit, period, used, remaining, next_available_at, unlimited}.
    period is "week" or "month". next_available_at is when the period resets
    (ISO time, UTC) if they have none left, otherwise None. Admins and Staff
    (the Lavoo team, who test the decision engine) get unlimited=True."""
    now = now or datetime.now(UTC)
    # 1. Admins and Staff: no weekly limit.
    if getattr(user, "is_admin", False) or getattr(user, "is_staff", False):
        tier = "admin" if getattr(user, "is_admin", False) else "staff"
        return {"tier": tier, "limit": None, "period": None, "used": 0, "remaining": None,
                "next_available_at": None, "unlimited": True}

    # 2. Everyone else: their plan's limit (Pro 1 a week, Premium 10 a month).
    tier = user_plan_tier(db, user)
    limit, period = CHECKUP_LIMITS[tier]
    # 3. Checkups started since this week or month began.
    start, next_start = period_bounds(period, now)
    used = (
        db.query(CheckupUsage)
        .filter(
            CheckupUsage.user_id == user.id,
            CheckupUsage.created_at >= start,
            CheckupUsage.status.in_(COUNTED_STATUSES),
        )
        .count()
    )
    remaining = max(0, limit - used)
    # 4. When none are left, they all come back when the next week or month starts.
    next_available = next_start if remaining == 0 else None
    return {
        "tier": tier, "limit": limit, "period": period, "used": used, "remaining": remaining,
        "next_available_at": next_available.isoformat() if next_available else None,
        "unlimited": False,
    }


def _limit_message(allowance: dict) -> str:
    """The text shown to a user who has used this period's checkups."""
    plan = allowance["tier"].capitalize()
    count = allowance["limit"]
    plural = "check-up" if count == 1 else "check-ups"
    period = "a week (Monday to Sunday)" if allowance["period"] == "week" else "a month"
    when = ""
    if allowance["next_available_at"]:
        when_dt = datetime.fromisoformat(allowance["next_available_at"])
        when = f" Your check-ups reset on {when_dt.strftime('%a %d %b at %H:%M')} UTC."
    premium_count, premium_period = CHECKUP_LIMITS["premium"]
    upgrade = (f" Upgrade to Premium for {premium_count} check-ups a {premium_period}."
               if allowance["tier"] == "pro" else "")
    return (f"{plan} includes {count} {plural} {period}, and you've used "
            f"{'it' if count == 1 else 'them'}.{when}{upgrade}")


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
