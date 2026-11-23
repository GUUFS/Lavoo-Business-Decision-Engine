"""
Check-up speed (decision_engine/agentic_analyzer.py analyze(), the ad
check-up in api/routes/public_checkup.py and decision_engine/guest_checkup.py):

  - the safety check and Stage 1 run at the same time, and an unsafe query
    stops Stage 1;
  - the early preview arrives straight after the action plans, before the
    roadmap and the tool matching (which run at the same time);
  - the ad page gets its teaser from that preview, once;
  - signing up while the check-up is still finishing waits for it.

The LLM stages are faked; the timing is checked with asyncio events.
"""
import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from api.routes import public_checkup
from database.pg_models import BusinessAnalysis
from decision_engine import guest_checkup
from decision_engine.agentic_analyzer import AgenticAnalyzer
from tests.test_guest_checkup import _parse, _stream_request, make_user

PRIMARY = {"primary_bottleneck": {"title": "Slow follow-up", "description": "d", "consequence": "c"},
           "strategic_priority": "Reply fast", "what_to_stop": "Stop waiting", "recommendation_mode": "automation_stack"}
SECONDARY = {"secondary_constraints": [{"title": "No CRM", "description": "Leads live in DMs"}]}
PLANS = {"action_plans": [{"id": 1, "title": "Reply within an hour", "what_to_do": ["Hidden step"]}],
         "exclusions_note": ""}
ROADMAP = {"execution_roadmap": [{"phase": 1, "tasks": ["Call back", "Log it"]}], "motivational_quote": "Go"}


def _analyzer(monkeypatch, safe=True):
    """A real AgenticAnalyzer whose LLM stages are fakes that record the order."""
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    analyzer = AgenticAnalyzer(db_session=None)
    log, tools_may_finish = [], asyncio.Event()

    async def safety(query):
        # 1. Stage 1 has already started while the safety check runs.
        await asyncio.sleep(0.05)
        log.append("safety")
        return {"is_safe": safe, "reason": "Fraud", "suggestions": []}

    async def stage1(query):
        log.append("stage1 started")
        await asyncio.sleep(0.02)
        log.append("stage1 done")
        return json.loads(json.dumps(PRIMARY))

    async def stage2(query, primary):
        return json.loads(json.dumps(SECONDARY))

    async def stage3(query, primary, secondary, assign_tools=True):
        assert assign_tools is False
        return json.loads(json.dumps(PLANS))

    async def assign(action_plans, user_query):
        # 2. Tool matching only finishes once the preview has gone out.
        await tools_may_finish.wait()
        log.append("tools done")
        for plan in action_plans:
            plan["step_tools"] = [{"tool_name": "Zapier"}]
        return action_plans

    async def stacks(**kwargs):
        return {"recommended_tool_stacks": [], "single_tool_recommendation": None}

    async def roadmap(query, plans):
        await asyncio.sleep(0.01)
        log.append("roadmap done")
        return json.loads(json.dumps(ROADMAP))

    async def save(**kwargs):
        log.append("saved")
        assert kwargs["action_plans_result"]["action_plans"][0]["step_tools"]
        return 42

    monkeypatch.setattr(analyzer, "_check_query_safety", safety)
    monkeypatch.setattr(analyzer, "_stage1_primary_bottleneck", stage1)
    monkeypatch.setattr(analyzer, "_stage2_secondary_constraints", stage2)
    monkeypatch.setattr(analyzer, "_stage3_action_plans", stage3)
    monkeypatch.setattr(analyzer, "_assign_tools_to_steps", assign)
    monkeypatch.setattr(analyzer, "_stage3_automation_stacks", stacks)
    monkeypatch.setattr(analyzer, "_stage4_roadmap_and_motivation", roadmap)
    monkeypatch.setattr(analyzer, "_save_to_database", save)
    monkeypatch.setattr(analyzer, "_format_for_frontend", lambda **kwargs: {"data": {"analysis_id": 42}})
    return analyzer, log, tools_may_finish


def test_safety_and_stage1_run_together_and_the_preview_comes_straight_after_the_plans(monkeypatch):
    analyzer, log, tools_may_finish = _analyzer(monkeypatch)
    previews = []

    async def preview(data):
        # Neither the roadmap nor the tools are done when the preview arrives.
        assert "roadmap done" not in log and "tools done" not in log and "saved" not in log
        previews.append(data)
        tools_may_finish.set()

    result = asyncio.run(analyzer.analyze("My leads never reply", user_id=None, preview_callback=preview))
    # 1. Stage 1 started before the safety check answered.
    assert log.index("stage1 started") < log.index("safety")
    # 2. One preview, with what the teaser needs; then the tools; then the save.
    assert len(previews) == 1
    assert previews[0]["primary_bottleneck"]["title"] == "Slow follow-up"
    assert previews[0]["action_plans"][0]["title"] == "Reply within an hour"
    assert "roadmap done" in log
    assert log[-1] == "saved" and {"tools done", "roadmap done"} <= set(log)
    assert result["data"]["analysis_id"] == 42


