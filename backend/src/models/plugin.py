# -*- coding: utf-8 -*-
"""
Plugin 模型 —— D-2 插件注册后端

契约以 mobile/src/lib/api/__mocks__/capabilities.mock.ts 的 Plugin 为准：
    { id, name, display_name, source, status, description, publisher, icon? }

source：'official' | 'private' | 'mcp'
status：'enabled' | 'disabled' | 'pending_review'

本表只存 **registry 条目**（source='official' / 'private'）的管理元数据。

source='mcp' 的插件 **不入本表**：由服务层把既有 ``McpServerConfig``
（mcp_server_configs 表，见 models/mcp_config.py 与 routes/mcp_routes.py）
投影为 source='mcp' 的 Plugin —— MCP server 即 mcp 来源插件，单一事实源
仍是 McpServerConfig，避免数据双写。投影详见
``services/plugin_service.py``。

status='pending_review'（审核态）：
    仅作为「状态字段」保留，用于 private 插件提交后待审核的展示。
    完整审核工作流（提交→审核人→放行/驳回的流转、审计、通知）= MVP 不做，
    标为 P-later（同 IM 协议握手 / cron 实际执行）。当前 toggle 只在
    enabled / disabled 间切换；pending_review 由创建时或后台直接置位，
    本表不含审核流转字段。
"""

from datetime import datetime

# 全库约定：JSON 列用通用 JSON（Postgres 落 JSONB，SQLite 落 JSON），禁 PG 专属 JSONB
from sqlalchemy import JSON as JSONB
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import GUID, Base


class Plugin(Base):
    """插件注册表条目（official / private 来源）。

    source='mcp' 不落本表，由服务层从 McpServerConfig 投影。
    """

    __tablename__ = "plugins"

    # 机器名（org 内唯一），如 'beidafabao' / 'private-erp'
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    display_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    source: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        index=True,
        comment="official|private（mcp 来源由 McpServerConfig 投影，不入本表）",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="disabled",
        index=True,
        comment="enabled|disabled|pending_review",
    )

    description: Mapped[str] = mapped_column(String(1024), nullable=False, default="")

    publisher: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    # 可选图标（URL 或图标名），对齐前端契约的 icon?
    icon: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # 自由扩展（接入配置、审核备注等），保持向后兼容
    config: Mapped[dict[str, "object"]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # --- 多租户隔离 ---
    org_id: Mapped[str | None] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_by: Mapped[str | None] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # --- 审计时间戳 ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.utcnow(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.utcnow(),
    )

    __table_args__ = (
        # 同 org 内机器名唯一（org_id 为 NULL 时不约束，留给全局/系统级条目）
        UniqueConstraint("org_id", "name", name="uq_plugins_org_name"),
        Index("ix_plugins_org_source", "org_id", "source"),
    )

    def __repr__(self) -> str:
        return (
            f"<Plugin id={self.id} name={self.name!r} "
            f"source={self.source} status={self.status}>"
        )
