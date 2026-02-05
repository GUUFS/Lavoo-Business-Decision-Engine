"""add_missing_new_schema_columns

Revision ID: 7566c41975d1
Revises: 842d2ec24078
Create Date: 2026-01-16 14:45:31.233917

Adds the new schema columns that were defined but not properly created in the previous migration.
This ensures the database matches the new agentic analyzer structure.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7566c41975d1'
down_revision: Union[str, Sequence[str], None] = '842d2ec24078'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new schema columns if they don't exist."""

    # Use raw SQL to check and add columns conditionally
    conn = op.get_bind()

    # Check which columns exist
    result = conn.execute(sa.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'business_analyses'
    """))
    existing_columns = {row[0] for row in result}

    # Add columns only if they don't exist
    if 'primary_bottleneck' not in existing_columns:
        op.add_column('business_analyses', sa.Column('primary_bottleneck', postgresql.JSON(astext_type=sa.Text()), nullable=True))

    if 'secondary_constraints' not in existing_columns:
        op.add_column('business_analyses', sa.Column('secondary_constraints', postgresql.JSON(astext_type=sa.Text()), nullable=True))

    if 'what_to_stop' not in existing_columns:
        op.add_column('business_analyses', sa.Column('what_to_stop', sa.Text(), nullable=True))

    if 'strategic_priority' not in existing_columns:
        op.add_column('business_analyses', sa.Column('strategic_priority', sa.Text(), nullable=True))

    if 'action_plans' not in existing_columns:
        op.add_column('business_analyses', sa.Column('action_plans', postgresql.JSON(astext_type=sa.Text()), nullable=True))

    if 'total_phases' not in existing_columns:
        op.add_column('business_analyses', sa.Column('total_phases', sa.Integer(), nullable=True))

    if 'estimated_days' not in existing_columns:
        op.add_column('business_analyses', sa.Column('estimated_days', sa.Integer(), nullable=True))

    if 'execution_roadmap' not in existing_columns:
        op.add_column('business_analyses', sa.Column('execution_roadmap', postgresql.JSON(astext_type=sa.Text()), nullable=True))

    if 'exclusions_note' not in existing_columns:
        op.add_column('business_analyses', sa.Column('exclusions_note', sa.Text(), nullable=True))

    if 'motivational_quote' not in existing_columns:
        op.add_column('business_analyses', sa.Column('motivational_quote', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove the new schema columns."""
    op.drop_column('business_analyses', 'motivational_quote')
    op.drop_column('business_analyses', 'exclusions_note')
    op.drop_column('business_analyses', 'execution_roadmap')
    op.drop_column('business_analyses', 'estimated_days')
    op.drop_column('business_analyses', 'total_phases')
    op.drop_column('business_analyses', 'action_plans')
    op.drop_column('business_analyses', 'strategic_priority')
    op.drop_column('business_analyses', 'what_to_stop')
    op.drop_column('business_analyses', 'secondary_constraints')
    op.drop_column('business_analyses', 'primary_bottleneck')

