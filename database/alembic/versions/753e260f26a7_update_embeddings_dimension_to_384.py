"""update_embeddings_dimension_to_384

Revision ID: 753e260f26a7
Revises: b4bef45d5c57
Create Date: 2026-01-22 23:29:37.677956

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '753e260f26a7'
down_revision: Union[str, Sequence[str], None] = 'b4bef45d5c57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Change embedding vector from 1024D to 384D for sentence-transformers."""
    # Drop old index and column
    op.execute("DROP INDEX IF EXISTS ai_tools_embedding_hnsw_idx")
    op.drop_column('ai_tools', 'embedding')

    # Add new column with 384 dimensions
    op.execute("""
        ALTER TABLE ai_tools
        ADD COLUMN embedding vector(384)
    """)

    # Recreate HNSW index with same parameters (optimized for search speed)
    op.execute("""
        CREATE INDEX ai_tools_embedding_hnsw_idx
        ON ai_tools
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    """Downgrade schema: Revert to 1024D vectors."""
    # Drop new index and column
    op.execute("DROP INDEX IF EXISTS ai_tools_embedding_hnsw_idx")
    op.drop_column('ai_tools', 'embedding')

    # Restore old column with 1024 dimensions
    op.execute("""
        ALTER TABLE ai_tools
        ADD COLUMN embedding vector(1024)
    """)

    # Recreate HNSW index
    op.execute("""
        CREATE INDEX ai_tools_embedding_hnsw_idx
        ON ai_tools
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
