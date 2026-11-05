"""
Tests for the Decision Engine health check (decision_engine/health.py),
shown on the admin Engine Health page.

Runs the real checks against real Postgres and the real embedding model.
Only the LLM call is faked.
"""
import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import text

from database.pg_models import CheckupUsage, ClarityTeacherRun, User
from decision_engine import health
from decision_engine.health import run_health_checks


def by_key(result):
    """Checks keyed by their id, e.g. result['llm']."""
    return {c["key"]: c for c in result["checks"]}


def seed_healthy_engine(db):
    """Data a working engine has: searchable tools, trusted examples, a
    recent clean teacher run and a completed checkup."""
    vector = "[" + ",".join(["0.01"] * 384) + "]"
    db.execute(text("DELETE FROM ai_tools"))
    db.execute(text("INSERT INTO ai_tools (name, description, embedding) VALUES "
                    "('Zapier', 'Automation', CAST(:v AS vector)), ('Notion', 'Docs', CAST(:v AS vector))"),
               {"v": vector})
    for i in range(25):
        db.execute(text(
            "INSERT INTO clarity_corpus (submission_text, needs_clarification, gap_types, questions, source, embedding) "
            "VALUES (:t, false, '[]', '[]', 'llm_seed', CAST(:v AS vector))"), {"t": f"example {i}", "v": vector})
    db.add(ClarityTeacherRun(trigger="scheduled", started_at=datetime.now(UTC) - timedelta(hours=1),
                             finished_at=datetime.now(UTC), reviewed=5, agreed=4))
    user = User(name="Health", email="health@test.local", password="x", confirm_password="x")
    db.add(user)
    db.flush()
    db.add(CheckupUsage(user_id=user.id, status="completed", created_at=datetime.now(UTC) - timedelta(hours=2)))
    # Committed to the test's savepoint: a failed check rolls back, and the
    # seeded data must survive that (it's still discarded after the test).
    db.commit()
    return user


def test_healthy_engine_reports_ok_everywhere(db, monkeypatch):
    seed_healthy_engine(db)
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    result = asyncio.run(run_health_checks(db))
    checks = by_key(result)

    assert set(checks) == {"database", "tools", "embeddings", "micromodel", "examples",
                           "teacher", "llm", "files", "cache", "checkups"}
    not_ok = {k: c["detail"] for k, c in checks.items() if c["status"] != "ok"}
    assert not_ok == {}
    assert result["status"] == "ok"
    assert "Sample prompt decided by" in checks["micromodel"]["detail"]


def test_problems_are_reported_not_crashed(db, monkeypatch):
    user = seed_healthy_engine(db)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    db.execute(text("UPDATE ai_tools SET embedding = NULL"))
    db.add(ClarityTeacherRun(trigger="scheduled", started_at=datetime.now(UTC), error="LLM down"))
    for _ in range(3):
        db.add(CheckupUsage(user_id=user.id, status="failed", error="xAI 503",
                            created_at=datetime.now(UTC) - timedelta(minutes=5)))
    db.flush()

    checks = by_key(asyncio.run(run_health_checks(db)))
    assert checks["llm"]["status"] == "fail" and "XAI_API_KEY" in checks["llm"]["detail"]
    assert checks["tools"]["status"] == "fail" and "none have embeddings" in checks["tools"]["detail"]
    assert checks["teacher"]["status"] == "fail" and "LLM down" in checks["teacher"]["detail"]
    assert checks["checkups"]["status"] == "fail"       # 3 of 4 failed in the last 24 h
    assert "xAI 503" in checks["checkups"]["detail"]


def test_one_broken_check_does_not_break_the_rest(db, monkeypatch):
    seed_healthy_engine(db)
    monkeypatch.setenv("XAI_API_KEY", "test-key")

    def broken(_db):
        _db.execute(text("SELECT * FROM table_that_does_not_exist"))
    with patch.object(health, "_tools_catalog", broken):
        checks = by_key(asyncio.run(run_health_checks(db)))
    assert checks["tools"]["status"] == "fail" and "UndefinedTable" in checks["tools"]["detail"]
    # Database checks after the broken one still ran on a working session.
    assert checks["examples"]["status"] == "ok" and checks["checkups"]["status"] == "ok"


def test_live_llm_check_makes_one_small_call(db, monkeypatch):
    seed_healthy_engine(db)
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    reply = MagicMock()
    reply.choices = [MagicMock(message=MagicMock(content="ok"))]
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=reply)
    with patch("openai.AsyncOpenAI", return_value=client):
        checks = by_key(asyncio.run(run_health_checks(db, live=True)))
    assert checks["llm"]["status"] == "ok" and "answered 'ok'" in checks["llm"]["detail"]
    assert client.chat.completions.create.await_args.kwargs["max_tokens"] == 3
