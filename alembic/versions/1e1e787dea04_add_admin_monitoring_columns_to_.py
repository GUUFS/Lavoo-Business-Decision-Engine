"""add_admin_monitoring_columns_to_business_analyses

Revision ID: 1e1e787dea04
Revises: ef3c9479f1ad
Create Date: 2025-12-20 15:11:42.144037

Adds admin monitoring columns to business_analyses table:
- confidence_score: AI confidence in analysis (0-100)
- duration: Analysis processing time (e.g., "2m 34s")
- analysis_type: Category of analysis (Sales, Market, etc.)
- insights_count: Number of insights generated
- recommendations_count: Number of recommendations generated
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '1e1e787dea04'
down_revision: Union[str, Sequence[str], None] = 'ef3c9479f1ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add admin monitoring columns to business_analyses table."""
    conn = op.get_bind()
    inspector = inspect(conn)

    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('business_analyses')]

    # Add confidence_score column
    if 'confidence_score' not in existing_columns:
        op.add_column('business_analyses', sa.Column('confidence_score', sa.Integer(), nullable=True))
        print("✅ Added 'confidence_score' column to business_analyses table")
    else:
        print("⏭️  Column 'confidence_score' already exists in business_analyses table")

    # Add duration column
    if 'duration' not in existing_columns:
        op.add_column('business_analyses', sa.Column('duration', sa.String(50), nullable=True))
        print("✅ Added 'duration' column to business_analyses table")
    else:
        print("⏭️  Column 'duration' already exists in business_analyses table")

    # Add analysis_type column
    if 'analysis_type' not in existing_columns:
        op.add_column('business_analyses', sa.Column('analysis_type', sa.String(100), nullable=True))
        print("✅ Added 'analysis_type' column to business_analyses table")
    else:
        print("⏭️  Column 'analysis_type' already exists in business_analyses table")

    # Add insights_count column
    if 'insights_count' not in existing_columns:
        op.add_column('business_analyses', sa.Column('insights_count', sa.Integer(), nullable=True, server_default='0'))
        print("✅ Added 'insights_count' column to business_analyses table")
    else:
        print("⏭️  Column 'insights_count' already exists in business_analyses table")

    # Add recommendations_count column
    if 'recommendations_count' not in existing_columns:
        op.add_column('business_analyses', sa.Column('recommendations_count', sa.Integer(), nullable=True, server_default='0'))
        print("✅ Added 'recommendations_count' column to business_analyses table")
    else:
        print("⏭️  Column 'recommendations_count' already exists in business_analyses table")

    # Create indexes for commonly queried columns
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('business_analyses')]

    if 'idx_business_analyses_status' not in existing_indexes:
        op.create_index('idx_business_analyses_status', 'business_analyses', ['status'])
        print("✅ Created index 'idx_business_analyses_status'")

    if 'idx_business_analyses_analysis_type' not in existing_indexes:
        op.create_index('idx_business_analyses_analysis_type', 'business_analyses', ['analysis_type'])
        print("✅ Created index 'idx_business_analyses_analysis_type'")

    if 'idx_business_analyses_created_at' not in existing_indexes:
        op.create_index('idx_business_analyses_created_at', 'business_analyses', ['created_at'])
        print("✅ Created index 'idx_business_analyses_created_at'")

    # Populate default values for existing records
    op.execute("""
        UPDATE business_analyses
        SET
            confidence_score = COALESCE(confidence_score, 75),
            duration = COALESCE(duration, '2m 30s'),
            analysis_type = COALESCE(analysis_type, 'General Analysis'),
            insights_count = COALESCE(insights_count, 3),
            recommendations_count = COALESCE(recommendations_count, 2)
        WHERE confidence_score IS NULL
           OR duration IS NULL
           OR analysis_type IS NULL
           OR insights_count IS NULL
           OR recommendations_count IS NULL
    """)
    print("✅ Populated default values for existing records")


def downgrade() -> None:
    """Remove admin monitoring columns from business_analyses table."""
    # Drop indexes first
    op.drop_index('idx_business_analyses_created_at', table_name='business_analyses')
    op.drop_index('idx_business_analyses_analysis_type', table_name='business_analyses')
    op.drop_index('idx_business_analyses_status', table_name='business_analyses')

    # Drop columns
    op.drop_column('business_analyses', 'recommendations_count')
    op.drop_column('business_analyses', 'insights_count')
    op.drop_column('business_analyses', 'analysis_type')
    op.drop_column('business_analyses', 'duration')
    op.drop_column('business_analyses', 'confidence_score')
