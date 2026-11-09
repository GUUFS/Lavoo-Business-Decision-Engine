"""add_partner_premium

Revision ID: e7b9d1f3a5c6
Revises: d4f6a8c0e2b1
Create Date: 2026-11-09 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e7b9d1f3a5c6'
down_revision: str | Sequence[str] | None = 'd4f6a8c0e2b1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Partners (set on the admin Permissions page) get Premium for 6 months
    from the day they become a partner (subscriptions/partner_service.py):
    store that day and when their free Premium ends."""
    op.execute("""
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS partner_since TIMESTAMP WITH TIME ZONE,
            ADD COLUMN IF NOT EXISTS partner_premium_until TIMESTAMP WITH TIME ZONE;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE users
            DROP COLUMN IF EXISTS partner_since,
            DROP COLUMN IF EXISTS partner_premium_until;
    """)
