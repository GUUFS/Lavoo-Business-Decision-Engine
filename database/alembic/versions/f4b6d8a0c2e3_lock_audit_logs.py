"""Lock the audit logs: their records can never be changed or deleted.

The database itself refuses (a trigger), so it holds for the app, the admin
panel, scripts and anyone running SQL by hand:

  - admin_activity (the admin panel's Admin Activity page)
  - audit_log

Refused: DELETE, UPDATE and TRUNCATE. New records can still be added.

One change is allowed on admin_activity: when an admin's user account is
deleted, the database sets admin_id to empty on their records (the foreign
key's ON DELETE SET NULL). Their name, email, role and every other field stay
exactly as they were, so the record still says who did it.

Only a database owner who deliberately removes the trigger could get round
this (see downgrade()).

Revision ID: f4b6d8a0c2e3
Revises: e3a5c7e9f1b2
Create Date: 2026-11-24
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'f4b6d8a0c2e3'
down_revision: str | Sequence[str] | None = 'e3a5c7e9f1b2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The tables that are locked.
LOCKED_TABLES = ("admin_activity", "audit_log")


def upgrade() -> None:
    """Create the refusing function and attach it to each audit table."""
    # 1. The function: refuse every change and delete, except the user-deleted case above.
    op.execute("""
        CREATE OR REPLACE FUNCTION refuse_audit_log_change() RETURNS trigger AS $$
        BEGIN
            -- Nested, so OLD/NEW are only read for a row UPDATE (a TRUNCATE has neither).
            IF TG_OP = 'UPDATE' AND TG_TABLE_NAME = 'admin_activity' THEN
                IF OLD.admin_id IS NOT NULL AND NEW.admin_id IS NULL
                   AND (to_jsonb(NEW) - 'admin_id') = (to_jsonb(OLD) - 'admin_id') THEN
                    RETURN NEW;
                END IF;
            END IF;
            RAISE EXCEPTION 'Audit log records in % can''t be changed or deleted (% refused).', TG_TABLE_NAME, TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END;
        $$ LANGUAGE plpgsql;
    """)
    # 2. Attach it to each table that exists: row by row for UPDATE/DELETE, and once for TRUNCATE.
    for table in LOCKED_TABLES:
        op.execute(f"""
            DO $$
            BEGIN
                IF to_regclass('public.{table}') IS NOT NULL THEN
                    DROP TRIGGER IF EXISTS {table}_no_change ON {table};
                    CREATE TRIGGER {table}_no_change BEFORE UPDATE OR DELETE ON {table}
                        FOR EACH ROW EXECUTE FUNCTION refuse_audit_log_change();
                    DROP TRIGGER IF EXISTS {table}_no_truncate ON {table};
                    CREATE TRIGGER {table}_no_truncate BEFORE TRUNCATE ON {table}
                        FOR EACH STATEMENT EXECUTE FUNCTION refuse_audit_log_change();
                END IF;
            END $$;
        """)


def downgrade() -> None:
    """Unlock (remove the triggers and the function)."""
    # 1. The triggers, then the function.
    for table in LOCKED_TABLES:
        op.execute(f"""
            DO $$
            BEGIN
                IF to_regclass('public.{table}') IS NOT NULL THEN
                    DROP TRIGGER IF EXISTS {table}_no_change ON {table};
                    DROP TRIGGER IF EXISTS {table}_no_truncate ON {table};
                END IF;
            END $$;
        """)
    op.execute("DROP FUNCTION IF EXISTS refuse_audit_log_change()")
