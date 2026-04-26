# -*- coding: utf-8 -*-
"""
IM 网关 ORM 模型

包含三张表：
    - ``im_gateway_channels``  : IM 通道（飞书 bot / Slack workspace ...）
    - ``im_gateway_bindings``  : 平台用户 ↔ 内部用户绑定
    - ``im_gateway_pairings``  : 配对授权请求（24h 窗口）

为避免与既有 ``models/im.py`` 中的 ``im_conversations / im_participants /
im_messages`` 冲突，本模块独立使用 ``im_gateway_*`` 前缀。
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import GUID, Base, TimestampMixin, ValueEnum


class IMChannelType(str, enum.Enum):
    """IM 通道类型枚举（与 adapter ``channel_type`` 一致）。"""

    FEISHU = "feishu"
    WECHAT = "wechat"
    DINGTALK = "dingtalk"
    TELEGRAM = "telegram"
    SLACK = "slack"
    DISCORD = "discord"  # 预留


class PairingStatus(str, enum.Enum):
    """配对授权状态。"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ----------------------------------------------------------------------
# IMChannel
# ----------------------------------------------------------------------
class IMChannel(Base, TimestampMixin):
    """IM 通道（一个租户/团队接入的某平台 bot 实例）。"""

    __tablename__ = "im_gateway_channels"

    channel_type: Mapped[IMChannelType] = mapped_column(
        ValueEnum(IMChannelType, name="im_gateway_channel_type"),
        nullable=False,
        comment="通道类型",
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="通道展示名（如 '法务团队飞书机器人'）",
    )
    config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="通道配置（app_id/app_secret/webhook_url/...）；敏感字段需加密",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="是否启用",
    )

    __table_args__ = (
        Index("ix_im_gateway_channels_type", "channel_type"),
        Index("ix_im_gateway_channels_enabled", "enabled"),
    )


# ----------------------------------------------------------------------
# IMBinding
# ----------------------------------------------------------------------
class IMBinding(Base, TimestampMixin):
    """平台外部用户 ↔ 内部用户绑定。"""

    __tablename__ = "im_gateway_bindings"

    channel_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("im_gateway_channels.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属通道",
    )
    external_user_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="平台侧用户 ID（飞书 open_id / Slack U.../Telegram chat_id）",
    )
    internal_user_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="安心系统内部用户 ID",
    )
    bound_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="绑定生效时间（通常 = 配对审批通过时刻）",
    )

    __table_args__ = (
        UniqueConstraint(
            "channel_id",
            "external_user_id",
            name="uq_im_gateway_binding_channel_extuser",
        ),
        Index("ix_im_gateway_bindings_internal_user", "internal_user_id"),
    )


# ----------------------------------------------------------------------
# PairingRequest
# ----------------------------------------------------------------------
class PairingRequest(Base, TimestampMixin):
    """配对授权请求。

    用户在 IM 端发送配对码 / 扫码 → 创建 ``PENDING`` 请求 → 内部用户在 App
    审批后变 ``APPROVED`` 并写入 ``IMBinding``。``expires_at`` 默认 24h。
    """

    __tablename__ = "im_gateway_pairings"

    channel_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("im_gateway_channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_user_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="平台侧用户 ID",
    )
    status: Mapped[PairingStatus] = mapped_column(
        ValueEnum(PairingStatus, name="im_gateway_pairing_status"),
        nullable=False,
        default=PairingStatus.PENDING,
        comment="配对状态",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="过期时间（默认 created_at + 24h）",
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="审批通过时间（仅 APPROVED 写入）",
    )

    __table_args__ = (
        Index("ix_im_gateway_pairings_channel_ext", "channel_id", "external_user_id"),
        Index("ix_im_gateway_pairings_status", "status"),
        Index("ix_im_gateway_pairings_expires_at", "expires_at"),
    )
