"""add platform balance snapshots table

Revision ID: d67cb5bdcbec
Revises: 441946e0ee4d
Create Date: 2026-10-08 10:16:44.123148

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd67cb5bdcbec'
down_revision: Union[str, Sequence[str], None] = '441946e0ee4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "platform_balance_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("available_balance", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("ledger_balance", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("pending_obligations", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("threshold", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("below_threshold", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("check_failed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "idx_platform_balance_provider_currency_time",
        "platform_balance_snapshots",
        ["provider", "currency", sa.text("checked_at DESC")],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_platform_balance_provider_currency_time", table_name="platform_balance_snapshots")
    op.drop_table("platform_balance_snapshots")
