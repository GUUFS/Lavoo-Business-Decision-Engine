"""
A person checks the LLM's answers.

WHY: every 3 hours the LLM teacher (clarity_teacher.py) answers the
micromodel's hardest checkups, and its answers are saved as examples the
micromodel copies. If nobody ever checks the LLM, the micromodel can only
become as good as the LLM, mistakes included.

HOW IT WORKS:
  1. Each week the admin page shows 5 LLM answers nobody has looked at yet
     (picked at random, but the same 5 all week).
  2. The admin clicks "Good" or "Wrong".
  3. A "Wrong" answer is never copied by the micromodel again, and is left
     out of the training data (clarity_engine._TRUSTED_FILTER and
     training_data._QUESTIONS_SQL both skip person_verdict = 'wrong').
"""
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from database.pg_models import ClarityCorpus

# How many LLM answers a person checks each week.
CHECKS_PER_WEEK = 5

# SQL that shuffles rows the same way all week (the id mixed with the week number).
_SAME_ORDER_ALL_WEEK = "md5(id::text || to_char(date_trunc('week', now()), 'IYYY-IW'))"


def answers_to_check_this_week(db: Session, how_many: int = CHECKS_PER_WEEK) -> list[dict]:
    """This week's LLM answers for a person to check (ones nobody has checked)."""
    # 1. LLM teacher answers with no verdict yet, in this week's order.
    rows = db.execute(text(f"""
        SELECT id, submission_text, needs_clarification, questions, created_at
        FROM clarity_corpus
        WHERE source = 'llm_teacher' AND person_verdict IS NULL
        ORDER BY {_SAME_ORDER_ALL_WEEK}
        LIMIT :how_many
    """), {"how_many": how_many}).mappings().all()
    # 2. In the shape the page needs.
    return [{"id": r["id"], "prompt": r["submission_text"], "llm_says_ask": bool(r["needs_clarification"]),
             "llm_questions": [q.get("question") for q in (r["questions"] or []) if isinstance(q, dict) and q.get("question")],
             "created_at": r["created_at"].isoformat() if r["created_at"] else None} for r in rows]


def save_verdict(db: Session, answer_id: int, verdict: str, checked_by: int | None, note: str | None = None) -> bool:
    """Save a person's 'good' or 'wrong' on one LLM answer."""
    # 1. Only 'good' or 'wrong'.
    if verdict not in ("good", "wrong"):
        raise ValueError("verdict must be 'good' or 'wrong'")
    # 2. Only LLM answers can be checked.
    row = db.get(ClarityCorpus, answer_id)
    if not row or row.source not in ("llm_teacher", "llm_seed"):
        return False
    # 3. Save the verdict, who gave it, when, and why.
    row.person_verdict = verdict
    row.person_note = (note or "").strip()[:1000] or None
    row.person_checked_at = datetime.now(UTC)
    row.person_checked_by = checked_by
    db.commit()
    return True


def person_check_summary(db: Session, days: int = 7) -> dict:
    """How many LLM answers a person checked: in the last `days` days, and ever."""
    row = db.execute(text("""
        SELECT
          count(*) FILTER (WHERE created_at > now() - make_interval(days => :days))        AS new_llm_answers,
          count(*) FILTER (WHERE person_checked_at > now() - make_interval(days => :days)) AS checked_recently,
          count(*) FILTER (WHERE person_checked_at > now() - make_interval(days => :days)
                           AND person_verdict = 'wrong')                                     AS wrong_recently,
          count(*) FILTER (WHERE person_verdict IS NOT NULL)                                AS checked_ever,
          count(*) FILTER (WHERE person_verdict = 'wrong')                                  AS wrong_ever,
          count(*) FILTER (WHERE person_verdict IS NULL)                                    AS never_checked
        FROM clarity_corpus WHERE source = 'llm_teacher'
    """), {"days": days}).mappings().one()
    return {**dict(row), "per_week": CHECKS_PER_WEEK}
