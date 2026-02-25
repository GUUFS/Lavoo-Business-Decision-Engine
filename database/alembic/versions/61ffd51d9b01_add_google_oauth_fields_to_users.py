"""add_google_oauth_fields_to_users

Revision ID: 61ffd51d9b01
Revises: a92b2fa14fa6
Create Date: 2026-02-08 20:39:07.624673

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61ffd51d9b01'
down_revision: Union[str, Sequence[str], None] = 'a92b2fa14fa6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Google OAuth fields to users table."""
    # Add google_id column (unique identifier from Google)
    op.add_column('users', sa.Column('google_id', sa.String(255), nullable=True))
    op.create_index('ix_users_google_id', 'users', ['google_id'], unique=True)
    
    # Add profile_image_url (from Google profile picture)
    op.add_column('users', sa.Column('profile_image_url', sa.String(500), nullable=True))
    
    # Add email_verified flag (Google emails are pre-verified)
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Remove Google OAuth fields from users table."""
    # Drop columns in reverse order
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'profile_image_url')
    op.drop_index('ix_users_google_id', table_name='users')
    op.drop_column('users', 'google_id')
