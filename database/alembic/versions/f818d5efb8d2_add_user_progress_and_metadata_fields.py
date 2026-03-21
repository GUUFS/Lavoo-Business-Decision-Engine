"""add_user_progress_and_metadata_fields

Revision ID: f818d5efb8d2
Revises: 63f9c5ca4f61
Create Date: 2026-03-16 23:24:20.513802

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f818d5efb8d2'
down_revision: Union[str, Sequence[str], None] = '63f9c5ca4f61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add user_progress field to business_analyses table
    # This stores mission progress: completed actions, reflections, resolved constraints
    op.add_column('business_analyses', sa.Column('user_progress', sa.JSON(), nullable=True))

    # Add user_metadata field to users table for settings and other user data
    op.add_column('users', sa.Column('user_metadata', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove user_progress field from business_analyses
    op.drop_column('business_analyses', 'user_progress')

    # Remove user_metadata field from users
    op.drop_column('users', 'user_metadata')
