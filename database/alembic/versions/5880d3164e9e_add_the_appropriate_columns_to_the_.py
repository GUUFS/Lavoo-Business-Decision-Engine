"""Add the appropriate columns to the security tables

Revision ID: 5880d3164e9e
Revises: fbd856f8ccd8
Create Date: 2025-12-22 15:52:53.775516

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5880d3164e9e'
down_revision: Union[str, Sequence[str], None] = 'fbd856f8ccd8'
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
