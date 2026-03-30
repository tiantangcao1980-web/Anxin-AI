# -*- coding: utf-8 -*-
"""添加功能开关表

Revision ID: 013_feature_flags
Revises: 012_payment_orders
Create Date: 2026-03-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_utils import safe_create_index, safe_create_table

revision: str = '013_feature_flags'
down_revision: Union[str, None] = '012_payment_orders'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    safe_create_table(
        'feature_flags',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('key', sa.String(100), nullable=False, unique=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('rollout_percentage', sa.Integer, nullable=False, server_default=sa.text('100')),
        sa.Column('target_roles', sa.JSON, nullable=True),
        sa.Column('target_org_ids', sa.JSON, nullable=True),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    safe_create_index('ix_feature_flags_key', 'feature_flags', ['key'], unique=True)
    safe_create_index('ix_feature_flags_enabled', 'feature_flags', ['enabled'])


def downgrade() -> None:
    op.drop_index('ix_feature_flags_enabled', table_name='feature_flags')
    op.drop_index('ix_feature_flags_key', table_name='feature_flags')
    op.drop_table('feature_flags')
