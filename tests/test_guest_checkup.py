"""
Tests for the ad checkup run before signup (decision_engine/guest_checkup.py
and api/routes/public_checkup.py).

  - Free limits: per browser, per internet address, and for everyone per day.
  - The visitor only gets the teaser: both problems in full, the action
    plan's titles, and nothing of what to stop doing or the Missions.
  - Every failure is logged; more than 3 in an hour emails the admin once.
  - Claiming copies the ad's UTM tags onto the new account.
  - Claiming after signup hands the analysis over, is safe to repeat, refuses
    another account, and doesn't use up a monthly or weekly checkup.
  - Unclaimed checkups are deleted after 7 days.

The analyzer (LLM) is faked; everything else runs against real Postgres.
"""
import asyncio
import itertools
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException
from starlette.requests import Request

from api.routes import public_checkup
from database.pg_models import BusinessAnalysis, CheckupFailure, CheckupUsage, GuestCheckup, User
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


def finished_checkup(db, created_at=None, visitor="v-1", utm=(None, None)):
    """A guest checkup whose analysis (no owner) is saved."""
    analysis = BusinessAnalysis(
        user_id=None, business_goal="My bakery has no customers on weekdays",
        primary_bottleneck={"title": "Nobody knows you exist", "description": "No marketing",
                            "consequence": "Empty weekdays"},
        secondary_constraints=[{"title": "Prices", "description": "Too high for weekdays"}, "Opening hours"],
        action_plans=[{"title": "Post daily on Instagram", "what_to_do": ["Film the ovens at 6am"]},
                      {"action_title": "Start a loyalty card", "what_to_do": ["Print 200 cards"]},
                      {"what_to_do": ["Secret step"]}],
        what_to_stop="Stop paying for flyers",
        execution_roadmap=[{"phase": 1, "tasks": ["Film the ovens", "film the  ovens", "Print cards"]},
                           {"phase": 2, "tasks": ["Hand out cards"]}],
        recommended_tool_stacks=[{"tools": ["Canva", {"tool_name": "Mailchimp"}, "Canva"]}],
        estimated_days=30,
    )
    db.add(analysis)
    db.commit()
    row = guest_checkup.start(db, analysis.business_goal, visitor, "ip-1", *utm)
    guest_checkup.finish(db, row.id, analysis_id=analysis.id)
    db.refresh(row)
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


def test_finish_is_saved_even_when_the_session_let_go_of_the_row(db):
    """While the answer streams, the request's session no longer tracks the
    row (that is what happened live). The outcome must still be saved."""
    row = guest_checkup.start(db, "Grow my shop please", "browser-detached", "ip-x")
    row_id = row.id
    db.expunge(row)                                   # the session lets go of it
    guest_checkup.finish(db, row_id, error="LLM timeout")
    saved = db.get(GuestCheckup, row_id)
    assert (saved.status, saved.error) == ("failed", "LLM timeout")


def test_a_failed_checkup_is_given_back(db):
    row = guest_checkup.start(db, "Grow my shop please", "browser-b", "ip-b")
    guest_checkup.finish(db, row.id, error="LLM timeout")
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

def test_teaser_shows_both_problems_and_only_the_plan_titles(db):
    _, analysis = finished_checkup(db, visitor="v-teaser")
    teaser = guest_checkup.teaser(analysis)
    # 1. The Primary Problem and the Secondary Problems, in full.
    assert teaser["primary_problem"] == {"title": "Nobody knows you exist", "description": "No marketing",
                                         "consequence": "Empty weekdays"}
    assert teaser["secondary_problems"] == [
        {"number": "02", "title": "Prices", "description": "Too high for weekdays"},
        {"number": "03", "title": "Opening hours", "description": "Opening hours"},
    ]
    # 2. The action plan: titles only (a missing title gets "Action N").
    assert teaser["action_plan_titles"] == ["Post daily on Instagram", "Start a loyalty card", "Action 3"]
    # 3. Behind the card: only that they exist (a repeated roadmap task counts once).
    assert teaser["locked"] == {"main_priority": False, "stop_doing": True, "missions": 3}
    # 4. None of the hidden content is in it.
    sent = json.dumps(teaser)
    for hidden in ("Film the ovens", "Secret step", "Stop paying for flyers", "Hand out cards", "Canva"):
        assert hidden not in sent


