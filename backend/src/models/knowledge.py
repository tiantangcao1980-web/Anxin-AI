"""
知识库模型
"""

from typing import Optional
from sqlalchemy import String, Text, ForeignKey, Integer, Enum as SQLEnum, Boolean
from sqlalchemy import JSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.models.base import Base, TimestampMixin, GUID


class KnowledgeType(str, enum.Enum):
    """知识类型"""
    LAW = "law"  # 法律法规
    REGULATION = "regulation"  # 部门规章
    CASE = "case"  # 司法判例
    INTERPRETATION = "interpretation"  # 司法解释
    TEMPLATE = "template"  # 合同模板
    ARTICLE = "article"  # 法律文章
    INTERNAL = "internal"  # 内部知识
    COMPLIANCE = "compliance"  # 合规文件、行业标准
    LETTER = "letter"  # 律师函、法律意见书模板
    LITIGATION = "litigation"  # 诉讼文书（起诉状、答辩状等）
    POLICY = "policy"  # 政策文件
    OTHER = "other"


class KnowledgeBase(Base, TimestampMixin):
    """知识库"""
    
    __tablename__ = "knowledge_bases"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    knowledge_type: Mapped[KnowledgeType] = mapped_column(
        # values_callable 强制 SQLAlchemy 使用枚举的 value（小写）作为 DB 存储值，
        # 与 Alembic migration 创建的 PostgreSQL ENUM type 保持一致。
        # 不指定时 SQLAlchemy 2.x 默认用枚举 name（大写），会导致
        # "'law' is not among the defined enum values" 错误。
        SQLEnum(KnowledgeType, values_callable=lambda x: [e.value for e in x]),
        default=KnowledgeType.OTHER,
    )
    
    # 统计信息
    doc_count: Mapped[int] = mapped_column(Integer, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    
    # 向量存储信息
    vector_collection: Mapped[Optional[str]] = mapped_column(String(100))
    embedding_model: Mapped[str] = mapped_column(
        String(100), default="text-embedding-3-large"
    )
    embedding_dimensions: Mapped[int] = mapped_column(Integer, default=3072)
    
    # 配置
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # 外键
    org_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE")
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # 关系
    documents: Mapped[list["KnowledgeDocument"]] = relationship(
        "KnowledgeDocument", back_populates="knowledge_base", cascade="all, delete-orphan"
    )


class KnowledgeDocument(Base, TimestampMixin):
    """知识库文档"""
    
    __tablename__ = "knowledge_documents"
    
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(255))  # 来源
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # 内容
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    
    # 处理状态
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # 元数据
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    tags: Mapped[Optional[list]] = mapped_column(JSONB)
    
    # 法律相关字段
    law_category: Mapped[Optional[str]] = mapped_column(String(100))  # 法律类别
    effective_date: Mapped[Optional[str]] = mapped_column(String(50))  # 生效日期
    issuing_authority: Mapped[Optional[str]] = mapped_column(String(255))  # 发布机关

    # 数据采集与版本管理
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255), index=True
    )  # 外部稳定ID，用于幂等导入
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))  # SHA256 内容哈希
    version: Mapped[int] = mapped_column(Integer, default=1)  # 文档版本号
    status: Mapped[str] = mapped_column(
        String(20), default="active"
    )  # active / superseded

    # 外键
    knowledge_base_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False
    )
    
    # 关系
    knowledge_base: Mapped["KnowledgeBase"] = relationship(
        "KnowledgeBase", back_populates="documents"
    )
