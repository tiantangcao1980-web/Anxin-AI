"""
应用授权 ORM 模型（P4-A）

两张表：
    - ``app_authorizations`` : 一条授权记录（user × provider）
    - ``app_tokens``         : 该授权对应的加密 token（access + refresh）

设计取舍
--------
- token 与授权拆表，便于 key rotation 时只迁移 ``app_tokens`` 行；
- token 字段存 ``LargeBinary``，由 ``token_store.TokenStore`` 用 Fernet 加密；
- 状态枚举字符串化（小写），与 PostgreSQL 创建的 enum 保持一致。
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import GUID, Base, TimestampMixin, ValueEnum


class AppAuthorizationStatus(str, enum.Enum):
    """授权状态枚举。"""

    CONNECTED = "connected"  # 正常连接中
    EXPIRED = "expired"  # token 过期且 refresh 失败
    REVOKED = "revoked"  # 用户主动 disconnect
    ERROR = "error"  # 平台报错（如 invalid_grant）


# ----------------------------------------------------------------------
# AppAuthorization
# ----------------------------------------------------------------------
class AppAuthorization(Base, TimestampMixin):
    """一条第三方应用授权（user × provider 唯一）。"""

    __tablename__ = "app_authorizations"

    user_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="授权所属内部用户",
    )
    provider_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="provider 唯一标识（feishu / dingtalk / notion / shopify ...）",
    )
    status: Mapped[AppAuthorizationStatus] = mapped_column(
        ValueEnum(
            AppAuthorizationStatus,
            name="app_authorization_status",
        ),
        nullable=False,
        default=AppAuthorizationStatus.CONNECTED,
        comment="授权状态",
    )
    scopes: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="实际授予的 scope 列表（JSON 数组）",
    )
    connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="首次成功授权时间",
    )
    last_refresh_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最近一次 refresh_token 成功时间",
    )
    error_message: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="最近一次错误描述（status=error 时填）",
    )

    # 关联 token（一对一；删 authorization 自动删 token）
    token: Mapped[AppToken | None] = relationship(
        "AppToken",
        back_populates="authorization",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index(
            "ix_app_authorizations_user_provider_status",
            "user_id",
            "provider_id",
            "status",
        ),
        Index("ix_app_authorizations_provider", "provider_id"),
    )

    def to_safe_dict(self) -> dict[str, Any]:
        """序列化用于 API 响应（不含 token）。"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "provider_id": self.provider_id,
            "status": (
                self.status.value
                if isinstance(self.status, AppAuthorizationStatus)
                else self.status
            ),
            "scopes": self.scopes or [],
            "connected_at": self.connected_at,
            "last_refresh_at": self.last_refresh_at,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ----------------------------------------------------------------------
# AppToken
# ----------------------------------------------------------------------
class AppToken(Base, TimestampMixin):
    """加密存储的 token 记录（一对一关联 AppAuthorization）。"""

    __tablename__ = "app_tokens"

    authorization_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("app_authorizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="所属授权记录（一对一）",
    )
    encrypted_access_token: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
        comment="Fernet 加密后的 access_token",
    )
    encrypted_refresh_token: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
        comment="Fernet 加密后的 refresh_token（部分 provider 无）",
    )
    token_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="Bearer",
        comment="token 类型，通常 Bearer",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="access_token 过期时间（UTC）；None 表示长期有效",
    )

    authorization: Mapped[AppAuthorization] = relationship(
        "AppAuthorization",
        back_populates="token",
    )

    __table_args__ = (Index("ix_app_tokens_expires_at", "expires_at"),)
