"""remove_unused_analysis_columns

Revision ID: 4263c5d64e37
Revises: 7566c41975d1
Create Date: 2026-01-16 15:44:33.606405

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4263c5d64e37'
down_revision: Union[str, Sequence[str], None] = '7566c41975d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove unused columns from business_analyses table."""
    # Drop old schema columns that are no longer used
    columns_to_drop = [
        'objective',
        'bottlenecks',
        'business_strategies',
        'ai_tools',
        'key_evidence',
        'assumptions',
        'reasoning_trace',
        'intent_analysis',
        'tool_combinations',
        'roadmap',
        'roi_projections',
        'ai_tools_data',
        'estimated_cost',
        'timeline_weeks'
    ]

    for column in columns_to_drop:
        op.drop_column('business_analyses', column)


def downgrade() -> None:
    """Restore dropped columns (if needed for rollback)."""
    # Add columns back with JSON/TEXT types
    op.add_column('business_analyses', sa.Column('objective', sa.TEXT(), nullable=True))
    op.add_column('business_analyses', sa.Column('bottlenecks', sa.JSON(), nullable=True))
    op.add_column('business_analyses', sa.Column('business_strategies', sa.JSON(), nullable=True))
    op.add_column('business_analyses', sa.Column('ai_tools', sa.JSON(), nullable=True))
    op.add_column('business_analyses', sa.Column('key_evidence', sa.JSON(), nullable=True))
    op.add_column('business_analyses', sa.Column('assumptions', sa.JSON(), nullable=True))
    op.add_column('business_analyses', sa.Column('reasoning_trace', sa.JSON(), nullable=True))
    op.add_column('business_analyses', sa.Column('intent_analysis', sa.JSON(), nullable=True))
    op.add_column('business_analyses', sa.Column('tool_combinations', sa.JSON(), nullable=True))
    op.add_column('business_analyses', sa.Column('roadmap', sa.JSON(), nullable=True))
    op.add_column('business_analyses', sa.Column('roi_projections', sa.JSON(), nullable=True))
    op.add_column('business_analyses', sa.Column('ai_tools_data', sa.JSON(), nullable=True))
    op.add_column('business_analyses', sa.Column('estimated_cost', sa.Float(), nullable=True))
    op.add_column('business_analyses', sa.Column('timeline_weeks', sa.Integer(), nullable=True))
