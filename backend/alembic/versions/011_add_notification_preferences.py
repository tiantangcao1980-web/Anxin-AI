"""添加通知偏好设置表

Revision ID: 011_notification_preferences
Revises: 010_lawyer_matching
Create Date: 2026-03-27

安心法务通知系统增强：
- notification_preferences: 用户通知偏好设置（渠道 x 事件类型）
- notifications 表增加 event_type 字段
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from migration_utils import safe_add_column, safe_create_index, safe_create_table

revision: str = '011_notification_preferences'
down_revision: Union[str, None] = '011_approval_chain_templates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建通知偏好表
    safe_create_table(
        'notification_preferences',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel', sa.String(20), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'channel', 'event_type', name='uq_user_channel_event'),
    )
    safe_create_index('ix_notification_preferences_user_id', 'notification_preferences', ['user_id'])

    # 为 notifications 表添加 event_type 字段
    safe_add_column('notifications', sa.Column('event_type', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('notifications', 'event_type')
    op.drop_index('ix_notification_preferences_user_id', table_name='notification_preferences')
    op.drop_table('notification_preferences')
