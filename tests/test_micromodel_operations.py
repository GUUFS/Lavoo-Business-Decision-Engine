"""
The admin Micromodel operations page (decision_engine/clarity_teacher.py):

  - every teacher run records, in plain words, why it did or didn't call
    the LLM (nothing new, too new, confident copies, reused answers, errors);
  - the schedule (every 3 hours) is timed from the last run in the database,
    so a server restart doesn't push the next run back;
  - the prompt history shows each prompt start to finish: the micromodel's
    questions and reasoning, the user's answers, the LLM's questions, and
    what was learned (the trusted example made, and later prompts using it).
"""
import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from database.pg_models import ClarityCorpus, ClarityTeacherCall, ClarityTeacherRun, User
from decision_engine import clarity_teacher
from decision_engine.clarity_teacher import (
    RUN_EVERY_SECONDS,
    decision_history,
    seconds_until_next_run,
    why_nothing_to_check,
)

NOW = datetime.now(UTC)


def _clear(db):
    """Start with no decisions and no runs (rolled back after the test)."""
    db.query(ClarityTeacherCall).delete()
    db.query(ClarityTeacherRun).delete()
    db.query(ClarityCorpus).delete()
    db.flush()


def _live(db, prompt, minutes_ago=60, **fields):
    """A live micromodel decision on `prompt`, made `minutes_ago`."""
    fields.setdefault("needs_clarification", True)
    fields.setdefault("decision_path", "reasoner")
    row = ClarityCorpus(submission_text=prompt, source="live", created_at=NOW - timedelta(minutes=minutes_ago),
                        **fields)
    db.add(row)
    db.flush()
    return row


class FakeAnalyzer:
    """The teacher's LLM: answers every prompt with one fixed question."""

    async def generate_clarifying_questions(self, prompt):
        return {"needs_clarification": True, "questions": [{"question": "What does your app do, and who is it for?"}]}


def _run(db):
    """One teacher run with the fake LLM."""
    with patch("decision_engine.agentic_analyzer.create_analyzer", return_value=FakeAnalyzer()):
        return asyncio.run(clarity_teacher.run_teacher_batch(db, limit=5))


# ── Why a run didn't call the LLM ──────────────────────────────────────────

def test_no_new_prompts_is_given_as_the_reason(db):
    _clear(db)
    result = _run(db)
    assert result["llm_calls"] == 0
    assert "every checkup prompt has already been checked" in result["note"]
    assert db.get(ClarityTeacherRun, result["run_id"]).note == result["note"]


def test_too_new_and_confident_prompts_are_counted_in_the_reason(db):
    _clear(db)
    _live(db, "Sales dropped", minutes_ago=2)
    _live(db, "I sell shoes on Instagram", decision_path="neighbor", confidence=0.95)
    note = why_nothing_to_check(db)
    assert "2 unchecked prompt(s)" in note
    assert "1 under 15 minutes old" in note and "1 copied a trusted example" in note


def test_a_normal_run_says_what_it_did(db):
    _clear(db)
    _live(db, "People sign up for my app but don't come back")
    result = _run(db)
    assert result["llm_calls"] == 1
    assert result["note"].startswith("Checked 1 of 1: 1 LLM call(s)")


def test_reusing_an_earlier_llm_answer_is_given_as_the_reason(db):
    _clear(db)
    prompt = "People sign up for my app but don't come back"
    db.add(ClarityCorpus(submission_text=prompt, source="llm_teacher", needs_clarification=True,
                         questions=[{"question": "What does your app do?"}], gap_types=[]))
    _live(db, prompt)
    result = _run(db)
    assert result["llm_calls"] == 0
    assert "had an earlier LLM answer" in result["note"]


def test_a_failing_llm_gives_its_exact_error(db):
    _clear(db)
    _live(db, "Should I raise my prices?")

    class Broken:
        async def generate_clarifying_questions(self, prompt):
            return {"error": "401 invalid API key"}

    with patch("decision_engine.agentic_analyzer.create_analyzer", return_value=Broken()):
        result = asyncio.run(clarity_teacher.run_teacher_batch(db, limit=5))
    assert "401 invalid API key" in result["note"]


# ── The schedule ───────────────────────────────────────────────────────────

def test_runs_every_three_hours():
    assert RUN_EVERY_SECONDS == 3 * 60 * 60


def test_schedule_is_timed_from_the_last_run_not_the_restart(db):
    _clear(db)
    assert seconds_until_next_run(db, NOW) == clarity_teacher.MIN_FIRST_WAIT_SECONDS      # never run: soon
    db.add(ClarityTeacherRun(trigger="scheduled", started_at=NOW - timedelta(hours=2)))
    db.flush()
    assert abs(seconds_until_next_run(db, NOW) - 3600) < 5                               # 1 hour left
    db.query(ClarityTeacherRun).update({"started_at": NOW - timedelta(hours=5)})
    db.flush()
    assert seconds_until_next_run(db, NOW) == clarity_teacher.MIN_FIRST_WAIT_SECONDS      # overdue: soon


# ── The prompt history ─────────────────────────────────────────────────────

def test_history_shows_a_prompt_from_submission_to_what_was_learned(db):
    _clear(db)
    user = User(name="Ada", email="ada-history@test.local", password="x", confirm_password="x")
    db.add(user)
    db.flush()
    prompt = "People sign up for my app but don't come back"
    first = _live(db, prompt, user_id=user.id, outcome="answered",
                  questions=[{"question": "What does your app do, and who is it for?"}],
                  answers=[{"question": "What does your app do, and who is it for?", "answer": "Budgeting for students"}],
                  reasoning={"trace": ["It says 'app' but not what it does."]})
    _run(db)
    llm_example = db.query(ClarityCorpus).filter_by(source="llm_teacher").one()
    # A later, similar prompt that copied the LLM's example.
    _live(db, "Users sign up to my app then never return", minutes_ago=5, decision_path="neighbor",
          confidence=0.91, reasoning={"precedent_id": llm_example.id, "precedent_similarity": 0.91})

    data = decision_history(db)
    item = next(i for i in data["items"] if i["id"] == first.id)
    assert item["user"]["name"] == "Ada"
    assert item["micromodel"]["questions"] == ["What does your app do, and who is it for?"]
    assert item["micromodel"]["trace"] == ["It says 'app' but not what it does."]
    assert item["user_response"]["answers"][0]["answer"] == "Budgeting for students"
    assert item["teacher"]["llm_questions"] == ["What does your app do, and who is it for?"]
    assert item["teacher"]["agreed"] is True
    kinds = {entry["kind"]: entry for entry in item["learned"]}
    assert set(kinds) == {"user", "llm"}
    assert [u["prompt"] for u in kinds["llm"]["used_by"]] == ["Users sign up to my app then never return"]

    later = next(i for i in data["items"] if i["id"] != first.id)
    assert later["micromodel"]["precedent"]["id"] == llm_example.id
    assert "Copied a trusted example" in later["micromodel"]["path_label"]
    assert "under 15 minutes old" in later["not_checked_reason"]
    assert data["counts"]["used_learning"] == 1


def test_history_filters_disagreements(db):
    _clear(db)
    _live(db, "a", teacher_reviewed_at=NOW, teacher_agreed=False)
    _live(db, "b", teacher_reviewed_at=NOW, teacher_agreed=True)
    data = decision_history(db, view="disagreed")
    assert [i["prompt"] for i in data["items"]] == ["a"] and data["total"] == 1
