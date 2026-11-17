"""add_clarity_teacher_log_tables

Revision ID: b8e4d2f1c3a5
Revises: a7f3c9e1b2d4
Create Date: 2026-11-05 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b8e4d2f1c3a5'
down_revision: str | Sequence[str] | None = 'a7f3c9e1b2d4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Log of the micromodel teacher job (decision_engine/clarity_teacher.py):
    one row per run and one per decision the LLM checked. IF NOT EXISTS
    because app startup (init_db) creates the same tables."""
    op.execute("""
        CREATE TABLE IF NOT EXISTS clarity_teacher_runs (
            id SERIAL PRIMARY KEY,
            trigger VARCHAR(20) NOT NULL DEFAULT 'scheduled',
            started_at TIMESTAMPTZ DEFAULT now(),
            finished_at TIMESTAMPTZ,
            candidates INTEGER NOT NULL DEFAULT 0,
            reviewed INTEGER NOT NULL DEFAULT 0,
            agreed INTEGER NOT NULL DEFAULT 0,
            llm_calls INTEGER NOT NULL DEFAULT 0,
            new_precedents INTEGER NOT NULL DEFAULT 0,
            errors INTEGER NOT NULL DEFAULT 0,
            error TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_clarity_teacher_runs_started_at ON clarity_teacher_runs (started_at);

        CREATE TABLE IF NOT EXISTS clarity_teacher_calls (
            id SERIAL PRIMARY KEY,
            run_id INTEGER NOT NULL REFERENCES clarity_teacher_runs(id) ON DELETE CASCADE,
            corpus_id INTEGER REFERENCES clarity_corpus(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            submission_text TEXT NOT NULL,
            called_llm BOOLEAN NOT NULL DEFAULT TRUE,
            micromodel_asked BOOLEAN,
            micromodel_confidence DOUBLE PRECISION,
            decision_path VARCHAR(20),
            llm_asked BOOLEAN,
            llm_questions JSON,
            agreed BOOLEAN,
            duration_ms INTEGER,
            error TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_clarity_teacher_calls_run_id ON clarity_teacher_calls (run_id);
        CREATE INDEX IF NOT EXISTS ix_clarity_teacher_calls_created_at ON clarity_teacher_calls (created_at);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS clarity_teacher_calls; DROP TABLE IF EXISTS clarity_teacher_runs;")
