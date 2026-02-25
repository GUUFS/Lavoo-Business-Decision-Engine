"""final_merge_all_heads

Revision ID: d3f6564cfdb9
Revises: bb1dd4e4b0e9, 3cf5392506dc
Create Date: 2026-01-07 18:09:30.886704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f6564cfdb9'
down_revision: Union[str, Sequence[str], None] = ('bb1dd4e4b0e9', '3cf5392506dc')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
