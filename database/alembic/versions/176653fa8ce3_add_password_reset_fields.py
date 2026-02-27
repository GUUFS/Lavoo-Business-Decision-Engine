"""add_password_reset_fields

Revision ID: 176653fa8ce3
Revises: 61ffd51d9b01
Create Date: 2026-02-25 22:48:25.607928

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '176653fa8ce3'
down_revision: Union[str, Sequence[str], None] = '61ffd51d9b01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add password reset fields to users table
    op.add_column('users', sa.Column('password_reset_token', sa.String(255), nullable=True, unique=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('password_reset_used_at', sa.DateTime(timezone=True), nullable=True))

    # Create unique constraint on password_reset_token
    op.create_index('idx_users_password_reset_token', 'users', ['password_reset_token'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index and columns
    op.drop_index('idx_users_password_reset_token', table_name='users')
    op.drop_column('users', 'password_reset_used_at')
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')
