# -*- coding: utf-8 -*-
"""添加 AI 私有助手相关表（ai_assistant_configs, conversation_summaries, ai_assistant_feedbacks）

Revision ID: 019_ai_assistant
Revises: 018_billing_tables
Create Date: 2026-03-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from migration_utils import safe_create_index, safe_create_table

# revision identifiers, used by Alembic.
revision: str = '019_ai_assistant'
down_revision: Union[str, None] = '018_billing_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===== AI 助手配置表 =====
    safe_create_table(
        'ai_assistant_configs',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False, server_default='安心法务助手', comment='助手名称'),
        sa.Column('description', sa.Text, nullable=True, comment='助手描述'),
        sa.Column('avatar_url', sa.String(500), nullable=True, comment='助手头像'),
        sa.Column('welcome_message', sa.Text, nullable=True,
                  server_default='您好！我是您的专属法务助手，有什么法律问题可以帮您？',
                  comment='欢迎消息'),
        sa.Column('system_prompt', sa.Text, nullable=True, comment='自定义系统提示词'),
        sa.Column('personality', sa.JSON, nullable=True, comment='风格配置 JSON'),
        sa.Column('enabled_agents', sa.JSON, nullable=True, comment='启用的 Agent key 列表'),
        sa.Column('knowledge_base_ids', sa.JSON, nullable=True, comment='关联的知识库 ID 列表'),
        sa.Column('max_context_turns', sa.Integer, nullable=False, server_default='10', comment='保留上下文轮数'),
        sa.Column('temperature', sa.Float, nullable=False, server_default='0.7', comment='LLM 温度'),
        sa.Column('llm_config_id', sa.String(36), nullable=True, comment='指定 LLM 配置 ID'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true'), comment='是否启用'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    safe_create_index('ix_ai_assistant_configs_org_id', 'ai_assistant_configs', ['org_id'])
    safe_create_index('ix_ai_assistant_configs_is_active', 'ai_assistant_configs', ['is_active'])

    # ===== 对话摘要表 =====
    safe_create_table(
        'conversation_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=False),
                  sa.ForeignKey('conversations.id', ondelete='CASCADE'),
                  unique=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('summary', sa.Text, nullable=False, comment='AI 生成的摘要'),
        sa.Column('key_topics', sa.JSON, nullable=True, comment='关键话题'),
        sa.Column('action_items', sa.JSON, nullable=True, comment='待办事项'),
        sa.Column('sentiment', sa.String(20), nullable=True, comment='情感倾向'),
        sa.Column('turn_count', sa.Integer, nullable=False, server_default='0', comment='对话轮次'),
        sa.Column('token_count', sa.Integer, nullable=False, server_default='0', comment='Token 用量'),
        sa.Column('legal_domains', sa.JSON, nullable=True, comment='涉及法律领域'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    safe_create_index('ix_conversation_summaries_user_id', 'conversation_summaries', ['user_id'])
    safe_create_index('ix_conversation_summaries_conversation_id', 'conversation_summaries', ['conversation_id'])

    # ===== AI 助手反馈表 =====
    safe_create_table(
        'ai_assistant_feedbacks',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('assistant_config_id', postgresql.UUID(as_uuid=False),
                  sa.ForeignKey('ai_assistant_configs.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', sa.String(36), nullable=True, comment='对话 ID'),
        sa.Column('message_id', sa.String(36), nullable=True, comment='消息 ID'),
        sa.Column('rating', sa.Integer, nullable=False, comment='评分 1-5'),
        sa.Column('feedback_text', sa.Text, nullable=True, comment='反馈文本'),
        sa.Column('feedback_type', sa.String(30), nullable=False, server_default='helpful',
                  comment='反馈类型: helpful/unhelpful/incorrect/offensive/other'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    safe_create_index('ix_ai_assistant_feedbacks_user_id', 'ai_assistant_feedbacks', ['user_id'])
    safe_create_index('ix_ai_assistant_feedbacks_config_id', 'ai_assistant_feedbacks', ['assistant_config_id'])
    safe_create_index('ix_ai_assistant_feedbacks_conversation_id', 'ai_assistant_feedbacks', ['conversation_id'])


def downgrade() -> None:
    op.drop_table('ai_assistant_feedbacks')
    op.drop_table('conversation_summaries')
    op.drop_table('ai_assistant_configs')
