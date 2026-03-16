"""add_missions_and_settings_tables

Revision ID: 63f9c5ca4f61
Revises: 176653fa8ce3
Create Date: 2026-03-16 23:15:28.173360

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63f9c5ca4f61'
down_revision: Union[str, Sequence[str], None] = '176653fa8ce3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create missions table
    op.create_table(
        'missions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('difficulty', sa.String(50), server_default='beginner'),
        sa.Column('total_steps', sa.Integer(), nullable=False),
        sa.Column('points_reward', sa.Integer(), server_default='0'),
        sa.Column('estimated_days', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('order_index', sa.Integer(), server_default='0'),
        sa.Column('icon', sa.String(100), nullable=True),
        sa.Column('color_theme', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Create mission_steps table
    op.create_table(
        'mission_steps',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('mission_id', sa.Integer(), sa.ForeignKey('missions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('day', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('points', sa.Integer(), server_default='0'),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_mission_steps_mission_id', 'mission_steps', ['mission_id'])

    # Create user_missions table
    op.create_table(
        'user_missions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('mission_id', sa.Integer(), sa.ForeignKey('missions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('status', sa.String(50), server_default='active'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('progress_percentage', sa.Integer(), server_default='0'),
        sa.Column('completed_steps', sa.Integer(), server_default='0'),
    )
    op.create_index('idx_user_mission_user_id', 'user_missions', ['user_id'])
    op.create_index('idx_user_mission_status', 'user_missions', ['status'])

    # Create user_mission_steps table
    op.create_table(
        'user_mission_steps',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_mission_id', sa.Integer(), sa.ForeignKey('user_missions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('step_id', sa.Integer(), sa.ForeignKey('mission_steps.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('completed', sa.Boolean(), server_default='false'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reflection', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create user_settings table
    op.create_table(
        'user_settings',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('email_notifications', sa.Boolean(), server_default='true'),
        sa.Column('push_notifications', sa.Boolean(), server_default='true'),
        sa.Column('analysis_reminders', sa.Boolean(), server_default='true'),
        sa.Column('community_notifications', sa.Boolean(), server_default='true'),
        sa.Column('active_constraint_mode', sa.Boolean(), server_default='true'),
        sa.Column('pending_task_reminders', sa.Boolean(), server_default='true'),
        sa.Column('dark_mode', sa.Boolean(), server_default='false'),
        sa.Column('compact_view', sa.Boolean(), server_default='false'),
        sa.Column('profile_visibility', sa.String(50), server_default='community'),
        sa.Column('show_earnings', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('user_mission_steps')
    op.drop_table('user_missions')
    op.drop_table('mission_steps')
    op.drop_table('missions')
    op.drop_table('user_settings')
