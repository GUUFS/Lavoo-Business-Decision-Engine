"""
Shared pytest setup for tests that need a real Postgres database.

Set TEST_DATABASE_URL to a LOCAL, throwaway Postgres (with the pgvector
extension) to run them, e.g.

    TEST_DATABASE_URL=postgresql://postgres@localhost/lavoo_test venv/bin/pytest tests

Without TEST_DATABASE_URL these tests are skipped. A URL that points
anywhere other than this machine is refused, so the suite can never touch a
production database.

How it works:
  - DATABASE_URL is set to TEST_DATABASE_URL BEFORE the app's database
    module is imported (that module connects on import).
  - All tables are created from database/pg_models.py. The untyped
    `embedding` columns (production adds them as vector(384) with SQL) are
    given that type here so CREATE TABLE works on an empty database.
  - Each test gets a Session inside a transaction that is rolled back at the
    end. Commits made by the code under test only release a SAVEPOINT, so
    nothing a test writes is kept.
"""
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

# Make the project packages (database, subscriptions, decision_engine, ...)
# importable when pytest is run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def _is_local(url: str) -> bool:
    """True if the URL's host is this machine (localhost or a Unix socket)."""
    parsed = urlparse(url)
    host = parsed.hostname or parse_qs(parsed.query).get("host", [""])[0]
    return host in ("", "localhost", "127.0.0.1", "::1") or host.startswith("/")


if TEST_DATABASE_URL:
    if not _is_local(TEST_DATABASE_URL):
        raise RuntimeError("TEST_DATABASE_URL must point at a local database; refusing to run.")
    # Must happen before database.pg_connections is imported anywhere.
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    # api/routes/auth/login.py requires a JWT secret at import; tests only
    # need a placeholder (a real one in the environment is left as is).
    os.environ.setdefault("SECRET_KEY", "test-only-secret")
    # Import the auth routes first, as api/main.py effectively does: importing
    # subscriptions.commission_service on its own hits an existing circular
    # import (notification_service -> customer_service -> auth -> signup ->
    # notification_service). This order resolves it.
    import api.routes.auth  # noqa: E402,F401


@pytest.fixture(scope="session")
def pg_engine():
    """Create every table once per test session and return the engine."""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set (needs a local Postgres with pgvector)")
    from sqlalchemy import text
    from sqlalchemy.types import NullType, UserDefinedType

    from database.pg_connections import engine
    from database.pg_models import Base

    class Vector384(UserDefinedType):
        """DDL-only stand-in for Postgres's vector(384) type."""
        cache_ok = True

        def get_col_spec(self, **kw):
            return "vector(384)"

    # Give the untyped embedding columns their real database type.
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, NullType):
                column.type = Vector384()

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db(pg_engine):
    """A Session whose changes are all rolled back after the test."""
    from sqlalchemy.orm import Session

    connection = pg_engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()
