# -*- coding: utf-8 -*-
"""添加审批流表

创建 approvals 表，支持审批流工作流管理。

Revision ID: 008_add_approvals
Revises: 007_user_security
Create Date: 2026-03-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008_add_approvals'
down_revision: Union[str, None] = '007_user_security'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'approvals',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False, comment='审批标题'),
        sa.Column('type', sa.String(50), nullable=False, server_default='custom', comment='审批类型'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending', comment='审批状态'),
        sa.Column('description', sa.Text(), nullable=True, comment='审批说明'),
        sa.Column('requester_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id'), nullable=False, comment='发起人ID'),
        sa.Column('requester_name', sa.String(255), nullable=True, comment='发起人姓名'),
        sa.Column('approver_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id'), nullable=True, comment='审批人ID'),
        sa.Column('approver_name', sa.String(255), nullable=True, comment='审批人姓名'),
        sa.Column('resource_type', sa.String(50), nullable=True, comment='关联资源类型'),
        sa.Column('resource_id', sa.String(255), nullable=True, comment='关联资源ID'),
        sa.Column('comment', sa.Text(), nullable=True, comment='审批意见'),
        sa.Column('metadata', sa.JSON(), nullable=True, comment='附加数据'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='1', comment='优先级'),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True, comment='审批完成时间'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 添加索引
    op.create_index('ix_approvals_requester_id', 'approvals', ['requester_id'])
    op.create_index('ix_approvals_approver_id', 'approvals', ['approver_id'])
    op.create_index('ix_approvals_status', 'approvals', ['status'])
    op.create_index('ix_approvals_type', 'approvals', ['type'])


def downgrade() -> None:
    op.drop_index('ix_approvals_type', table_name='approvals')
    op.drop_index('ix_approvals_status', table_name='approvals')
    op.drop_index('ix_approvals_approver_id', table_name='approvals')
    op.drop_index('ix_approvals_requester_id', table_name='approvals')
    op.drop_table('approvals')
