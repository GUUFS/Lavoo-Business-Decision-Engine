"""
The teacher job: the LLM checks the micromodel's work.

Every 6 hours it picks the decisions the micromodel was least sure about
(questions the user skipped, prompts with no similar example, or questions
whose wording was borrowed from another example). For each one it asks the
LLM the same question and saves the LLM's answer as a new trusted example.
Next time a similar prompt comes in, the micromodel copies the LLM's answer.

"Agreed" means BOTH:
  - the same call on whether to ask questions at all, and
  - when both ask, the same questions in meaning: every micromodel question
    has an LLM question close to it (question_match >= QUESTION_MATCH_THRESHOLD,
    measured with the local embedding model, no extra LLM call).
So the micromodel asking the wrong question counts as a disagreement.

clarity_stats shows how often they agree. That number going up means the
micromodel is getting smarter.
"""
import logging
import time
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from database.pg_models import ClarityCorpus, ClarityTeacherCall, ClarityTeacherRun
from decision_engine.clarity_reasoner import classify_question

logger = logging.getLogger(__name__)

LOW_CONFIDENCE = 0.6
# Two questions mean the same thing above this similarity. Measured on real
# pairs: same meaning scored 0.50-0.72, different questions 0.09-0.28.
QUESTION_MATCH_THRESHOLD = 0.45
# How often api/main.py runs the job, and when the next run is due (set by
# that job; shown on the admin page). None until the server's job has started.
RUN_EVERY_SECONDS = 6 * 60 * 60
next_scheduled_run_at: datetime | None = None
# Wait until the user has had time to answer or skip.
MIN_AGE_MINUTES = 15


