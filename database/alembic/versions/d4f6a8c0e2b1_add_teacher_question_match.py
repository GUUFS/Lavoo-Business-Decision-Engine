"""add_teacher_question_match

Revision ID: d4f6a8c0e2b1
Revises: c9d1e3f5a7b2
Create Date: 2026-11-06 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd4f6a8c0e2b1'
down_revision: str | Sequence[str] | None = 'c9d1e3f5a7b2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """The teacher now compares the questions themselves, not just whether
    to ask (decision_engine/clarity_teacher.py): store the micromodel's
    questions and how closely they match the LLM's."""
    op.execute("""
        ALTER TABLE clarity_teacher_calls
            ADD COLUMN IF NOT EXISTS micromodel_questions JSON,
            ADD COLUMN IF NOT EXISTS question_match DOUBLE PRECISION;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE clarity_teacher_calls
            DROP COLUMN IF EXISTS micromodel_questions,
            DROP COLUMN IF EXISTS question_match;
    """)
