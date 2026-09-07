"""Add contact_messages reply fields

Revision ID: 3a7b8c9d0e1f
Revises: 23f3dc51bf18
Create Date: 2026-09-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3a7b8c9d0e1f'
down_revision: Union[str, Sequence[str], None] = '23f3dc51bf18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with IF NOT EXISTS safety guards."""
    op.execute("ALTER TABLE contact_messages ADD COLUMN IF NOT EXISTS admin_replies JSON DEFAULT '[]'::json")
    op.execute("ALTER TABLE contact_messages ADD COLUMN IF NOT EXISTS last_replied_at TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE contact_messages ADD COLUMN IF NOT EXISTS last_replied_by VARCHAR(255)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE contact_messages DROP COLUMN IF EXISTS last_replied_by")
    op.execute("ALTER TABLE contact_messages DROP COLUMN IF EXISTS last_replied_at")
    op.execute("ALTER TABLE contact_messages DROP COLUMN IF EXISTS admin_replies")
