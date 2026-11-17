"""add_teacher_run_note

Revision ID: f2c4e6a8b0d1
Revises: e7b9d1f3a5c6
Create Date: 2026-11-11 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f2c4e6a8b0d1'
down_revision: str | Sequence[str] | None = 'e7b9d1f3a5c6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Each micromodel teacher run (clarity_teacher_runs) gets a plain-words
    note saying why it did or didn't call the LLM ("Nothing to check: 2
    decisions under 15 minutes old..."), shown on the admin Micromodel page."""
    op.execute("ALTER TABLE clarity_teacher_runs ADD COLUMN IF NOT EXISTS note TEXT;")


def downgrade() -> None:
    op.execute("ALTER TABLE clarity_teacher_runs DROP COLUMN IF EXISTS note;")
