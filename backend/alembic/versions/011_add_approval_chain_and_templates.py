# -*- coding: utf-8 -*-
"""添加审批链和审批模板支持

为 approvals 表新增 approval_chain、current_step、template_id 列；
新建 approval_templates 表，支持预定义审批流程。

Revision ID: 011_approval_chain_templates
Revises: 010_lawyer_matching
Create Date: 2026-03-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '011_approval_chain_templates'
down_revision: Union[str, None] = '010_lawyer_matching'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------- approvals 表新增列 ----------
    op.add_column('approvals', sa.Column(
        'approval_chain', sa.JSON(), nullable=True,
        comment='审批链配置JSON'
    ))
    op.add_column('approvals', sa.Column(
        'current_step', sa.Integer(), nullable=False,
        server_default='0', comment='当前审批步骤'
    ))
    op.add_column('approvals', sa.Column(
        'template_id', postgresql.UUID(as_uuid=False), nullable=True,
        comment='关联审批模板ID'
    ))

    # ---------- approval_templates 表 ----------
    op.create_table(
        'approval_templates',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False, comment='模板名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='模板说明'),
        sa.Column('type', sa.String(100), nullable=False,
                  server_default='custom', comment='适用审批类型'),
        sa.Column('chain_config', sa.JSON(), nullable=True,
                  comment='审批链配置JSON'),
        sa.Column('created_by', postgresql.UUID(as_uuid=False),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False, comment='创建人ID'),
        sa.Column('enabled', sa.Boolean(), nullable=False,
                  server_default='1', comment='是否启用'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_approval_templates_type', 'approval_templates', ['type'])
    op.create_index('ix_approval_templates_created_by', 'approval_templates', ['created_by'])


def downgrade() -> None:
    op.drop_index('ix_approval_templates_created_by', table_name='approval_templates')
    op.drop_index('ix_approval_templates_type', table_name='approval_templates')
    op.drop_table('approval_templates')

    op.drop_column('approvals', 'template_id')
    op.drop_column('approvals', 'current_step')
    op.drop_column('approvals', 'approval_chain')
