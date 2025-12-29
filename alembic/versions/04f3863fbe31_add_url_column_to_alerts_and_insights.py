"""add_url_column_to_alerts_and_insights

Revision ID: 04f3863fbe31
Revises: a626028d446c
Create Date: 2025-12-24 18:38:10.499848

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04f3863fbe31'
down_revision: Union[str, Sequence[str], None] = 'a626028d446c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if url column exists before adding to alerts
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    alerts_columns = [col['name'] for col in inspector.get_columns('alerts')]
    
    if 'url' not in alerts_columns:
        op.add_column('alerts', sa.Column('url', sa.String(), nullable=True))
    
    # Check if url column exists before adding to insights
    insights_columns = [col['name'] for col in inspector.get_columns('insights')]
    
    if 'url' not in insights_columns:
        op.add_column('insights', sa.Column('url', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Check if url column exists before dropping from insights
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    insights_columns = [col['name'] for col in inspector.get_columns('insights')]
    
    if 'url' in insights_columns:
        op.drop_column('insights', 'url')
    
    # Check if url column exists before dropping from alerts
    alerts_columns = [col['name'] for col in inspector.get_columns('alerts')]
    
    if 'url' in alerts_columns:
        op.drop_column('alerts', 'url')
