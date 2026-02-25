"""add_company_name_to_users

Revision ID: 5811f4722726
Revises: 753e260f26a7
Create Date: 2026-01-29 12:15:25.175004

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5811f4722726'
down_revision: Union[str, Sequence[str], None] = '753e260f26a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add company_name field to users table for enhanced profile customization."""
    op.add_column('users', sa.Column('company_name', sa.String(255), nullable=True))


def downgrade() -> None:
    """Remove company_name field from users table."""
    op.drop_column('users', 'company_name')
