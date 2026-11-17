"""Ad checkups run before signup (lavoo.io/checkup).

Adds:
  - guest_checkups: one row per checkup a visitor runs from the Facebook ad
    before having an account (decision_engine/guest_checkup.py).
  - business_analyses.user_id may now be empty: an ad checkup has no owner
    until the visitor signs up and claims it.

Revision ID: a8c0e2f4b6d1
Revises: f7b9d1e3a5c8
Create Date: 2026-11-17
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'a8c0e2f4b6d1'
down_revision: str | Sequence[str] | None = 'f7b9d1e3a5c8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create guest_checkups and allow ownerless analyses (safe to run twice)."""
    # 1. The guest checkups table.
    op.execute("""
        CREATE TABLE IF NOT EXISTS guest_checkups (
            id SERIAL PRIMARY KEY,
            token VARCHAR(64) NOT NULL UNIQUE,
            visitor_id VARCHAR(64),
            ip_hash VARCHAR(64),
            business_goal TEXT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'started',
            error TEXT,
            analysis_id INTEGER REFERENCES business_analyses(id) ON DELETE SET NULL,
            utm_source VARCHAR(100),
            utm_campaign VARCHAR(150),
            claimed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            claimed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now()
        );
    """)
    # 2. Indexes for the limit checks and the daily clean-up.
    op.execute("CREATE INDEX IF NOT EXISTS ix_guest_checkups_id ON guest_checkups (id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_guest_checkups_token ON guest_checkups (token);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_guest_checkups_visitor_id ON guest_checkups (visitor_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_guest_checkups_ip_hash ON guest_checkups (ip_hash);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_guest_checkups_created_at ON guest_checkups (created_at);")
    # 3. An ad checkup's analysis has no owner until it is claimed.
    op.execute("ALTER TABLE business_analyses ALTER COLUMN user_id DROP NOT NULL;")


def downgrade() -> None:
    """Remove ownerless analyses, make the owner required again, drop the table."""
    # 1. Ownerless analyses can't stay once the owner is required.
    op.execute("DELETE FROM business_analyses WHERE user_id IS NULL;")
    op.execute("ALTER TABLE business_analyses ALTER COLUMN user_id SET NOT NULL;")
    # 2. The table.
    op.execute("DROP TABLE IF EXISTS guest_checkups;")
