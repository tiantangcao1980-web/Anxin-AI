# -*- coding: utf-8 -*-
"""添加支付订单表

Revision ID: 012_payment_orders
Revises: 011_approval_chain
Create Date: 2026-03-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '012_payment_orders'
down_revision: Union[str, None] = '011_notification_preferences'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'payment_orders',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False, index=True),
        sa.Column('order_type', sa.String(50), nullable=False, comment='订单类型'),
        sa.Column('amount', sa.Float, nullable=False, comment='金额（元）'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending', comment='支付状态'),
        sa.Column('description', sa.String(256), nullable=False, server_default='', comment='订单描述'),
        sa.Column('related_id', sa.String(36), nullable=True, comment='关联业务ID'),
        sa.Column('transaction_id', sa.String(128), nullable=True, comment='第三方交易号'),
        sa.Column('payment_provider', sa.String(30), nullable=False, server_default='mock', comment='支付渠道'),
        sa.Column('payment_url', sa.Text, nullable=True, comment='支付链接'),
        sa.Column('qr_code', sa.Text, nullable=True, comment='二维码数据'),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True, comment='支付时间'),
        sa.Column('refunded_at', sa.DateTime(timezone=True), nullable=True, comment='退款时间'),
        sa.Column('refund_reason', sa.String(256), nullable=True, comment='退款原因'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='订单过期时间'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # 状态索引加速查询
    op.create_index('ix_payment_orders_status', 'payment_orders', ['status'])
    op.create_index('ix_payment_orders_user_status', 'payment_orders', ['user_id', 'status'])


def downgrade() -> None:
    op.drop_index('ix_payment_orders_user_status', table_name='payment_orders')
    op.drop_index('ix_payment_orders_status', table_name='payment_orders')
    op.drop_table('payment_orders')
