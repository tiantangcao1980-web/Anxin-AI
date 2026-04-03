# -*- coding: utf-8 -*-
"""扩展知识库：新增知识类型 + 文档版本管理字段

- KnowledgeType 枚举新增: compliance, letter, litigation, policy
- KnowledgeDocument 新增: external_id, content_hash, version, status

Revision ID: 026_add_legal_collection_support
Revises: 025_fix_feedback_conversation_fk
Create Date: 2026-04-03

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "026_add_legal_collection_support"
down_revision: Union[str, None] = "025_fix_feedback_conversation_fk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# PostgreSQL ALTER TYPE ... ADD VALUE 不能在事务块内执行，
# 需要 AUTOCOMMIT 模式。
NEW_ENUM_VALUES = ["compliance", "letter", "litigation", "policy"]


def upgrade() -> None:
    # ------ 1. 扩展 knowledgetype 枚举 ------
    # 必须在 AUTOCOMMIT 下逐个添加
    conn = op.get_bind()
    for val in NEW_ENUM_VALUES:
        conn.execute(
            sa.text(
                f"ALTER TYPE knowledgetype ADD VALUE IF NOT EXISTS '{val}'"
            )
        )

    # ------ 2. KnowledgeDocument 新增字段 ------
    op.add_column(
        "knowledge_documents",
        sa.Column("external_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "knowledge_documents",
        sa.Column("content_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "knowledge_documents",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "knowledge_documents",
        sa.Column(
            "status", sa.String(20), server_default="active", nullable=False
        ),
    )

    # 索引：加速幂等导入时按 external_id 查找
    op.create_index(
        "ix_knowledge_documents_external_id",
        "knowledge_documents",
        ["external_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_knowledge_documents_external_id",
        table_name="knowledge_documents",
    )
    op.drop_column("knowledge_documents", "status")
    op.drop_column("knowledge_documents", "version")
    op.drop_column("knowledge_documents", "content_hash")
    op.drop_column("knowledge_documents", "external_id")
    # 注意：PostgreSQL 不支持 ALTER TYPE ... REMOVE VALUE，
    # 降级时枚举值无法自动移除，需手动处理。
