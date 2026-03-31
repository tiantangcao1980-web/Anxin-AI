"""add sentiment and collaboration tables

Revision ID: 004_add_sentiment_collaboration
Revises: 003_add_audit_logs
Create Date: 2026-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_utils import safe_create_index, safe_create_table

# revision identifiers, used by Alembic.
revision: str = '004_add_sentiment_collaboration'
down_revision: Union[str, None] = '003_add_audit_logs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_enum_types() -> dict[str, postgresql.ENUM]:
    bind = op.get_bind()
    enum_types = {
        'source_type': postgresql.ENUM(
            'news',
            'social_media',
            'forum',
            'blog',
            'official',
            'other',
            name='sourcetype',
            create_type=False,
        ),
        'sentiment_type': postgresql.ENUM(
            'positive',
            'negative',
            'neutral',
            name='sentimenttype',
            create_type=False,
        ),
        'risk_level': postgresql.ENUM(
            'low',
            'medium',
            'high',
            'critical',
            name='risklevel',
            create_type=False,
        ),
        'alert_type': postgresql.ENUM(
            'negative_surge',
            'high_risk',
            'keyword_match',
            'trend_anomaly',
            'reputation_risk',
            name='alerttype',
            create_type=False,
        ),
        'alert_level': postgresql.ENUM(
            'info',
            'warning',
            'danger',
            'critical',
            name='alertlevel',
            create_type=False,
        ),
        'session_status': postgresql.ENUM(
            'active',
            'paused',
            'closed',
            name='sessionstatus',
            create_type=False,
        ),
        'collaborator_role': postgresql.ENUM(
            'owner',
            'editor',
            'viewer',
            'commenter',
            name='collaboratorrole',
            create_type=False,
        ),
        'edit_operation': postgresql.ENUM(
            'insert',
            'delete',
            'replace',
            'format',
            'comment',
            'cursor',
            name='editoperation',
            create_type=False,
        ),
    }

    for enum_type in enum_types.values():
        enum_type.create(bind, checkfirst=True)

    return enum_types


def upgrade() -> None:
    enum_types = _ensure_enum_types()

    # ============ 舆情监控表 ============
    
    # 舆情监控配置表
    safe_create_table(
        'sentiment_monitors',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('keywords', postgresql.JSONB(), nullable=False),
        sa.Column('sources', postgresql.JSONB(), nullable=True),
        sa.Column('exclude_keywords', postgresql.JSONB(), nullable=True),
        sa.Column('alert_threshold', sa.Float(), nullable=False, default=0.7),
        sa.Column('negative_threshold', sa.Float(), nullable=False, default=0.6),
        sa.Column('risk_threshold', sa.Float(), nullable=False, default=0.8),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_scan_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scan_interval', sa.Integer(), nullable=False, default=3600),
        sa.Column('total_records', sa.Integer(), nullable=False, default=0),
        sa.Column('negative_count', sa.Integer(), nullable=False, default=0),
        sa.Column('alert_count', sa.Integer(), nullable=False, default=0),
        sa.Column('org_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 舆情记录表
    safe_create_table(
        'sentiment_records',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('keyword', sa.String(100), nullable=False),
        sa.Column('source', sa.String(255), nullable=True),
        sa.Column('source_type', enum_types['source_type'], nullable=False, default='other'),
        sa.Column('sentiment_type', enum_types['sentiment_type'], nullable=False, default='neutral'),
        sa.Column('sentiment_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('risk_level', enum_types['risk_level'], nullable=False, default='low'),
        sa.Column('risk_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('risk_factors', postgresql.JSONB(), nullable=True),
        sa.Column('ai_analysis', postgresql.JSONB(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('publish_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('author', sa.String(100), nullable=True),
        sa.Column('engagement', postgresql.JSONB(), nullable=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('monitor_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['monitor_id'], ['sentiment_monitors.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    safe_create_index('ix_sentiment_records_keyword', 'sentiment_records', ['keyword'])
    
    # 舆情预警表
    safe_create_table(
        'sentiment_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('alert_type', enum_types['alert_type'], nullable=False),
        sa.Column('alert_level', enum_types['alert_level'], nullable=False, default='info'),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_handled', sa.Boolean(), nullable=False, default=False),
        sa.Column('handled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('handled_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('handle_note', sa.Text(), nullable=True),
        sa.Column('related_records', postgresql.JSONB(), nullable=True),
        sa.Column('statistics', postgresql.JSONB(), nullable=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('monitor_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['monitor_id'], ['sentiment_monitors.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['handled_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # ============ 协作编辑表 ============
    
    # 文档协作会话表
    safe_create_table(
        'document_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('status', enum_types['session_status'], nullable=False, default='active'),
        sa.Column('max_collaborators', sa.Integer(), nullable=False, default=10),
        sa.Column('allow_anonymous', sa.Boolean(), nullable=False, default=False),
        sa.Column('require_approval', sa.Boolean(), nullable=False, default=False),
        sa.Column('current_version', sa.Integer(), nullable=False, default=1),
        sa.Column('base_content', sa.Text(), nullable=True),
        sa.Column('current_content', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('total_edits', sa.Integer(), nullable=False, default=0),
        sa.Column('active_collaborators', sa.Integer(), nullable=False, default=0),
        sa.Column('settings', postgresql.JSONB(), nullable=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 文档协作者表
    safe_create_table(
        'document_collaborators',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('role', enum_types['collaborator_role'], nullable=False, default='editor'),
        sa.Column('nickname', sa.String(50), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('is_online', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('cursor_position', postgresql.JSONB(), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('left_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('edit_count', sa.Integer(), nullable=False, default=0),
        sa.Column('session_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['document_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 文档编辑记录表
    safe_create_table(
        'document_edits',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('operation', enum_types['edit_operation'], nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('position', postgresql.JSONB(), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('old_content', sa.Text(), nullable=True),
        sa.Column('format_type', sa.String(50), nullable=True),
        sa.Column('format_value', postgresql.JSONB(), nullable=True),
        sa.Column('operation_time', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('is_synced', sa.Boolean(), nullable=False, default=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('collaborator_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['document_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['collaborator_id'], ['document_collaborators.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # 删除协作编辑表
    op.drop_table('document_edits')
    op.drop_table('document_collaborators')
    op.drop_table('document_sessions')
    
    # 删除舆情监控表
    op.drop_index('ix_sentiment_records_keyword', 'sentiment_records')
    op.drop_table('sentiment_alerts')
    op.drop_table('sentiment_records')
    op.drop_table('sentiment_monitors')
    
    # 删除枚举类型
    # op.execute('DROP TYPE IF EXISTS editoperation')
    # op.execute('DROP TYPE IF EXISTS collaboratorrole')
    # op.execute('DROP TYPE IF EXISTS sessionstatus')
    # op.execute('DROP TYPE IF EXISTS alerttype')
    # op.execute('DROP TYPE IF EXISTS alertlevel')
    # op.execute('DROP TYPE IF EXISTS risklevel')
    # op.execute('DROP TYPE IF EXISTS sentimenttype')
    # op.execute('DROP TYPE IF EXISTS sourcetype')
