"""Tool discovery: ai_tools.source and the tool_discoveries log.

ai_tools.source says where a tool came from ("catalog" for every existing
row, "discovered" for tools added by decision_engine/tool_discovery.py).
tool_discoveries logs every suggested tool the catalog didn't have and what
happened to it.

Revision ID: b5d7f9a1c3e4
Revises: a3c5e7f9b1d2
Create Date: 2026-11-11
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'b5d7f9a1c3e4'
down_revision: str | Sequence[str] | None = 'a3c5e7f9b1d2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the source column and the log table (safe to run twice)."""
    # 1. Where each tool came from; existing rows are the original catalog.
    op.execute("ALTER TABLE ai_tools ADD COLUMN IF NOT EXISTS source VARCHAR(40) DEFAULT 'catalog';")
    op.execute("UPDATE ai_tools SET source = 'catalog' WHERE source IS NULL;")
    # 2. The discovery log, one row per tool name.
    op.execute("""
        CREATE TABLE IF NOT EXISTS tool_discoveries (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            name_key VARCHAR(255) NOT NULL UNIQUE,
            status VARCHAR(30) NOT NULL DEFAULT 'pending',
            reason TEXT,
            times_suggested INTEGER NOT NULL DEFAULT 1,
            attempts INTEGER NOT NULL DEFAULT 0,
            website VARCHAR(500),
            directory VARCHAR(40),
            directory_url VARCHAR(500),
            tool_id INTEGER REFERENCES ai_tools(id) ON DELETE SET NULL,
            first_analysis_id INTEGER,
            last_analysis_id INTEGER,
            created_at TIMESTAMPTZ DEFAULT now(),
            processed_at TIMESTAMPTZ
        );
    """)
    # 3. Lookups by status (the hourly job and the admin filter).
    op.execute("CREATE INDEX IF NOT EXISTS ix_tool_discoveries_status ON tool_discoveries (status);")


def downgrade() -> None:
    """Remove the log table and the source column."""
    # 1. Log first (it points at ai_tools).
    op.execute("DROP TABLE IF EXISTS tool_discoveries;")
    # 2. Then the column.
    op.execute("ALTER TABLE ai_tools DROP COLUMN IF EXISTS source;")
