"""enable_pgvector_extension

Revision ID: dc406ec79858
Revises: 4263c5d64e37
Create Date: 2026-01-22 22:51:47.958919

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc406ec79858'
down_revision: Union[str, Sequence[str], None] = '4263c5d64e37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable pgvector extension for vector similarity search."""
    # Enable pgvector extension (requires superuser or rds_superuser role)
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')


def downgrade() -> None:
    """Disable pgvector extension."""
    op.execute('DROP EXTENSION IF EXISTS vector')
