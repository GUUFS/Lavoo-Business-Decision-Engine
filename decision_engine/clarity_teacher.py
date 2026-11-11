"""
The teacher job: the LLM checks the micromodel's work.

Every 3 hours it picks the decisions the micromodel was least sure about
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
from datetime import UTC, datetime, timedelta

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
RUN_EVERY_SECONDS = 3 * 60 * 60
next_scheduled_run_at: datetime | None = None
# Set by api/main.py's job: when this server's scheduler started, and the
# last error that stopped a scheduled run (None when the last one ran).
scheduler_started_at: datetime | None = None
last_job_error: str | None = None
# Never start a scheduled run sooner than this after the server starts.
MIN_FIRST_WAIT_SECONDS = 60
# Wait until the user has had time to answer or skip.
MIN_AGE_MINUTES = 15
# Rows the micromodel copies from (same rule as clarity_engine._TRUSTED_FILTER).
_TRUSTED_SQL = "(source IN ('llm_seed', 'llm_teacher') OR (source = 'live' AND outcome = 'answered'))"


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


def seconds_until_next_run(db: Session, now: datetime | None = None) -> float:
    """How long the scheduler should wait before the next run: RUN_EVERY_SECONDS
    after the last run of any kind (scheduled or "Run now"), as stored in the
    database. Because it reads the database, a server restart or redeploy no
    longer resets the clock (a redeploy every few hours used to mean the job
    never ran). Never less than MIN_FIRST_WAIT_SECONDS."""
    # 1. When did the last run start?
    now = now or datetime.now(UTC)
    last = db.query(ClarityTeacherRun.started_at).order_by(ClarityTeacherRun.started_at.desc()).first()
    # 2. Never run: start soon. Otherwise: whatever is left of the interval.
    if not last or not last[0]:
        return MIN_FIRST_WAIT_SECONDS
    remaining = (last[0] + timedelta(seconds=RUN_EVERY_SECONDS) - now).total_seconds()
    return max(MIN_FIRST_WAIT_SECONDS, remaining)


# SQL: is this unchecked live decision too weak to trust without the LLM?
# Mirrors the WHERE clause in _candidates.
# NULL-safe (an unanswered row has outcome NULL), so NOT (...) works too.
_WEAK_SQL = ("(COALESCE(outcome, '') = 'skipped' OR COALESCE(decision_path, '') IN ('reasoner', 'blend') "
             "OR COALESCE(confidence, 0) < :low)")


def why_nothing_to_check(db: Session) -> str:
    """The exact reason a run found nothing for the LLM to check, from the
    same rules _candidates uses: no unchecked decisions, decisions too new
    (the user may still be answering), or decisions confident enough not to
    need the LLM."""
    # 1. Count the unchecked live decisions, and why each one isn't picked.
    row = db.execute(text(f"""
        SELECT count(*) AS unchecked,
               count(*) FILTER (WHERE created_at >= now() - interval '{MIN_AGE_MINUTES} minutes') AS too_new,
               count(*) FILTER (WHERE created_at < now() - interval '{MIN_AGE_MINUTES} minutes'
                                AND NOT {_WEAK_SQL}) AS confident
        FROM clarity_corpus WHERE source = 'live' AND teacher_reviewed_at IS NULL
    """), {"low": LOW_CONFIDENCE}).mappings().one()
    # 2. Nothing unchecked at all.
    if not row["unchecked"]:
        return ("Nothing to check, so the LLM wasn't called: every checkup prompt has already been checked "
                "(no new prompts since the last run).")
    # 3. Unchecked, but none of them qualify yet: say which rule held each back.
    parts = []
    if row["too_new"]:
        parts.append(f"{row['too_new']} under {MIN_AGE_MINUTES} minutes old (the user may still be answering)")
    if row["confident"]:
        parts.append(f"{row['confident']} copied a trusted example with confidence of at least {LOW_CONFIDENCE}, "
                     "so they don't need the LLM")
    return (f"Nothing to check, so the LLM wasn't called: {row['unchecked']} unchecked prompt(s), "
            + "; ".join(parts) + ".")


def _run_note(db: Session, run: ClarityTeacherRun, counts: dict) -> str:
    """One plain sentence for the admin page on what the run did, and if it
    didn't call the LLM, exactly why."""
    # 1. The whole run failed before or while checking.
    if run.error:
        return f"The run failed, so the LLM checks stopped: {run.error}"
    # 2. Nothing qualified for checking.
    if not counts["candidates"]:
        return why_nothing_to_check(db)
    # 3. Every LLM call failed: give the first error word for word.
    if counts["errors"] and not counts["reviewed"]:
        first = (db.query(ClarityTeacherCall.error).filter(ClarityTeacherCall.run_id == run.id,
                                                         ClarityTeacherCall.error.isnot(None))
                 .order_by(ClarityTeacherCall.id).first())
        return f"All {counts['errors']} LLM check(s) failed. First error: {first[0] if first else 'unknown'}"
    # 4. Checked, but every prompt reused an earlier LLM answer.
    reused = counts["reviewed"] - counts["llm_calls"] + counts["errors"]
    if counts["reviewed"] and not counts["llm_calls"]:
        return (f"No LLM call was needed: all {counts['reviewed']} prompt(s) had an earlier LLM answer "
                "for the exact same text, which was reused.")
    # 5. A normal run.
    note = (f"Checked {counts['reviewed']} of {counts['candidates']}: {counts['llm_calls']} LLM call(s), "
            f"{max(reused, 0)} reused earlier answer(s), {counts['agreed']} agreed with the micromodel, "
            f"{counts['new_precedents']} new trusted example(s).")
    if counts["errors"]:
        note += f" {counts['errors']} check(s) failed and will be retried next run."
    return note


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
    # Save the counts and a plain-words note on what happened (or why not).
    for key, value in counts.items():
        setattr(run, key, value)
    try:
        run.note = _run_note(db, run, counts)
    except Exception as e:
        db.rollback()
        run.note = f"Couldn't work out the run's note: {e}"
    run.finished_at = datetime.now(UTC)
    db.commit()
    return {"run_id": run.id, **counts, "note": run.note, **({"error": run.error} if run.error else {})}


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
    # Is this server's scheduler running, and if not, why.
    if scheduler_started_at is None:
        scheduler = ("The scheduled job hasn't started on this server, so no automatic runs will happen until it does "
                     "(it starts with the API server).")
    elif last_job_error:
        scheduler = f"The last scheduled run couldn't start: {last_job_error}"
    else:
        scheduler = None
    return {
        "next_run_at": iso(next_scheduled_run_at),
        "run_every_hours": RUN_EVERY_SECONDS // 3600,
        "scheduler_problem": scheduler,
        "last_llm_call_at": iso(last_llm_call[0]) if last_llm_call else None,
        "runs": [
            {
                "id": r.id, "trigger": r.trigger, "started_at": iso(r.started_at), "finished_at": iso(r.finished_at),
                "candidates": r.candidates, "reviewed": r.reviewed, "agreed": r.agreed,
                "llm_calls": r.llm_calls, "new_precedents": r.new_precedents, "errors": r.errors, "error": r.error,
                "note": r.note,
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


def _check(key: str, label: str, ok: bool | None, detail: str) -> dict:
    """One link in the learning loop for the admin page. ok: True working,
    False broken, None nothing to judge yet (e.g. no prompts this week)."""
    return {"key": key, "label": label, "ok": ok, "detail": detail}


def learning_progress(db: Session, days: int = 7, weeks: int = 8) -> dict:
    """For the admin Micromodel page: is the micromodel learning from users
    and from the LLM, and is every link of that loop connected?

    The loop: the micromodel asks questions -> users answer or skip them ->
    answered decisions become trusted examples; the teacher job has the LLM
    re-check weak decisions -> the LLM's answers become trusted examples;
    new prompts then copy or borrow from those examples instead of the
    micromodel guessing. Returns the numbers for each part (this period vs
    the one before), the weekly growth of trusted examples, and a check for
    each link (working / broken / nothing to judge yet)."""
    # 1. This period and the one before it, for "up from N" comparisons.
    params = {"days": days}
    period = "created_at > now() - make_interval(days => :days)"
    previous = ("created_at <= now() - make_interval(days => :days) "
                "AND created_at > now() - make_interval(days => :days * 2)")

    # 2. Trusted examples: what the micromodel copies from. LLM seed rows,
    #    LLM teacher rows, and live decisions a user answered.
    trusted = db.execute(text(f"""
        SELECT
          count(*) FILTER (WHERE source = 'llm_seed') AS llm_seed,
          count(*) FILTER (WHERE source = 'llm_teacher') AS llm_teacher,
          count(*) FILTER (WHERE source = 'live' AND outcome = 'answered') AS user_answered,
          count(*) FILTER (WHERE {period} AND source = 'llm_teacher') AS new_llm,
          count(*) FILTER (WHERE {period} AND source = 'live' AND outcome = 'answered') AS new_user,
          count(*) FILTER (WHERE {previous} AND (source = 'llm_teacher' OR (source = 'live' AND outcome = 'answered'))) AS new_before,
          count(*) FILTER (WHERE {_TRUSTED_SQL} AND embedding IS NULL) AS missing_embedding
        FROM clarity_corpus
    """), params).mappings().one()
    total_trusted = trusted["llm_seed"] + trusted["llm_teacher"] + trusted["user_answered"]

    # 3. Feedback from users: questions shown, answered, skipped, and shown
    #    over an hour ago with nothing recorded (the answer never came back).
    users = db.execute(text(f"""
        SELECT
          count(*) AS decisions,
          count(*) FILTER (WHERE needs_clarification) AS asked,
          count(*) FILTER (WHERE outcome = 'answered') AS answered,
          count(*) FILTER (WHERE outcome = 'skipped') AS skipped,
          count(*) FILTER (WHERE needs_clarification AND outcome IS NULL
                           AND created_at < now() - interval '1 hour') AS no_outcome,
          count(*) FILTER (WHERE decision_path = 'neighbor') AS copied,
          count(*) FILTER (WHERE decision_path = 'blend') AS borrowed,
          count(*) FILTER (WHERE decision_path = 'reasoner') AS own,
          max(created_at) FILTER (WHERE outcome = 'answered') AS last_answered_at
        FROM clarity_corpus WHERE source = 'live' AND {period}
    """), params).mappings().one()
    users_before = db.execute(text(f"""
        SELECT count(*) AS decisions,
               count(*) FILTER (WHERE decision_path IN ('neighbor', 'blend')) AS learned
        FROM clarity_corpus WHERE source = 'live' AND {previous}
    """), params).mappings().one()

    # 4. Feedback from the LLM: teacher checks this period and the one
    #    before (agreement going up = the micromodel getting smarter).
    def teacher_numbers(where: str) -> dict:
        return dict(db.execute(text(f"""
            SELECT count(*) AS checks,
                   count(*) FILTER (WHERE agreed) AS agreed,
                   count(*) FILTER (WHERE error IS NOT NULL) AS errors,
                   count(*) FILTER (WHERE called_llm) AS llm_calls
            FROM clarity_teacher_calls WHERE {where}
        """), params).mappings().one())
    teacher_now, teacher_before = teacher_numbers(period), teacher_numbers(previous)
    last_run = db.query(ClarityTeacherRun).order_by(ClarityTeacherRun.started_at.desc()).first()

    # 5. Weekly growth: trusted examples added each week, and the running total.
    weekly = db.execute(text("""
        SELECT date_trunc('week', created_at) AS week,
               count(*) FILTER (WHERE source = 'llm_teacher') AS from_llm,
               count(*) FILTER (WHERE source = 'live' AND outcome = 'answered') AS from_users
        FROM clarity_corpus
        WHERE created_at > date_trunc('week', now()) - make_interval(weeks => :weeks - 1)
        GROUP BY 1 ORDER BY 1
    """), {"weeks": weeks}).mappings().all()
    added_in_window = sum(r["from_llm"] + r["from_users"] for r in weekly)
    running = total_trusted - added_in_window
    growth = []
    for r in weekly:
        running += r["from_llm"] + r["from_users"]
        growth.append({"week": r["week"].date().isoformat(), "from_llm": r["from_llm"],
                       "from_users": r["from_users"], "total": running})

    # 6. Percentages (None when there's nothing to divide by).
    def pct(a, b):
        return round(100 * a / b, 1) if b else None
    learned_now = users["copied"] + users["borrowed"]

    # 7. Check each link of the loop.
    checks = []
    # 7a. Questions are being asked at all.
    checks.append(_check(
        "asking", "The micromodel is asking users questions",
        None if not users["decisions"] else users["asked"] > 0,
        f"{users['asked']} of {users['decisions']} checkups got questions in the last {days} days"
        if users["decisions"] else f"No checkups in the last {days} days",
    ))
    # 7b. Users' answers come back with the checkup (the corpus_id link
    #     from the app to /analyze). Answers can be abandoned, so it's only
    #     broken when questions were shown and NONE came back.
    recorded = users["answered"] + users["skipped"]
    checks.append(_check(
        "answers_saved", "Users' answers and skips are saved",
        None if not users["asked"] else recorded > 0,
        f"{recorded} recorded ({users['answered']} answered, {users['skipped']} skipped), "
        f"{users['no_outcome']} shown with nothing back" if users["asked"] else "No questions shown yet",
    ))
    # 7c. Answered decisions are searchable as trusted examples.
    checks.append(_check(
        "examples_searchable", "Trusted examples can be found by new prompts",
        trusted["missing_embedding"] == 0,
        f"{total_trusted} trusted examples" + (f", {trusted['missing_embedding']} without a search vector"
                                               if trusted["missing_embedding"] else ", all searchable"),
    ))
    # 7d. The teacher job runs on schedule (within 1.5x its interval).
    overdue_after = RUN_EVERY_SECONDS * 1.5
    last_age = (datetime.now(UTC) - last_run.started_at).total_seconds() if last_run and last_run.started_at else None
    checks.append(_check(
        "teacher_running", f"The LLM teacher runs every {RUN_EVERY_SECONDS // 3600} hours",
        bool(last_run) and last_age is not None and last_age <= overdue_after,
        f"Last run {round(last_age / 3600, 1)} hours ago" if last_age is not None else "It has never run",
    ))
    # 7e. The teacher's LLM checks succeed (not all failing).
    checks.append(_check(
        "teacher_ok", "The LLM's checks succeed",
        None if not teacher_now["checks"] else teacher_now["errors"] < teacher_now["checks"],
        f"{teacher_now['checks'] - teacher_now['errors']} of {teacher_now['checks']} checks succeeded in the last {days} days"
        if teacher_now["checks"] else f"No checks in the last {days} days",
    ))
    # 7f. New prompts actually use what was learned.
    checks.append(_check(
        "examples_used", "New prompts use what it learned",
        None if not users["decisions"] or not total_trusted else learned_now > 0,
        f"{learned_now} of {users['decisions']} checkups copied or borrowed from a trusted example"
        if users["decisions"] else f"No checkups in the last {days} days",
    ))

    # 8. One-line verdict for the top of the page.
    broken = [c for c in checks if c["ok"] is False]
    if broken:
        status, headline = "attention", f"Not fully connected: {broken[0]['label'].lower()} isn't working."
    elif trusted["new_llm"] + trusted["new_user"] > 0:
        status = "learning"
        headline = (f"Learning: {trusted['new_llm'] + trusted['new_user']} new trusted examples in the last {days} days "
                    f"({trusted['new_user']} from users' answers, {trusted['new_llm']} from the LLM).")
    else:
        status, headline = "idle", f"Connected, but nothing new was learned in the last {days} days."

    return {
        "status": status,
        "headline": headline,
        "days": days,
        "trusted": {
            "total": total_trusted, "llm_seed": trusted["llm_seed"], "llm_teacher": trusted["llm_teacher"],
            "user_answered": trusted["user_answered"], "new": trusted["new_llm"] + trusted["new_user"],
            "new_from_llm": trusted["new_llm"], "new_from_users": trusted["new_user"], "new_before": trusted["new_before"],
        },
        "users": {
            "decisions": users["decisions"], "asked": users["asked"], "answered": users["answered"],
            "skipped": users["skipped"], "no_outcome": users["no_outcome"],
            "answer_rate_pct": pct(users["answered"], recorded),
            "last_answered_at": users["last_answered_at"].isoformat() if users["last_answered_at"] else None,
        },
        "llm": {
            "checks": teacher_now["checks"], "agreed": teacher_now["agreed"], "errors": teacher_now["errors"],
            "llm_calls": teacher_now["llm_calls"],
            "agreement_pct": pct(teacher_now["agreed"], teacher_now["checks"] - teacher_now["errors"]),
            "agreement_before_pct": pct(teacher_before["agreed"], teacher_before["checks"] - teacher_before["errors"]),
            "last_run_at": last_run.started_at.isoformat() if last_run and last_run.started_at else None,
        },
        "usage": {
            "copied": users["copied"], "borrowed": users["borrowed"], "own": users["own"],
            "learned_pct": pct(learned_now, users["decisions"]),
            "learned_before_pct": pct(users_before["learned"], users_before["decisions"]),
        },
        "growth": growth,
        "checks": checks,
    }


# Filters for the admin prompt history (decision_history), as SQL on clarity_corpus.
_HISTORY_VIEWS = {
    "all": "TRUE",
    "disagreed": "teacher_agreed IS FALSE",
    "agreed": "teacher_agreed IS TRUE",
    "unchecked": "teacher_reviewed_at IS NULL",
    "answered": "outcome = 'answered'",
    "skipped": "outcome = 'skipped'",
    "used_learning": "decision_path IN ('neighbor', 'blend')",
}

# How each decision path reads on the admin page.
_PATH_LABEL = {
    "neighbor": "Copied a trusted example (a near-identical prompt)",
    "blend": "Its own reasoning, with wording borrowed from a trusted example",
    "reasoner": "Its own reasoning only (no close trusted example yet)",
}


def _not_checked_reason(row: dict, now: datetime) -> str:
    """Why the LLM hasn't checked this prompt yet, from the same rules as
    _candidates: too new, confident enough not to need it, or waiting its turn."""
    # 1. Too new: the user may still answer or skip.
    created = row["created_at"]
    if created and created > now - timedelta(minutes=MIN_AGE_MINUTES):
        return f"Waiting: it's under {MIN_AGE_MINUTES} minutes old, so the user may still be answering."
    # 2. Weak decisions are queued; confident copies are left alone.
    weak = (row["outcome"] == "skipped" or row["decision_path"] in ("reasoner", "blend")
            or (row["confidence"] or 0) < LOW_CONFIDENCE)
    if not weak:
        return (f"Not needed: it copied a trusted example with confidence {row['confidence']:.2f} "
                f"(the LLM checks decisions below {LOW_CONFIDENCE}, skipped questions and the micromodel's own reasoning).")
    when = f" at {next_scheduled_run_at.isoformat()}" if next_scheduled_run_at else ""
    return f"Queued for the next LLM run{when} (up to 20 prompts per run, weakest first)."


def decision_history(db: Session, view: str = "all", limit: int = 25, offset: int = 0) -> dict:
    """Every prompt the micromodel handled, start to finish, for the admin
    Micromodel page:
      1. the prompt and who submitted it;
      2. the micromodel: what it asked, how it decided (its own reasoning
         notes, and the trusted example it copied or borrowed from);
      3. the user: answered (with answers), skipped, or no reply;
      4. the LLM teacher: what it asked, agreed or not, or why it hasn't
         checked yet;
      5. what was learned: the trusted example this prompt produced, and the
         later prompts that used it.
    view: a key of _HISTORY_VIEWS. Returns {items, total, counts}."""
    from database.pg_models import User

    # 1. The page of live decisions for this view, newest first, and the
    #    size of every view (for the filter tabs).
    where = _HISTORY_VIEWS.get(view, "TRUE")
    rows = db.execute(text(f"""
        SELECT id, submission_text, needs_clarification, questions, outcome, answers, confidence,
               decision_path, reasoning, user_id, created_at, teacher_reviewed_at, teacher_agreed
        FROM clarity_corpus WHERE source = 'live' AND {where}
        ORDER BY created_at DESC, id DESC LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset}).mappings().all()
    counts = dict(db.execute(text("SELECT " + ", ".join(
        f"count(*) FILTER (WHERE {sql}) AS {name}" for name, sql in _HISTORY_VIEWS.items()
    ) + " FROM clarity_corpus WHERE source = 'live'")).mappings().one())
    if not rows:
        return {"items": [], "total": counts.get(view, 0), "counts": counts}

    ids = [r["id"] for r in rows]
    texts_lower = list({(r["submission_text"] or "").lower() for r in rows})

    # 2. Who submitted each prompt.
    user_ids = {r["user_id"] for r in rows if r["user_id"]}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

    # 3. The trusted examples each decision copied or borrowed from.
    precedent_ids = {int(r["reasoning"]["precedent_id"]) for r in rows
                     if isinstance(r["reasoning"], dict) and r["reasoning"].get("precedent_id")}
    precedents = {p.id: p for p in db.query(ClarityCorpus).filter(ClarityCorpus.id.in_(precedent_ids)).all()} \
        if precedent_ids else {}

    # 4. The teacher's check of each prompt (by row, or by the same text,
    #    since one check marks every identical prompt).
    calls = (db.query(ClarityTeacherCall)
             .filter((ClarityTeacherCall.corpus_id.in_(ids))
                     | (text("lower(clarity_teacher_calls.submission_text) = ANY(:texts)")))
             .params(texts=texts_lower)
             .order_by(ClarityTeacherCall.created_at.desc()).all())
    call_by_id, call_by_text = {}, {}
    for c in calls:
        if c.corpus_id:
            call_by_id.setdefault(c.corpus_id, c)
        if not c.error:
            call_by_text.setdefault(c.submission_text.lower(), c)

    # 5. The LLM's answer saved as a trusted example for the same prompt.
    llm_rows = db.execute(text("""
        SELECT id, source, created_at, questions, needs_clarification, lower(submission_text) AS t
        FROM clarity_corpus
        WHERE source IN ('llm_seed', 'llm_teacher') AND lower(submission_text) = ANY(:texts)
        ORDER BY created_at DESC
    """), {"texts": texts_lower}).mappings().all()
    llm_by_text = {}
    for r in llm_rows:
        llm_by_text.setdefault(r["t"], r)

    # 6. Later prompts that used what this prompt taught: copied or borrowed
    #    from this row (if the user answered) or from its LLM example.
    example_ids = ids + [r["id"] for r in llm_rows]
    usage_rows = db.execute(text("""
        SELECT id, submission_text, decision_path, created_at,
               CAST(reasoning->>'precedent_id' AS INTEGER) AS precedent_id
        FROM clarity_corpus
        WHERE source = 'live' AND decision_path IN ('neighbor', 'blend')
          AND reasoning IS NOT NULL AND CAST(reasoning->>'precedent_id' AS INTEGER) = ANY(:ids)
        ORDER BY created_at DESC
    """), {"ids": example_ids}).mappings().all()
    used_by: dict[int, list] = {}
    for u in usage_rows:
        used_by.setdefault(u["precedent_id"], []).append({
            "id": u["id"], "prompt": (u["submission_text"] or "")[:160], "path": u["decision_path"],
            "created_at": u["created_at"].isoformat() if u["created_at"] else None,
        })

    # 7. Put each prompt's story together.
    def iso(d):
        return d.isoformat() if d else None
    now = datetime.now(UTC)
    items = []
    for r in rows:
        reasoning = r["reasoning"] if isinstance(r["reasoning"], dict) else {}
        prompt_lower = (r["submission_text"] or "").lower()
        user = users.get(r["user_id"])
        # 7a. The trusted example the micromodel leaned on, if any.
        precedent = None
        pid = reasoning.get("precedent_id")
        if pid and r["decision_path"] in ("neighbor", "blend") and int(pid) in precedents:
            p = precedents[int(pid)]
            precedent = {"id": p.id, "source": p.source, "prompt": (p.submission_text or "")[:300],
                         "similarity": reasoning.get("precedent_similarity")}
        # 7b. The teacher's check, or why there isn't one yet.
        call = call_by_id.get(r["id"]) or call_by_text.get(prompt_lower)
        teacher = None
        if call:
            teacher = {
                "checked_at": iso(call.created_at), "run_id": call.run_id, "called_llm": call.called_llm,
                "llm_asked": call.llm_asked, "llm_questions": call.llm_questions or [],
                "question_match": call.question_match, "agreed": call.agreed, "error": call.error,
            }
        # 7c. What was learned from this prompt, and who used it since.
        llm_example = llm_by_text.get(prompt_lower)
        learned = []
        if r["outcome"] == "answered":
            learned.append({"kind": "user", "example_id": r["id"],
                            "text": "The user answered, so this decision became a trusted example.",
                            "used_by": used_by.get(r["id"], [])})
        if llm_example:
            learned.append({"kind": "llm", "example_id": llm_example["id"],
                            "text": ("The LLM's answer to this prompt is a trusted example"
                                     + (" (from the starter set)." if llm_example["source"] == "llm_seed" else ".")),
                            "llm_questions": [q.get("question") for q in (llm_example["questions"] or []) if q.get("question")],
                            "used_by": used_by.get(llm_example["id"], [])})
        items.append({
            "id": r["id"],
            "created_at": iso(r["created_at"]),
            "prompt": (r["submission_text"] or "")[:2000],
            "user": {"id": user.id, "name": user.name, "email": user.email} if user else None,
            "micromodel": {
                "asked": bool(r["needs_clarification"]),
                "questions": [q.get("question") for q in (r["questions"] or []) if isinstance(q, dict) and q.get("question")],
                "path": r["decision_path"], "path_label": _PATH_LABEL.get(r["decision_path"] or "", r["decision_path"]),
                "confidence": r["confidence"], "trace": reasoning.get("trace") or [],
                "history_used": bool(reasoning.get("history_used")), "precedent": precedent,
            },
            "user_response": {
                "outcome": r["outcome"] or ("not_asked" if not r["needs_clarification"] else "no_reply"),
                "answers": r["answers"] or [],
            },
            "teacher": teacher,
            "teacher_status": ("checked" if r["teacher_reviewed_at"] else "unchecked"),
            "not_checked_reason": None if r["teacher_reviewed_at"] else _not_checked_reason(dict(r), now),
            "learned": learned,
        })
    return {"items": items, "total": counts.get(view, 0), "counts": counts}
