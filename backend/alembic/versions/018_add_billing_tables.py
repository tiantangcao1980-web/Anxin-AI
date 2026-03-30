# -*- coding: utf-8 -*-
"""添加计费系统表（billing_plans, subscriptions, refunds）

Revision ID: 018_billing_tables
Revises: 017_lawyer_certification
Create Date: 2026-03-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '018_billing_tables'
down_revision: Union[str, None] = '017_lawyer_certification'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===== 计费方案表 =====
    op.create_table(
        'billing_plans',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, comment='方案名称'),
        sa.Column('code', sa.String(50), unique=True, nullable=False, comment='方案代码'),
        sa.Column('description', sa.Text, nullable=True, comment='方案描述'),
        sa.Column('billing_mode', sa.String(30), nullable=False, comment='计费模式'),
        sa.Column('base_price', sa.Float, nullable=False, comment='基础价格'),
        sa.Column('original_price', sa.Float, nullable=True, comment='原价（划线价）'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='CNY', comment='币种'),
        sa.Column('features', sa.JSON, nullable=True, comment='功能列表'),
        sa.Column('ai_quota', sa.Integer, nullable=False, server_default=sa.text('100'), comment='AI对话次数/月'),
        sa.Column('storage_gb', sa.Integer, nullable=False, server_default=sa.text('5'), comment='存储空间GB'),
        sa.Column('max_team_members', sa.Integer, nullable=False, server_default=sa.text('5'), comment='团队成员数上限'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true'), comment='是否上架'),
        sa.Column('sort_order', sa.Integer, nullable=False, server_default=sa.text('0'), comment='排序权重'),
        sa.Column('badge', sa.String(20), nullable=True, comment='角标'),
        sa.Column('highlight', sa.Boolean, nullable=False, server_default=sa.text('false'), comment='是否高亮推荐'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_billing_plans_code', 'billing_plans', ['code'])
    op.create_index('ix_billing_plans_is_active', 'billing_plans', ['is_active'])
    op.create_index('ix_billing_plans_sort_order', 'billing_plans', ['sort_order'])

    # ===== 订阅表 =====
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=False),
                   sa.ForeignKey('users.id', ondelete='CASCADE'),
                   nullable=False, comment='用户ID'),
        sa.Column('plan_id', postgresql.UUID(as_uuid=False),
                   sa.ForeignKey('billing_plans.id', ondelete='CASCADE'),
                   nullable=False, comment='计费方案ID'),
        sa.Column('org_id', postgresql.UUID(as_uuid=False),
                   sa.ForeignKey('organizations.id', ondelete='SET NULL'),
                   nullable=True, comment='企业订阅关联组织'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active',
                   comment='订阅状态: active/past_due/cancelled/expired'),
        sa.Column('current_period_start', sa.Date, nullable=False, comment='当前周期开始'),
        sa.Column('current_period_end', sa.Date, nullable=False, comment='当前周期结束'),
        sa.Column('auto_renew', sa.Boolean, nullable=False, server_default=sa.text('true'), comment='是否自动续费'),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True, comment='取消时间'),
        sa.Column('cancellation_reason', sa.String(256), nullable=True, comment='取消原因'),
        sa.Column('last_payment_id', sa.String(36), nullable=True, comment='最近一次支付订单ID'),
        sa.Column('next_billing_date', sa.Date, nullable=True, comment='下次扣费日期'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])
    op.create_index('ix_subscriptions_plan_id', 'subscriptions', ['plan_id'])
    op.create_index('ix_subscriptions_org_id', 'subscriptions', ['org_id'])
    op.create_index('ix_subscriptions_status', 'subscriptions', ['status'])
    op.create_index('ix_subscriptions_next_billing', 'subscriptions', ['next_billing_date'])

    # ===== 退款表 =====
    op.create_table(
        'refunds',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=False),
                   sa.ForeignKey('payment_orders.id', ondelete='CASCADE'),
                   nullable=False, comment='支付订单ID'),
        sa.Column('user_id', postgresql.UUID(as_uuid=False),
                   sa.ForeignKey('users.id', ondelete='CASCADE'),
                   nullable=False, comment='申请人ID'),
        sa.Column('amount', sa.Float, nullable=False, comment='退款金额'),
        sa.Column('reason', sa.String(500), nullable=False, comment='退款原因'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending',
                   comment='退款状态: pending/approved/rejected/processed'),
        sa.Column('approved_by', postgresql.UUID(as_uuid=False),
                   sa.ForeignKey('users.id', ondelete='SET NULL'),
                   nullable=True, comment='审批人ID'),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True, comment='审批时间'),
        sa.Column('rejection_reason', sa.String(256), nullable=True, comment='驳回原因'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True, comment='处理完成时间'),
        sa.Column('processor_transaction_id', sa.String(128), nullable=True, comment='支付渠道退款流水号'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_refunds_order_id', 'refunds', ['order_id'])
    op.create_index('ix_refunds_user_id', 'refunds', ['user_id'])
    op.create_index('ix_refunds_status', 'refunds', ['status'])


def downgrade() -> None:
    op.drop_table('refunds')
    op.drop_table('subscriptions')
    op.drop_table('billing_plans')
