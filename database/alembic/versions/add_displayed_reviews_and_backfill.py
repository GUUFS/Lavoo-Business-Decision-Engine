"""Add displayed_reviews table and backfill IP blacklist emails

Revision ID: add_displayed_reviews_and_backfill
Revises: fbd856f8ccd8
Create Date: 2025-12-30 16:27:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_displayed_reviews_and_backfill'
down_revision = 'fbd856f8ccd8'
branch_labels = None
depends_on = None


def upgrade():
    """
    This migration does three things:
    1. Creates the displayed_reviews table for admin-managed homepage reviews
    2. Backfills email addresses in ip_blacklist from failed_login_attempts
    3. Adds indexes for performance optimization
    """
    
    # 1. Create displayed_reviews table
    # This table stores which reviews the admin has selected to display on the homepage
    op.create_table('displayed_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('review_id', sa.Integer(), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('added_by', sa.Integer(), nullable=True),  # FIX: Changed from UUID to Integer to match users.id
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['added_by'], ['users.id'], ondelete='SET NULL')
    )
    
    # Add indexes for better query performance
    op.create_index('idx_displayed_reviews_review_id', 'displayed_reviews', ['review_id'], unique=True)
    op.create_index('idx_displayed_reviews_order', 'displayed_reviews', ['display_order'])
    
    # 2. Backfill email addresses in ip_blacklist from failed_login_attempts
    # This updates existing blacklisted IPs to include the email that triggered the block
    op.execute("""
        UPDATE ip_blacklist
        SET email = subquery.email
        FROM (
            SELECT DISTINCT ON (ip_address) 
                ip_address, 
                email
            FROM failed_login_attempts
            WHERE email IS NOT NULL
            ORDER BY ip_address, created_at DESC
        ) AS subquery
        WHERE ip_blacklist.ip_address = subquery.ip_address
        AND ip_blacklist.email IS NULL;
    """)
    
    # 3. Add composite index on security_events for faster metrics queries
    # This speeds up the security dashboard metrics calculation
    op.create_index(
        'idx_security_events_type_created', 
        'security_events', 
        ['type', 'created_at'],
        postgresql_using='btree'
    )
    
    # 4. Add index on security_events severity for faster filtering
    op.create_index(
        'idx_security_events_severity_created',
        'security_events',
        ['severity', 'created_at'],
        postgresql_using='btree'
    )


def downgrade():
    """
    Rollback changes if needed
    """
    # Remove indexes
    op.drop_index('idx_security_events_severity_created', table_name='security_events')
    op.drop_index('idx_security_events_type_created', table_name='security_events')
    op.drop_index('idx_displayed_reviews_order', table_name='displayed_reviews')
    op.drop_index('idx_displayed_reviews_review_id', table_name='displayed_reviews')
    
    # Drop displayed_reviews table
    op.drop_table('displayed_reviews')
    
    # Note: We don't revert the email backfill as it's data correction, not schema change
