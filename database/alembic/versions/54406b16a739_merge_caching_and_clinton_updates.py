"""merge_caching_and_clinton_updates

Revision ID: 54406b16a739
Revises: 1e1e787dea04, cd505f22437a
Create Date: 2025-12-24 12:51:22.101851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '54406b16a739'
down_revision: Union[str, Sequence[str], None] = ('1e1e787dea04', 'cd505f22437a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
