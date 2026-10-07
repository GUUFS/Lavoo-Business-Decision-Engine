"""merge push_subscriptions and pending_signups branches

Revision ID: 441946e0ee4d
Revises: 20261006_push_subscriptions, 3a7b8c9d0e1f
Create Date: 2026-10-07 15:14:34.013939

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '441946e0ee4d'
down_revision: Union[str, Sequence[str], None] = ('20261006_push_subscriptions', '3a7b8c9d0e1f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
