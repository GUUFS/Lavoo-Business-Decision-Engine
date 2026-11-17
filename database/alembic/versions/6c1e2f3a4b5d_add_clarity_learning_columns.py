"""add_clarity_learning_columns

Revision ID: 6c1e2f3a4b5d
Revises: 5b49a7a07e58
Create Date: 2026-11-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '6c1e2f3a4b5d'
down_revision: Union[str, Sequence[str], None] = '5b49a7a07e58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add the columns the micromodel needs to learn.
    IF NOT EXISTS because app startup adds the same columns."""
    op.execute("""
        ALTER TABLE clarity_corpus
            ADD COLUMN IF NOT EXISTS reasoning JSON,
            ADD COLUMN IF NOT EXISTS decision_path VARCHAR(20),
            ADD COLUMN IF NOT EXISTS answers JSON,
            ADD COLUMN IF NOT EXISTS teacher_reviewed_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS teacher_agreed BOOLEAN
    """)


def downgrade() -> None:
    """Downgrade schema: drop the learning columns."""
    op.execute("""
        ALTER TABLE clarity_corpus
            DROP COLUMN IF EXISTS teacher_agreed,
            DROP COLUMN IF EXISTS teacher_reviewed_at,
            DROP COLUMN IF EXISTS answers,
            DROP COLUMN IF EXISTS decision_path,
            DROP COLUMN IF EXISTS reasoning
    """)
