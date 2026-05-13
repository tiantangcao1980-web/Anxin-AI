"""add lawyer matching tables

Revision ID: 010
Revises: 009
Create Date: 2026-03-26

安心智能助手找律师模块：
- lawyer_profiles: 入驻律师档案
- consultations: 咨询请求
- delegations: 委托记录
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '010_lawyer_matching'
down_revision = '009_user_rbac'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 入驻律师档案
    op.create_table(
        'lawyer_profiles',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('real_name', sa.String(100), nullable=False),
        sa.Column('license_number', sa.String(50), unique=True, nullable=False),
        sa.Column('law_firm', sa.String(200)),
        sa.Column('years_of_practice', sa.Integer, default=0),
        sa.Column('city', sa.String(50)),
        sa.Column('province', sa.String(50)),
        sa.Column('specializations', sa.JSON, default=[]),
        sa.Column('bio', sa.Text),
        sa.Column('avatar_url', sa.String(500)),
        sa.Column('rating', sa.Float, default=5.0),
        sa.Column('total_cases', sa.Integer, default=0),
        sa.Column('success_cases', sa.Integer, default=0),
        sa.Column('total_reviews', sa.Integer, default=0),
        sa.Column('hourly_rate_min', sa.Integer),
        sa.Column('hourly_rate_max', sa.Integer),
        sa.Column('is_online', sa.Boolean, default=False),
        sa.Column('is_accepting', sa.Boolean, default=True),
        sa.Column('available_hours', sa.JSON),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # 咨询请求
    op.create_table(
        'consultations',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('anonymous_summary', sa.Text),
        sa.Column('original_description', sa.Text),
        sa.Column('legal_domain', sa.String(100)),
        sa.Column('legal_tags', sa.JSON, default=[]),
        sa.Column('urgency', sa.String(20), default='medium'),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('privacy_level', sa.Integer, default=0),
        sa.Column('matched_lawyer_id', UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('matched_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('user_rating', sa.Integer),
        sa.Column('user_review', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_consultations_user_id', 'consultations', ['user_id'])
    op.create_index('ix_consultations_status', 'consultations', ['status'])

    # 委托记录
    op.create_table(
        'delegations',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('consultation_id', UUID(as_uuid=False), sa.ForeignKey('consultations.id', ondelete='SET NULL')),
        sa.Column('client_id', UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lawyer_id', UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('service_type', sa.String(50)),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('quoted_amount', sa.Float),
        sa.Column('platform_fee', sa.Float),
        sa.Column('total_amount', sa.Float),
        sa.Column('paid_amount', sa.Float),
        sa.Column('contract_url', sa.String(500)),
        sa.Column('signed_at', sa.DateTime(timezone=True)),
        sa.Column('paid_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_delegations_client_id', 'delegations', ['client_id'])
    op.create_index('ix_delegations_lawyer_id', 'delegations', ['lawyer_id'])


def downgrade() -> None:
    op.drop_table('delegations')
    op.drop_table('consultations')
    op.drop_table('lawyer_profiles')
