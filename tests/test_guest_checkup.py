"""
Tests for the ad checkup run before signup (decision_engine/guest_checkup.py
and api/routes/public_checkup.py).

  - Free limits: per browser, per internet address, and for everyone per day.
  - The visitor only gets the teaser, never the full plan.
  - Claiming after signup hands the analysis over, is safe to repeat, refuses
    another account, and doesn't use up a monthly or weekly checkup.
  - Unclaimed checkups are deleted after 7 days.

The analyzer (LLM) is faked; everything else runs against real Postgres.
"""
import asyncio
import itertools
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi import BackgroundTasks, HTTPException
from starlette.requests import Request

from api.routes import public_checkup
from database.pg_models import BusinessAnalysis, CheckupUsage, GuestCheckup, User
from decision_engine import guest_checkup
from decision_engine.checkup_limits import checkup_allowance

_ids = itertools.count(1)


def make_user(db):
    """A signed-up user with no subscription yet."""
    n = next(_ids)
    user = User(name=f"Guest {n}", email=f"guest{n}@test.local", password="x", confirm_password="x")
    db.add(user)
    db.commit()
    return user


def finished_checkup(db, created_at=None, visitor="v-1"):
    """A guest checkup whose analysis (no owner) is saved."""
    analysis = BusinessAnalysis(
        user_id=None, business_goal="My bakery has no customers on weekdays",
        primary_bottleneck={"title": "Nobody knows you exist", "description": "No marketing",
                            "consequence": "Empty weekdays"},
        secondary_constraints=[{"title": "Prices"}, {"title": "Opening hours"}],
        action_plans=[{"step": 1}, {"step": 2}, {"step": 3}],
        recommended_tool_stacks=[{"tools": ["Canva", {"tool_name": "Mailchimp"}, "Canva"]}],
        estimated_days=30,
    )
    db.add(analysis)
    db.commit()
    row = guest_checkup.start(db, analysis.business_goal, visitor, "ip-1")
    guest_checkup.finish(db, row, analysis_id=analysis.id)
    if created_at:
        row.created_at = created_at
        db.commit()
    return row, analysis


@pytest.fixture(autouse=True)
def roomy_limits(monkeypatch):
    """Small, known limits for every test."""
    monkeypatch.setattr(guest_checkup, "GUEST_CHECKUPS_PER_VISITOR", 2)
    monkeypatch.setattr(guest_checkup, "GUEST_CHECKUPS_PER_IP", 3)
    monkeypatch.setattr(guest_checkup, "GUEST_CHECKUPS_PER_DAY", 1000)


# ── Limits ──────────────────────────────────────────────────────────────────

def test_a_browser_gets_two_free_checkups_a_day(db):
    guest_checkup.start(db, "Grow my shop please", "browser-a", "ip-a")
    guest_checkup.start(db, "Grow my shop please", "browser-a", "ip-a")
    with pytest.raises(HTTPException) as refused:
        guest_checkup.start(db, "Grow my shop please", "browser-a", "ip-a")
    assert refused.value.status_code == 429
    assert refused.value.detail["code"] == "guest_visitor_limit"


def test_a_failed_checkup_is_given_back(db):
    row = guest_checkup.start(db, "Grow my shop please", "browser-b", "ip-b")
    guest_checkup.finish(db, row, error="LLM timeout")
    guest_checkup.start(db, "Grow my shop please", "browser-b", "ip-b")
    guest_checkup.start(db, "Grow my shop please", "browser-b", "ip-b")   # still allowed


def test_one_network_is_limited_even_with_new_browsers(db):
    for n in range(3):
        guest_checkup.start(db, "Grow my shop please", f"browser-c{n}", "ip-c")
    with pytest.raises(HTTPException) as refused:
        guest_checkup.start(db, "Grow my shop please", "browser-c9", "ip-c")
    assert refused.value.detail["code"] == "guest_ip_limit"


def test_everyone_together_has_a_daily_cap(db, monkeypatch):
    monkeypatch.setattr(guest_checkup, "GUEST_CHECKUPS_PER_DAY",
                        db.query(GuestCheckup).filter(GuestCheckup.status.in_(guest_checkup._COUNTED)).count() + 1)
    guest_checkup.start(db, "Grow my shop please", "browser-d", "ip-d")
    with pytest.raises(HTTPException) as refused:
        guest_checkup.start(db, "Grow my shop please", "browser-e", "ip-e")
    assert refused.value.detail["code"] == "guest_daily_limit"


def test_yesterdays_checkups_no_longer_count(db):
    for _ in range(2):
        row = guest_checkup.start(db, "Grow my shop please", "browser-f", "ip-f")
        row.created_at = datetime.now(UTC) - timedelta(hours=25)
        db.commit()
    guest_checkup.start(db, "Grow my shop please", "browser-f", "ip-f")   # a new day


def test_goal_must_be_a_sensible_length():
    with pytest.raises(HTTPException) as short:
        guest_checkup.clean_goal("  hi  ")
    assert short.value.status_code == 400
    with pytest.raises(HTTPException):
        guest_checkup.clean_goal("x" * 2001)
    assert guest_checkup.clean_goal("  Grow my shop  ") == "Grow my shop"


def test_the_ip_is_never_stored_as_is():
    hashed = guest_checkup.hash_ip("1.2.3.4")
    assert hashed != "1.2.3.4" and len(hashed) == 64
    assert guest_checkup.hash_ip(None) is None


# ── Teaser ──────────────────────────────────────────────────────────────────

