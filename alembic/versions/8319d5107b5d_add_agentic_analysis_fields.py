"""add_agentic_analysis_fields

Revision ID: 8319d5107b5d
Revises: d3f6564cfdb9
Create Date: 2026-01-09 17:37:03.261791

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision: str = '8319d5107b5d'
down_revision: Union[str, Sequence[str], None] = 'd3f6564cfdb9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new fields for agentic analyzer v2."""
    # Add new JSON columns for structured analysis data
    op.add_column('business_analyses', sa.Column('objective', sa.Text(), nullable=True))
    op.add_column('business_analyses', sa.Column('bottlenecks', JSON, nullable=True))
    op.add_column('business_analyses', sa.Column('business_strategies', JSON, nullable=True))
    op.add_column('business_analyses', sa.Column('ai_tools', JSON, nullable=True))
    op.add_column('business_analyses', sa.Column('key_evidence', JSON, nullable=True))
    op.add_column('business_analyses', sa.Column('assumptions', JSON, nullable=True))
    op.add_column('business_analyses', sa.Column('reasoning_trace', JSON, nullable=True))


def downgrade() -> None:
    """Remove agentic analyzer v2 fields."""
    op.drop_column('business_analyses', 'reasoning_trace')
    op.drop_column('business_analyses', 'assumptions')
    op.drop_column('business_analyses', 'key_evidence')
    op.drop_column('business_analyses', 'ai_tools')
    op.drop_column('business_analyses', 'business_strategies')
    op.drop_column('business_analyses', 'bottlenecks')
    op.drop_column('business_analyses', 'objective')
