"""add_ai_tools_data_column

Revision ID: 2cf00103f307
Revises: d11af9f1dc97
Create Date: 2025-11-25 23:58:52.538050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2cf00103f307'
down_revision: Union[str, Sequence[str], None] = 'd11af9f1dc97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add ai_tools_data column to business_analyses table
    op.add_column(
        'business_analyses',
        sa.Column('ai_tools_data', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove ai_tools_data column from business_analyses table
    op.drop_column('business_analyses', 'ai_tools_data')
