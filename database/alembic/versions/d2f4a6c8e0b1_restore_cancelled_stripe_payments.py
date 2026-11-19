"""Put back Stripe payments that were hidden from revenue on cancel.

When a Stripe subscription was cancelled, the code also set the PAYMENT
row's status to 'cancelled' (subscriptions/stripe.py). Revenue only counts
completed payments, so money a customer really paid (and kept paying for)
vanished from the admin Revenue page the moment they cancelled.

The cancel code now only changes subscription_status (the plan). This puts
the hidden payments back to 'completed'. A payment row is only ever created
once money is taken, and refunds/disputes use 'refunded'/'disputed', so a
Stripe row with status 'cancelled' is always a real payment.

Revision ID: d2f4a6c8e0b1
Revises: c1e3a5b7d9f2
Create Date: 2026-11-19
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'd2f4a6c8e0b1'
down_revision: str | Sequence[str] | None = 'c1e3a5b7d9f2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Mark cancelled Stripe payments as completed again (safe to run twice)."""
    # 1. Only Stripe rows hidden by the old cancel code; the plan stays cancelled.
    op.execute(
        "UPDATE subscriptions SET status = 'completed' "
        "WHERE status = 'cancelled' AND lower(payment_provider) = 'stripe';"
    )


def downgrade() -> None:
    """Nothing to undo: which rows were changed isn't recorded, and hiding paid money was the bug."""
    # 1. Leave the data as it is.
    pass