def test_teaser_shows_only_what_to_fix_and_counts(db):
    _, analysis = finished_checkup(db, visitor="v-teaser")
    teaser = guest_checkup.teaser(analysis)
    assert teaser["what_to_fix"]["title"] == "Nobody knows you exist"
    assert teaser["locked"] == {"other_problems": 2, "action_steps": 3, "tools": 2, "roadmap_days": 30}
    # The full plan's content is not in it.
    assert "Prices" not in json.dumps(teaser) and "Canva" not in json.dumps(teaser)


# ── Claim ───────────────────────────────────────────────────────────────────

def test_claim_hands_the_analysis_over_without_using_a_checkup(db):
    row, analysis = finished_checkup(db, visitor="v-claim")
    user = make_user(db)
    # 1. The user becomes the owner.
    assert guest_checkup.claim(db, row.token, user) == analysis.id
    db.refresh(analysis)
    assert analysis.user_id == user.id and row.status == "claimed" and row.claimed_by == user.id
    # 2. It shows in their history as 'guest' and doesn't use up a checkup.
    usage = db.query(CheckupUsage).filter_by(user_id=user.id).one()
    assert (usage.status, usage.analysis_id) == ("guest", analysis.id)
    assert checkup_allowance(db, user)["used"] == 0
    # 3. Claiming again is safe.
    assert guest_checkup.claim(db, row.token, user) == analysis.id
    assert db.query(CheckupUsage).filter_by(user_id=user.id).count() == 1


def test_another_account_cannot_claim_it(db):
    row, _ = finished_checkup(db, visitor="v-other")
    guest_checkup.claim(db, row.token, make_user(db))
    with pytest.raises(HTTPException) as refused:
        guest_checkup.claim(db, row.token, make_user(db))
    assert refused.value.status_code == 404


def test_unknown_or_unfinished_checkup_cannot_be_claimed(db):
    user = make_user(db)
    with pytest.raises(HTTPException):
        guest_checkup.claim(db, "not-a-real-token-123", user)
    running = guest_checkup.start(db, "Grow my shop please", "v-running", "ip-r")
    with pytest.raises(HTTPException):
        guest_checkup.claim(db, running.token, user)


# ── Clean-up ────────────────────────────────────────────────────────────────

def test_unclaimed_checkups_are_deleted_after_seven_days(db):
    old = datetime.now(UTC) - timedelta(days=8)
    stale, stale_analysis = finished_checkup(db, created_at=old, visitor="v-old")
    kept, kept_analysis = finished_checkup(db, created_at=old, visitor="v-kept")
    fresh, _ = finished_checkup(db, visitor="v-new")
    guest_checkup.claim(db, kept.token, make_user(db))
    stale_id, stale_analysis_id = stale.id, stale_analysis.id

    assert guest_checkup.delete_unclaimed(db) >= 1
    # 1. The old unclaimed one and its ownerless analysis are gone.
    assert db.get(GuestCheckup, stale_id) is None
    assert db.get(BusinessAnalysis, stale_analysis_id) is None
    # 2. The claimed one and the new one stay.
    assert db.get(GuestCheckup, kept.id) is not None and db.get(BusinessAnalysis, kept_analysis.id) is not None
    assert db.get(GuestCheckup, fresh.id) is not None


# ── Through the real stream endpoint ────────────────────────────────────────

class FakeAnalyzer:
    """Stands in for AgenticAnalyzer: saves an ownerless analysis, or fails."""

    def __init__(self, db, fail=False):
        self.db, self.fail = db, fail

    async def analyze(self, **kwargs):
        assert kwargs["user_id"] is None
        if self.fail:
            raise RuntimeError("LLM timeout")
        analysis = BusinessAnalysis(user_id=None, business_goal=kwargs["user_query"],
                                    primary_bottleneck={"title": "Slow follow-up"},
                                    action_plans=[{"step": 1}])
        self.db.add(analysis)
        self.db.commit()
        return {"data": {"analysis_id": analysis.id, "recommended_tool_stacks": []}}


def run_stream(db, visitor, fail=False):
    """Call /api/public/checkup/stream and return its events as (name, data)."""
    async def go():
        body = public_checkup.GuestCheckupRequest(business_goal="My leads never reply to me", visitor_id=visitor,
                                                  utm_source="facebook", utm_campaign="nov")
        request = Request({"type": "http", "method": "POST", "path": "/", "headers": [],
                           "client": ("9.9.9.9", 1)})
        with patch("decision_engine.agentic_analyzer.create_analyzer", return_value=FakeAnalyzer(db, fail)), \
             patch("decision_engine.tool_discovery.discover_tools_for_analysis"):
            response = await public_checkup.run_guest_checkup(body, request, BackgroundTasks(), db)
            return [chunk async for chunk in response.body_iterator]
    events = []
    for chunk in asyncio.run(go()):
        if chunk.startswith("event:"):
            name, data = chunk.strip().split("\n", 1)
            events.append((name.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return events


def test_stream_returns_only_the_token_and_teaser(db):
    events = run_stream(db, "v-stream")
    name, data = events[-1]
    assert name == "result" and set(data) == {"token", "teaser"}
    assert data["teaser"]["what_to_fix"]["title"] == "Slow follow-up"
    row = guest_checkup.find(db, data["token"])
    assert (row.status, row.utm_source) == ("completed", "facebook")


def test_a_failed_stream_shows_a_plain_message(db):
    events = run_stream(db, "v-stream-fail", fail=True)
    assert events[-1] == ("error", {"message": "The checkup couldn't finish. Please try again."})
