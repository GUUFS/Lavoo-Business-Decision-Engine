"""add_industry_to_users

Revision ID: a92b2fa14fa6
Revises: 5811f4722726
Create Date: 2026-02-01 10:00:37.056780

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a92b2fa14fa6'
down_revision: Union[str, Sequence[str], None] = '5811f4722726'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('industry', sa.String(100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'industry')
