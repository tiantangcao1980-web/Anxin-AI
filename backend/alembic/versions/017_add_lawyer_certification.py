# -*- coding: utf-8 -*-
"""添加律师认证与接单配置表

Revision ID: 017_lawyer_certification
Revises: 016_firm_management
Create Date: 2026-03-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '017_lawyer_certification'
down_revision: Union[str, None] = '016_firm_management'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===== 律师认证表 =====
    op.create_table(
        'lawyer_certifications',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('lawyer_profile_id', postgresql.UUID(as_uuid=False),
                   sa.ForeignKey('lawyer_profiles.id', ondelete='CASCADE'),
                   unique=True, nullable=False, comment='律师档案ID'),
        sa.Column('license_image_url', sa.String(500), nullable=False, comment='执业证照片URL'),
        sa.Column('id_card_image_url', sa.String(500), nullable=True, comment='身份证照片URL'),
        sa.Column('license_issue_date', sa.Date, nullable=False, comment='执业证签发日期'),
        sa.Column('license_expiry_date', sa.Date, nullable=False, comment='执业证到期日期'),
        sa.Column('bar_association', sa.String(100), nullable=True, comment='所属律师协会'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending',
                   comment='认证状态: pending/approved/rejected/expired'),
        sa.Column('rejection_reason', sa.Text, nullable=True, comment='驳回原因'),
        sa.Column('verified_by', postgresql.UUID(as_uuid=False),
                   sa.ForeignKey('users.id', ondelete='SET NULL'),
                   nullable=True, comment='审核人ID'),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True, comment='审核时间'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_lawyer_certifications_status', 'lawyer_certifications', ['status'])
    op.create_index('ix_lawyer_certifications_expiry', 'lawyer_certifications', ['license_expiry_date'])

    # ===== 律师接单配置表 =====
    op.create_table(
        'lawyer_service_configs',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('lawyer_profile_id', postgresql.UUID(as_uuid=False),
                   sa.ForeignKey('lawyer_profiles.id', ondelete='CASCADE'),
                   unique=True, nullable=False, comment='律师档案ID'),
        sa.Column('service_types', sa.JSON, nullable=True, comment='服务类型列表'),
        sa.Column('auto_accept', sa.Boolean, nullable=False, server_default=sa.text('false'), comment='是否自动接单'),
        sa.Column('max_concurrent_cases', sa.Integer, nullable=False, server_default=sa.text('10'), comment='最大并发案件数'),
        sa.Column('response_time_hours', sa.Integer, nullable=False, server_default=sa.text('24'), comment='承诺响应时间（小时）'),
        sa.Column('working_hours', sa.JSON, nullable=True, comment='工作时间配置'),
        sa.Column('min_case_amount', sa.Float, nullable=True, comment='最低接案金额'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('lawyer_service_configs')
    op.drop_table('lawyer_certifications')
