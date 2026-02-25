"""merge admin integration migrations

Revision ID: 7126648c61e4
Revises: 51496cdf9f10, add_analysis_monitoring
Create Date: 2025-12-11 18:02:04.909864

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7126648c61e4'
down_revision: Union[str, Sequence[str], None] = ('51496cdf9f10', 'add_analysis_monitoring')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
