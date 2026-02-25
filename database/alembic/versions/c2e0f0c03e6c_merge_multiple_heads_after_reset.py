"""merge multiple heads after reset

Revision ID: c2e0f0c03e6c
Revises: 2cf00103f307, 99a3cffb50d4
Create Date: 2025-12-02 15:28:32.791309

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2e0f0c03e6c'
down_revision: Union[str, Sequence[str], None] = ('2cf00103f307', '99a3cffb50d4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
