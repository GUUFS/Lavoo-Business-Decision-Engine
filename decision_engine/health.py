"""
Decision Engine health check, shown on the admin Engine Health page.

Checks every part a checkup depends on and reports each one as
'ok', 'warn' or 'fail' with a plain explanation:

  1. Database and pgvector     - can we query, is the vector extension on
  2. AI tools catalog          - tools exist and have embeddings (tool picks)
  3. Embedding model           - the local SentenceTransformer gives 384 numbers
  4. Clarity micromodel        - runs a full clarifying-questions decision on
                                 a sample prompt (nothing is saved)
  5. Trusted examples          - the micromodel has LLM-checked examples to copy
  6. Micromodel teacher job    - ran in the last ~6 hours, without failing
  7. LLM (xAI Grok)            - API key set; with live=True, a tiny real call
  8. File and image reading    - the document/image parsers load
  9. Cache                     - a value can be saved and read back
 10. Recent checkups           - completed vs failed in the last 24 hours and
                                 7 days, and any stuck for over 30 minutes

The overall status is the worst of all checks. Nothing here changes data.
"""
import os
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database.pg_models import CheckupUsage

OK, WARN, FAIL = "ok", "warn", "fail"
_RANK = {OK: 0, WARN: 1, FAIL: 2}
SAMPLE_PROMPT = "I run a small bakery in Lagos and sales dropped 30% in the last two months. What should I fix first?"


async def _check(key: str, name: str, fn, db: Session | None = None) -> dict:
    """Run one check. `fn` returns (status, detail), or a coroutine giving
    it; an exception is a 'fail' with the error as the detail. Adds how long
    the check took. A failed database check is rolled back so the checks
    after it still get a working session."""
    started = time.monotonic()
    try:
        result = fn()
        if hasattr(result, "__await__"):
            result = await result
        status, detail = result
    except Exception as e:  # a broken part must show as failed, not crash the page
        status, detail = FAIL, f"{type(e).__name__}: {e}"[:500]
        if db is not None:
            db.rollback()
    return {"key": key, "name": name, "status": status, "detail": detail,
            "ms": int((time.monotonic() - started) * 1000)}


def _database(db: Session):
    """Database answers and the pgvector extension is installed."""
    db.execute(text("SELECT 1"))
    has_vector = db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).first()
    if not has_vector:
        return FAIL, "Database is reachable, but the pgvector extension is missing (tool search and the micromodel need it)."
    return OK, "Database is reachable and pgvector is installed."


def _tools_catalog(db: Session):
    """There are AI tools to recommend, and they have embeddings for search."""
    total, embedded = db.execute(text(
        "SELECT count(*), count(embedding) FROM ai_tools"
    )).first()
    if not total:
        return FAIL, "The AI tools catalog is empty, so checkups can't recommend tools."
    if not embedded:
        return FAIL, f"{total} tools, but none have embeddings, so tool search returns nothing."
    if embedded < total:
        return WARN, f"{embedded} of {total} tools have embeddings; the rest can't be found by search."
    return OK, f"{total} tools, all searchable."


def _embedding_model():
    """The local embedding model is loaded and returns a 384-number vector."""
    from decision_engine.clarity_engine import _generate_embedding
    vector = _generate_embedding("health check")
    if len(vector) != 384:
        return FAIL, f"Embedding model returned {len(vector)} numbers instead of 384."
    return OK, "Embedding model is loaded (384 dimensions)."


def _micromodel(db: Session):
    """The clarifying-questions micromodel makes a decision end to end:
    reasoning, embedding, nearest trusted example, final decision. Uses the
    same steps as clarity_engine.get_clarifying_questions but saves nothing."""
    from decision_engine.clarity_engine import _decide, _find_trusted_neighbors, _generate_embedding
    from decision_engine.clarity_reasoner import reason

    reasoning = reason(SAMPLE_PROMPT)
    neighbors = _find_trusted_neighbors(db, _generate_embedding(SAMPLE_PROMPT), k=1)
    similarity = float(neighbors[0]["similarity_score"]) if neighbors else 0.0
    path, asks, questions = _decide(SAMPLE_PROMPT, reasoning, neighbors[0] if neighbors else None, similarity)
    verdict = f"would ask {len(questions)} question(s)" if asks and questions else "would not ask questions"
    return OK, f"Sample prompt decided by '{path}' (closest example {similarity:.2f}); {verdict}."


def _trusted_examples(db: Session):
    """The micromodel has LLM-checked examples it can copy from."""
    count = db.execute(text(
        "SELECT count(*) FROM clarity_corpus WHERE source IN ('llm_seed', 'llm_teacher') AND embedding IS NOT NULL"
    )).scalar() or 0
    if count == 0:
        return FAIL, "No trusted examples. The micromodel can only use its own rules."
    if count < 20:
        return WARN, f"Only {count} trusted examples; answers improve as the teacher adds more."
    return OK, f"{count} trusted examples."


