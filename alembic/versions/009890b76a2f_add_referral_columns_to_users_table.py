"""add referral columns to users table

Revision ID: 009890b76a2f
Revises: a4743de87323
Create Date: 2025-11-23 21:12:13.387553

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '009890b76a2f'
down_revision: Union[str, Sequence[str], None] = 'a4743de87323'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('referral_code', sa.String(length=10), nullable=True))
    op.add_column('users', sa.Column('referrer_code', sa.String(length=10), nullable=True))
    


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'referral_code')
    op.drop_column('users', 'referrer_code')
    
