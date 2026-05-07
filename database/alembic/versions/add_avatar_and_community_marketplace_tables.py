"""add_avatar_and_community_marketplace_tables

Revision ID: add_community_marketplace_001
Revises: f818d5efb8d2
Create Date: 2026-03-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'add_community_marketplace_001'
down_revision: Union[str, Sequence[str], None] = 'f818d5efb8d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add avatar_url to users table (IF NOT EXISTS to handle re-runs)
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT")

    # Create community_channels table
    op.create_table(
        'community_channels',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=False, server_default='General'),
        sa.Column('member_count', sa.Integer(), server_default='0'),
        sa.Column('post_count', sa.Integer(), server_default='0'),
        sa.Column('icon', sa.String(10), nullable=True),
        sa.Column('is_public', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create channel_members table
    op.create_table(
        'channel_members',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel_id', sa.Integer(), sa.ForeignKey('community_channels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('is_moderator', sa.Boolean(), server_default='false'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'channel_id', name='uq_channel_members_user_channel'),
    )
    op.create_index('idx_channel_members_user', 'channel_members', ['user_id'])
    op.create_index('idx_channel_members_channel', 'channel_members', ['channel_id'])

    # Create community_discussions table
    op.create_table(
        'community_discussions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('channel_id', sa.Integer(), sa.ForeignKey('community_channels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tags', JSONB(), nullable=True),
        sa.Column('like_count', sa.Integer(), server_default='0'),
        sa.Column('reply_count', sa.Integer(), server_default='0'),
        sa.Column('view_count', sa.Integer(), server_default='0'),
        sa.Column('is_pinned', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('idx_discussions_channel', 'community_discussions', ['channel_id'])
    op.create_index('idx_discussions_user', 'community_discussions', ['user_id'])

    # Create discussion_replies table
    op.create_table(
        'discussion_replies',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('discussion_id', sa.Integer(), sa.ForeignKey('community_discussions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('like_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create discussion_likes table
    op.create_table(
        'discussion_likes',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('discussion_id', sa.Integer(), sa.ForeignKey('community_discussions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'discussion_id', name='uq_discussion_likes_user_discussion'),
    )

    # Create community_events table
    op.create_table(
        'community_events',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False, server_default='Webinar'),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), server_default='60'),
        sa.Column('max_attendees', sa.Integer(), nullable=True),
        sa.Column('attendee_count', sa.Integer(), server_default='0'),
        sa.Column('host_name', sa.String(100), nullable=True),
        sa.Column('meeting_link', sa.String(500), nullable=True),
        sa.Column('is_published', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create event_registrations table
    op.create_table(
        'event_registrations',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('community_events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('registered_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'event_id', name='uq_event_registrations_user_event'),
    )

    # Create community_activities table
    op.create_table(
        'community_activities',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('target_type', sa.String(50), nullable=True),
        sa.Column('target_name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_community_activities_user', 'community_activities', ['user_id'])

    # Create saved_items table
    op.create_table(
        'saved_items',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('item_type', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'item_id', 'item_type', name='uq_saved_items_user_item'),
    )
    op.create_index('idx_saved_items_user', 'saved_items', ['user_id'])

    # Create marketplace_tools table
    op.create_table(
        'marketplace_tools',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('author', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('full_description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=False, server_default='AI Tools'),
        sa.Column('price', sa.Float(), server_default='0.0'),
        sa.Column('tags', JSONB(), nullable=True),
        sa.Column('features', JSONB(), nullable=True),
        sa.Column('icon_name', sa.String(50), nullable=False, server_default='Cpu'),
        sa.Column('color_theme', sa.String(30), nullable=False, server_default='orange'),
        sa.Column('sales_count', sa.Integer(), server_default='0'),
        sa.Column('rating', sa.Float(), server_default='0.0'),
        sa.Column('review_count', sa.Integer(), server_default='0'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('purchase_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )

    # Create marketplace_purchases table
    op.create_table(
        'marketplace_purchases',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tool_id', sa.Integer(), sa.ForeignKey('marketplace_tools.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('amount_paid', sa.Float(), server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'tool_id', name='uq_marketplace_purchases_user_tool'),
    )

    # Create marketplace_requests table
    op.create_table(
        'marketplace_requests',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('budget', sa.String(100), nullable=True),
        sa.Column('timeline', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='open'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('marketplace_requests')
    op.drop_table('marketplace_purchases')
    op.drop_table('marketplace_tools')
    op.drop_table('saved_items')
    op.drop_table('community_activities')
    op.drop_table('event_registrations')
    op.drop_table('community_events')
    op.drop_table('discussion_likes')
    op.drop_table('discussion_replies')
    op.drop_table('community_discussions')
    op.drop_table('channel_members')
    op.drop_table('community_channels')
    op.drop_column('users', 'avatar_url')
