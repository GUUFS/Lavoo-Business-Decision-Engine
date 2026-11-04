"""add_founding_pricing_columns

Revision ID: a7f3c9e1b2d4
Revises: 6c1e2f3a4b5d
Create Date: 2026-11-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a7f3c9e1b2d4'
down_revision: Union[str, Sequence[str], None] = '6c1e2f3a4b5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: founding members, the plan and price set of each
    payment, the founding watch settings, and the currency/plan a beta user
    picked when saving their card. IF NOT EXISTS because app
    startup adds the same columns."""
    op.execute("""
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS is_founding_member BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS founding_number INTEGER,
            ADD COLUMN IF NOT EXISTS founding_member_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS preferred_currency VARCHAR(3),
            ADD COLUMN IF NOT EXISTS preferred_plan_tier VARCHAR(20)
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_founding_number ON users (founding_number)")
    op.execute("""
        ALTER TABLE subscriptions
            ADD COLUMN IF NOT EXISTS plan_tier VARCHAR(20),
            ADD COLUMN IF NOT EXISTS price_type VARCHAR(20)
    """)
    op.execute("""
        ALTER TABLE system_settings
            ADD COLUMN IF NOT EXISTS founding_watch_enabled BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS founding_member_limit INTEGER DEFAULT 500,
            ADD COLUMN IF NOT EXISTS founding_monthly_ends_at TIMESTAMPTZ
    """)


def downgrade() -> None:
    """Downgrade schema: drop the founding pricing columns."""
    op.execute("""
        ALTER TABLE system_settings
            DROP COLUMN IF EXISTS founding_monthly_ends_at,
            DROP COLUMN IF EXISTS founding_member_limit,
            DROP COLUMN IF EXISTS founding_watch_enabled
    """)
    op.execute("""
        ALTER TABLE subscriptions
            DROP COLUMN IF EXISTS price_type,
            DROP COLUMN IF EXISTS plan_tier
    """)
    op.execute("DROP INDEX IF EXISTS ix_users_founding_number")
    op.execute("""
        ALTER TABLE users
            DROP COLUMN IF EXISTS preferred_plan_tier,
            DROP COLUMN IF EXISTS preferred_currency,
            DROP COLUMN IF EXISTS founding_member_at,
            DROP COLUMN IF EXISTS founding_number,
            DROP COLUMN IF EXISTS is_founding_member
    """)
