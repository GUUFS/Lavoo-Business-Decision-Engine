"""Admin activity stamps, and which analyses got a discovered tool's link.

Adds:
  - admin_activity: who did what, and when, for every change an admin makes
    from the admin end (api/services/admin_activity.py).
  - tool_discoveries.linked_analyses: the analyses whose saved result got the
    discovered tool's website link written in (decision_engine/tool_discovery.py).

Revision ID: f7b9d1e3a5c8
Revises: e3a5c7d9f1b4
Create Date: 2026-11-16
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'f7b9d1e3a5c8'
down_revision: str | Sequence[str] | None = 'e3a5c7d9f1b4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create admin_activity and add the column (safe to run twice)."""
    # 1. Admin activity stamps.
    op.execute("""
        CREATE TABLE IF NOT EXISTS admin_activity (
            id SERIAL PRIMARY KEY,
            admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            admin_name VARCHAR(255),
            admin_email VARCHAR(255),
            method VARCHAR(10) NOT NULL,
            path VARCHAR(500) NOT NULL,
            query VARCHAR(500),
            action VARCHAR(300) NOT NULL,
            status_code INTEGER NOT NULL,
            succeeded BOOLEAN NOT NULL DEFAULT true,
            ip_address VARCHAR(64),
            created_at TIMESTAMPTZ DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_admin_activity_admin_id ON admin_activity (admin_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_admin_activity_created_at ON admin_activity (created_at);")
    # 2. Which analyses got a discovered tool's link.
    op.execute("ALTER TABLE tool_discoveries ADD COLUMN IF NOT EXISTS linked_analyses JSON;")


def downgrade() -> None:
    """Drop both."""
    op.execute("ALTER TABLE tool_discoveries DROP COLUMN IF EXISTS linked_analyses;")
    op.execute("DROP TABLE IF EXISTS admin_activity;")
