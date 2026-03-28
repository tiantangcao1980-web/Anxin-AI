"""添加LLM配置表

Revision ID: 002_llm_configs
Revises: 001_initial
Create Date: 2026-01-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_llm_configs'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================== LLM配置表 ====================
    op.create_table(
        'llm_configs',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        
        # 基本信息
        sa.Column('name', sa.String(100), nullable=False, comment='配置名称'),
        sa.Column('provider', sa.String(50), nullable=False, comment='提供商'),
        sa.Column('config_type', sa.String(20), default='llm', comment='配置类型: llm/embedding/reranker'),
        sa.Column('description', sa.Text(), nullable=True, comment='配置描述'),
        
        # API配置
        sa.Column('api_key', sa.String(500), nullable=True, comment='API密钥（加密存储）'),
        sa.Column('api_base_url', sa.String(500), nullable=True, comment='API基础URL'),
        sa.Column('api_version', sa.String(50), nullable=True, comment='API版本'),
        
        # 模型配置
        sa.Column('model_name', sa.String(100), nullable=False, comment='模型名称'),
        sa.Column('model_version', sa.String(50), nullable=True, comment='模型版本'),
        
        # 参数配置
        sa.Column('max_tokens', sa.Integer(), default=4096, comment='最大token数'),
        sa.Column('temperature', sa.Float(), default=0.7, comment='温度参数'),
        sa.Column('top_p', sa.Float(), default=1.0, comment='Top-P采样'),
        sa.Column('top_k', sa.Integer(), nullable=True, comment='Top-K采样'),
        sa.Column('frequency_penalty', sa.Float(), default=0.0, comment='频率惩罚'),
        sa.Column('presence_penalty', sa.Float(), default=0.0, comment='存在惩罚'),
        
        # 本地模型配置
        sa.Column('local_endpoint', sa.String(500), nullable=True, comment='本地服务端点'),
        sa.Column('local_model_path', sa.String(1000), nullable=True, comment='本地模型路径'),
        sa.Column('gpu_layers', sa.Integer(), nullable=True, comment='GPU层数'),
        sa.Column('context_length', sa.Integer(), default=4096, comment='上下文长度'),
        
        # 额外配置
        sa.Column('extra_params', postgresql.JSONB(), default={}, comment='额外参数'),
        sa.Column('headers', postgresql.JSONB(), default={}, comment='自定义请求头'),
        
        # 状态
        sa.Column('is_active', sa.Boolean(), default=True, comment='是否启用'),
        sa.Column('is_default', sa.Boolean(), default=False, comment='是否为默认配置'),
        sa.Column('priority', sa.Integer(), default=0, comment='优先级'),
        
        # 使用统计
        sa.Column('total_calls', sa.Integer(), default=0, comment='总调用次数'),
        sa.Column('total_tokens', sa.Integer(), default=0, comment='总token消耗'),
        sa.Column('avg_latency', sa.Float(), nullable=True, comment='平均延迟(ms)'),
        
        # 组织关联
        sa.Column('org_id', postgresql.UUID(as_uuid=False), nullable=True, comment='组织ID'),
        
        # 时间戳
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # 创建索引
    op.create_index('ix_llm_configs_provider', 'llm_configs', ['provider'])
    op.create_index('ix_llm_configs_config_type', 'llm_configs', ['config_type'])
    op.create_index('ix_llm_configs_is_active', 'llm_configs', ['is_active'])
    op.create_index('ix_llm_configs_is_default', 'llm_configs', ['is_default'])
    op.create_index('ix_llm_configs_org_id', 'llm_configs', ['org_id'])


def downgrade() -> None:
    # 删除表
    op.drop_table('llm_configs')
