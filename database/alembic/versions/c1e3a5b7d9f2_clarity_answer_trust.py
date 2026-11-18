"""Whether a founder's answers can teach the micromodel.

Adds to clarity_corpus:
  - answer_trusted: False when the founder's answers looked fake, or the
    account went over its daily limit of trusted answers
    (decision_engine/answer_trust.py). Those checkups are not copied for
    other founders. NULL for old rows, which stay trusted.
  - answer_flag: why it wasn't trusted ('junk: keyboard mash', 'over_daily_limit').

Revision ID: c1e3a5b7d9f2
Revises: b9d1f3a5c7e2
Create Date: 2026-11-18
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'c1e3a5b7d9f2'
down_revision: str | Sequence[str] | None = 'b9d1f3a5c7e2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the two answer-trust columns (safe to run twice)."""
    # 1. Can this founder's answers be copied?
    op.execute("ALTER TABLE clarity_corpus ADD COLUMN IF NOT EXISTS answer_trusted BOOLEAN;")
    # 2. If not, why.
    op.execute("ALTER TABLE clarity_corpus ADD COLUMN IF NOT EXISTS answer_flag VARCHAR(60);")


def downgrade() -> None:
    """Drop the two answer-trust columns."""
    # 1. Remove both columns.
    op.execute("ALTER TABLE clarity_corpus DROP COLUMN IF EXISTS answer_flag;")
    op.execute("ALTER TABLE clarity_corpus DROP COLUMN IF EXISTS answer_trusted;")
