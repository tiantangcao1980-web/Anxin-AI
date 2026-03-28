"""
审计日志模型
记录用户的所有敏感操作
"""

from datetime import datetime
from typing import Optional, Any
from enum import Enum

from sqlalchemy import String, Text, ForeignKey, DateTime, Enum as SQLEnum, Index
from sqlalchemy import JSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, GUID


class AuditAction(str, Enum):
    """审计操作类型"""
    # 用户相关
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_REGISTER = "user.register"
    USER_PASSWORD_CHANGE = "user.password_change"
    USER_PROFILE_UPDATE = "user.profile_update"
    
    # 案件相关
    CASE_CREATE = "case.create"
    CASE_UPDATE = "case.update"
    CASE_DELETE = "case.delete"
    CASE_VIEW = "case.view"
    CASE_ASSIGN = "case.assign"
    CASE_STATUS_CHANGE = "case.status_change"
    
    # 文档相关
    DOCUMENT_UPLOAD = "document.upload"
    DOCUMENT_DOWNLOAD = "document.download"
    DOCUMENT_DELETE = "document.delete"
    DOCUMENT_VIEW = "document.view"
    
    # 合同相关
    CONTRACT_CREATE = "contract.create"
    CONTRACT_REVIEW = "contract.review"
    CONTRACT_SIGN = "contract.sign"
    CONTRACT_DELETE = "contract.delete"
    
    # 权限相关
    PERMISSION_GRANT = "permission.grant"
    PERMISSION_REVOKE = "permission.revoke"
    ROLE_CHANGE = "role.change"
    
    # Token相关
    TOKEN_REFRESH = "token.refresh"
    TOKEN_REVOKE = "token.revoke"
    
    # 系统相关
    CONFIG_CHANGE = "config.change"
    API_ACCESS = "api.access"
    EXPORT_DATA = "export.data"
    
    # 搜索相关
    SEARCH_QUERY = "search.query"
    
    # 对话相关
    CHAT_CREATE = "chat.create"
    CHAT_MESSAGE = "chat.message"


class ResourceType(str, Enum):
    """资源类型"""
    USER = "user"
    ORGANIZATION = "organization"
    CASE = "case"
    DOCUMENT = "document"
    CONTRACT = "contract"
    CONVERSATION = "conversation"
    MESSAGE = "message"
    KNOWLEDGE = "knowledge"
    PERMISSION = "permission"
    TOKEN = "token"
    CONFIG = "config"
    SEARCH = "search"


class AuditLog(Base):
    """审计日志模型"""
    
    __tablename__ = "audit_logs"
    
    # 操作信息
    action: Mapped[str] = mapped_column(
        String(100), 
        nullable=False,
        index=True,
        comment="操作类型"
    )
    
    # 资源信息
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="资源类型"
    )
    resource_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="资源ID"
    )
    
    # 操作者信息
    user_id: Mapped[Optional[str]] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="操作用户ID"
    )
    user_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="操作用户邮箱"
    )
    user_role: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="操作时的用户角色"
    )
    
    # 变更内容
    old_value: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="变更前的值"
    )
    new_value: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="变更后的值"
    )
    
    # 请求信息
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        comment="客户端IP地址"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="用户代理"
    )
    request_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="请求ID"
    )
    
    # 操作结果
    status: Mapped[str] = mapped_column(
        String(20),
        default="success",
        comment="操作状态：success/failed"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息"
    )
    
    # 附加信息
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="额外数据"
    )
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
        comment="创建时间"
    )
    
    # 复合索引，优化常见查询
    __table_args__ = (
        Index('ix_audit_user_action', 'user_id', 'action'),
        Index('ix_audit_resource', 'resource_type', 'resource_id'),
        Index('ix_audit_created_at_action', 'created_at', 'action'),
    )
    
    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by {self.user_email} at {self.created_at}>"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "user_role": self.user_role,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "status": self.status,
            "error_message": self.error_message,
            "extra_data": self.extra_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