def _candidates(db: Session, limit: int) -> list[dict]:
    """Pick up to `limit` live micromodel decisions for the LLM to re-check:
    unchecked, at least MIN_AGE_MINUTES old, and weak (the user skipped the
    questions, no similar trusted example was found, or confidence was
    below LOW_CONFIDENCE), or blended (question wording borrowed from another
    example). Duplicate prompts are dropped so each is checked once."""
    # 1. Unchecked live decisions that are old enough and look weak.
    #    Order: skipped questions first, then no similar example, then least sure.
    rows = db.execute(text(f"""
        SELECT id, submission_text, needs_clarification, questions, outcome, decision_path, confidence
        FROM clarity_corpus
        WHERE source = 'live'
          AND teacher_reviewed_at IS NULL
          AND created_at < now() - interval '{MIN_AGE_MINUTES} minutes'
          AND (outcome = 'skipped' OR decision_path IN ('reasoner', 'blend') OR confidence < :low)
        ORDER BY
          CASE WHEN outcome = 'skipped' THEN 0 WHEN decision_path = 'blend' THEN 1
               WHEN decision_path = 'reasoner' THEN 2 ELSE 3 END,
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
    """Return the LLM's earlier verdict on this exact prompt (seed or teacher
    row), or None. Lets a run reuse that answer instead of paying for a new call."""
    return db.execute(text("""
        SELECT needs_clarification, questions FROM clarity_corpus
        WHERE source IN ('llm_seed', 'llm_teacher') AND lower(submission_text) = lower(:t)
        LIMIT 1
    """), {"t": submission_text}).mappings().first()


def _mark_reviewed(db: Session, submission_text: str, agreed: bool) -> None:
    """Stamp every unchecked live row with this exact prompt as reviewed, with
    whether the LLM agreed, so _candidates never picks them again."""
    db.execute(text("""
        UPDATE clarity_corpus SET teacher_reviewed_at = :now, teacher_agreed = :agreed
        WHERE source = 'live' AND teacher_reviewed_at IS NULL AND lower(submission_text) = lower(:t)
    """), {"now": datetime.now(UTC), "agreed": agreed, "t": submission_text})


async def run_teacher_batch(db: Session, limit: int = 20, trigger: str = "scheduled") -> dict:
    """Reviews up to `limit` weak live decisions. Returns counts for logging.
    Every run and every decision it checks is saved (clarity_teacher_runs,
    clarity_teacher_calls) for the admin Micromodel page."""
    run = ClarityTeacherRun(trigger=trigger, started_at=datetime.now(UTC))
    db.add(run)
    db.commit()
    counts = {"candidates": 0, "reviewed": 0, "agreed": 0, "llm_calls": 0, "new_precedents": 0, "errors": 0}
    try:
        await _review_candidates(db, limit, run.id, counts)
    except Exception as e:
        db.rollback()
        run.error = str(e)[:2000]
        logger.error(f"[clarity-teacher] run {run.id} failed: {e}", exc_info=True)
    for key, value in counts.items():
        setattr(run, key, value)
    run.finished_at = datetime.now(UTC)
    db.commit()
    return {"run_id": run.id, **counts, **({"error": run.error} if run.error else {})}


def _question_texts(questions) -> list[str]:
    """The question strings from a stored or LLM question list."""
    return [q.get("question") for q in (questions or []) if isinstance(q, dict) and q.get("question")]


def question_match(micromodel_questions: list[str], llm_questions: list[str]) -> float | None:
    """How well the micromodel's questions match the LLM's, 0 to 1: for each
    micromodel question, the similarity of the closest LLM question, and the
    LOWEST of those (one off-topic question is enough to disagree). None if
    either side asked nothing."""
    if not micromodel_questions or not llm_questions:
        return None
    from decision_engine.clarity_engine import _cosine, _generate_embedding
    llm_vectors = [_generate_embedding(q) for q in llm_questions]
    best = [max(_cosine(_generate_embedding(q), v) for v in llm_vectors) for q in micromodel_questions]
    return round(min(best), 3)


def _log_call(db: Session, run_id: int, c: dict, **fields) -> None:
    """Add one clarity_teacher_calls row for a checked decision: the prompt,
    what the micromodel decided, and (via **fields) the LLM's answer,
    agreement, timing or error. The caller commits."""
    db.add(ClarityTeacherCall(
        run_id=run_id,
        corpus_id=c["id"],
        submission_text=c["submission_text"][:4000],
        micromodel_asked=bool(c["needs_clarification"]),
        micromodel_questions=_question_texts(c.get("questions")),
        micromodel_confidence=c.get("confidence"),
        decision_path=c.get("decision_path"),
        **fields,
    ))


async def _review_candidates(db: Session, limit: int, run_id: int, counts: dict) -> None:
    """The body of a teacher run. For each weak decision: get the LLM's
    verdict (reusing an earlier one if it exists), compare it with the
    micromodel's, save it as a trusted example, mark the decision reviewed
    and log the check. Updates `counts` in place. One bad decision is logged
    as an error and skipped; it never stops the rest of the run."""
    from decision_engine.agentic_analyzer import create_analyzer
    from decision_engine.clarity_engine import _generate_embedding

    # 1. Pick the weakest decisions to check.
    candidates = _candidates(db, limit)
    counts["candidates"] = len(candidates)
    if not candidates:
        return

    analyzer = create_analyzer(db)

    for c in candidates:
        prompt = c["submission_text"]
        started = time.monotonic()
        called_llm = False
        try:
            # 2. Get the LLM's answer. If the LLM already judged this exact
            #    prompt, reuse that instead of paying for another call.
            existing = _existing_teacher_row(db, prompt)
            if existing:
                verdict = {"needs_clarification": existing["needs_clarification"], "questions": existing["questions"] or []}
            else:
                called_llm = True
                counts["llm_calls"] += 1
                verdict = await analyzer.generate_clarifying_questions(prompt)
                if verdict.get("error"):
                    # Leave the row unreviewed so the next run retries it.
                    counts["errors"] += 1
                    _log_call(db, run_id, c, called_llm=True, error=str(verdict.get("error"))[:2000],
                              duration_ms=int((time.monotonic() - started) * 1000))
                    db.commit()
                    continue

            # 3. Did the micromodel make the same call (ask / don't ask)?
            #    And when both ask, did it ask the same things?
            same_call = bool(verdict["needs_clarification"]) == bool(c["needs_clarification"])
            match = None
            if same_call and c["needs_clarification"]:
                match = question_match(_question_texts(c.get("questions")), _question_texts(verdict.get("questions")))
            agreed = same_call and (match is None or match >= QUESTION_MATCH_THRESHOLD)

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
                counts["new_precedents"] += 1

            # 5. Mark the decision as checked, so it isn't picked again,
            #    and log the result for the admin page.
            _mark_reviewed(db, prompt, agreed)
            _log_call(
                db, run_id, c,
                called_llm=called_llm,
                llm_asked=bool(verdict["needs_clarification"]),
                question_match=match,
                llm_questions=[q.get("question") for q in (verdict.get("questions") or []) if q.get("question")],
                agreed=agreed,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            db.commit()
            counts["reviewed"] += 1
            counts["agreed"] += int(agreed)
            logger.info(
                f"[clarity-teacher] {prompt[:60]!r} micromodel_asked={c['needs_clarification']} "
                f"llm_asked={verdict['needs_clarification']} question_match={match} agreed={agreed}"
            )
        except Exception as e:
            db.rollback()
            counts["errors"] += 1
            logger.warning(f"[clarity-teacher] failed on corpus row {c['id']}: {e}")
            try:
                _log_call(db, run_id, c, called_llm=called_llm, error=str(e)[:2000],
                          duration_ms=int((time.monotonic() - started) * 1000))
                db.commit()
            except Exception:
                db.rollback()


def teacher_activity(db: Session, runs: int = 20, calls: int = 50) -> dict:
    """For the admin Micromodel page and the status pill: the latest runs,
    the latest decisions the LLM checked, and when the next run is due."""
    run_rows = db.query(ClarityTeacherRun).order_by(ClarityTeacherRun.started_at.desc()).limit(runs).all()
    call_rows = db.query(ClarityTeacherCall).order_by(ClarityTeacherCall.created_at.desc()).limit(calls).all()
    last_llm_call = (
        db.query(ClarityTeacherCall.created_at)
        .filter(ClarityTeacherCall.called_llm.is_(True))
        .order_by(ClarityTeacherCall.created_at.desc())
        .first()
    )
    # Datetimes go out as ISO strings (None stays None) for the admin app.
    def iso(d):
        return d.isoformat() if d else None
    return {
        "next_run_at": iso(next_scheduled_run_at),
        "run_every_hours": RUN_EVERY_SECONDS // 3600,
        "last_llm_call_at": iso(last_llm_call[0]) if last_llm_call else None,
        "runs": [
            {
                "id": r.id, "trigger": r.trigger, "started_at": iso(r.started_at), "finished_at": iso(r.finished_at),
                "candidates": r.candidates, "reviewed": r.reviewed, "agreed": r.agreed,
                "llm_calls": r.llm_calls, "new_precedents": r.new_precedents, "errors": r.errors, "error": r.error,
            }
            for r in run_rows
        ],
        "calls": [
            {
                "id": c.id, "run_id": c.run_id, "created_at": iso(c.created_at),
                "submission_text": c.submission_text[:300], "called_llm": c.called_llm,
                "micromodel_asked": c.micromodel_asked, "micromodel_confidence": c.micromodel_confidence,
                "micromodel_questions": c.micromodel_questions or [], "question_match": c.question_match,
                "decision_path": c.decision_path, "llm_asked": c.llm_asked, "llm_questions": c.llm_questions or [],
                "agreed": c.agreed, "duration_ms": c.duration_ms, "error": c.error,
            }
            for c in call_rows
        ],
    }


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
