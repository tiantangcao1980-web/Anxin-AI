"""add user RBAC fields (department, user_type)

Revision ID: 009
Revises: 008
Create Date: 2026-03-26

安心智能助手权限体系升级：
- 添加 department 字段（部门，用于数据范围控制）
- 添加 user_type 字段（用户类型标识）
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '009_user_rbac'
down_revision = '008_add_approvals'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加部门字段
    op.add_column('users', sa.Column('department', sa.String(100), nullable=True))
    # 添加用户类型字段
    op.add_column('users', sa.Column('user_type', sa.String(30), server_default='internal', nullable=False))


def downgrade() -> None:
    op.drop_column('users', 'user_type')
    op.drop_column('users', 'department')
