"""add_checkup_usage_table

Revision ID: c9d1e3f5a7b2
Revises: b8e4d2f1c3a5
Create Date: 2026-11-05 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c9d1e3f5a7b2'
down_revision: str | Sequence[str] | None = 'b8e4d2f1c3a5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """One row per Decision Engine checkup a user starts, for the weekly
    limit (decision_engine/checkup_limits.py) and the admin Engine Health
    page's success/failure numbers. IF NOT EXISTS because app
    startup (init_db) creates the same table."""
    op.execute("""
        CREATE TABLE IF NOT EXISTS checkup_usage (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            status VARCHAR(20) NOT NULL DEFAULT 'started',
            analysis_id INTEGER,
            finished_at TIMESTAMPTZ,
            error TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_checkup_usage_user_id ON checkup_usage (user_id);
        CREATE INDEX IF NOT EXISTS ix_checkup_usage_created_at ON checkup_usage (created_at);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS checkup_usage;")
