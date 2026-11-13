"""
Tests for how we know the micromodel gets smarter, and what keeps it honest:

  - the weekly exam (micromodel_exam.py)
  - a person checking the LLM's answers (micromodel_person_check.py)
  - random checks of decisions it was sure about (clarity_teacher._candidates)
  - founders' answers counting for more than the LLM's (clarity_engine._pick_neighbor)
  - did asking help? (micromodel_outcomes.py)
  - one time format (clarity_teacher.ago)
"""
from datetime import UTC, datetime, timedelta

from database.pg_models import (
    BusinessAnalysis,
    ClarityCorpus,
    ClarityTeacherCall,
    ClarityTeacherRun,
    MicromodelExamQuestion,
    MicromodelExamResult,
    User,
)
from decision_engine.clarity_engine import (
    _find_trusted_neighbors,
    _generate_embedding,
    _pick_neighbor,
    decide,
    link_analysis,
    update_outcome,
)
from decision_engine.clarity_teacher import _candidates, ago, learning_progress
from decision_engine.micromodel_exam import add_exam_question, exam_summary, run_exam
from decision_engine.micromodel_outcomes import did_asking_help
from decision_engine.micromodel_person_check import (
    answers_to_check_this_week,
    person_check_summary,
    save_verdict,
)
from decision_engine.training_data import export_jsonl

NOW = datetime.now(UTC)


def _empty(db):
    """Start with no micromodel data (everything is rolled back after the test)."""
    for model in (ClarityTeacherCall, ClarityTeacherRun, MicromodelExamResult, MicromodelExamQuestion, ClarityCorpus):
        db.query(model).delete()
    db.flush()


def _saved_example(db, prompt, source, hours_ago=2, **fields):
    """A saved prompt with its real search vector, so the micromodel can find it."""
    row = ClarityCorpus(submission_text=prompt, source=source, created_at=NOW - timedelta(hours=hours_ago), **fields)
    db.add(row)
    db.flush()
    vector = "[" + ",".join(map(str, _generate_embedding(prompt))) + "]"
    db.execute(ClarityCorpus.__table__.update().where(ClarityCorpus.id == row.id).values(embedding=vector))
    return row


def _founder(db, email="founder@test.local"):
    """A founder account."""
    user = User(name="Founder", email=email, password="x", confirm_password="x")
    db.add(user)
    db.flush()
    return user


# ------------------------------------------------------------ weekly exam

def test_exam_marks_each_answer_and_saves_no_checkups(db):
    _empty(db)
    # 1. Two exam questions with opposite right answers.
    vague = add_exam_question(db, "I want more sales", should_ask=True)
    clear = add_exam_question(db, "I run a candle shop on Etsy selling 40 candles a month at $25; my ads cost "
                                  "$300 a month and bring 5 sales. Which channel should I try next?",
                              should_ask=False)
    # 2. Take the exam.
    result = run_exam(db, trigger="manual")
    # 3. No checkups were saved by the exam.
    assert db.query(ClarityCorpus).filter_by(source="live").count() == 0
    # 4. Each question is marked right exactly when the micromodel's decision matches.
    marking = {m["question_id"]: m for m in db.get(MicromodelExamResult, result["result_id"]).marking}
    for q in (vague, clear):
        it_asked = decide(q.prompt, db, exclude_same_prompt=True)["needs_clarification"]
        assert marking[q.id]["right_decision"] == (it_asked == q.should_ask)
    assert result["total"] == 2


def test_exam_cannot_copy_the_saved_answer_to_the_same_prompt(db):
    _empty(db)
    prompt = "help me grow my business"
    # 1. The LLM's answer to this exact prompt is saved.
    llm_answer = _saved_example(db, prompt, "llm_teacher", needs_clarification=False, questions=[])
    # 2. A real checkup may copy it; the exam may not.
    assert decide(prompt, db)["neighbor"]["id"] == llm_answer.id
    in_exam = decide(prompt, db, exclude_same_prompt=True)["neighbor"]
    assert in_exam is None or in_exam["id"] != llm_answer.id


