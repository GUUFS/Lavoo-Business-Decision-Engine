"""
The free trial every new account gets.

WHAT THE PRICING PAGE PROMISES: "One free check-up and 3 days of Premium".
Every new account (signup, Google, or claiming an ad check-up) gets
users.grace_period_ends_at set to signup + GRACE_PERIOD_DAYS
(subscriptions/beta_service.py initialize_grace_period).

WHAT THIS MEANS IN THE APP:
  - Until grace_period_ends_at, the account can use the Decision Engine like
    a Premium member: open its check-up results, Missions and progress
    (api/routes/dependencies.py subscriber_required).
  - It gets ONE check-up during the trial (decision_engine/checkup_limits.py,
    tier "trial"). An ad check-up claimed when signing up IS that check-up.
  - After the trial, the account is on Starter until it subscribes.
"""
from datetime import UTC, datetime, timedelta

from database.pg_models import User

# How many check-ups the free trial includes.
TRIAL_CHECKUPS = 1


def _as_utc(moment: datetime | None) -> datetime | None:
    """The time in UTC; a time saved without a timezone is read as UTC."""
    # 1. Nothing saved.
    if moment is None:
        return None
    # 2. Add UTC to a time with no timezone, otherwise convert it.
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)


def free_trial_ends_at(user: User | None) -> datetime | None:
    """When this account's free trial ends (UTC), or None if it never had one."""
    # 1. No account, or no trial was set up.
    if user is None:
        return None
    # 2. The end saved when the account was created.
    return _as_utc(getattr(user, "grace_period_ends_at", None))


def free_trial_active(user: User | None, now: datetime | None = None) -> bool:
    """True while this account is in its free trial."""
    # 1. When does it end?
    ends = free_trial_ends_at(user)
    # 2. Active until then.
    return ends is not None and (now or datetime.now(UTC)) < ends


def free_trial_starts_at(user: User) -> datetime | None:
    """When the free trial began: the end minus the trial length, so it
    matches even for beta accounts whose trial started at launch."""
    from subscriptions.beta_service import BetaService
    # 1. No trial, no start.
    ends = free_trial_ends_at(user)
    if ends is None:
        return None
    # 2. Count back the trial length.
    return ends - timedelta(days=BetaService.get_grace_period_days())
