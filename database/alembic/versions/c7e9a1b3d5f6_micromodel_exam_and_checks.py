"""Micromodel: weekly exam, a person checks the LLM, checkup -> diagnosis link.

Adds:
  - micromodel_exam_questions: the exam an admin writes (prompt + right answer).
  - micromodel_exam_results: each time the micromodel sits the exam.
  - clarity_corpus.analysis_id: the diagnosis a checkup produced.
  - clarity_corpus.person_verdict (+ note, when, who): a person's 'good' or
    'wrong' on an LLM answer. 'wrong' answers are never used again.
  - clarity_teacher_calls.why_checked: 'unsure' or 'random'.

Revision ID: c7e9a1b3d5f6
Revises: b5d7f9a1c3e4
Create Date: 2026-11-13
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'c7e9a1b3d5f6'
down_revision: str | Sequence[str] | None = 'b5d7f9a1c3e4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the columns and tables (safe to run twice)."""
    # 1. On each checkup: its diagnosis, and a person's verdict on LLM answers.
    op.execute("""
        ALTER TABLE clarity_corpus
          ADD COLUMN IF NOT EXISTS analysis_id INTEGER REFERENCES business_analyses(id) ON DELETE SET NULL,
          ADD COLUMN IF NOT EXISTS person_verdict VARCHAR(20),
          ADD COLUMN IF NOT EXISTS person_note TEXT,
          ADD COLUMN IF NOT EXISTS person_checked_at TIMESTAMPTZ,
          ADD COLUMN IF NOT EXISTS person_checked_by INTEGER REFERENCES users(id) ON DELETE SET NULL;
    """)
    # 2. Why the LLM checked a decision (every earlier check was an unsure one).
    op.execute("ALTER TABLE clarity_teacher_calls "
               "ADD COLUMN IF NOT EXISTS why_checked VARCHAR(20) NOT NULL DEFAULT 'unsure';")
    # 3. The exam questions.
    op.execute("""
        CREATE TABLE IF NOT EXISTS micromodel_exam_questions (
            id SERIAL PRIMARY KEY,
            prompt TEXT NOT NULL,
            should_ask BOOLEAN NOT NULL,
            expected_questions JSON NOT NULL DEFAULT '[]',
            note TEXT,
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            active BOOLEAN NOT NULL DEFAULT true
        );
    """)
    # 4. The exam results.
    op.execute("""
        CREATE TABLE IF NOT EXISTS micromodel_exam_results (
            id SERIAL PRIMARY KEY,
            trigger VARCHAR(20) NOT NULL DEFAULT 'weekly',
            taken_at TIMESTAMPTZ DEFAULT now(),
            total INTEGER NOT NULL DEFAULT 0,
            right_decision INTEGER NOT NULL DEFAULT 0,
            fully_right INTEGER NOT NULL DEFAULT 0,
            marking JSON,
            error TEXT
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_micromodel_exam_results_taken_at "
               "ON micromodel_exam_results (taken_at);")


def downgrade() -> None:
    """Remove the tables and columns."""
    # 1. Tables.
    op.execute("DROP TABLE IF EXISTS micromodel_exam_results;")
    op.execute("DROP TABLE IF EXISTS micromodel_exam_questions;")
    # 2. Columns.
    op.execute("ALTER TABLE clarity_teacher_calls DROP COLUMN IF EXISTS why_checked;")
    op.execute("""
        ALTER TABLE clarity_corpus
          DROP COLUMN IF EXISTS analysis_id, DROP COLUMN IF EXISTS person_verdict,
          DROP COLUMN IF EXISTS person_note, DROP COLUMN IF EXISTS person_checked_at,
          DROP COLUMN IF EXISTS person_checked_by;
    """)
