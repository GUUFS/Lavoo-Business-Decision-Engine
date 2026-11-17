"""What the payout system did with each commission.

Adds:
  - commission_payout_attempts: one row per kind of outcome when the system
    tries to pay a commission (sent, waiting for money, no payout account, ...),
    with the route (Flutterwave or Stripe), whether it is cross-border
    (converted to another currency), the amounts, the balance it saw, and a
    plain-words reason. Shown on the admin Payout Tracker page.

Revision ID: e3a5c7d9f1b4
Revises: d9f1b3c5e7a2
Create Date: 2026-11-13
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'e3a5c7d9f1b4'
down_revision: str | Sequence[str] | None = 'd9f1b3c5e7a2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the table and its index (safe to run twice)."""
    # 1. The table.
    op.execute("""
        CREATE TABLE IF NOT EXISTS commission_payout_attempts (
            id SERIAL PRIMARY KEY,
            commission_id INTEGER NOT NULL REFERENCES commissions(id) ON DELETE CASCADE,
            route VARCHAR(20),
            cross_border BOOLEAN NOT NULL DEFAULT false,
            from_currency VARCHAR(10),
            to_currency VARCHAR(10),
            amount NUMERIC(12, 2),
            converted_amount NUMERIC(14, 2),
            fx_rate NUMERIC(18, 6),
            balance_available NUMERIC(14, 2),
            outcome VARCHAR(30) NOT NULL,
            reason TEXT NOT NULL,
            payout_id INTEGER REFERENCES payouts(id) ON DELETE SET NULL,
            tries INTEGER NOT NULL DEFAULT 1,
            first_tried_at TIMESTAMPTZ DEFAULT now(),
            last_tried_at TIMESTAMPTZ DEFAULT now()
        );
    """)
    # 2. Looked up by commission on every attempt and on the tracker page.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_commission_payout_attempts_commission_id "
        "ON commission_payout_attempts (commission_id);"
    )


def downgrade() -> None:
    """Drop the table."""
    op.execute("DROP TABLE IF EXISTS commission_payout_attempts;")
