"""add admin monitoring columns to business_analyses

Revision ID: add_analysis_monitoring
Revises: create_trends_table
Create Date: 2025-12-11 10:35:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_analysis_monitoring'
down_revision = 'create_trends_table'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns for admin monitoring
    op.add_column('business_analyses', sa.Column('confidence_score', sa.Integer(), nullable=True))
    op.add_column('business_analyses', sa.Column('duration', sa.String(50), nullable=True))
    op.add_column('business_analyses', sa.Column('analysis_type', sa.String(100), nullable=True))
    op.add_column('business_analyses', sa.Column('insights_count', sa.Integer(), server_default='0'))
    op.add_column('business_analyses', sa.Column('recommendations_count', sa.Integer(), server_default='0'))

    # Create indexes for filtering
    op.create_index('idx_business_analyses_status', 'business_analyses', ['status'])
    op.create_index('idx_business_analyses_analysis_type', 'business_analyses', ['analysis_type'])
    op.create_index('idx_business_analyses_created_at', 'business_analyses', ['created_at'])


def downgrade():
    op.drop_index('idx_business_analyses_created_at', 'business_analyses')
    op.drop_index('idx_business_analyses_analysis_type', 'business_analyses')
    op.drop_index('idx_business_analyses_status', 'business_analyses')

    op.drop_column('business_analyses', 'recommendations_count')
    op.drop_column('business_analyses', 'insights_count')
    op.drop_column('business_analyses', 'analysis_type')
    op.drop_column('business_analyses', 'duration')
    op.drop_column('business_analyses', 'confidence_score')
