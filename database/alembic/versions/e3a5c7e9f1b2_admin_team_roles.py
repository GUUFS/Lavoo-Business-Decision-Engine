"""Admin team roles: who in the company may see and change each admin area.

Adds:
  - admin_roles: job roles and their permissions (api/services/admin_access.py)
  - users.admin_role_id / users.admin_title: an admin's role and job title
  - admin_activity.admin_role: the role someone acted in, for the Activity log

Existing admins get no role, which means Owner (full access), so nothing
changes for them. The starting roles (Owner, Administrator, Developer,
Finance, Customer Support, Content & Community, Viewer) are created the first
time the Team & Access page opens.

Revision ID: e3a5c7e9f1b2
Revises: d2f4a6c8e0b1
Create Date: 2026-11-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'e3a5c7e9f1b2'
down_revision: str | Sequence[str] | None = 'd2f4a6c8e0b1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the roles table and the new columns."""
    # 1. The roles.
    op.create_table(
        'admin_roles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(80), nullable=False, unique=True),
        sa.Column('description', sa.String(300), nullable=True),
        sa.Column('permissions', sa.JSON(), nullable=False),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_admin_roles_id', 'admin_roles', ['id'])
    # 2. Each admin's role and job title (no role = Owner).
    op.add_column('users', sa.Column('admin_role_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('admin_title', sa.String(120), nullable=True))
    op.create_foreign_key('fk_users_admin_role_id', 'users', 'admin_roles', ['admin_role_id'], ['id'],
                          ondelete='RESTRICT')
    op.create_index('ix_users_admin_role_id', 'users', ['admin_role_id'])
    # 3. The role each logged action was taken in.
    op.add_column('admin_activity', sa.Column('admin_role', sa.String(80), nullable=True))


def downgrade() -> None:
    """Remove the columns and the roles table."""
    # 1. In reverse order.
    op.drop_column('admin_activity', 'admin_role')
    op.drop_index('ix_users_admin_role_id', table_name='users')
    op.drop_constraint('fk_users_admin_role_id', 'users', type_='foreignkey')
    op.drop_column('users', 'admin_title')
    op.drop_column('users', 'admin_role_id')
    op.drop_index('ix_admin_roles_id', table_name='admin_roles')
    op.drop_table('admin_roles')