def test_teaser_reads_sections_saved_as_json_text(db):
    """Many analyses store each section as JSON TEXT. The teaser must unpack
    it like the result page does, not treat each character as an item."""
    analysis = BusinessAnalysis(
        user_id=None, business_goal="I want an advertising business",
        primary_bottleneck=json.dumps({"title": "No defined offer", "description": "No package",
                                       "consequence": "Lost revenue"}),
        secondary_constraints=json.dumps([{"title": "No portfolio", "description": "Nothing to show"}]),
        action_plans=json.dumps([{"title": "Pick one niche", "what_to_do": ["Hidden step"]},
                                 {"title": "Build one package"}]),
        strategic_priority="Hidden priority",
    )
    db.add(analysis)
    db.commit()
    teaser = guest_checkup.teaser(analysis)
    assert teaser["primary_problem"]["title"] == "No defined offer"
    assert [p["title"] for p in teaser["secondary_problems"]] == ["No portfolio"]
    assert teaser["action_plan_titles"] == ["Pick one niche", "Build one package"]
    assert teaser["locked"]["main_priority"] is True
    assert "Hidden step" not in json.dumps(teaser) and "Hidden priority" not in json.dumps(teaser)


# ── Failures ────────────────────────────────────────────────────────────────

def test_every_failure_is_logged_and_four_in_an_hour_alert_once(db, monkeypatch):
    sent = []
    monkeypatch.setattr(guest_checkup, "_send_failure_alert", lambda count, latest: sent.append(count))
    # Start from a clean hour, so other tests' failures don't count.
    db.query(CheckupFailure).delete()
    db.commit()
    # 1. Three failures: logged, no email yet.
    for n in range(3):
        assert guest_checkup.record_failure(db, "browser", f"Network dropped {n}", visitor_id="v-f") is False
    assert db.query(CheckupFailure).count() == 3
    # 2. The fourth: one email.
    assert guest_checkup.record_failure(db, "server", "LLM timeout") is True
    assert sent == [4]
    # 3. The fifth in the same hour: logged, but no second email.
    assert guest_checkup.record_failure(db, "server", "LLM timeout") is False
    assert sent == [4] and db.query(CheckupFailure).count() == 5


def test_a_visitor_closing_the_page_is_logged_but_never_alerts(db, monkeypatch):
    sent = []
    monkeypatch.setattr(guest_checkup, "_send_failure_alert", lambda count, latest: sent.append(count))
    db.query(CheckupFailure).delete()
    db.commit()
    for _ in range(6):
        guest_checkup.record_failure(db, "server", guest_checkup.VISITOR_LEFT)
    assert sent == [] and db.query(CheckupFailure).count() == 6


def test_a_failed_server_run_goes_in_the_failure_log(db):
    row = guest_checkup.start(db, "Grow my shop please", "browser-log", "ip-log")
    guest_checkup.finish(db, row.id, error="LLM timeout")
    logged = db.query(CheckupFailure).filter_by(checkup_id=row.id).one()
    assert (logged.source, logged.reason) == ("server", "LLM timeout")


# ── Claim ───────────────────────────────────────────────────────────────────

def test_claim_hands_the_analysis_over_without_using_a_checkup(db):
    row, analysis = finished_checkup(db, visitor="v-claim", utm=("facebook", "nov-launch"))
    user = make_user(db)
    # 1. The user becomes the owner.
    assert guest_checkup.claim(db, row.token, user) == analysis.id
    db.refresh(analysis)
    assert analysis.user_id == user.id and row.status == "claimed" and row.claimed_by == user.id
    # 2. It shows in their history as 'guest' and doesn't use up a checkup.
    usage = db.query(CheckupUsage).filter_by(user_id=user.id).one()
    assert (usage.status, usage.analysis_id) == ("guest", analysis.id)
    assert checkup_allowance(db, user)["used"] == 0
    # 3. The account remembers which ad brought them.
    db.refresh(user)
    assert (user.utm_source, user.utm_campaign) == ("facebook", "nov-launch")
    # 4. Claiming again is safe.
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
                                    action_plans=[{"title": "Reply within an hour", "what_to_do": ["Hidden"]}])
        self.db.add(analysis)
        self.db.commit()
        return {"data": {"analysis_id": analysis.id, "recommended_tool_stacks": []}}


def _stream_request(visitor):
    """The body and request the check-up page sends."""
    body = public_checkup.GuestCheckupRequest(business_goal="My leads never reply to me", visitor_id=visitor,
                                              utm_source="facebook", utm_campaign="nov")
    request = Request({"type": "http", "method": "POST", "path": "/", "headers": [],
                       "client": ("9.9.9.9", 1)})
    return body, request