def test_headline_is_the_exam_result_compared_with_last_time(db):
    _empty(db)
    add_exam_question(db, "I want more sales", should_ask=True)
    # 1. Last week 10 of 20, this week 15 of 20; the teacher ran recently.
    db.add(MicromodelExamResult(taken_at=NOW - timedelta(days=7), total=20, right_decision=12, fully_right=10))
    db.add(MicromodelExamResult(taken_at=NOW - timedelta(hours=1), total=20, right_decision=17, fully_right=15))
    db.add(ClarityTeacherRun(trigger="scheduled", started_at=NOW - timedelta(hours=1)))
    db.flush()
    data = learning_progress(db)
    # 2. Better than last time: "learning", with both results as counts.
    assert data["status"] == "learning"
    assert data["headline"] == "Exam: 15 of 20 right (last time 10 of 20)."
    assert [r["fully_right"] for r in data["exam"]["results"]] == [10, 15]


def test_a_worse_exam_result_needs_attention(db):
    _empty(db)
    add_exam_question(db, "I want more sales", should_ask=True)
    db.add(MicromodelExamResult(taken_at=NOW - timedelta(days=7), total=20, right_decision=18, fully_right=16))
    db.add(MicromodelExamResult(taken_at=NOW - timedelta(hours=1), total=20, right_decision=15, fully_right=12))
    db.add(ClarityTeacherRun(trigger="scheduled", started_at=NOW - timedelta(hours=1)))
    db.flush()
    assert learning_progress(db)["status"] == "attention"


def test_a_crashed_exam_is_reported_but_not_counted(db):
    _empty(db)
    add_exam_question(db, "I want more sales", should_ask=True)
    db.add(MicromodelExamResult(taken_at=NOW - timedelta(hours=2), total=1, right_decision=1, fully_right=1))
    db.add(MicromodelExamResult(taken_at=NOW - timedelta(hours=1), total=1, error="model not loaded"))
    db.flush()
    summary = exam_summary(db)
    assert len(summary["results"]) == 1 and summary["last_crash"] == "model not loaded"


# ------------------------------------------ a person checks the LLM's answers

def test_an_llm_answer_marked_wrong_is_never_used_again(db):
    _empty(db)
    admin = _founder(db, "admin-check@test.local")
    prompt = "how do I price my consulting services"
    bad = _saved_example(db, prompt, "llm_teacher", needs_clarification=True,
                         questions=[{"id": "q1", "question": "What is your favourite colour?"}])
    # 1. Before: the micromodel can copy it, and it is in the training data.
    assert any(n["id"] == bad.id for n in _find_trusted_neighbors(db, _generate_embedding(prompt)))
    assert prompt in export_jsonl(db, "questions")[0]
    # 2. A person marks it wrong.
    assert save_verdict(db, bad.id, "wrong", admin.id, "off-topic question")
    # 3. After: not copied, not in the training data, and counted.
    assert not any(n["id"] == bad.id for n in _find_trusted_neighbors(db, _generate_embedding(prompt)))
    assert prompt not in export_jsonl(db, "questions")[0]
    summary = person_check_summary(db)
    assert summary["checked_recently"] == 1 and summary["wrong_recently"] == 1


def test_this_weeks_list_has_only_unchecked_llm_answers(db):
    _empty(db)
    checked = _saved_example(db, "prompt one", "llm_teacher", needs_clarification=False, questions=[])
    unchecked = _saved_example(db, "prompt two", "llm_teacher", needs_clarification=False, questions=[])
    _saved_example(db, "prompt three", "live", needs_clarification=False, questions=[])
    save_verdict(db, checked.id, "good", None)
    # 1. Only the unchecked LLM answer, and the same list on a second look.
    assert [a["id"] for a in answers_to_check_this_week(db)] == [unchecked.id]
    assert answers_to_check_this_week(db) == answers_to_check_this_week(db)


