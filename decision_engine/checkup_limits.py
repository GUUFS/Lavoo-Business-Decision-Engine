"""
Checkup limits for the Decision Engine.

  - Pro:     1 checkup per WEEK   (resets Monday 00:00 UTC)
  - Premium: 10 checkups per MONTH (resets on the 1st, 00:00 UTC)
  - Free trial (new accounts, not paying yet): 1 checkup for the whole
    trial (subscriptions/free_trial.py). An ad check-up claimed at signup
    is that checkup.

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
  4. close_stuck_checkups() - every 15 minutes: anything still 'started'
                           after 30 minutes is completed (if its analysis
                           was saved) or failed.
Deleting an analysis later does NOT give the checkup back, because the
usage record is separate from the analysis. Admin checkups are recorded
too (never limited), so the admin Engine Health page sees every checkup.
"""
import logging
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import inspect, true
from sqlalchemy.orm import Session

from database.pg_models import CheckupUsage, Subscriptions, User

# Each plan: (how many checkups, per "week" or "month").
logger = logging.getLogger(__name__)

CHECKUP_LIMITS = {"pro": (1, "week"), "premium": (10, "month")}
# Payment statuses that mean "this subscription payment went through"
# (Stripe and Flutterwave each use their own words).
PAID_STATUSES = ("completed", "active", "paid", "successful", "succeeded")
# Checkup statuses that use up one of the week's checkups.
COUNTED_STATUSES = ("started", "completed")
# Subscription statuses that mean the account pays (same as api/routes/dependencies.py).
PAYING_STATUSES = ("active", "trialing")


def on_free_trial_only(user: User, now: datetime | None = None) -> bool:
    """True for a new account in its free trial that doesn't pay and has no
    free Premium (partner or forever): its checkups follow the trial's limit."""
    from subscriptions.free_trial import free_trial_active
    from subscriptions.lifetime_premium import lifetime_premium_active
    from subscriptions.partner_service import partner_premium_active
    # 1. Paying, or free Premium: their plan's limit applies, not the trial's.
    if (user.subscription_status or "").lower() in PAYING_STATUSES:
        return False
    if lifetime_premium_active(user) or partner_premium_active(user):
        return False
    # 2. Otherwise: only while the trial lasts.
    return free_trial_active(user, now)


def _trial_allowance(db: Session, user: User) -> dict:
    """The free trial's allowance: TRIAL_CHECKUPS for the whole trial, never reset.
    A claimed ad check-up (status 'guest', run before the account existed)
    counts as the trial's checkup."""
    from sqlalchemy import or_

    from subscriptions.free_trial import TRIAL_CHECKUPS, free_trial_starts_at
    # 1. Checkups run since the trial began, plus any claimed ad check-up.
    start = free_trial_starts_at(user)
    used = (
        db.query(CheckupUsage)
        .filter(
            CheckupUsage.user_id == user.id,
            or_(
                CheckupUsage.status == "guest",
                (CheckupUsage.created_at >= start) & CheckupUsage.status.in_(COUNTED_STATUSES),
            ),
        )
        .count()
    )
    # 2. What's left. They don't come back: subscribing gives more.
    return {"tier": "trial", "limit": TRIAL_CHECKUPS, "period": "trial", "used": used,
            "remaining": max(0, TRIAL_CHECKUPS - used), "next_available_at": None, "unlimited": False}


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

    # 2. A new account in its free trial: one checkup for the whole trial.
    if on_free_trial_only(user, now):
        return _trial_allowance(db, user)

    # 3. Everyone else: their plan's limit (Pro 1 a week, Premium 10 a month).
    tier = user_plan_tier(db, user)
    limit, period = CHECKUP_LIMITS[tier]
    # 4. Checkups started since this week or month began.
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
    # 5. When none are left, they all come back when the next week or month starts.
    next_available = next_start if remaining == 0 else None
    return {
        "tier": tier, "limit": limit, "period": period, "used": used, "remaining": remaining,
        "next_available_at": next_available.isoformat() if next_available else None,
        "unlimited": False,
    }


def _limit_message(allowance: dict) -> str:
    """The text shown to a user who has used this period's checkups."""
    # 1. The free trial's one checkup is used: subscribing gives more.
    if allowance["tier"] == "trial":
        return ("Your free trial includes one check-up, and you've used it. "
                "Subscribe to Pro or Premium to run more check-ups.")
    # 2. A plan's checkups for this week or month are used.
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


def _usage_id(usage: CheckupUsage) -> int | None:
    """The row's id, without touching the database.

    A streamed checkup ends after its request's session has been closed, so
    reading `usage.id` there tries to reload the expired row through a closed
    session and fails (that left every streamed checkup stuck at 'started').
    The id is kept in the object's identity, which can always be read."""
    identity = inspect(usage).identity
    return identity[0] if identity else None


def _finish(db: Session, usage: CheckupUsage | None, **fields) -> None:
    """Save a checkup's final status. Never raises: recording the outcome
    must not break the response the user is waiting for (a failure is logged)."""
    if usage is None:
        return
    try:
        # 1. The row's id (safe even after the request's session closed).
        usage_id = _usage_id(usage)
        # 2. Save the outcome on the database row itself.
        db.query(CheckupUsage).filter(CheckupUsage.id == usage_id).update(
            {**fields, "finished_at": datetime.now(UTC)}
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(f"[checkup-limits] could not record checkup outcome {fields.get('status')}: {exc}")


# A checkup still 'started' after this long has stopped (a server restart,
# or an outcome that couldn't be saved).
STUCK_AFTER = timedelta(minutes=30)


def close_stuck_checkups(db: Session, now: datetime | None = None) -> dict:
    """Finish checkups left at 'started' for over STUCK_AFTER:
      - if the user got an analysis in that time, it is 'completed' and linked;
      - otherwise 'failed' (which gives the checkup back to the user).
    Returns {"completed": n, "failed": n}. Run by a job every 15 minutes."""
    from database.pg_models import BusinessAnalysis

    now = now or datetime.now(UTC)
    counts = {"completed": 0, "failed": 0}
    # 1. The stuck ones, oldest first.
    stuck = (db.query(CheckupUsage)
             .filter(CheckupUsage.status == "started", CheckupUsage.created_at < now - STUCK_AFTER)
             .order_by(CheckupUsage.created_at).all())
    # Analyses already linked to a checkup can't be linked twice.
    linked = {a for (a,) in db.query(CheckupUsage.analysis_id).filter(CheckupUsage.analysis_id.isnot(None)).all()}
    for usage in stuck:
        # 2. Their analysis: the first one saved for them within STUCK_AFTER of starting.
        analysis = (db.query(BusinessAnalysis.id)
                    .filter(BusinessAnalysis.user_id == usage.user_id,
                            BusinessAnalysis.created_at >= usage.created_at,
                            BusinessAnalysis.created_at <= usage.created_at + STUCK_AFTER,
                            BusinessAnalysis.id.notin_(linked) if linked else true())
                    .order_by(BusinessAnalysis.created_at).first())
        # 3. Completed (with its analysis), or failed.
        if analysis:
            usage.status, usage.analysis_id = "completed", analysis[0]
            linked.add(analysis[0])
            counts["completed"] += 1
        else:
            usage.status = "failed"
            usage.error = "Never finished (the server restarted or the outcome couldn't be saved)."
            counts["failed"] += 1
        usage.finished_at = now
    db.commit()
    return counts
