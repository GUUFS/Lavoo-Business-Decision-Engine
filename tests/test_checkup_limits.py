"""
Tests for the weekly Decision Engine checkup limits
(decision_engine/checkup_limits.py and the analyze routes in
api/routes/decision_engine/analyzer.py).

  - Pro: 1 checkup per calendar week (Mon 00:00 to Sun 23:59 UTC). Premium: 2.
    Same on monthly, quarterly and yearly.
  - A failed or cancelled checkup is given back; deleting an analysis is not.
  - Admins have no limit.

The analyzer (LLM) is faked; everything else runs against real Postgres.
Setup data is committed (to the test's savepoint) because the limit code
rolls back on refusal, and the test's own rows must survive that.
"""
import asyncio
import itertools
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import BackgroundTasks, HTTPException
from starlette.requests import Request

from api.routes.decision_engine.analyzer import analyze_business_goal, analyze_business_goal_stream
from database.pg_models import CheckupUsage, Subscriptions, User
from decision_engine.checkup_limits import (
    checkup_allowance,
    release_checkup,
    reserve_checkup,
)

_ids = itertools.count(1)


def make_subscriber(db, tier="pro", period="monthly", is_admin=False):
    """An active subscriber whose latest payment is on `tier`/`period`."""
    n = next(_ids)
    user = User(name=f"Founder {n}", email=f"checkup{n}@test.local", password="x", confirm_password="x",
                subscription_status="active", is_admin=is_admin)
    db.add(user)
    db.flush()
    now = datetime.now(UTC)
    db.add(Subscriptions(
        user_id=user.id, subscription_plan=period, plan_tier=tier, transaction_id=f"ck-tx{n}",
        tx_ref=f"ck-ref{n}", amount=Decimal("20.00"), currency="USD", status="completed",
        subscription_status="active", payment_provider="stripe", created_at=now - timedelta(days=1),
        start_date=now, end_date=now + timedelta(days=30),
    ))
    db.commit()
    return user


# ── The limits themselves ───────────────────────────────────────────────────

@pytest.mark.parametrize("period", ["monthly", "quarterly", "yearly"])
def test_pro_gets_one_checkup_a_week_on_every_billing_period(db, period):
    user = make_subscriber(db, "pro", period)
    assert checkup_allowance(db, user)["remaining"] == 1
    reserve_checkup(db, user)
    with pytest.raises(HTTPException) as refused:
        reserve_checkup(db, user)
    assert refused.value.status_code == 429
    assert refused.value.detail["code"] == "checkup_limit_reached"
    assert "Pro includes 1 checkup a week" in refused.value.detail["message"]


@pytest.mark.parametrize("period", ["monthly", "quarterly", "yearly"])
def test_premium_gets_two_checkups_a_week_on_every_billing_period(db, period):
    user = make_subscriber(db, "premium", period)
    reserve_checkup(db, user)
    reserve_checkup(db, user)
    with pytest.raises(HTTPException) as refused:
        reserve_checkup(db, user)
    assert refused.value.status_code == 429
    assert "Premium includes 2 checkups a week" in refused.value.detail["message"]


def used_checkup_at(db, user, when):
    """Record a checkup the user started at `when`."""
    db.add(CheckupUsage(user_id=user.id, created_at=when))
    db.commit()


# Wednesday 11 Nov 2026, 15:00 UTC; that week runs Mon 9 Nov 00:00 to Sun 15 Nov.
WEDNESDAY = datetime(2026, 11, 11, 15, 0, tzinfo=UTC)
NEXT_MONDAY = datetime(2026, 11, 16, 0, 0, tzinfo=UTC)


def test_week_is_monday_to_sunday(db):
    user = make_subscriber(db, "pro")
    used_checkup_at(db, user, datetime(2026, 11, 8, 23, 59, tzinfo=UTC))   # Sunday last week
    assert checkup_allowance(db, user, now=WEDNESDAY)["remaining"] == 1
    used_checkup_at(db, user, datetime(2026, 11, 9, 0, 0, tzinfo=UTC))     # Monday 00:00 this week
    allowance = checkup_allowance(db, user, now=WEDNESDAY)
    assert allowance["remaining"] == 0
    assert datetime.fromisoformat(allowance["next_available_at"]) == NEXT_MONDAY


