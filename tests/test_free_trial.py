"""
Tests for the free trial promised on the pricing page: "One free check-up
and 3 days of Premium" (subscriptions/free_trial.py).

  - During the trial, a new account can open the Decision Engine
    (api/routes/dependencies.py subscriber_required), e.g. to read the ad
    check-up it claimed when signing up.
  - The trial includes one check-up. A claimed ad check-up is that one.
  - After the trial, the account is asked to upgrade.
  - Paying subscribers keep their plan's limit.
"""
import itertools
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from api.routes.dependencies import subscriber_required
from database.pg_models import CheckupUsage, User
from decision_engine.checkup_limits import checkup_allowance, reserve_checkup
from tests.test_checkup_limits import make_subscriber

_ids = itertools.count(1)


def new_account(db, trial_days_left=3.0):
    """A new, non-paying account whose free trial ends in `trial_days_left` days (negative: ended)."""
    # 1. A Starter account, as signup leaves it.
    n = next(_ids)
    user = User(name=f"Trial {n}", email=f"trial{n}@test.local", password="x", confirm_password="x",
                subscription_status="Free",
                grace_period_ends_at=datetime.now(UTC) + timedelta(days=trial_days_left))
    db.add(user)
    # 2. Saved (to the test's savepoint), because reserve_checkup rolls back on refusal.
    db.commit()
    return user


def claimed_ad_checkup(db, user):
    """The ad check-up they ran before signing up, claimed onto the account
    (as decision_engine/guest_checkup.claim records it)."""
    # 1. Recorded as 'guest', dated before the account existed.
    db.add(CheckupUsage(user_id=user.id, created_at=datetime.now(UTC) - timedelta(hours=1), status="guest"))
    db.commit()


def test_a_new_account_can_open_the_decision_engine_during_its_trial(db):
    user = new_account(db)
    assert subscriber_required(user) is user


def test_after_the_trial_the_account_is_asked_to_upgrade(db):
    user = new_account(db, trial_days_left=-0.1)
    with pytest.raises(HTTPException) as refused:
        subscriber_required(user)
    assert refused.value.status_code == 403


def test_the_trial_includes_one_checkup(db):
    user = new_account(db)
    # 1. One to use.
    allowance = checkup_allowance(db, user)
    assert allowance["tier"] == "trial" and allowance["remaining"] == 1 and allowance["next_available_at"] is None
    # 2. After using it, the next is refused with the trial's message.
    reserve_checkup(db, user)
    with pytest.raises(HTTPException) as refused:
        reserve_checkup(db, user)
    assert refused.value.status_code == 429
    assert "free trial includes one check-up" in refused.value.detail["message"]


def test_a_claimed_ad_checkup_is_the_trials_checkup(db):
    user = new_account(db)
    claimed_ad_checkup(db, user)
    # 1. They can still read it...
    assert subscriber_required(user) is user
    # 2. ...but it was their free check-up.
    assert checkup_allowance(db, user)["remaining"] == 0


def test_paying_subscribers_keep_their_plans_limit_during_the_trial(db):
    user = make_subscriber(db, "premium")
    user.grace_period_ends_at = datetime.now(UTC) + timedelta(days=2)
    db.commit()
    allowance = checkup_allowance(db, user)
    assert allowance["tier"] == "premium" and allowance["limit"] == 10


def test_access_ends_exactly_when_the_trial_ends(db):
    from api.routes.dependencies import decision_engine_access_ends_at, has_decision_engine_access
    user = new_account(db, trial_days_left=1)
    # 1. During the trial: access, and the app is told when it stops.
    assert has_decision_engine_access(user)
    assert decision_engine_access_ends_at(user) == user.grace_period_ends_at.astimezone(UTC).isoformat()
    # 2. One second after the trial ends: no access.
    user.grace_period_ends_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert not has_decision_engine_access(user)
    assert decision_engine_access_ends_at(user) is None
    with pytest.raises(HTTPException):
        subscriber_required(user)


def test_a_paying_subscriber_has_no_trial_end_on_their_access(db):
    from api.routes.dependencies import decision_engine_access_ends_at
    user = make_subscriber(db, "pro")
    user.grace_period_ends_at = datetime.now(UTC) + timedelta(days=1)
    db.commit()
    assert decision_engine_access_ends_at(user) is None