def _parse(chunks):
    """Server-sent chunks as (event name, data) pairs."""
    events = []
    for chunk in chunks:
        if chunk.startswith("event:"):
            name, data = chunk.strip().split("\n", 1)
            events.append((name.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return events


def run_stream(db, visitor, fail=False):
    """Call /api/public/checkup/stream and return its events as (name, data)."""
    async def go():
        body, request = _stream_request(visitor)
        with patch("decision_engine.agentic_analyzer.create_analyzer", return_value=FakeAnalyzer(db, fail)), \
             patch("decision_engine.tool_discovery.discover_tools_for_analysis", new=AsyncMock()), \
             patch.object(public_checkup, "_task_session", return_value=db):
            response = await public_checkup.run_guest_checkup(body, request, BackgroundTasks(), db)
            return [chunk async for chunk in response.body_iterator]
    return _parse(asyncio.run(go()))


def test_stream_returns_only_the_token_and_teaser(db):
    events = run_stream(db, "v-stream")
    # 1. The token comes first, so a dropped connection can pick the result up later.
    assert events[0][0] == "started"
    name, data = events[-1]
    assert data["token"] == events[0][1]["token"]
    assert name == "result" and set(data) == {"token", "teaser"}
    assert data["teaser"]["primary_problem"]["title"] == "Slow follow-up"
    assert data["teaser"]["action_plan_titles"] == ["Reply within an hour"]
    assert "Hidden" not in json.dumps(data)
    row = guest_checkup.find(db, data["token"])
    assert (row.status, row.utm_source) == ("completed", "facebook")


def test_a_failed_stream_shows_a_plain_message(db):
    events = run_stream(db, "v-stream-fail", fail=True)
    assert events[-1] == ("error", {"message": "The check-up couldn't finish. Please try again."})


def test_a_dropped_connection_does_not_lose_the_check_up(db):
    """The page disconnects right after `started` (mobile data). The analysis
    keeps running, and the page can fetch the result by its token."""
    async def go():
        body, request = _stream_request("v-dropped")
        with patch("decision_engine.agentic_analyzer.create_analyzer", return_value=FakeAnalyzer(db)), \
             patch("decision_engine.tool_discovery.discover_tools_for_analysis", new=AsyncMock()), \
             patch.object(public_checkup, "_task_session", return_value=db):
            response = await public_checkup.run_guest_checkup(body, request, BackgroundTasks(), db)
            stream = response.body_iterator
            first = await stream.__anext__()          # only the token arrives
            await stream.aclose()                     # then the connection drops
            await asyncio.gather(*public_checkup._running)   # the analysis carries on
            return first
    token = _parse([asyncio.run(go())])[0][1]["token"]
    found = public_checkup.get_checkup(token, db)["data"]
    assert found["status"] == "completed" and found["teaser"]["primary_problem"]["title"] == "Slow follow-up"


def test_status_shows_running_and_failed_without_a_teaser(db):
    running = guest_checkup.start(db, "Grow my shop please", "v-status", "ip-s")
    assert public_checkup.get_checkup(running.token, db)["data"] | {"token": None} == {
        "token": None, "status": "running", "claimed": False, "teaser": None}
    guest_checkup.finish(db, running.id, error="LLM timeout")
    assert public_checkup.get_checkup(running.token, db)["data"]["status"] == "failed"
    with pytest.raises(HTTPException):
        public_checkup.get_checkup("not-a-real-token-123", db)


# ── Browser failures and Meta events ────────────────────────────────────────

def test_the_page_can_report_a_failure(db):
    public_checkup.report_failure(public_checkup.FailureReport(reason="Network dropped", visitor_id="v-page"), db)
    assert db.query(CheckupFailure).filter_by(source="browser", visitor_id="v-page").count() == 1


def test_only_the_ad_pages_events_are_relayed_to_meta():
    request = Request({"type": "http", "method": "POST", "path": "/", "headers": [], "client": ("9.9.9.9", 1)})
    tasks = BackgroundTasks()
    public_checkup.track_event(public_checkup.TrackRequest(event="ViewGate", event_id="e-1"), request, tasks)
    assert len(tasks.tasks) == 1
    with pytest.raises(HTTPException) as refused:
        public_checkup.track_event(public_checkup.TrackRequest(event="Purchase", event_id="e-2"), request, tasks)
    assert refused.value.status_code == 400


def test_meta_events_do_nothing_until_set_up(monkeypatch):
    from services import meta_capi
    monkeypatch.delenv("META_PIXEL_ID", raising=False)
    monkeypatch.delenv("META_CAPI_TOKEN", raising=False)
    assert meta_capi.send_event("ViewContent", "e-3") is False


def test_meta_event_hashes_the_email(monkeypatch):
    from services import meta_capi
    monkeypatch.setenv("META_PIXEL_ID", "123")
    monkeypatch.setenv("META_CAPI_TOKEN", "tok")
    posted = {}

    class Ok:
        status_code = 200

    def fake_post(url, params, json, timeout):
        posted.update(url=url, body=json)
        return Ok()

    monkeypatch.setattr(meta_capi.requests, "post", fake_post)
    assert meta_capi.send_event("CompleteRegistration", "e-4", email=" Ada@Example.com ") is True
    event = posted["body"]["data"][0]
    assert posted["url"].endswith("/123/events") and event["event_id"] == "e-4"
    assert event["user_data"]["em"] == [meta_capi._sha256("ada@example.com")]
    assert "Ada@Example.com" not in str(posted)
