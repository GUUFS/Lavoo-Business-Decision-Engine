"""add_missing_columns_url_and_user_management

Revision ID: ef3c9479f1ad
Revises: 7126648c61e4
Create Date: 2025-12-19 22:42:56.055972

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef3c9479f1ad'
down_revision: Union[str, Sequence[str], None] = '7126648c61e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.

    This migration consolidates previously scattered database column additions:
    - Adds 'url' column to 'insights' and 'alerts' tables (if not exists)
    - Adds 'user_status' and 'last_login' columns to 'users' table (if not exists)
    - Creates indexes for performance optimization (if not exists)

    These columns were previously added via raw SQL scripts, now
    properly managed through Alembic for version control.
    """
    from sqlalchemy import text, inspect

    # Get connection and inspector
    conn = op.get_bind()
    inspector = inspect(conn)

    # === INSIGHTS TABLE ===
    existing_insights_columns = [col['name'] for col in inspector.get_columns('insights')]

    if 'url' not in existing_insights_columns:
        # Add URL column to insights table
        op.add_column(
            'insights',
            sa.Column('url', sa.String(length=500), nullable=True)
        )
        print("✅ Added 'url' column to insights table")
    else:
        print("⏭️  Column 'url' already exists in insights table")

    # Check if index exists before creating
    existing_insights_indexes = [idx['name'] for idx in inspector.get_indexes('insights')]
    if 'idx_insights_url' not in existing_insights_indexes:
        op.create_index(
            'idx_insights_url',
            'insights',
            ['url'],
            unique=False
        )
        print("✅ Created index 'idx_insights_url'")
    else:
        print("⏭️  Index 'idx_insights_url' already exists")

    # === ALERTS TABLE ===
    existing_alerts_columns = [col['name'] for col in inspector.get_columns('alerts')]

    if 'url' not in existing_alerts_columns:
        # Add URL column to alerts table
        op.add_column(
            'alerts',
            sa.Column('url', sa.String(length=500), nullable=True)
        )
        print("✅ Added 'url' column to alerts table")
    else:
        print("⏭️  Column 'url' already exists in alerts table")

    # Check if index exists before creating
    existing_alerts_indexes = [idx['name'] for idx in inspector.get_indexes('alerts')]
    if 'idx_alerts_url' not in existing_alerts_indexes:
        op.create_index(
            'idx_alerts_url',
            'alerts',
            ['url'],
            unique=False
        )
        print("✅ Created index 'idx_alerts_url'")
    else:
        print("⏭️  Index 'idx_alerts_url' already exists")

    # === USERS TABLE ===
    existing_users_columns = [col['name'] for col in inspector.get_columns('users')]

    if 'user_status' not in existing_users_columns:
        # Add user_status column
        op.add_column(
            'users',
            sa.Column('user_status', sa.String(length=20), server_default='active', nullable=False)
        )
        print("✅ Added 'user_status' column to users table")

        # Populate from is_active
        conn.execute(
            text("""
            UPDATE users
            SET user_status = CASE
                WHEN is_active = true THEN 'active'
                ELSE 'inactive'
            END
            WHERE user_status IS NULL OR user_status = ''
            """)
        )
        print("✅ Populated 'user_status' from 'is_active'")
    else:
        print("⏭️  Column 'user_status' already exists in users table")

    # Check if index exists before creating
    existing_users_indexes = [idx['name'] for idx in inspector.get_indexes('users')]
    if 'idx_users_status' not in existing_users_indexes:
        op.create_index(
            'idx_users_status',
            'users',
            ['user_status'],
            unique=False
        )
        print("✅ Created index 'idx_users_status'")
    else:
        print("⏭️  Index 'idx_users_status' already exists")

    if 'last_login' not in existing_users_columns:
        # Add last_login tracking column
        op.add_column(
            'users',
            sa.Column('last_login', sa.DateTime(timezone=True), nullable=True)
        )
        print("✅ Added 'last_login' column to users table")

        # Populate with updated_at or created_at
        conn.execute(
            text("""
            UPDATE users
            SET last_login = COALESCE(updated_at, created_at)
            WHERE last_login IS NULL
            """)
        )
        print("✅ Populated 'last_login' with updated_at/created_at")
    else:
        print("⏭️  Column 'last_login' already exists in users table")

    if 'idx_users_last_login' not in existing_users_indexes:
        op.create_index(
            'idx_users_last_login',
            'users',
            ['last_login'],
            unique=False
        )
        print("✅ Created index 'idx_users_last_login'")
    else:
        print("⏭️  Index 'idx_users_last_login' already exists")


def downgrade() -> None:
    """
    Downgrade schema.

    Removes all columns and indexes added in upgrade().
    WARNING: This will permanently delete data in these columns!
    """

    # Drop indexes first (required before dropping columns)
    op.drop_index('idx_users_last_login', table_name='users')
    op.drop_index('idx_users_status', table_name='users')
    op.drop_index('idx_alerts_url', table_name='alerts')
    op.drop_index('idx_insights_url', table_name='insights')

    # Drop columns
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'user_status')
    op.drop_column('alerts', 'url')
    op.drop_column('insights', 'url')
