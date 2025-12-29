"""add_user_profile_fields_manual

Revision ID: a626028d446c
Revises: 54406b16a739
Create Date: 2025-12-24 15:21:33.535845

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a626028d446c'
down_revision: Union[str, Sequence[str], None] = '54406b16a739'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check existing columns to avoid errors
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_columns = {col['name'] for col in inspector.get_columns('users')}
    
    # Add new user profile fields if they don't exist
    if 'department' not in existing_columns:
        op.add_column('users', sa.Column('department', sa.String(100), nullable=True))
    if 'location' not in existing_columns:
        op.add_column('users', sa.Column('location', sa.String(100), nullable=True))
    if 'bio' not in existing_columns:
        op.add_column('users', sa.Column('bio', sa.Text(), nullable=True))
    if 'two_factor_enabled' not in existing_columns:
        op.add_column('users', sa.Column('two_factor_enabled', sa.Boolean(), server_default='false', nullable=True))
    if 'email_notifications' not in existing_columns:
        op.add_column('users', sa.Column('email_notifications', sa.Boolean(), server_default='true', nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'email_notifications')
    op.drop_column('users', 'two_factor_enabled')
    op.drop_column('users', 'bio')
    op.drop_column('users', 'location')
    op.drop_column('users', 'department')
