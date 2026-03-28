"""
协作编辑数据模型
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, DateTime, Boolean, Enum as SQLEnum, Integer
from sqlalchemy import JSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.models.base import Base, TimestampMixin, GUID

if TYPE_CHECKING:
    from src.models.user import User
    from src.models.document import Document


class SessionStatus(str, enum.Enum):
    """协作会话状态"""
    ACTIVE = "active"          # 活跃
    PAUSED = "paused"          # 暂停
    CLOSED = "closed"          # 已关闭


class CollaboratorRole(str, enum.Enum):
    """协作角色"""
    OWNER = "owner"            # 所有者
    EDITOR = "editor"          # 编辑者
    VIEWER = "viewer"          # 查看者
    COMMENTER = "commenter"    # 评论者


class EditOperation(str, enum.Enum):
    """编辑操作类型"""
    INSERT = "insert"          # 插入
    DELETE = "delete"          # 删除
    REPLACE = "replace"        # 替换
    FORMAT = "format"          # 格式化
    COMMENT = "comment"        # 评论
    CURSOR = "cursor"          # 光标移动


class DocumentSession(Base, TimestampMixin):
    """文档协作会话模型"""
    
    __tablename__ = "document_sessions"
    
    # 基本信息
    name: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[SessionStatus] = mapped_column(
        SQLEnum(SessionStatus), default=SessionStatus.ACTIVE
    )
    
    # 会话配置
    max_collaborators: Mapped[int] = mapped_column(Integer, default=10)
    allow_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    require_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 版本控制
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    base_content: Mapped[Optional[str]] = mapped_column(Text)  # 基础内容快照
    current_content: Mapped[Optional[str]] = mapped_column(Text)  # 当前内容
    
    # 时间节点
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    
    # 统计
    total_edits: Mapped[int] = mapped_column(Integer, default=0)
    active_collaborators: Mapped[int] = mapped_column(Integer, default=0)
    
    # 元数据
    settings: Mapped[Optional[dict]] = mapped_column(JSONB)  # 会话设置
    
    # 外键
    document_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # 关系
    document: Mapped["Document"] = relationship("Document", back_populates="sessions")
    creator: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[created_by]
    )
    collaborators: Mapped[list["DocumentCollaborator"]] = relationship(
        "DocumentCollaborator", back_populates="session", cascade="all, delete-orphan"
    )
    edits: Mapped[list["DocumentEdit"]] = relationship(
        "DocumentEdit", back_populates="session", cascade="all, delete-orphan"
    )


class DocumentCollaborator(Base, TimestampMixin):
    """文档协作者模型"""
    
    __tablename__ = "document_collaborators"
    
    # 协作者信息
    role: Mapped[CollaboratorRole] = mapped_column(
        SQLEnum(CollaboratorRole), default=CollaboratorRole.EDITOR
    )
    nickname: Mapped[Optional[str]] = mapped_column(String(50))
    color: Mapped[Optional[str]] = mapped_column(String(20))  # 用户标识颜色
    
    # 状态
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 光标位置
    cursor_position: Mapped[Optional[dict]] = mapped_column(JSONB)  # {line, column, selection}
    
    # 时间
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    left_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # 统计
    edit_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # 外键
    session_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("document_sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # 关系
    session: Mapped["DocumentSession"] = relationship(
        "DocumentSession", back_populates="collaborators"
    )
    user: Mapped[Optional["User"]] = relationship("User")
    edits: Mapped[list["DocumentEdit"]] = relationship(
        "DocumentEdit", back_populates="collaborator"
    )


class DocumentEdit(Base, TimestampMixin):
    """文档编辑记录模型"""
    
    __tablename__ = "document_edits"
    
    # 编辑信息
    operation: Mapped[EditOperation] = mapped_column(
        SQLEnum(EditOperation), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 编辑内容
    position: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {start, end, line, column}
    content: Mapped[Optional[str]] = mapped_column(Text)  # 插入/替换的内容
    old_content: Mapped[Optional[str]] = mapped_column(Text)  # 被删除/替换的内容
    
    # 格式化信息（如果是格式化操作）
    format_type: Mapped[Optional[str]] = mapped_column(String(50))
    format_value: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # 操作时间戳（精确到毫秒）
    operation_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    
    # 是否已同步
    is_synced: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 外键
    session_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("document_sessions.id", ondelete="CASCADE"), nullable=False
    )
    collaborator_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("document_collaborators.id", ondelete="SET NULL")
    )
    
    # 关系
    session: Mapped["DocumentSession"] = relationship(
        "DocumentSession", back_populates="edits"
    )
    collaborator: Mapped[Optional["DocumentCollaborator"]] = relationship(
        "DocumentCollaborator", back_populates="edits"
    )
