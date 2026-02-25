"""add_embeddings_to_ai_tools

Revision ID: b4bef45d5c57
Revises: dc406ec79858
Create Date: 2026-01-22 22:53:01.798361

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4bef45d5c57'
down_revision: Union[str, Sequence[str], None] = 'dc406ec79858'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add vector embeddings column and HNSW index to ai_tools table."""
    # Add vector column for 1024-dimensional embeddings (Cohere embed-english-v3.0)
    # Using 'vector' type from pgvector extension
    op.execute("""
        ALTER TABLE ai_tools
        ADD COLUMN IF NOT EXISTS embedding vector(1024)
    """)

    # Create HNSW index for fast similarity search
    # HNSW (Hierarchical Navigable Small World) is optimized for vector similarity
    # m=16: number of connections per layer (default, good balance)
    # ef_construction=64: controls index quality during build (default)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ai_tools_embedding_hnsw_idx
        ON ai_tools
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    """Remove vector embeddings column and index from ai_tools table."""
    # Drop index first
    op.execute('DROP INDEX IF EXISTS ai_tools_embedding_hnsw_idx')

    # Drop embedding column
    op.execute('ALTER TABLE ai_tools DROP COLUMN IF EXISTS embedding')
