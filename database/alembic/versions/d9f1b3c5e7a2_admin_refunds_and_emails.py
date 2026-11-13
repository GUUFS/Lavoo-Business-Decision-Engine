"""Admin refunds and admin emails: a record of each.

Adds:
  - admin_refunds: every refund an admin made from the admin Refunds page.
  - admin_sent_emails: every email an admin sent to a user.

Revision ID: d9f1b3c5e7a2
Revises: c7e9a1b3d5f6
Create Date: 2026-11-13
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'd9f1b3c5e7a2'
down_revision: str | Sequence[str] | None = 'c7e9a1b3d5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create both tables (safe to run twice)."""
    # 1. Refunds made by an admin.
    op.execute("""
        CREATE TABLE IF NOT EXISTS admin_refunds (
            id SERIAL PRIMARY KEY,
            stripe_charge_id VARCHAR(255) NOT NULL,
            stripe_payment_intent_id VARCHAR(255),
            stripe_refund_id VARCHAR(255),
            amount NUMERIC(10, 2) NOT NULL,
            currency VARCHAR(10) NOT NULL,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            subscription_record_id INTEGER REFERENCES subscriptions(id) ON DELETE SET NULL,
            stripe_subscription_cancelled VARCHAR(255),
            reason VARCHAR(40) NOT NULL,
            note TEXT,
            steps JSON,
            refunded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_admin_refunds_stripe_charge_id ON admin_refunds (stripe_charge_id);")
    # 2. Emails sent by an admin.
    op.execute("""
        CREATE TABLE IF NOT EXISTS admin_sent_emails (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            to_email VARCHAR(255) NOT NULL,
            subject VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            status VARCHAR(20) NOT NULL,
            sent_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        );
    """)


def downgrade() -> None:
    """Drop both tables."""
    op.execute("DROP TABLE IF EXISTS admin_sent_emails;")
    op.execute("DROP TABLE IF EXISTS admin_refunds;")
