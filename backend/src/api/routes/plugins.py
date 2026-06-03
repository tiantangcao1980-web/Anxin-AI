# -*- coding: utf-8 -*-
"""
plugins 路由 —— D-2 插件注册后端

挂载点（在 ``api/routes/__init__.py`` 以 ``prefix="/plugins"`` 注册）::

    GET    /api/v1/plugins              -> Plugin[]
    POST   /api/v1/plugins              -> Plugin（创建 registry 插件）
    PUT    /api/v1/plugins/{id}/toggle  body {enabled} -> Plugin

权限：均需登录；registry 数据按 user.org_id 隔离（多租户）。
mcp 来源插件由 McpServerConfig 投影，详见 services/plugin_service.py。

MVP 范围：仅「管理 API」真实落库。pending_review 审核工作流 / 插件实际运行
= P-later（同 IM 协议握手 / cron 实际执行），详见 service 与 model 注释。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.schemas.plugin import (
    PluginCreate,
    PluginOut,
    TogglePluginBody,
)
from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.models.user import User
from src.services.plugin_service import (
    PluginNotFoundError,
    PluginService,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# GET / — 当前 org 的插件列表（registry + mcp 投影）
# ---------------------------------------------------------------------------


@router.get("", response_model=list[PluginOut])
async def list_plugins(
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> list[PluginOut]:
    """当前用户所属 org 的 registry 插件 + 全局 mcp 投影插件。"""
    service = PluginService(db)
    return await service.list_for_org(user.org_id)


# ---------------------------------------------------------------------------
# POST / — 创建 registry 插件（official / private）
# ---------------------------------------------------------------------------


@router.post("", response_model=PluginOut, status_code=status.HTTP_201_CREATED)
async def create_plugin(
    body: PluginCreate,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> PluginOut:
    """创建 registry 插件（source 限 official / private；mcp 走 /mcp/servers）。"""
    service = PluginService(db)
    return await service.create(
        org_id=user.org_id,
        created_by=str(user.id),
        name=body.name,
        display_name=body.display_name,
        source=body.source,
        description=body.description,
        publisher=body.publisher,
        icon=body.icon,
        status=body.status,
    )


# ---------------------------------------------------------------------------
# PUT /{id}/toggle — 启用 / 停用
# ---------------------------------------------------------------------------


@router.put("/{plugin_id}/toggle", response_model=PluginOut)
async def toggle_plugin(
    plugin_id: str,
    body: TogglePluginBody,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> PluginOut:
    """enabled=True → 'enabled'，False → 'disabled'。

    id 带 ``mcp:`` 前缀时改写底层 MCP server；否则改写 registry 插件状态。
    """
    service = PluginService(db)
    try:
        return await service.toggle(plugin_id, user.org_id, body.enabled)
    except PluginNotFoundError as e:
        raise HTTPException(status_code=404, detail="插件不存在") from e
