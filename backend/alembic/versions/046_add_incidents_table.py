# -*- coding: utf-8 -*-
"""add incidents table for CREAO self-healing loop (Slice 1)

Revision ID: 046_add_incidents_table
Revises: 045_merge_030_044
Create Date: 2026-05-14 (renumbered from 028_incidents during T5 merge)

收集所有失败信号 (output_validator / agent_forum / low_rating /
api_5xx / frontend_error) 到统一 incidents 表，供后续 Slice 2 做
triage / GitHub Issue 化。

T5 (2026-05-14): 原 peaceful-goodall 分支上以 028_incidents 命名 +
down_revision=027_experience_patterns; 当前主线 alembic 处于 028/030/
044 多 head 状态, 由 045_merge_030_044 汇合. 本 migration 重编号为 046
并改 down_revision=045_merge_030_044, 与主线 alembic 链路保持一致.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = '046_add_incidents_table'
down_revision = '045_merge_030_044'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'incidents',
        sa.Column(
            'id',
            UUID(as_uuid=False),
            primary_key=True,
        ),
        sa.Column('source', sa.String(32), nullable=False),
        sa.Column(
            'severity',
            sa.String(8),
            nullable=False,
            server_default='P2',
        ),
        sa.Column('fingerprint', sa.String(64), nullable=False),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column(
            'payload',
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            'payload_classification',
            sa.String(16),
            nullable=False,
            server_default='CONFIDENTIAL',
        ),
        sa.Column(
            'user_id',
            UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('session_id', sa.String(64), nullable=True),
        sa.Column('trace_id', sa.String(64), nullable=True),
        sa.Column('agent_name', sa.String(64), nullable=True),
        sa.Column('route', sa.String(128), nullable=True),
        sa.Column(
            'status',
            sa.String(16),
            nullable=False,
            server_default='open',
        ),
        sa.Column(
            'occurrence_count',
            sa.Integer(),
            nullable=False,
            server_default='1',
        ),
        sa.Column(
            'first_seen_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            'last_seen_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column('triage_summary', sa.Text(), nullable=True),
        sa.Column('github_issue_url', sa.String(256), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 单列索引
    op.create_index('ix_incidents_source', 'incidents', ['source'])
    op.create_index('ix_incidents_severity', 'incidents', ['severity'])
    op.create_index('ix_incidents_fingerprint', 'incidents', ['fingerprint'])
    op.create_index('ix_incidents_user_id', 'incidents', ['user_id'])
    op.create_index('ix_incidents_session_id', 'incidents', ['session_id'])
    op.create_index('ix_incidents_trace_id', 'incidents', ['trace_id'])
    op.create_index('ix_incidents_status', 'incidents', ['status'])
    op.create_index('ix_incidents_last_seen_at', 'incidents', ['last_seen_at'])

    # 部分唯一索引：同 fingerprint 在 open 状态只能有一条 → UPSERT 锚点
    op.create_index(
        'uq_incidents_fingerprint_open',
        'incidents',
        ['fingerprint'],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )


def downgrade():
    op.drop_index('uq_incidents_fingerprint_open', table_name='incidents')
    op.drop_index('ix_incidents_last_seen_at', table_name='incidents')
    op.drop_index('ix_incidents_status', table_name='incidents')
    op.drop_index('ix_incidents_trace_id', table_name='incidents')
    op.drop_index('ix_incidents_session_id', table_name='incidents')
    op.drop_index('ix_incidents_user_id', table_name='incidents')
    op.drop_index('ix_incidents_fingerprint', table_name='incidents')
    op.drop_index('ix_incidents_severity', table_name='incidents')
    op.drop_index('ix_incidents_source', table_name='incidents')
    op.drop_table('incidents')
