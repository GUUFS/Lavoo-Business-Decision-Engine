"""create trends table

Revision ID: create_trends_table
Revises:
Create Date: 2025-12-11 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_trends_table'
down_revision = '99a3cffb50d4'  # Latest migration
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'trends',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('industry', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('engagement', sa.String(50), nullable=True),
        sa.Column('growth', sa.String(50), nullable=True),
        sa.Column('viral_score', sa.Integer(), nullable=False),
        sa.Column('search_volume', sa.String(50), nullable=True),
        sa.Column('peak_time', sa.String(50), nullable=True),
        sa.Column('competition', sa.String(20), server_default='medium'),
        sa.Column('opportunity', sa.String(50), nullable=True),
        sa.Column('nature', sa.String(50), nullable=False),
        sa.Column('hashtags', postgresql.JSON(), nullable=True),
        sa.Column('platforms', postgresql.JSON(), nullable=True),
        sa.Column('action_items', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for better query performance
    op.create_index('idx_trends_industry', 'trends', ['industry'])
    op.create_index('idx_trends_is_active', 'trends', ['is_active'])
    op.create_index('idx_trends_created_at', 'trends', ['created_at'])
    op.create_index('idx_trends_viral_score', 'trends', ['viral_score'])


def downgrade():
    op.drop_index('idx_trends_viral_score', 'trends')
    op.drop_index('idx_trends_created_at', 'trends')
    op.drop_index('idx_trends_is_active', 'trends')
    op.drop_index('idx_trends_industry', 'trends')
    op.drop_table('trends')