def _teacher_job(db: Session):
    """The teacher job ran recently and its last run didn't fail."""
    from decision_engine import clarity_teacher
    last = db.execute(text(
        "SELECT started_at, error, errors, reviewed FROM clarity_teacher_runs ORDER BY started_at DESC LIMIT 1"
    )).mappings().first()
    if not last:
        return WARN, "The teacher job hasn't run yet (it runs every 6 hours after the server starts)."
    age = datetime.now(UTC) - last["started_at"]
    hours = age.total_seconds() / 3600
    every = clarity_teacher.RUN_EVERY_SECONDS / 3600
    if last["error"]:
        return FAIL, f"Last run ({hours:.1f} h ago) failed: {last['error'][:200]}"
    if hours > every * 2 + 1:
        return WARN, f"Last run was {hours:.1f} h ago; it should run every {every:.0f} h. Is the server's job running?"
    if last["errors"]:
        return WARN, f"Last run {hours:.1f} h ago had {last['errors']} failed check(s)."
    return OK, f"Last run {hours:.1f} h ago checked {last['reviewed']} decision(s) without errors."


async def _llm(live: bool):
    """The xAI key is set; with live=True also make a tiny real call."""
    if not os.getenv("XAI_API_KEY"):
        return FAIL, "XAI_API_KEY is not set. Every checkup will fail."
    if not live:
        return OK, "API key is set. Run the full check to test a live call."
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1", timeout=30.0, max_retries=0)
    started = time.monotonic()
    reply = await client.chat.completions.create(
        model="grok-4-1-fast-non-reasoning",
        messages=[{"role": "user", "content": "Reply with the single word: ok"}],
        max_tokens=3, temperature=0,
    )
    seconds = time.monotonic() - started
    answer = (reply.choices[0].message.content or "").strip()
    status = OK if seconds < 15 else WARN
    return status, f"Live call answered {answer!r} in {seconds:.1f}s."


def _file_readers():
    """The document and image parsers used for uploaded files load."""
    from decision_engine.multimodal.handler import MultimodalHandler
    MultimodalHandler(use_vision_for_images=False)
    return OK, "Document and image readers load."


async def _cache():
    """A value can be written to the cache and read back."""
    from api.cache import delete_cached, get_cached, set_cached

    key = f"health:{time.time_ns()}"
    await set_cached(key, {"ok": True}, 30)
    value = await get_cached(key)
    await delete_cached(key)
    if value != {"ok": True}:
        return WARN, "Cache didn't return the value just saved; lists may load slowly."
    return OK, "Cache saves and returns values."


def _recent_checkups(db: Session):
    """Completed vs failed checkups recently, plus any stuck as 'started'."""
    now = datetime.now(UTC)

    def counts(since):
        rows = db.query(CheckupUsage.status, func.count()).filter(
            CheckupUsage.created_at > since).group_by(CheckupUsage.status).all()
        return dict(rows)

    day, week = counts(now - timedelta(days=1)), counts(now - timedelta(days=7))
    stuck = db.query(CheckupUsage).filter(
        CheckupUsage.status == "started", CheckupUsage.created_at < now - timedelta(minutes=30)
    ).count()
    done, failed = day.get("completed", 0), day.get("failed", 0)
    summary = (f"Last 24 h: {done} completed, {failed} failed. "
               f"Last 7 days: {week.get('completed', 0)} completed, {week.get('failed', 0)} failed.")
    last_error = (
        db.query(CheckupUsage.error).filter(CheckupUsage.status == "failed", CheckupUsage.error.isnot(None))
        .order_by(CheckupUsage.created_at.desc()).first()
    )
    if last_error and failed:
        summary += f" Latest error: {last_error[0][:200]}"
    if stuck:
        return WARN, f"{stuck} checkup(s) have been running for over 30 minutes. " + summary
    if done + failed >= 3 and failed / (done + failed) > 0.25:
        return FAIL, summary
    if failed:
        return WARN, summary
    return OK, summary


async def run_health_checks(db: Session, live: bool = False) -> dict:
    """Run every check, one after another. live=True also makes one tiny
    real LLM call. Returns {status, checked_at, live, checks: [...]}."""
    checks = [
        await _check("database", "Database and pgvector", lambda: _database(db), db),
        await _check("tools", "AI tools catalog", lambda: _tools_catalog(db), db),
        await _check("embeddings", "Embedding model", _embedding_model),
        await _check("micromodel", "Clarity micromodel", lambda: _micromodel(db), db),
        await _check("examples", "Trusted examples", lambda: _trusted_examples(db), db),
        await _check("teacher", "Micromodel teacher job", lambda: _teacher_job(db), db),
        await _check("llm", "LLM (xAI Grok)", lambda: _llm(live)),
        await _check("files", "File and image reading", _file_readers),
        await _check("cache", "Cache", _cache),
        await _check("checkups", "Recent checkups", lambda: _recent_checkups(db), db),
    ]
    db.rollback()  # end the read-only transaction
    overall = max((c["status"] for c in checks), key=_RANK.__getitem__)
    return {"status": overall, "checked_at": datetime.now(UTC).isoformat(), "live": live, "checks": checks}