# ------------------------------------- random checks of sure decisions

def test_each_teacher_run_also_checks_random_sure_decisions(db):
    _empty(db)
    # 1. One unsure decision and four sure ones, all old enough.
    _saved_example(db, "unsure one", "live", needs_clarification=True, decision_path="reasoner", confidence=0.3)
    for i in range(4):
        _saved_example(db, f"sure {i}", "live", needs_clarification=False, decision_path="neighbor", confidence=0.95)
    picked = _candidates(db, limit=20, random_checks=3)
    # 2. The unsure one, plus exactly 3 random sure ones.
    reasons = [c["why_checked"] for c in picked]
    assert reasons.count("unsure") == 1 and reasons.count("random") == 3
    assert all(c["confidence"] >= 0.6 for c in picked if c["why_checked"] == "random")


# --------------------------------------- founders' answers count for more

def test_a_founders_answer_beats_a_slightly_closer_llm_answer():
    llm = {"id": 1, "source": "llm_teacher", "similarity_score": 0.90}
    founder = {"id": 2, "source": "live", "similarity_score": 0.88}
    far_founder = {"id": 3, "source": "live", "similarity_score": 0.80}
    # 1. Close enough: the founder's answer is used.
    chosen, similarity, note = _pick_neighbor([llm, founder])
    assert chosen["id"] == 2 and similarity == 0.88 and "real answers count for more" in note
    # 2. Too far behind: the closer LLM answer is used.
    assert _pick_neighbor([llm, far_founder])[0]["id"] == 1


# ------------------------------------------------- did asking help?

def test_a_checkup_with_no_questions_is_linked_but_never_called_skipped(db):
    _empty(db)
    founder = _founder(db)
    row = ClarityCorpus(submission_text="clear prompt", source="live", needs_clarification=False, user_id=founder.id)
    db.add(row)
    db.flush()
    # 1. The app sends the checkup id with no answers (nothing was asked).
    update_outcome(db, row.id, None, founder.id)
    db.refresh(row)
    assert row.outcome is None
    # 2. The diagnosis is linked to the checkup.
    analysis = BusinessAnalysis(user_id=founder.id, business_goal="clear prompt", confidence_score=80,
                                user_progress={"completed_actions": ["a1"]})
    db.add(analysis)
    db.flush()
    link_analysis(db, row.id, analysis.id, founder.id)
    db.refresh(row)
    assert row.analysis_id == analysis.id


def test_outcomes_are_grouped_by_what_happened(db):
    _empty(db)
    founder = _founder(db)

    def checkup(asked, outcome, confidence, acted):
        """One checkup and the diagnosis it produced."""
        a = BusinessAnalysis(user_id=founder.id, business_goal="g", confidence_score=confidence,
                             user_progress={"completed_actions": ["x"] if acted else []})
        db.add(a)
        db.flush()
        db.add(ClarityCorpus(submission_text="p", source="live", needs_clarification=asked, outcome=outcome,
                             user_id=founder.id, analysis_id=a.id))
        db.flush()

    checkup(True, "answered", 80, acted=True)
    checkup(True, "answered", 60, acted=False)
    checkup(False, None, 70, acted=False)
    checkup(True, "skipped", 50, acted=False)
    # 1. Counts, founders who acted, and average confidence per group.
    data = did_asking_help(db)
    assert data["groups"]["answered"] == {"checkups": 2, "acted": 1, "avg_confidence": 70.0}
    assert data["groups"]["not_asked"]["checkups"] == 1 and data["groups"]["skipped"]["checkups"] == 1
    assert data["linked"] == 4 and data["enough_to_compare"] is False


# ------------------------------------------------- one time format

def test_times_read_the_same_as_the_admin_app():
    assert ago(None) == "never"
    assert ago(20) == "just now"
    assert ago(49 * 60) == "49 min ago"
    assert ago(15 * 3600) == "15 h ago"
    assert ago(3 * 86400) == "3 d ago"
