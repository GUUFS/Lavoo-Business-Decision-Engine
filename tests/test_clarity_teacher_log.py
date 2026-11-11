"""
Tests for the micromodel teacher's activity log (decision_engine/clarity_teacher.py),
which feeds the admin Micromodel page and header status pill.

The LLM and the embedding model are replaced with fakes, so no API calls are
made. Everything else (SQL queries, the clarity_teacher_runs and
clarity_teacher_calls tables) runs against real Postgres.
"""
import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from database.pg_models import ClarityCorpus, ClarityTeacherCall, ClarityTeacherRun
from decision_engine import clarity_teacher


class FakeAnalyzer:
    """Stands in for AgenticAnalyzer: answers from a dict of prompt -> verdict
    and counts how many times the "LLM" was called."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = 0

    async def generate_clarifying_questions(self, prompt):
        self.calls += 1
        answer = self.answers[prompt]
        if isinstance(answer, Exception):
            raise answer
        return answer


def add_live_decision(db, text, asked, outcome=None, path="reasoner", confidence=0.4):
    """A weak live micromodel decision, old enough for the teacher to pick up."""
    row = ClarityCorpus(
        submission_text=text, needs_clarification=asked, gap_types=[], questions=[], source="live",
        outcome=outcome, decision_path=path, confidence=confidence,
        created_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db.add(row)
    db.flush()
    return row


def run_batch(db, answers, trigger="scheduled"):
    """Run one teacher batch with the fake LLM; returns (result, fake)."""
    fake = FakeAnalyzer(answers)
    with patch("decision_engine.agentic_analyzer.create_analyzer", return_value=fake), \
         patch("decision_engine.clarity_engine._generate_embedding", return_value=[0.0] * 384):
        result = asyncio.run(clarity_teacher.run_teacher_batch(db, limit=20, trigger=trigger))
    return result, fake


@pytest.fixture(autouse=True)
def only_this_tests_rows(db):
    """Hide decisions left by other data in the database, so each test only
    sees the rows it creates (all rolled back afterwards)."""
    db.query(ClarityCorpus).filter(ClarityCorpus.source == "live").update(
        {"teacher_reviewed_at": datetime.now(UTC)}, synchronize_session=False
    )


def test_run_and_each_check_are_logged(db):
    agree = add_live_decision(db, "Grow my bakery revenue", asked=True, outcome="skipped")
    disagree = add_live_decision(db, "Launch a fintech app in Lagos", asked=False)
    result, fake = run_batch(db, {
        agree.submission_text: {"needs_clarification": True, "questions": [{"question": "Who are your customers?"}]},
        disagree.submission_text: {"needs_clarification": True, "questions": [{"question": "What is your budget?"}]},
    }, trigger="manual")

    assert result["reviewed"] == 2 and result["agreed"] == 1 and result["llm_calls"] == 2 and fake.calls == 2
    run = db.get(ClarityTeacherRun, result["run_id"])
    assert run.trigger == "manual" and run.finished_at is not None and run.error is None
    assert (run.reviewed, run.agreed, run.llm_calls, run.new_precedents) == (2, 1, 2, 2)

    calls = {c.corpus_id: c for c in db.query(ClarityTeacherCall).filter_by(run_id=run.id)}
    assert calls[agree.id].agreed is True and calls[agree.id].llm_questions == ["Who are your customers?"]
    assert calls[disagree.id].agreed is False
    assert calls[disagree.id].micromodel_asked is False and calls[disagree.id].llm_asked is True
    assert all(c.called_llm and c.duration_ms is not None for c in calls.values())


def test_llm_error_is_logged_and_decision_left_for_retry(db):
    row = add_live_decision(db, "Open a second shop", asked=True)
    result, _ = run_batch(db, {row.submission_text: {"error": "rate limited"}})

    assert result["errors"] == 1 and result["reviewed"] == 0
    call = db.query(ClarityTeacherCall).filter_by(run_id=result["run_id"]).one()
    assert call.error == "rate limited" and call.called_llm is True and call.agreed is None
    db.refresh(row)
    assert row.teacher_reviewed_at is None  # picked again next run


def test_exception_on_one_decision_does_not_stop_the_run(db):
    bad = add_live_decision(db, "Prompt that breaks", asked=True, outcome="skipped")
    good = add_live_decision(db, "Prompt that works", asked=False)
    result, _ = run_batch(db, {
        bad.submission_text: RuntimeError("LLM timeout"),
        good.submission_text: {"needs_clarification": False, "questions": []},
    })

    assert result["errors"] == 1 and result["reviewed"] == 1 and result["agreed"] == 1
    errors = [c.error for c in db.query(ClarityTeacherCall).filter_by(run_id=result["run_id"])]
    assert "LLM timeout" in errors


def test_whole_run_failure_is_recorded(db):
    with patch.object(clarity_teacher, "_candidates", side_effect=RuntimeError("db down")):
        result, _ = run_batch(db, {})
    run = db.get(ClarityTeacherRun, result["run_id"])
    assert run.error == "db down" and run.finished_at is not None and result["error"] == "db down"


def test_activity_feed_for_admin_page(db):
    first = add_live_decision(db, "Hire my first salesperson", asked=True)
    first_result, _ = run_batch(db, {first.submission_text: {
        "needs_clarification": True, "questions": [{"question": "What does the role need to sell?"}]}})
    # Same prompt again: the earlier LLM answer is reused, no new LLM call.
    add_live_decision(db, "Hire my first salesperson", asked=False)
    result, fake = run_batch(db, {})
    assert fake.calls == 0 and result["llm_calls"] == 0 and result["reviewed"] == 1

    clarity_teacher.next_scheduled_run_at = datetime(2030, 1, 1, tzinfo=UTC)
    try:
        activity = clarity_teacher.teacher_activity(db, runs=5, calls=5)
    finally:
        clarity_teacher.next_scheduled_run_at = None

    assert activity["next_run_at"] == "2030-01-01T00:00:00+00:00"
    assert activity["run_every_hours"] == 3
    assert {r["id"] for r in activity["runs"]} >= {first_result["run_id"], result["run_id"]}

    # (Inside one test transaction Postgres now() is constant, so rows are
    # matched by run id rather than by time order.)
    calls = {c["run_id"]: c for c in activity["calls"]}
    assert calls[first_result["run_id"]]["called_llm"] is True
    reused = calls[result["run_id"]]
    assert reused["called_llm"] is False and reused["agreed"] is False and reused["micromodel_asked"] is False
    first_call = db.query(ClarityTeacherCall).filter_by(run_id=first_result["run_id"]).one()
    assert activity["last_llm_call_at"] == first_call.created_at.isoformat()
