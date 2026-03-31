# -*- coding: utf-8 -*-
"""添加律所内部管理表

Revision ID: 016_firm_management
Revises: 015_add_reviews
Create Date: 2026-03-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_utils import safe_create_index, safe_create_table, safe_create_unique_constraint

# revision identifiers, used by Alembic.
revision: str = '016_firm_management'
down_revision: Union[str, None] = '015_add_reviews'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===== 团队表 =====
    safe_create_table(
        'teams',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False, comment='团队名称'),
        sa.Column('description', sa.Text, nullable=True, comment='团队描述'),
        sa.Column('leader_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment='团队负责人'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    safe_create_index('ix_teams_org_id', 'teams', ['org_id'])

    # ===== 团队成员表 =====
    safe_create_table(
        'team_members',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('team_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('teams.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='member', comment='角色: leader | member'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    safe_create_index('ix_team_members_team_id', 'team_members', ['team_id'])
    safe_create_index('ix_team_members_user_id', 'team_members', ['user_id'])
    safe_create_unique_constraint('uq_team_members_team_user', 'team_members', ['team_id', 'user_id'])

    # ===== 案件分配表 =====
    safe_create_table(
        'case_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assignee_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment='分配人'),
        sa.Column('role', sa.String(30), nullable=False, server_default='support', comment='角色: lead | support | review'),
        sa.Column('hours_estimated', sa.Float, nullable=True, comment='预估工时'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active', comment='状态: active | completed | withdrawn'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    safe_create_index('ix_case_assignments_case_id', 'case_assignments', ['case_id'])
    safe_create_index('ix_case_assignments_assignee_id', 'case_assignments', ['assignee_id'])

    # ===== 工时记录表 =====
    safe_create_table(
        'time_entries',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('cases.id', ondelete='SET NULL'), nullable=True),
        sa.Column('date', sa.Date, nullable=False, comment='工时日期'),
        sa.Column('minutes', sa.Integer, nullable=False, comment='工时（分钟）'),
        sa.Column('description', sa.String(500), nullable=True, comment='工时说明'),
        sa.Column('billable', sa.Boolean, nullable=False, server_default=sa.text('true'), comment='是否可计费'),
        sa.Column('rate', sa.Float, nullable=True, comment='费率（元/小时）'),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft', comment='状态: draft | submitted | approved | rejected'),
        sa.Column('approved_by', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment='审批人'),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True, comment='审批时间'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    safe_create_index('ix_time_entries_user_id', 'time_entries', ['user_id'])
    safe_create_index('ix_time_entries_case_id', 'time_entries', ['case_id'])
    safe_create_index('ix_time_entries_user_date', 'time_entries', ['user_id', 'date'])

    # ===== 发票表 =====
    safe_create_table(
        'invoices',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('cases.id', ondelete='SET NULL'), nullable=True),
        sa.Column('number', sa.String(50), nullable=False, unique=True, comment='发票编号'),
        sa.Column('client_name', sa.String(200), nullable=False, comment='客户名称'),
        sa.Column('total_amount', sa.Float, nullable=False, comment='总金额'),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft', comment='状态'),
        sa.Column('due_date', sa.Date, nullable=True, comment='到期日'),
        sa.Column('items', sa.JSON, nullable=True, comment='发票明细'),
        sa.Column('notes', sa.Text, nullable=True, comment='备注'),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True, comment='支付时间'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    safe_create_index('ix_invoices_org_id', 'invoices', ['org_id'])
    safe_create_index('ix_invoices_case_id', 'invoices', ['case_id'])
    safe_create_index('ix_invoices_status', 'invoices', ['status'])


def downgrade() -> None:
    op.drop_table('invoices')
    op.drop_table('time_entries')
    op.drop_table('case_assignments')
    op.drop_table('team_members')
    op.drop_table('teams')
