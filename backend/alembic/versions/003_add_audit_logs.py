"""添加审计日志表

Revision ID: 003_add_audit_logs
Revises: 002_add_llm_configs
Create Date: 2026-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_add_audit_logs'
down_revision: Union[str, None] = '002_llm_configs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建审计日志表
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        
        # 操作信息
        sa.Column('action', sa.String(100), nullable=False, index=True, comment='操作类型'),
        
        # 资源信息
        sa.Column('resource_type', sa.String(50), nullable=False, index=True, comment='资源类型'),
        sa.Column('resource_id', sa.String(100), nullable=True, index=True, comment='资源ID'),
        
        # 操作者信息
        sa.Column('user_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='SET NULL'), 
                  nullable=True, index=True, comment='操作用户ID'),
        sa.Column('user_email', sa.String(255), nullable=True, comment='操作用户邮箱'),
        sa.Column('user_role', sa.String(50), nullable=True, comment='操作时的用户角色'),
        
        # 变更内容
        sa.Column('old_value', postgresql.JSONB, nullable=True, comment='变更前的值'),
        sa.Column('new_value', postgresql.JSONB, nullable=True, comment='变更后的值'),
        
        # 请求信息
        sa.Column('ip_address', sa.String(45), nullable=True, comment='客户端IP地址'),
        sa.Column('user_agent', sa.String(500), nullable=True, comment='用户代理'),
        sa.Column('request_id', sa.String(100), nullable=True, comment='请求ID'),
        
        # 操作结果
        sa.Column('status', sa.String(20), default='success', comment='操作状态'),
        sa.Column('error_message', sa.Text, nullable=True, comment='错误信息'),
        
        # 附加信息
        sa.Column('extra_data', postgresql.JSONB, nullable=True, comment='额外数据'),
        
        # 时间戳
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now(), nullable=False, index=True, 
                  comment='创建时间'),
    )
    
    # 创建复合索引
    op.create_index('ix_audit_user_action', 'audit_logs', ['user_id', 'action'])
    op.create_index('ix_audit_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('ix_audit_created_at_action', 'audit_logs', ['created_at', 'action'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_audit_created_at_action', table_name='audit_logs')
    op.drop_index('ix_audit_resource', table_name='audit_logs')
    op.drop_index('ix_audit_user_action', table_name='audit_logs')
    
    # 删除表
    op.drop_table('audit_logs')
