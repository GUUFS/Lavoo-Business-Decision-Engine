"""
The admin "Is the micromodel learning?" summary (clarity_teacher.learning_progress).

It must show, in plain numbers, that the micromodel gains trusted examples
from users' answers and from the LLM teacher, that new prompts use them,
and flag the link that's broken when the loop isn't connected (e.g.
questions shown but no answers ever saved).
"""
from datetime import UTC, datetime, timedelta

from database.pg_models import ClarityCorpus, ClarityTeacherCall, ClarityTeacherRun
from decision_engine.clarity_teacher import learning_progress

NOW = datetime.now(UTC)
VECTOR = "[" + ",".join(["0.1"] * 384) + "]"


def _clear(db):
    """Start from an empty learning loop (rolled back after the test)."""
    db.query(ClarityTeacherCall).delete()
    db.query(ClarityTeacherRun).delete()
    db.query(ClarityCorpus).delete()
    db.flush()


def _row(db, source, hours_ago=2, searchable=True, **fields):
    """One clarity_corpus row, created `hours_ago`, with a search vector unless told not to."""
    row = ClarityCorpus(submission_text=f"prompt {source} {hours_ago} {fields}", source=source,
                        created_at=NOW - timedelta(hours=hours_ago), **fields)
    db.add(row)
    db.flush()
    if searchable:
        db.execute(ClarityCorpus.__table__.update().where(ClarityCorpus.id == row.id)
                   .values(embedding=VECTOR))
    return row


def _teacher_run(db, hours_ago=1, checks=2, agreed=1, errors=0):
    """A teacher run with its checks."""
    run = ClarityTeacherRun(trigger="scheduled", started_at=NOW - timedelta(hours=hours_ago),
                            finished_at=NOW - timedelta(hours=hours_ago), reviewed=checks, agreed=agreed)
    db.add(run)
    db.flush()
    for i in range(checks):
        db.add(ClarityTeacherCall(run_id=run.id, submission_text="p", micromodel_asked=True, called_llm=True,
                                  agreed=i < agreed, error="boom" if i < errors else None,
                                  created_at=NOW - timedelta(hours=hours_ago)))
    db.flush()


def _working_loop(db):
    """Seed examples, users answering, the teacher adding an example, and a
    new prompt copying a learned one."""
    _clear(db)
    _row(db, "llm_seed", hours_ago=24 * 60)
    _row(db, "live", needs_clarification=True, outcome="answered", decision_path="reasoner")
    _row(db, "live", needs_clarification=True, outcome="skipped", decision_path="reasoner")
    _row(db, "live", needs_clarification=False, decision_path="neighbor")
    _row(db, "llm_teacher", hours_ago=1)
    _teacher_run(db)


def test_a_connected_loop_says_it_is_learning_and_from_where(db):
    _working_loop(db)
    data = learning_progress(db)
    # No exam yet: the headline says there's no real measure, not "learning".
    assert data["status"] == "idle" and "No exam result yet" in data["headline"]
    assert data["trusted"]["total"] == 3                       # seed + teacher + answered
    assert data["trusted"]["new_from_users"] == 1 and data["trusted"]["new_from_llm"] == 1
    assert data["users"]["answered"] == 1 and data["users"]["skipped"] == 1
    assert data["usage"]["copied"] == 1
    assert data["llm"]["agreement_pct"] == 50.0
    # Every link works; only a person checking the LLM's answers is still to do.
    assert [c["key"] for c in data["checks"] if c["ok"] is False] == ["person_checked"]
    assert data["growth"][-1]["total"] == 3


def test_questions_shown_with_no_answers_saved_is_flagged(db):
    """The app not sending corpus_id back would look exactly like this."""
    _clear(db)
    _row(db, "llm_seed", hours_ago=24 * 60)
    _row(db, "live", needs_clarification=True, decision_path="reasoner")
    _row(db, "live", needs_clarification=True, decision_path="reasoner")
    _teacher_run(db)
    data = learning_progress(db)
    check = next(c for c in data["checks"] if c["key"] == "answers_saved")
    assert check["ok"] is False and "2 shown with nothing back" in check["detail"]
    assert data["status"] == "attention"


def test_a_teacher_that_stopped_running_is_flagged(db):
    _working_loop(db)
    db.query(ClarityTeacherRun).update({"started_at": NOW - timedelta(days=2)})
    db.flush()
    check = next(c for c in learning_progress(db)["checks"] if c["key"] == "teacher_running")
    assert check["ok"] is False


def test_an_example_without_a_search_vector_is_flagged(db):
    _working_loop(db)
    _row(db, "live", hours_ago=3, searchable=False, needs_clarification=True, outcome="answered")
    check = next(c for c in learning_progress(db)["checks"] if c["key"] == "examples_searchable")
    assert check["ok"] is False and "1 without a search vector" in check["detail"]


def test_no_activity_is_not_called_broken(db):
    _clear(db)
    data = learning_progress(db)
    assert {c["key"]: c["ok"] for c in data["checks"]}["answers_saved"] is None
    assert data["growth"] == []
