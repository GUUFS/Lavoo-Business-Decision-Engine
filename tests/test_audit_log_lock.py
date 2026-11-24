"""
The audit logs are locked (migration f4b6d8a0c2e3_lock_audit_logs.py): the
database refuses to change, delete or empty admin_activity and audit_log.
New records can still be added, and deleting an admin's user account still
works (their records keep their name, email and role; only admin_id empties).

The test database is built without migrations, so each test applies the
migration's SQL itself, inside the test's transaction (rolled back after).
"""
import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from database.pg_models import AdminActivity, User

_MIGRATION = Path(__file__).resolve().parents[1] / "database/alembic/versions/f4b6d8a0c2e3_lock_audit_logs.py"


def _lock(db, monkeypatch):
    """Run the migration's upgrade() against this test's session."""
    spec = importlib.util.spec_from_file_location("lock_audit_logs", _MIGRATION)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    monkeypatch.setattr(migration.op, "execute", lambda sql: db.execute(text(sql)), raising=False)
    migration.upgrade()


def _refused(db, sql, **params):
    """True if the database refuses this statement (checked in a savepoint)."""
    savepoint = db.begin_nested()
    try:
        db.execute(text(sql), params)
    except DBAPIError as exc:
        savepoint.rollback()
        assert "can't be changed or deleted" in str(exc)
        return True
    savepoint.rollback()
    return False


def _stamp(db, admin=None):
    """One Admin Activity record."""
    row = AdminActivity(admin_id=admin.id if admin else None, admin_name="Ada", admin_email="ada@x.test",
                        admin_role="Finance", method="POST", path="/api/control/refunds/1",
                        action="Refunded payment 1", status_code=200, succeeded=True)
    db.add(row)
    db.flush()
    return row


@pytest.fixture
def locked(db, monkeypatch):
    """The test's session with the audit logs locked."""
    _lock(db, monkeypatch)
    return db


def test_records_can_be_added_but_not_changed_deleted_or_emptied(locked):
    row = _stamp(locked)
    assert _refused(locked, "UPDATE admin_activity SET action = 'Nothing happened' WHERE id = :i", i=row.id)
    assert _refused(locked, "DELETE FROM admin_activity WHERE id = :i", i=row.id)
    assert _refused(locked, "TRUNCATE admin_activity")
    assert _refused(locked, "TRUNCATE audit_log")
    # The record is still there, unchanged.
    assert locked.execute(text("SELECT action FROM admin_activity WHERE id = :i"), {"i": row.id}).scalar() \
        == "Refunded payment 1"


def test_deleting_an_admins_account_keeps_their_records(locked):
    admin = User(name="Ada", email="ada-lock@x.test", password="x", confirm_password="x", is_admin=True)
    locked.add(admin)
    locked.flush()
    row = _stamp(locked, admin)
    # 1. The account can be deleted (the database empties admin_id on their records).
    locked.execute(text("DELETE FROM users WHERE id = :i"), {"i": admin.id})
    kept = locked.execute(text("SELECT admin_id, admin_name, admin_role, action FROM admin_activity WHERE id = :i"),
                          {"i": row.id}).one()
    assert tuple(kept) == (None, "Ada", "Finance", "Refunded payment 1")
    # 2. Emptying admin_id while changing something else is still refused.
    other = _stamp(locked, None)
    assert _refused(locked, "UPDATE admin_activity SET admin_name = 'Someone else' WHERE id = :i", i=other.id)
