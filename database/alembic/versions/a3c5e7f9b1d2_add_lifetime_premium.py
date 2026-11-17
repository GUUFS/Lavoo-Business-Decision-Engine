"""Premium forever: users.lifetime_premium, set for teamholyhustle@gmail.com.

Adds the flag read by subscriptions/lifetime_premium.py and turns it on for
the first Premium-forever account (active, plan "lifetime", no end date).
If that account doesn't exist yet the update matches nothing; run
grant_lifetime_premium for it once it signs up.

Revision ID: a3c5e7f9b1d2
Revises: f2c4e6a8b0d1
Create Date: 2026-11-11
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'a3c5e7f9b1d2'
down_revision: str | Sequence[str] | None = 'f2c4e6a8b0d1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FIRST_ACCOUNT = 'teamholyhustle@gmail.com'


def upgrade() -> None:
    """Add the column, then make the first account Premium forever."""
    # 1. The flag, false for everyone else.
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS lifetime_premium BOOLEAN NOT NULL DEFAULT false;")
    # 2. The account: flag on, active on the lifetime plan, no end date
    #    (the email is matched without regard to case).
    op.execute(
        "UPDATE users SET lifetime_premium = true, subscription_status = 'active', "
        "subscription_plan = 'lifetime', subscription_expires_at = NULL "
        f"WHERE lower(email) = '{FIRST_ACCOUNT}';"
    )


def downgrade() -> None:
    """Remove the flag (the account's status is then re-synced from its payments)."""
    # 1. Drop the column.
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS lifetime_premium;")