def test_checkups_reset_at_monday_midnight_utc(db):
    user = make_subscriber(db, "pro")
    used_checkup_at(db, user, datetime(2026, 11, 15, 22, 0, tzinfo=UTC))   # Sunday night
    assert checkup_allowance(db, user, now=datetime(2026, 11, 15, 23, 59, tzinfo=UTC))["remaining"] == 0
    assert checkup_allowance(db, user, now=NEXT_MONDAY)["remaining"] == 1   # reset


def test_premium_two_checkups_reset_together_on_monday(db):
    user = make_subscriber(db, "premium")
    used_checkup_at(db, user, datetime(2026, 11, 9, 8, 0, tzinfo=UTC))
    used_checkup_at(db, user, datetime(2026, 11, 10, 8, 0, tzinfo=UTC))
    allowance = checkup_allowance(db, user, now=WEDNESDAY)
    assert (allowance["used"], allowance["remaining"]) == (2, 0)
    assert datetime.fromisoformat(allowance["next_available_at"]) == NEXT_MONDAY
    assert checkup_allowance(db, user, now=NEXT_MONDAY)["remaining"] == 2


def test_released_checkup_is_given_back(db):
    user = make_subscriber(db, "pro")
    usage = reserve_checkup(db, user)
    release_checkup(db, usage)
    assert checkup_allowance(db, user)["remaining"] == 1


def test_admins_are_not_limited(db):
    admin = make_subscriber(db, "pro", is_admin=True)
    for _ in range(5):
        assert reserve_checkup(db, admin).status == "started"   # recorded, never refused
    assert checkup_allowance(db, admin)["unlimited"] is True


# ── Through the real analyze endpoints ──────────────────────────────────────

class FakeAnalyzer:
    """Stands in for AgenticAnalyzer: returns a saved analysis id, or fails."""

    def __init__(self, fail=False):
        self.fail = fail

    async def analyze(self, **kwargs):
        if self.fail:
            raise RuntimeError("LLM timeout")
        return {"data": {"analysis_id": 4242, "recommended_tool_stacks": []}}


def json_request(goal):
    """A POST request carrying {"business_goal": goal}, as the app sends it."""
    body = json.dumps({"business_goal": goal}).encode()

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    return Request({"type": "http", "method": "POST", "path": "/",
                    "headers": [(b"content-type", b"application/json")]}, receive)


def run_stream(db, user, goal, fail=False):
    """Call /analyze/stream and return the event names it sent."""
    async def go():
        with patch("decision_engine.agentic_analyzer.create_analyzer", return_value=FakeAnalyzer(fail)), \
             patch("decision_engine.founder_context.build_founder_context", return_value=""):
            response = await analyze_business_goal_stream(json_request(goal), BackgroundTasks(), user, db)
            return [chunk async for chunk in response.body_iterator]
    chunks = asyncio.run(go())
    return [c.split("\n")[0].removeprefix("event: ") for c in chunks if c.startswith("event:")]


def test_stream_checkup_is_counted_then_refused(db):
    user = make_subscriber(db, "pro")
    assert "result" in run_stream(db, user, "How do I grow my bakery?")
    usage = db.query(CheckupUsage).filter_by(user_id=user.id).one()
    assert (usage.analysis_id, usage.status) == (4242, "completed")

    with pytest.raises(HTTPException) as refused:
        run_stream(db, user, "A different question about my bakery")
    assert refused.value.status_code == 429


def test_failed_stream_checkup_is_not_counted(db):
    user = make_subscriber(db, "pro")
    assert "error" in run_stream(db, user, "Grow my shop", fail=True)
    assert checkup_allowance(db, user)["remaining"] == 1
    usage = db.query(CheckupUsage).filter_by(user_id=user.id).one()
    assert (usage.status, usage.error) == ("failed", "LLM timeout")   # kept for Engine Health


def test_non_streaming_endpoint_is_limited_too(db):
    user = make_subscriber(db, "pro")

    def call(goal, fail=False):
        async def go():
            with patch("decision_engine.agentic_analyzer.create_analyzer", return_value=FakeAnalyzer(fail)), \
                 patch("decision_engine.founder_context.build_founder_context", return_value=""):
                return await analyze_business_goal(json_request(goal), BackgroundTasks(), user, db)
        return asyncio.run(go())

    with pytest.raises(HTTPException) as failed:
        call("First try", fail=True)
    assert failed.value.status_code == 500
    assert checkup_allowance(db, user)["remaining"] == 1   # failure given back

    assert call("Second try")["success"] is True
    with pytest.raises(HTTPException) as refused:
        call("Third try")
    assert refused.value.status_code == 429                 # not turned into a 500
