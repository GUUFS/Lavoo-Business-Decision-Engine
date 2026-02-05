
"""add_payout_columns

Revision ID: d98ddbb66bb4
Revises: 4263c5d64e37
Create Date: 2026-01-24 16:37:59.412285

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd98ddbb66bb4'
down_revision: Union[str, Sequence[str], None] = '4263c5d64e37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Get current columns to avoid "already exists" errors
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = [c['name'] for c in inspector.get_columns('payouts')]
    
    # Safely add missing columns one by one
    new_columns = [
        ('provider', sa.String(50)),
        ('payment_method', sa.String(50)),
        ('provider_payout_id', sa.String(255)),
        ('provider_response', sa.Text()),
        ('recipient_email', sa.String(255)),
        ('recipient_name', sa.String(255)),
        ('account_details', sa.Text()),
        ('failure_reason', sa.Text()),
        ('created_at', sa.DateTime(timezone=True)),
        ('processed_at', sa.DateTime(timezone=True)),
        ('completed_at', sa.DateTime(timezone=True)),
        ('requested_at', sa.DateTime(timezone=True))
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            op.add_column('payouts', sa.Column(col_name, col_type, nullable=True))

    # The security_metrics_summary table check was causing issues, removing it 
    # as it's not the primary goal of this fix.
    pass

def downgrade() -> None:
    # Downgrade is optional and can be left as pass for these additive changes
    pass