def test_without_a_preview_the_analysis_is_unchanged(monkeypatch):
    analyzer, log, tools_may_finish = _analyzer(monkeypatch)
    tools_may_finish.set()
    asyncio.run(analyzer.analyze("My leads never reply", user_id=None))
    assert log[-1] == "saved" and {"tools done", "roadmap done"} <= set(log)


def test_an_unsafe_query_stops_stage1(monkeypatch):
    analyzer, log, _ = _analyzer(monkeypatch, safe=False)

    async def stage1_slow(query):
        log.append("stage1 started")
        await asyncio.sleep(5)
        log.append("stage1 done")

    monkeypatch.setattr(analyzer, "_stage1_primary_bottleneck", stage1_slow)
    with pytest.raises(ValueError, match="UNSAFE_QUERY::Fraud"):
        asyncio.run(analyzer.analyze("Help me launder money", user_id=None))
    assert "stage1 done" not in log


# ── The ad page ──────────────────────────────────────────────────────────────

class PreviewAnalyzer:
    """Sends the early preview, then saves (or fails after the preview)."""

    def __init__(self, db, fail_after_preview=False):
        self.db, self.fail_after_preview = db, fail_after_preview

    async def analyze(self, **kwargs):
        await kwargs["preview_callback"]({**PRIMARY, **SECONDARY, **PLANS, **ROADMAP})
        if self.fail_after_preview:
            raise RuntimeError("Tool search failed")
        analysis = BusinessAnalysis(user_id=None, business_goal=kwargs["user_query"],
                                    primary_bottleneck=PRIMARY["primary_bottleneck"],
                                    action_plans=PLANS["action_plans"])
        self.db.add(analysis)
        self.db.commit()
        return {"data": {"analysis_id": analysis.id, "recommended_tool_stacks": []}}


def _run(db, visitor, fail_after_preview=False):
    """Call the stream endpoint with the PreviewAnalyzer; return its events."""
    async def go():
        body, request = _stream_request(visitor)
        with patch("decision_engine.agentic_analyzer.create_analyzer",
                   return_value=PreviewAnalyzer(db, fail_after_preview)), \
             patch("decision_engine.tool_discovery.discover_tools_for_analysis", new=AsyncMock()), \
             patch.object(public_checkup, "_task_session", return_value=db):
            from fastapi import BackgroundTasks
            response = await public_checkup.run_guest_checkup(body, request, BackgroundTasks(), db)
            return [chunk async for chunk in response.body_iterator]
    return _parse(asyncio.run(go()))


def test_the_page_gets_the_early_teaser_once(db):
    events = _run(db, "v-speed")
    results = [data for name, data in events if name == "result"]
    assert len(results) == 1
    teaser = results[0]["teaser"]
    assert teaser["primary_problem"]["title"] == "Slow follow-up"
    assert teaser["secondary_problems"][0]["title"] == "No CRM"
    assert teaser["action_plan_titles"] == ["Reply within an hour"]
    assert teaser["locked"]["missions"] == 2
    assert "Hidden step" not in json.dumps(results[0])
    assert guest_checkup.find(db, results[0]["token"]).status == "completed"


def test_a_failure_after_the_teaser_sends_no_error_to_the_page(db):
    events = _run(db, "v-speed-fail", fail_after_preview=True)
    assert [name for name, _ in events] == ["started", "result"]
    assert guest_checkup.find(db, events[0][1]["token"]).status == "failed"


def test_signing_up_while_it_finishes_waits_for_it(db, monkeypatch):
    user = make_user(db)
    row = guest_checkup.start(db, "Grow my shop please", "v-wait", "ip-wait")
    analysis = BusinessAnalysis(user_id=None, business_goal="Grow my shop please")
    db.add(analysis)
    db.flush()
    checkup_id, token = row.id, row.token
    waits = []

    def finish_while_waiting(seconds):
        # The analysis finishes while claim() is waiting.
        waits.append(seconds)
        guest_checkup.finish(db, checkup_id, analysis_id=analysis.id)

    monkeypatch.setattr(guest_checkup.time, "sleep", finish_while_waiting)
    assert guest_checkup.claim(db, token, user) == analysis.id
    assert len(waits) == 1


def test_the_early_teaser_without_a_roadmap_still_shows_missions():
    """The preview has no roadmap yet: one blurred Mission row per plan."""
    teaser = guest_checkup.teaser_from_data({**PRIMARY, **SECONDARY, **PLANS, "execution_roadmap": []})
    assert teaser["locked"]["missions"] == 1
    assert teaser["locked"]["main_priority"] and teaser["locked"]["stop_doing"]
