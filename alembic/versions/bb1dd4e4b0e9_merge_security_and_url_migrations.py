"""merge_security_and_url_migrations

Revision ID: bb1dd4e4b0e9
Revises: 04f3863fbe31, 5880d3164e9e
Create Date: 2025-12-29 22:11:07.636637

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb1dd4e4b0e9'
down_revision: Union[str, Sequence[str], None] = ('04f3863fbe31', '5880d3164e9e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
