# -*- coding: utf-8 -*-
"""im_channels 路由 Pydantic schemas（P3-C 渠道管理后端）。

与前端 contract 严格对齐：
  - frontend/src/lib/api/imChannels.ts
  - mobile/src/lib/api/imChannels.ts
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.services.im_gateway.models import IMChannel, IMChannelStatus, IMChannelType

# ---------------------------------------------------------------------------
# 请求体
# ---------------------------------------------------------------------------


class SetupChannelRequest(BaseModel):
    """POST /im/channels/{channelType}/setup 请求体。"""

    config: dict[str, Any] = Field(
        default_factory=dict,
        description="渠道配置（app_id/app_secret/bot_token/...）",
    )


class BindAgentRequest(BaseModel):
    """PUT /im/channels/{id}/agent 请求体。"""

    agent_persona: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="要绑定的 agent persona key",
    )


# ---------------------------------------------------------------------------
# 响应体
# ---------------------------------------------------------------------------


class IMChannelStatsOut(BaseModel):
    """渠道统计计数（从绑定/配对真实聚合）。"""

    bound_users: int = 0
    bound_groups: int = 0
    pending_pairings: int = 0


class IMChannelOut(BaseModel):
    """渠道详情 DTO，字段顺序/命名对齐前端 ``IMChannel`` 接口。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    channel_type: IMChannelType
    name: str
    config: dict[str, Any]
    enabled: bool
    status: IMChannelStatus
    bound_agent_persona: str | None = None
    stats: IMChannelStatsOut
    created_at: datetime

    @classmethod
    def from_orm_with_stats(
        cls,
        channel: IMChannel,
        stats: dict[str, int],
    ) -> IMChannelOut:
        """从 ORM 行 + 单独聚合的 stats 组装 DTO。"""
        return cls(
            id=str(channel.id),
            channel_type=channel.channel_type,
            name=channel.name,
            config=channel.config or {},
            enabled=channel.enabled,
            status=channel.status,
            bound_agent_persona=channel.bound_agent_persona,
            stats=IMChannelStatsOut(**stats),
            created_at=channel.created_at,
        )


class TestConnectionResult(BaseModel):
    """GET /im/channels/{id}/test 响应（对齐前端 ``TestConnectionResult``）。"""

    ok: bool
    message: str | None = None
    detail: dict[str, Any] | None = None
