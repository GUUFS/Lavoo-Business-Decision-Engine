"""Merge Heads

Revision ID: 3cf5392506dc
Revises: 5880d3164e9e, add_displayed_reviews_and_backfill
Create Date: 2025-12-30 16:46:19.563944

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3cf5392506dc'
down_revision: Union[str, Sequence[str], None] = ('5880d3164e9e', 'add_displayed_reviews_and_backfill')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
