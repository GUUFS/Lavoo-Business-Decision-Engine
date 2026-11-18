"""Ad check-up failure log, and which ad brought each account.

Adds:
  - checkup_failures: every ad check-up that went wrong, with the reason
    (decision_engine/guest_checkup.py record_failure). More than 3 in an hour
    emails the admin.
  - users.utm_source / users.utm_campaign: copied from the visitor's ad
    check-up when they claim it, so we can see which ad brought each person.

Revision ID: b9d1f3a5c7e2
Revises: a8c0e2f4b6d1
Create Date: 2026-11-18
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'b9d1f3a5c7e2'
down_revision: str | Sequence[str] | None = 'a8c0e2f4b6d1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create checkup_failures and add the two ad columns to users (safe to run twice)."""
    # 1. The failure log.
    op.execute("""
        CREATE TABLE IF NOT EXISTS checkup_failures (
            id SERIAL PRIMARY KEY,
            source VARCHAR(20) NOT NULL,
            reason TEXT NOT NULL,
            checkup_id INTEGER REFERENCES guest_checkups(id) ON DELETE SET NULL,
            visitor_id VARCHAR(64),
            alerted BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_checkup_failures_id ON checkup_failures (id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_checkup_failures_created_at ON checkup_failures (created_at);")
    # 2. Which ad brought each account.
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS utm_source VARCHAR(100);")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS utm_campaign VARCHAR(150);")


def downgrade() -> None:
    """Drop the two ad columns and the failure log."""
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS utm_campaign;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS utm_source;")
    op.execute("DROP TABLE IF EXISTS checkup_failures;")
