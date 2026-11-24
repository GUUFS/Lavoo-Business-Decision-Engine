"""Saved cards only with consent: users.auto_renew and users.renewals_stopped_at.

auto_renew is on only when the customer ticked "Save my card and renew
automatically" on their latest payment (subscriptions/card_consent.py).
Lavoo never recorded that choice before, so EVERY existing customer starts
with it off (the owner's decision, 2026-11-24): nobody is charged
automatically until they tick it on a future payment. The daily expiry job
then forgets their saved cards and sets their Stripe subscriptions to end at
the end of the period already paid for (renewals_stopped_at records that).

Revision ID: a5c7e9b1d3f4
Revises: f4b6d8a0c2e3
Create Date: 2026-11-24
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a5c7e9b1d3f4'
down_revision: str | Sequence[str] | None = 'f4b6d8a0c2e3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the two columns (auto_renew off for everyone)."""
    # 1. The customer's choice, off for all existing customers.
    op.add_column('users', sa.Column('auto_renew', sa.Boolean(), nullable=False, server_default=sa.false()))
    # 2. When their Stripe subscriptions were set not to renew by themselves.
    op.add_column('users', sa.Column('renewals_stopped_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove the two columns."""
    # 1. In reverse order.
    op.drop_column('users', 'renewals_stopped_at')
    op.drop_column('users', 'auto_renew')
