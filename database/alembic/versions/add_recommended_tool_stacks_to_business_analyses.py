"""Add recommended_tool_stacks to business_analyses

Revision ID: add_recommended_tool_stacks_001
Revises: add_community_marketplace_001
Create Date: 2026-04-23 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_recommended_tool_stacks_001"
down_revision: Union[str, Sequence[str], None] = "add_community_marketplace_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "business_analyses",
        sa.Column("recommended_tool_stacks", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("business_analyses", "recommended_tool_stacks")
