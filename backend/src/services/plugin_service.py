# -*- coding: utf-8 -*-
"""
Plugin 服务层 —— D-2 插件注册后端

职责：list / get / create / toggle 真实落库，按 org 隔离。

数据来源融合（list 时）：
    1. registry 条目：source='official' / 'private' —— 存于 ``plugins`` 表，
       按 org 隔离。
    2. mcp 投影：source='mcp' —— 由既有 ``McpServerConfig``
       （mcp_server_configs）投影而来，单一事实源仍是 McpServerConfig，
       本服务不在 plugins 表里复制 MCP 数据（避免双写）。

mcp 投影插件的 id 统一加 ``mcp:`` 前缀（如 ``mcp:<server_id>``），
使 toggle 能据 id 前缀路由到对应处理：
    - ``mcp:`` 前缀  → 改写 McpServerConfig.is_enabled
    - 其余（裸 UUID） → 改写 Plugin.status

MVP 范围：
    - toggle 只在 enabled / disabled 间切换（契约 toggle(id, enabled)）。
    - pending_review = 审核态占位字段；完整审核工作流（提交→审核→放行的
      流转/审计/通知）= P-later，本服务不实现流转。toggle 一个
      pending_review 的 registry 插件会按 enabled 入参直接落到
      enabled/disabled（即「审核放行」的简化等价），注释说明不假装走审核流。
    - 插件「实际运行」（official 数据源真调用 / private webhook 真触发 /
      mcp server 真连接）= P-later，本服务只管理注册元数据。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.schemas.plugin import PluginOut
from src.models.mcp_config import McpServerConfig
from src.models.plugin import Plugin

# mcp 投影插件 id 前缀
MCP_ID_PREFIX = "mcp:"


class PluginError(Exception):
    """业务异常基类。"""


class PluginNotFoundError(PluginError):
    """插件不存在（或不属于当前 org）。"""


def _mcp_to_plugin_out(server: McpServerConfig) -> PluginOut:
    """把一条 McpServerConfig 投影为 source='mcp' 的 PluginOut。"""
    return PluginOut(
        id=f"{MCP_ID_PREFIX}{server.id}",
        name=server.name,
        display_name=server.name,
        source="mcp",
        status="enabled" if server.is_enabled else "disabled",
        description=server.description or "",
        publisher="MCP",
        icon=None,
    )


class PluginService:
    """插件管理服务（registry + mcp 投影，按 org 隔离）。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------ list
    async def list_for_org(self, org_id: str | None) -> list[PluginOut]:
        """返回 registry（official/private）+ mcp 投影 的合并列表。

        MCP server 当前为全局配置（McpServerConfig 无 org 维度），对所有
        org 可见；registry 条目按 org 隔离。
        """
        # registry 条目（本 org）
        stmt = (
            select(Plugin)
            .where(Plugin.org_id == org_id)
            .order_by(Plugin.created_at.asc())
        )
        registry_rows = list((await self.db.execute(stmt)).scalars().all())
        out: list[PluginOut] = [PluginOut.model_validate(p) for p in registry_rows]

        # mcp 投影（全局 McpServerConfig）
        mcp_rows = list(
            (await self.db.execute(select(McpServerConfig))).scalars().all()
        )
        out.extend(_mcp_to_plugin_out(s) for s in mcp_rows)
        return out

    # ---------------------------------------------------------------- create
    async def create(
        self,
        *,
        org_id: str | None,
        created_by: str | None,
        name: str,
        display_name: str,
        source: str,
        description: str = "",
        publisher: str = "",
        icon: str | None = None,
        status: str = "disabled",
    ) -> PluginOut:
        """创建一条 registry 插件（official / private）。

        source='mcp' 不走此处 —— 由 /mcp/servers 管理，详见模块 docstring。
        """
        plugin = Plugin(
            org_id=org_id,
            created_by=created_by,
            name=name,
            display_name=display_name,
            source=source,
            description=description,
            publisher=publisher,
            icon=icon,
            status=status,
        )
        self.db.add(plugin)
        await self.db.flush()
        await self.db.refresh(plugin)
        return PluginOut.model_validate(plugin)

    # ---------------------------------------------------------------- toggle
    async def toggle(
        self, plugin_id: str, org_id: str | None, enabled: bool
    ) -> PluginOut:
        """按 id 前缀路由 toggle。

        - ``mcp:<server_id>`` → 改写 McpServerConfig.is_enabled
        - 裸 id              → 改写 Plugin.status（registry）

        pending_review 的 registry 插件被 toggle 时，直接按 enabled 落到
        enabled/disabled（审核工作流 = P-later，不在此处流转）。
        """
        if plugin_id.startswith(MCP_ID_PREFIX):
            return await self._toggle_mcp(plugin_id, enabled)
        return await self._toggle_registry(plugin_id, org_id, enabled)

    async def _toggle_mcp(self, plugin_id: str, enabled: bool) -> PluginOut:
        server_id = plugin_id[len(MCP_ID_PREFIX):]
        server = await self.db.get(McpServerConfig, server_id)
        if server is None:
            raise PluginNotFoundError(plugin_id)
        server.is_enabled = enabled
        await self.db.flush()
        await self.db.refresh(server)
        return _mcp_to_plugin_out(server)

    async def _toggle_registry(
        self, plugin_id: str, org_id: str | None, enabled: bool
    ) -> PluginOut:
        stmt = select(Plugin).where(
            Plugin.id == plugin_id,
            Plugin.org_id == org_id,
        )
        plugin = (await self.db.execute(stmt)).scalar_one_or_none()
        if plugin is None:
            raise PluginNotFoundError(plugin_id)
        plugin.status = "enabled" if enabled else "disabled"
        await self.db.flush()
        await self.db.refresh(plugin)
        return PluginOut.model_validate(plugin)
