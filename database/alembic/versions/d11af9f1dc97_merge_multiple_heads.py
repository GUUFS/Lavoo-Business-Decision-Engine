"""merge_multiple_heads

Revision ID: d11af9f1dc97
Revises: 859df1086266, f76ba9dc56d7
Create Date: 2025-11-25 23:58:13.971942

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd11af9f1dc97'
down_revision: Union[str, Sequence[str], None] = ('859df1086266', 'f76ba9dc56d7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
