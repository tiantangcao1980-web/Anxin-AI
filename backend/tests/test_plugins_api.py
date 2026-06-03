# -*- coding: utf-8 -*-
"""
plugins 路由 API 测试（D-2）

覆盖：
    - GET    /api/v1/plugins              list（含创建后回读、字段契约）
    - POST   /api/v1/plugins              create（official / private）
    - PUT    /api/v1/plugins/{id}/toggle  toggle（registry + mcp 投影）
    - 鉴权：未登录 401/403
    - org 隔离：A org 看不到 / 不能 toggle B org 的 registry 插件
    - mcp 投影：McpServerConfig 以 source='mcp' 出现在 list，toggle 改写
      底层 is_enabled
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.mcp_config import McpServerConfig
from src.models.plugin import Plugin
from src.models.user import Organization

BASE = "/api/v1/plugins"


# ---------------------------------------------------------------------------
# Fixtures：第二个 org + 该 org 的 registry 插件（用于隔离测试）
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def other_org(db_session: AsyncSession) -> Organization:
    org = Organization(id=str(uuid4()), name="另一家公司")
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def other_org_plugin(
    db_session: AsyncSession, other_org: Organization
) -> Plugin:
    plugin = Plugin(
        id=str(uuid4()),
        org_id=other_org.id,
        name="other-private",
        display_name="他 org 的私有插件",
        source="private",
        status="enabled",
        description="不应被本 org 看到",
        publisher="他研发部",
    )
    db_session.add(plugin)
    await db_session.flush()
    return plugin


@pytest_asyncio.fixture
async def mcp_server(db_session: AsyncSession) -> McpServerConfig:
    server = McpServerConfig(
        id=str(uuid4()),
        name="mcp-filesystem",
        description="本地文件系统访问",
        type="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem"],
        env={},
        is_enabled=True,
    )
    db_session.add(server)
    await db_session.flush()
    return server


# ---------------------------------------------------------------------------
# 鉴权
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(BASE)
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# create + list（registry）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_then_list(auth_client: AsyncClient) -> None:
    create = await auth_client.post(
        BASE,
        json={
            "name": "beidafabao",
            "display_name": "北大法宝",
            "source": "official",
            "description": "法规与案例数据库",
            "publisher": "北大英华",
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    # 契约字段齐全
    for key in (
        "id",
        "name",
        "display_name",
        "source",
        "status",
        "description",
        "publisher",
        "icon",
    ):
        assert key in body
    assert body["source"] == "official"
    assert body["status"] == "disabled"  # 默认初始
    assert body["display_name"] == "北大法宝"

    listed = await auth_client.get(BASE)
    assert listed.status_code == 200
    items = listed.json()
    assert isinstance(items, list)
    assert any(it["id"] == body["id"] for it in items)


@pytest.mark.asyncio
async def test_create_private_pending_review(auth_client: AsyncClient) -> None:
    """private 插件可创建为 pending_review（审核态占位字段）。"""
    create = await auth_client.post(
        BASE,
        json={
            "name": "private-erp",
            "display_name": "内部 ERP 接入",
            "source": "private",
            "publisher": "研发部",
            "status": "pending_review",
        },
    )
    assert create.status_code == 201, create.text
    assert create.json()["status"] == "pending_review"


# ---------------------------------------------------------------------------
# toggle（registry）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_toggle_registry(auth_client: AsyncClient) -> None:
    created = (
        await auth_client.post(
            BASE,
            json={
                "name": "qichacha",
                "display_name": "企查查",
                "source": "official",
                "publisher": "企查查科技",
            },
        )
    ).json()
    pid = created["id"]

    enabled = await auth_client.put(f"{BASE}/{pid}/toggle", json={"enabled": True})
    assert enabled.status_code == 200
    assert enabled.json()["status"] == "enabled"

    disabled = await auth_client.put(f"{BASE}/{pid}/toggle", json={"enabled": False})
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"


@pytest.mark.asyncio
async def test_toggle_pending_review_to_enabled(auth_client: AsyncClient) -> None:
    """toggle 一个 pending_review 插件直接落 enabled（审核流 = P-later）。"""
    created = (
        await auth_client.post(
            BASE,
            json={
                "name": "private-hr",
                "display_name": "内部 HR 系统",
                "source": "private",
                "publisher": "研发部",
                "status": "pending_review",
            },
        )
    ).json()
    enabled = await auth_client.put(
        f"{BASE}/{created['id']}/toggle", json={"enabled": True}
    )
    assert enabled.status_code == 200
    assert enabled.json()["status"] == "enabled"


@pytest.mark.asyncio
async def test_toggle_unknown_404(auth_client: AsyncClient) -> None:
    resp = await auth_client.put(f"{BASE}/{uuid4()}/toggle", json={"enabled": True})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# org 隔离
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_excludes_other_org(
    auth_client: AsyncClient, other_org_plugin: Plugin
) -> None:
    listed = await auth_client.get(BASE)
    assert listed.status_code == 200
    ids = [it["id"] for it in listed.json()]
    assert other_org_plugin.id not in ids


@pytest.mark.asyncio
async def test_cannot_toggle_other_org_plugin(
    auth_client: AsyncClient, other_org_plugin: Plugin
) -> None:
    resp = await auth_client.put(
        f"{BASE}/{other_org_plugin.id}/toggle", json={"enabled": False}
    )
    # 跨 org → 视作不存在
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# mcp 投影：McpServerConfig 以 source='mcp' 出现并可 toggle 底层
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mcp_server_projected_in_list(
    auth_client: AsyncClient, mcp_server: McpServerConfig
) -> None:
    listed = await auth_client.get(BASE)
    assert listed.status_code == 200
    mcp_items = [it for it in listed.json() if it["source"] == "mcp"]
    assert any(it["id"] == f"mcp:{mcp_server.id}" for it in mcp_items)
    projected = next(it for it in mcp_items if it["id"] == f"mcp:{mcp_server.id}")
    assert projected["name"] == "mcp-filesystem"
    assert projected["status"] == "enabled"  # is_enabled=True


@pytest.mark.asyncio
async def test_toggle_mcp_updates_underlying_config(
    auth_client: AsyncClient, mcp_server: McpServerConfig, db_session: AsyncSession
) -> None:
    resp = await auth_client.put(
        f"{BASE}/mcp:{mcp_server.id}/toggle", json={"enabled": False}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"
    assert resp.json()["source"] == "mcp"

    # 底层 McpServerConfig.is_enabled 被改写
    refreshed = (
        await db_session.execute(
            select(McpServerConfig).where(McpServerConfig.id == mcp_server.id)
        )
    ).scalar_one()
    assert refreshed.is_enabled is False


@pytest.mark.asyncio
async def test_toggle_mcp_unknown_404(auth_client: AsyncClient) -> None:
    resp = await auth_client.put(
        f"{BASE}/mcp:{uuid4()}/toggle", json={"enabled": True}
    )
    assert resp.status_code == 404
