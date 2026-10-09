"""add flutterwave transfer events table

Revision ID: 4dc31916c1d9
Revises: d67cb5bdcbec
Create Date: 2026-10-09 15:29:33.765719

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4dc31916c1d9'
down_revision: Union[str, Sequence[str], None] = 'd67cb5bdcbec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "flutterwave_transfer_events",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("event_type", sa.String(length=50), nullable=True),
        sa.Column("reference", sa.String(length=255), nullable=True),
        sa.Column("transfer_id", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=True),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("matched_payout_id", sa.Integer(), sa.ForeignKey("payouts.id"), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_flw_transfer_events_reference", "flutterwave_transfer_events", ["reference"])
    op.create_index("idx_flw_transfer_events_transfer_id", "flutterwave_transfer_events", ["transfer_id"])
    op.create_index("idx_flw_transfer_events_matched_payout_id", "flutterwave_transfer_events", ["matched_payout_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_flw_transfer_events_matched_payout_id", table_name="flutterwave_transfer_events")
    op.drop_index("idx_flw_transfer_events_transfer_id", table_name="flutterwave_transfer_events")
    op.drop_index("idx_flw_transfer_events_reference", table_name="flutterwave_transfer_events")
    op.drop_table("flutterwave_transfer_events")
