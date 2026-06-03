# -*- coding: utf-8 -*-
"""plugins 路由 Pydantic schemas（请求 / 响应 DTO）。

契约对齐 mobile/src/lib/api/__mocks__/capabilities.mock.ts 的 Plugin：
    { id, name, display_name, source, status, description, publisher, icon? }

pluginsApi：list() -> Plugin[]、toggle(id, enabled) -> Plugin。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# 与前端 PluginSource / PluginStatus 对齐
PluginSource = Literal["official", "private", "mcp"]
PluginStatus = Literal["enabled", "disabled", "pending_review"]


class PluginOut(BaseModel):
    """单个插件 DTO（字段名 1:1 对齐前端契约）。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    display_name: str
    source: str
    status: str
    description: str
    publisher: str
    icon: str | None = None


class PluginCreate(BaseModel):
    """POST 创建 registry 插件请求体（仅 official / private）。

    source='mcp' 的插件由 MCP server 投影，不经本端点创建 —— 请走
    ``/api/v1/mcp/servers``。
    """

    name: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=255)
    source: Literal["official", "private"]
    description: str = Field(default="", max_length=1024)
    publisher: str = Field(default="", max_length=255)
    icon: str | None = Field(default=None, max_length=512)
    # 创建时初始状态；private 插件可置 pending_review 走（占位）审核态
    status: PluginStatus = "disabled"


class TogglePluginBody(BaseModel):
    """PUT /{id}/toggle 请求体。

    契约：toggle(id, enabled) —— enabled=True → 'enabled'，False → 'disabled'。
    """

    enabled: bool
