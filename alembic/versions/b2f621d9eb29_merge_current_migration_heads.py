"""Merge current migration heads

Revision ID: b2f621d9eb29
Revises: cd505f22437a, ef3c9479f1ad
Create Date: 2025-12-22 15:32:03.144489

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2f621d9eb29'
down_revision: Union[str, Sequence[str], None] = ('cd505f22437a', 'ef3c9479f1ad')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
