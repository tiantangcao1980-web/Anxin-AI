"""初始数据库结构

Revision ID: 001_initial
Revises: 
Create Date: 2026-01-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================== 组织表 ====================
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ==================== 用户表 ====================
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('role', sa.String(50), default='member'),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_org_id', 'users', ['org_id'])

    # ==================== 案件表 ====================
    op.create_table(
        'cases',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('case_number', sa.String(50), unique=True, nullable=True),
        sa.Column('case_type', sa.Enum('contract', 'labor', 'ip', 'corporate', 'litigation', 'compliance', 'due_diligence', 'other', name='casetype'), default='other'),
        sa.Column('status', sa.Enum('pending', 'in_progress', 'under_review', 'completed', 'closed', 'cancelled', name='casestatus'), default='pending'),
        sa.Column('priority', sa.Enum('low', 'medium', 'high', 'urgent', name='casepriority'), default='medium'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parties', postgresql.JSONB(), nullable=True),
        sa.Column('ai_analysis', postgresql.JSONB(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assignee_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_cases_org_id', 'cases', ['org_id'])
    op.create_index('ix_cases_status', 'cases', ['status'])

    # ==================== 案件事件表 ====================
    op.create_table(
        'case_events',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_data', postgresql.JSONB(), nullable=True),
        sa.Column('event_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_case_events_case_id', 'case_events', ['case_id'])

    # ==================== 文档表 ====================
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('doc_type', sa.Enum('contract', 'agreement', 'legal_opinion', 'lawsuit', 'evidence', 'report', 'template', 'other', name='documenttype'), default='other'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.BigInteger(), default=0),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('file_hash', sa.String(64), nullable=True),
        sa.Column('version', sa.Integer(), default=1),
        sa.Column('is_latest', sa.Boolean(), default=True),
        sa.Column('ai_summary', sa.Text(), nullable=True),
        sa.Column('ai_analysis', postgresql.JSONB(), nullable=True),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('doc_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('cases.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_documents_org_id', 'documents', ['org_id'])
    op.create_index('ix_documents_case_id', 'documents', ['case_id'])

    # ==================== 文档版本表 ====================
    op.create_table(
        'document_versions',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.BigInteger(), default=0),
        sa.Column('file_hash', sa.String(64), nullable=True),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_document_versions_document_id', 'document_versions', ['document_id'])

    # ==================== 合同表 ====================
    op.create_table(
        'contracts',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('contract_number', sa.String(50), unique=True, nullable=True),
        sa.Column('contract_type', sa.String(100), nullable=False),
        sa.Column('status', sa.Enum('draft', 'pending_review', 'under_review', 'approved', 'signed', 'active', 'expired', 'terminated', name='contractstatus'), default='draft'),
        sa.Column('party_a', postgresql.JSONB(), nullable=True),
        sa.Column('party_b', postgresql.JSONB(), nullable=True),
        sa.Column('other_parties', postgresql.JSONB(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(10), default='CNY'),
        sa.Column('sign_date', sa.Date(), nullable=True),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('risk_level', sa.Enum('low', 'medium', 'high', 'critical', name='risklevel'), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('review_summary', sa.Text(), nullable=True),
        sa.Column('key_terms', postgresql.JSONB(), nullable=True),
        sa.Column('review_result', postgresql.JSONB(), nullable=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_contracts_org_id', 'contracts', ['org_id'])
    op.create_index('ix_contracts_status', 'contracts', ['status'])

    # ==================== 合同条款表 ====================
    op.create_table(
        'contract_clauses',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('clause_number', sa.String(50), nullable=False),
        sa.Column('clause_type', sa.String(100), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_standard', sa.Boolean(), default=True),
        sa.Column('risk_level', sa.Enum('low', 'medium', 'high', 'critical', name='risklevel', create_type=False), nullable=True),
        sa.Column('analysis', postgresql.JSONB(), nullable=True),
        sa.Column('suggestions', postgresql.JSONB(), nullable=True),
        sa.Column('contract_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('contracts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_contract_clauses_contract_id', 'contract_clauses', ['contract_id'])

    # ==================== 合同风险表 ====================
    op.create_table(
        'contract_risks',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('risk_type', sa.String(100), nullable=False),
        sa.Column('risk_level', sa.Enum('low', 'medium', 'high', 'critical', name='risklevel', create_type=False), default='medium'),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('related_clause', sa.String(50), nullable=True),
        sa.Column('original_text', sa.Text(), nullable=True),
        sa.Column('suggestion', sa.Text(), nullable=True),
        sa.Column('suggested_text', sa.Text(), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), default=False),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('contract_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('contracts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_contract_risks_contract_id', 'contract_risks', ['contract_id'])

    # ==================== 对话表 ====================
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('context', postgresql.JSONB(), nullable=True),
        sa.Column('message_count', sa.Integer(), default=0),
        sa.Column('token_count', sa.Integer(), default=0),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('cases.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])

    # ==================== 消息表 ====================
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('role', sa.Enum('user', 'assistant', 'system', name='messagerole'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('agent_name', sa.String(100), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('citations', postgresql.JSONB(), nullable=True),
        sa.Column('actions', postgresql.JSONB(), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), default=0),
        sa.Column('completion_tokens', sa.Integer(), default=0),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('msg_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])

    # ==================== 知识库表 ====================
    op.create_table(
        'knowledge_bases',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('knowledge_type', sa.Enum('law', 'regulation', 'case', 'interpretation', 'template', 'article', 'internal', 'other', name='knowledgetype'), default='other'),
        sa.Column('doc_count', sa.Integer(), default=0),
        sa.Column('total_chunks', sa.Integer(), default=0),
        sa.Column('vector_collection', sa.String(100), nullable=True),
        sa.Column('embedding_model', sa.String(100), default='text-embedding-3-large'),
        sa.Column('embedding_dimensions', sa.Integer(), default=3072),
        sa.Column('is_public', sa.Boolean(), default=False),
        sa.Column('config', postgresql.JSONB(), nullable=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_knowledge_bases_org_id', 'knowledge_bases', ['org_id'])

    # ==================== 知识库文档表 ====================
    op.create_table(
        'knowledge_documents',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('source', sa.String(255), nullable=True),
        sa.Column('source_url', sa.String(500), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('is_processed', sa.Boolean(), default=False),
        sa.Column('chunk_count', sa.Integer(), default=0),
        sa.Column('extra_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('law_category', sa.String(100), nullable=True),
        sa.Column('effective_date', sa.String(50), nullable=True),
        sa.Column('issuing_authority', sa.String(255), nullable=True),
        sa.Column('knowledge_base_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('knowledge_bases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_knowledge_documents_kb_id', 'knowledge_documents', ['knowledge_base_id'])


def downgrade() -> None:
    # 删除所有表（逆序）
    op.drop_table('knowledge_documents')
    op.drop_table('knowledge_bases')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('contract_risks')
    op.drop_table('contract_clauses')
    op.drop_table('contracts')
    op.drop_table('document_versions')
    op.drop_table('documents')
    op.drop_table('case_events')
    op.drop_table('cases')
    op.drop_table('users')
    op.drop_table('organizations')
    
    # 删除枚举类型
    op.execute('DROP TYPE IF EXISTS knowledgetype')
    op.execute('DROP TYPE IF EXISTS messagerole')
    op.execute('DROP TYPE IF EXISTS risklevel')
    op.execute('DROP TYPE IF EXISTS contractstatus')
    op.execute('DROP TYPE IF EXISTS documenttype')
    op.execute('DROP TYPE IF EXISTS casepriority')
    op.execute('DROP TYPE IF EXISTS casestatus')
    op.execute('DROP TYPE IF EXISTS casetype')
