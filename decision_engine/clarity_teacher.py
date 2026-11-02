"""
The teacher job: the LLM checks the micromodel's work.

Every 6 hours it picks the decisions the micromodel was least sure about
(questions the user skipped, or prompts with no similar example). For each
one it asks the LLM the same question, notes whether they agreed, and saves
the LLM's answer as a new trusted example. Next time a similar prompt
comes in, the micromodel copies the LLM's answer.

clarity_stats shows how often they agree. That number going up means the
micromodel is getting smarter.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from database.pg_models import ClarityCorpus
from decision_engine.clarity_reasoner import classify_question

logger = logging.getLogger(__name__)

LOW_CONFIDENCE = 0.6
# Wait until the user has had time to answer or skip.
MIN_AGE_MINUTES = 15


def _candidates(db: Session, limit: int) -> list[dict]:
    # 1. Unchecked live decisions that are old enough and look weak.
    #    Order: skipped questions first, then no similar example, then least sure.
    rows = db.execute(text(f"""
        SELECT id, submission_text, needs_clarification, questions, outcome, decision_path, confidence
        FROM clarity_corpus
        WHERE source = 'live'
          AND teacher_reviewed_at IS NULL
          AND created_at < now() - interval '{MIN_AGE_MINUTES} minutes'
          AND (outcome = 'skipped' OR decision_path = 'reasoner' OR confidence < :low)
        ORDER BY
          CASE WHEN outcome = 'skipped' THEN 0 WHEN decision_path = 'reasoner' THEN 1 ELSE 2 END,
          confidence ASC NULLS FIRST,
          created_at DESC
        LIMIT :limit
    """), {"low": LOW_CONFIDENCE, "limit": limit * 3}).mappings().all()
    # 2. Drop repeats, so the same prompt only costs one LLM call.
    seen, out = set(), []
    for r in rows:
        key = " ".join(r["submission_text"].lower().split())
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(r))
        if len(out) >= limit:
            break
    return out


def _existing_teacher_row(db: Session, submission_text: str):
    return db.execute(text("""
        SELECT needs_clarification, questions FROM clarity_corpus
        WHERE source IN ('llm_seed', 'llm_teacher') AND lower(submission_text) = lower(:t)
        LIMIT 1
    """), {"t": submission_text}).mappings().first()


def _mark_reviewed(db: Session, submission_text: str, agreed: bool) -> None:
    # Every live row with this exact prompt shares the verdict.
    db.execute(text("""
        UPDATE clarity_corpus SET teacher_reviewed_at = :now, teacher_agreed = :agreed
        WHERE source = 'live' AND teacher_reviewed_at IS NULL AND lower(submission_text) = lower(:t)
    """), {"now": datetime.now(timezone.utc), "agreed": agreed, "t": submission_text})


async def run_teacher_batch(db: Session, limit: int = 20) -> dict:
    """Reviews up to `limit` weak live decisions. Returns counts for logging."""
    from decision_engine.agentic_analyzer import create_analyzer
    from decision_engine.clarity_engine import _generate_embedding

    # 1. Pick the weakest decisions to check.
    candidates = _candidates(db, limit)
    if not candidates:
        return {"reviewed": 0, "agreed": 0, "new_precedents": 0, "errors": 0}

    analyzer = create_analyzer(db)
    reviewed = agreed_n = new_rows = errors = 0

    for c in candidates:
        prompt = c["submission_text"]
        try:
            # 2. Get the LLM's answer. If the LLM already judged this exact
            #    prompt, reuse that instead of paying for another call.
            existing = _existing_teacher_row(db, prompt)
            if existing:
                verdict = {"needs_clarification": existing["needs_clarification"], "questions": existing["questions"] or []}
            else:
                verdict = await analyzer.generate_clarifying_questions(prompt)
                if verdict.get("error"):
                    # Leave the row unreviewed so the next run retries it.
                    errors += 1
                    continue

            # 3. Did the micromodel make the same call (ask / don't ask)?
            agreed = bool(verdict["needs_clarification"]) == bool(c["needs_clarification"])

            # 4. Save the LLM's answer as a new trusted example the
            #    micromodel can copy next time.
            if not existing:
                questions = [
                    {"id": q.get("id") or f"q{i+1}", "question": q["question"], "gap_type": classify_question(q["question"])}
                    for i, q in enumerate(verdict.get("questions") or [])
                    if q.get("question")
                ]
                row = ClarityCorpus(
                    submission_text=prompt,
                    needs_clarification=bool(verdict["needs_clarification"]) and bool(questions),
                    gap_types=[q["gap_type"] for q in questions],
                    questions=questions,
                    source="llm_teacher",
                    reasoning={"reviewed_live_id": c["id"], "micromodel_agreed": agreed},
                )
                db.add(row)
                db.flush()
                embedding = _generate_embedding(prompt)
                db.execute(
                    text("UPDATE clarity_corpus SET embedding = CAST(:emb AS vector) WHERE id = :id"),
                    {"emb": f"[{','.join(map(str, embedding))}]", "id": row.id},
                )
                new_rows += 1

            # 5. Mark the decision as checked, so it isn't picked again.
            _mark_reviewed(db, prompt, agreed)
            db.commit()
            reviewed += 1
            agreed_n += int(agreed)
            logger.info(
                f"[clarity-teacher] {prompt[:60]!r} micromodel_asked={c['needs_clarification']} "
                f"llm_asked={verdict['needs_clarification']} agreed={agreed}"
            )
        except Exception as e:
            db.rollback()
            errors += 1
            logger.warning(f"[clarity-teacher] failed on corpus row {c['id']}: {e}")

    return {"reviewed": reviewed, "agreed": agreed_n, "new_precedents": new_rows, "errors": errors}


def clarity_stats(db: Session, days: int = 30) -> dict:
    """Weekly numbers on how the micromodel is doing: how often the LLM
    agrees with it, and how often users answer its questions."""
    weekly = db.execute(text("""
        SELECT date_trunc('week', created_at) AS week,
               count(*) AS decisions,
               count(*) FILTER (WHERE needs_clarification) AS asked,
               count(*) FILTER (WHERE outcome = 'answered') AS answered,
               count(*) FILTER (WHERE outcome = 'skipped') AS skipped,
               count(*) FILTER (WHERE teacher_reviewed_at IS NOT NULL) AS reviewed,
               count(*) FILTER (WHERE teacher_agreed) AS agreed,
               count(*) FILTER (WHERE decision_path = 'neighbor') AS path_neighbor,
               count(*) FILTER (WHERE decision_path = 'blend') AS path_blend,
               count(*) FILTER (WHERE decision_path = 'reasoner') AS path_reasoner
        FROM clarity_corpus
        WHERE source = 'live' AND created_at > now() - make_interval(days => :days)
        GROUP BY 1 ORDER BY 1
    """), {"days": days}).mappings().all()
    corpus = db.execute(text("SELECT source, count(*) AS n FROM clarity_corpus GROUP BY source")).mappings().all()

    def pct(a, b):
        return round(100 * a / b, 1) if b else None

    return {
        "corpus_size": {r["source"]: r["n"] for r in corpus},
        "weeks": [
            {
                "week": r["week"].date().isoformat() if r["week"] else None,
                "decisions": r["decisions"],
                "ask_rate_pct": pct(r["asked"], r["decisions"]),
                "answer_rate_pct": pct(r["answered"], r["answered"] + r["skipped"]),
                "teacher_agreement_pct": pct(r["agreed"], r["reviewed"]),
                "reviewed": r["reviewed"],
                "paths": {"neighbor": r["path_neighbor"], "blend": r["path_blend"], "reasoner": r["path_reasoner"]},
            }
            for r in weekly
        ],
    }
