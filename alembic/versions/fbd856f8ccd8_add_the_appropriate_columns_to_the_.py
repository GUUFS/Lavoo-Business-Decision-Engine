"""Add the appropriate columns to the security tables

Revision ID: fbd856f8ccd8
Revises: b2f621d9eb29
Create Date: 2025-12-22 15:48:19.047551

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fbd856f8ccd8'
down_revision: Union[str, Sequence[str], None] = 'b2f621d9eb29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Skip this migration entirely - security tables already exist
    # This migration was created by Clinton but tables are already present
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # Skip downgrade - security tables should remain
    pass
