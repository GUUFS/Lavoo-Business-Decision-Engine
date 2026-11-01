"""add_clarity_corpus_table

Revision ID: 5b49a7a07e58
Revises: 4dc31916c1d9
Create Date: 2026-10-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b49a7a07e58'
down_revision: Union[str, Sequence[str], None] = '4dc31916c1d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create the clarity_corpus table (zero-LLM
    clarifying-questions engine's reference corpus) with a 384D pgvector
    embedding column and HNSW cosine index, matching ai_tools.embedding's
    existing pattern."""
    op.create_table(
        'clarity_corpus',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('submission_text', sa.Text(), nullable=False),
        sa.Column('needs_clarification', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('gap_types', sa.JSON(), nullable=False),
        sa.Column('questions', sa.JSON(), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('outcome', sa.String(length=20), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.execute("ALTER TABLE clarity_corpus ADD COLUMN embedding vector(384)")
    op.execute("""
        CREATE INDEX clarity_corpus_embedding_hnsw_idx
        ON clarity_corpus
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    """Downgrade schema: drop the clarity_corpus table."""
    op.execute("DROP INDEX IF EXISTS clarity_corpus_embedding_hnsw_idx")
    op.drop_table('clarity_corpus')
