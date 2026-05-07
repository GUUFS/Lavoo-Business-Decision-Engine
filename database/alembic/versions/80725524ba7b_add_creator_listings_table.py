"""add creator_listings table

Revision ID: 80725524ba7b
Revises: add_recommended_tool_stacks_001
Create Date: 2026-05-04 14:50:02.953148

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80725524ba7b'
down_revision: Union[str, Sequence[str], None] = 'add_recommended_tool_stacks_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('creator_listings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('full_description', sa.Text(), nullable=True),
    sa.Column('listing_type', sa.String(length=50), nullable=False),
    sa.Column('category', sa.String(length=100), nullable=False),
    sa.Column('price', sa.Float(), nullable=True),
    sa.Column('tags', sa.JSON(), nullable=True),
    sa.Column('features', sa.JSON(), nullable=True),
    sa.Column('icon_name', sa.String(length=50), nullable=False),
    sa.Column('color_theme', sa.String(length=30), nullable=False),
    sa.Column('purchase_url', sa.String(length=500), nullable=True),
    sa.Column('sales_count', sa.Integer(), nullable=True),
    sa.Column('rating', sa.Float(), nullable=True),
    sa.Column('review_count', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_creator_listings_id'), 'creator_listings', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_creator_listings_id'), table_name='creator_listings')
    op.drop_table('creator_listings')
