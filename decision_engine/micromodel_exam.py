"""
The micromodel's weekly exam.

WHY: the micromodel saves more examples every day, but "more examples"
doesn't prove it decides better. An exam does.

HOW IT WORKS:
  1. An admin writes exam questions on the admin page: a founder's prompt
     and the right answer (should it ask questions? which ones?).
  2. Once a week (api/main.py) the micromodel answers every question.
     - Its answers are NOT saved as checkups.
     - It may not copy a saved answer to the exact same prompt, so the
       exam tests what it learned, not what it memorised.
  3. Each answer is marked:
     - "right decision": it was right about WHETHER to ask;
     - "fully right":    right decision AND, if it asked, its questions mean
                          the same as the admin's (wording can differ).
  4. The result ("15 of 20 fully right") is the headline of the admin
     Learning tab. If this week beats last week, the micromodel improved.
"""
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from database.pg_models import MicromodelExamQuestion, MicromodelExamResult

logger = logging.getLogger(__name__)

# The exam is taken again when the last result is this many days old.
EXAM_EVERY_DAYS = 7


def _question_list(questions) -> list[str]:
    """Turn a list of strings or {"question": "..."} items into plain strings."""
    out = []
    for q in questions or []:
        wording = q.get("question") if isinstance(q, dict) else q
        if isinstance(wording, str) and wording.strip():
            out.append(wording.strip()[:500])
    return out[:5]


def add_exam_question(db: Session, prompt: str, should_ask: bool, expected_questions=None,
                      note: str | None = None, created_by: int | None = None) -> MicromodelExamQuestion:
    """Add one question to the exam."""
    # 1. A prompt is required.
    prompt = (prompt or "").strip()
    if not prompt:
        raise ValueError("The prompt is empty.")
    # 2. Only a "should ask" question has expected questions.
    expected = _question_list(expected_questions) if should_ask else []
    # 3. Save it.
    question = MicromodelExamQuestion(prompt=prompt[:4000], should_ask=bool(should_ask), expected_questions=expected,
                                      note=(note or "").strip()[:1000] or None, created_by=created_by, active=True)
    db.add(question)
    db.commit()
    return question


def remove_exam_question(db: Session, question_id: int) -> bool:
    """Take a question out of future exams (old results still mention it)."""
    # 1. Find it.
    question = db.get(MicromodelExamQuestion, question_id)
    if not question:
        return False
    # 2. Switch it off.
    question.active = False
    db.commit()
    return True


def run_exam(db: Session, trigger: str = "weekly") -> dict:
    """The micromodel answers every exam question; save and return the result."""
    from decision_engine.clarity_engine import decide
    from decision_engine.clarity_teacher import QUESTION_MATCH_THRESHOLD, question_match

    # 1. The questions in the exam.
    questions = (db.query(MicromodelExamQuestion).filter(MicromodelExamQuestion.active.is_(True))
                 .order_by(MicromodelExamQuestion.id).all())
    result = MicromodelExamResult(trigger=trigger, taken_at=datetime.now(UTC), total=len(questions))
    marking, right_decision, fully_right = [], 0, 0
    try:
        for q in questions:
            # 2. The micromodel's answer (not saved; may not copy this exact prompt).
            answer = decide(q.prompt, db, user_id=None, exclude_same_prompt=True)
            it_asked = bool(answer["needs_clarification"])
            its_questions = [item["question"] for item in answer["questions"]]

            # 3. Right about WHETHER to ask?
            decision_ok = it_asked == bool(q.should_ask)
            # 4. If both say "ask" and the admin listed questions: do they mean the same?
            match = None
            if decision_ok and it_asked and q.expected_questions:
                match = question_match(its_questions, _question_list(q.expected_questions))
            questions_ok = match is None or match >= QUESTION_MATCH_THRESHOLD

            # 5. Mark it.
            right_decision += int(decision_ok)
            fully_right += int(decision_ok and questions_ok)
            marking.append({"question_id": q.id, "prompt": q.prompt[:200], "should_ask": q.should_ask,
                            "it_asked": it_asked, "its_questions": its_questions, "question_match": match,
                            "right_decision": decision_ok, "fully_right": decision_ok and questions_ok})
    except Exception as e:
        # 6. If the exam crashes, save why (not half a score).
        db.rollback()
        result.error = str(e)[:2000]
        logger.error(f"[exam] failed: {e}", exc_info=True)

    # 7. Save the result.
    result.right_decision, result.fully_right, result.marking = right_decision, fully_right, marking
    db.add(result)
    db.commit()
    return {"result_id": result.id, "total": result.total, "right_decision": right_decision,
            "fully_right": fully_right, **({"error": result.error} if result.error else {})}


def exam_is_due(db: Session, now: datetime | None = None) -> bool:
    """True when there are questions and the last good result is a week old (or there is none)."""
    # 1. No questions: nothing to do.
    if not db.query(MicromodelExamQuestion.id).filter(MicromodelExamQuestion.active.is_(True)).first():
        return False
    # 2. When was it last taken without crashing?
    now = now or datetime.now(UTC)
    last = (db.query(MicromodelExamResult.taken_at).filter(MicromodelExamResult.error.is_(None))
            .order_by(MicromodelExamResult.taken_at.desc()).first())
    return not last or (now - last[0]).days >= EXAM_EVERY_DAYS


def exam_summary(db: Session, how_many_results: int = 12) -> dict:
    """Everything the admin page shows about the exam: the questions, the
    recent results (oldest first), and what the latest result got wrong."""
    # 1. The questions.
    questions = (db.query(MicromodelExamQuestion).filter(MicromodelExamQuestion.active.is_(True))
                 .order_by(MicromodelExamQuestion.id).all())
    # 2. Recent results that didn't crash, oldest first; and the latest crash, if any.
    results = (db.query(MicromodelExamResult).filter(MicromodelExamResult.error.is_(None))
               .order_by(MicromodelExamResult.taken_at.desc()).limit(how_many_results).all())[::-1]
    newest_any = db.query(MicromodelExamResult).order_by(MicromodelExamResult.taken_at.desc()).first()

    def short(r):
        """One result as the page needs it."""
        return {"id": r.id, "taken_at": r.taken_at.isoformat() if r.taken_at else None, "trigger": r.trigger,
                "total": r.total, "right_decision": r.right_decision, "fully_right": r.fully_right}

    latest = results[-1] if results else None
    # 3. Put it together.
    return {
        "questions": [{"id": q.id, "prompt": q.prompt, "should_ask": q.should_ask,
                       "expected_questions": q.expected_questions or [], "note": q.note,
                       "created_at": q.created_at.isoformat() if q.created_at else None} for q in questions],
        "question_count": len(questions),
        "should_ask_count": sum(1 for q in questions if q.should_ask),
        "results": [short(r) for r in results],
        "latest": short(latest) if latest else None,
        "previous": short(results[-2]) if len(results) > 1 else None,
        "latest_mistakes": [m for m in (latest.marking or []) if not m.get("fully_right")] if latest else [],
        "last_crash": newest_any.error if newest_any and newest_any.error else None,
        "every_days": EXAM_EVERY_DAYS,
    }
