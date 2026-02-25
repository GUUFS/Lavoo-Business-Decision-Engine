"""add_roi_projections_to_business_analyses

Revision ID: 859df1086266
Revises: 30819a16afaa
Create Date: 2025-11-20 14:09:44.972188

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '859df1086266'
down_revision: Union[str, Sequence[str], None] = '30819a16afaa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add roi_projections column to business_analyses table
    op.add_column(
        'business_analyses',
        sa.Column('roi_projections', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove roi_projections column
    op.drop_column('business_analyses', 'roi_projections')
