"""merge_all_heads

Revision ID: 51496cdf9f10
Revises: 2cf00103f307, 99a3cffb50d4
Create Date: 2025-11-30 14:10:41.736852

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51496cdf9f10'
down_revision: Union[str, Sequence[str], None] = ('2cf00103f307', '99a3cffb50d4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
