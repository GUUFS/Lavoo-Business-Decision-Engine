"""redesign_business_analysis_schema

Revision ID: 842d2ec24078
Revises: 8319d5107b5d
Create Date: 2026-01-14 19:59:22.588528

Major redesign of BusinessAnalysis table to match Clinton's new result page structure.

NEW STRUCTURE:
- Primary bottleneck (single, most critical)
- Secondary constraints (2-4 additional bottlenecks)
- What to stop (critical action to discontinue)
- Strategic priority (main focus)
- Action plans (ranked by leverage, with toolkits)
- Execution roadmap (timeline with phases)
- Exclusions note
- LLM-generated motivational quote

REMOVED:
- All v2 fields (objective, bottlenecks, business_strategies, ai_tools, key_evidence, assumptions, reasoning_trace)
- All legacy fields (intent_analysis, tool_combinations, roadmap, roi_projections, ai_tools_data)
- tool_combinations table (no longer needed - stored in action_plans)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '842d2ec24078'
down_revision: Union[str, Sequence[str], None] = '8319d5107b5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to new business analysis schema."""

    # Drop old v2 fields
    op.drop_column('business_analyses', 'objective')
    op.drop_column('business_analyses', 'bottlenecks')
    op.drop_column('business_analyses', 'business_strategies')
    op.drop_column('business_analyses', 'ai_tools')
    op.drop_column('business_analyses', 'key_evidence')
    op.drop_column('business_analyses', 'assumptions')
    op.drop_column('business_analyses', 'reasoning_trace')

    # Drop old legacy fields
    op.drop_column('business_analyses', 'intent_analysis')
    op.drop_column('business_analyses', 'tool_combinations')
    op.drop_column('business_analyses', 'roadmap')
    op.drop_column('business_analyses', 'roi_projections')
    op.drop_column('business_analyses', 'ai_tools_data')
    op.drop_column('business_analyses', 'estimated_cost')
    op.drop_column('business_analyses', 'timeline_weeks')

    # Add new unified fields
    op.add_column('business_analyses', sa.Column('primary_bottleneck', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Primary bottleneck: {title, description, consequence}'))
    op.add_column('business_analyses', sa.Column('secondary_constraints', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Secondary constraints array: [{id, title, description}]'))
    op.add_column('business_analyses', sa.Column('what_to_stop', sa.Text(), nullable=True, comment='Critical action user must stop'))
    op.add_column('business_analyses', sa.Column('strategic_priority', sa.Text(), nullable=True, comment='Main strategic focus'))
    op.add_column('business_analyses', sa.Column('action_plans', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Ranked action plans: [{id, title, what_to_do, why_it_matters, effort_level, toolkit}]'))
    op.add_column('business_analyses', sa.Column('total_phases', sa.Integer(), nullable=True, comment='Number of delivery phases'))
    op.add_column('business_analyses', sa.Column('estimated_days', sa.Integer(), nullable=True, comment='Total days for execution'))
    op.add_column('business_analyses', sa.Column('execution_roadmap', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Timeline: [{phase, days, title, tasks}]'))
    op.add_column('business_analyses', sa.Column('exclusions_note', sa.Text(), nullable=True, comment='What was excluded and why'))
    op.add_column('business_analyses', sa.Column('motivational_quote', sa.Text(), nullable=True, comment='LLM-generated motivational quote'))

    # Drop tool_combinations and roadmap_stages tables if they exist (no longer needed)
    try:
        op.drop_table('tool_combinations')
    except:
        pass  # Table may not exist

    try:
        op.drop_table('roadmap_stages')
    except:
        pass  # Table may not exist


def downgrade() -> None:
    """Downgrade back to old schema (not recommended)."""

    # Recreate tool_combinations table
    op.create_table(
        'tool_combinations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('analysis_id', sa.Integer(), sa.ForeignKey('business_analyses.id'), nullable=False),
        sa.Column('combo_name', sa.String(255)),
        sa.Column('tools', postgresql.JSON(astext_type=sa.Text())),
        sa.Column('synergy_score', sa.Float()),
        sa.Column('integration_flow', postgresql.JSON(astext_type=sa.Text())),
        sa.Column('setup_difficulty', sa.String(50)),
        sa.Column('total_monthly_cost', sa.Float()),
        sa.Column('why_this_combo', sa.Text()),
        sa.Column('expected_outcome', sa.Text()),
    )

    # Drop new fields
    op.drop_column('business_analyses', 'primary_bottleneck')
    op.drop_column('business_analyses', 'secondary_constraints')
    op.drop_column('business_analyses', 'what_to_stop')
    op.drop_column('business_analyses', 'strategic_priority')
    op.drop_column('business_analyses', 'action_plans')
    op.drop_column('business_analyses', 'total_phases')
    op.drop_column('business_analyses', 'estimated_days')
    op.drop_column('business_analyses', 'execution_roadmap')
    op.drop_column('business_analyses', 'exclusions_note')
    op.drop_column('business_analyses', 'motivational_quote')

    # Recreate old v2 fields
    op.add_column('business_analyses', sa.Column('objective', sa.Text(), nullable=True))
    op.add_column('business_analyses', sa.Column('bottlenecks', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('business_analyses', sa.Column('business_strategies', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('business_analyses', sa.Column('ai_tools', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('business_analyses', sa.Column('key_evidence', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('business_analyses', sa.Column('assumptions', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('business_analyses', sa.Column('reasoning_trace', postgresql.JSON(astext_type=sa.Text()), nullable=True))

    # Recreate old legacy fields
    op.add_column('business_analyses', sa.Column('intent_analysis', postgresql.JSON(astext_type=sa.Text())))
    op.add_column('business_analyses', sa.Column('tool_combinations', postgresql.JSON(astext_type=sa.Text())))
    op.add_column('business_analyses', sa.Column('roadmap', postgresql.JSON(astext_type=sa.Text())))
    op.add_column('business_analyses', sa.Column('roi_projections', postgresql.JSON(astext_type=sa.Text())))
    op.add_column('business_analyses', sa.Column('ai_tools_data', postgresql.JSON(astext_type=sa.Text())))
    op.add_column('business_analyses', sa.Column('estimated_cost', sa.Float()))
    op.add_column('business_analyses', sa.Column('timeline_weeks', sa.Integer()))

