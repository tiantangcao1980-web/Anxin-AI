# -*- coding: utf-8 -*-
"""IM 渠道管理后端测试（P3-C）。

覆盖 6 端点 happy path + 鉴权 + 状态机 + config 完整度推导。
使用 conftest 的 db_session / auth_client fixtures（SQLite 内存，禁用真实第三方）。
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


# 一组"完整"的飞书配置（满足必填 app_id / app_secret）
FEISHU_FULL_CONFIG = {"app_id": "cli_demo", "app_secret": "secret_demo"}


# --------------------------------------------------------------------------- 鉴权


async def test_list_channels_requires_auth(client):
    """未带 token 访问应 401。"""
    resp = await client.get("/api/v1/im/channels")
    assert resp.status_code == 401


async def test_setup_requires_auth(client):
    resp = await client.post(
        "/api/v1/im/channels/feishu/setup", json={"config": FEISHU_FULL_CONFIG}
    )
    assert resp.status_code == 401


# --------------------------------------------------------------------------- 列表


async def test_list_channels_empty(auth_client):
    """新组织无渠道时返回空列表。"""
    resp = await auth_client.get("/api/v1/im/channels")
    assert resp.status_code == 200
    assert resp.json() == []


# --------------------------------------------------------------------------- setup


async def test_setup_channel_with_full_config_connected(auth_client):
    """config 完整 → status=connected，enabled 默认 False，stats 全 0。"""
    resp = await auth_client.post(
        "/api/v1/im/channels/feishu/setup", json={"config": FEISHU_FULL_CONFIG}
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["channel_type"] == "feishu"
    assert data["config"] == FEISHU_FULL_CONFIG
    assert data["status"] == "connected"
    assert data["enabled"] is False
    assert data["bound_agent_persona"] is None
    assert data["stats"] == {
        "bound_users": 0,
        "bound_groups": 0,
        "pending_pairings": 0,
    }
    assert "id" in data and "created_at" in data


async def test_setup_channel_incomplete_config_unconfigured(auth_client):
    """config 缺必填字段 → status=unconfigured。"""
    resp = await auth_client.post(
        "/api/v1/im/channels/feishu/setup", json={"config": {"app_id": "only_id"}}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "unconfigured"


async def test_setup_invalid_channel_type_422(auth_client):
    """非法 channel_type → 422。"""
    resp = await auth_client.post(
        "/api/v1/im/channels/myspace/setup", json={"config": {}}
    )
    assert resp.status_code == 422


async def test_setup_is_upsert_same_type(auth_client):
    """同组织同类型重复 setup 走 upsert，列表里只有一条。"""
    await auth_client.post(
        "/api/v1/im/channels/feishu/setup", json={"config": {"app_id": "a"}}
    )
    await auth_client.post(
        "/api/v1/im/channels/feishu/setup", json={"config": FEISHU_FULL_CONFIG}
    )
    resp = await auth_client.get("/api/v1/im/channels")
    feishu = [c for c in resp.json() if c["channel_type"] == "feishu"]
    assert len(feishu) == 1
    assert feishu[0]["config"] == FEISHU_FULL_CONFIG
    assert feishu[0]["status"] == "connected"


# --------------------------------------------------------------------------- 状态机


async def test_enable_disable_state_machine(auth_client):
    """enable / disable 切换 enabled，不影响 connect 状态。"""
    setup = await auth_client.post(
        "/api/v1/im/channels/slack/setup", json={"config": {"bot_token": "xoxb-x"}}
    )
    cid = setup.json()["id"]
    assert setup.json()["enabled"] is False
    assert setup.json()["status"] == "connected"

    enabled = await auth_client.put(f"/api/v1/im/channels/{cid}/enable")
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True
    assert enabled.json()["status"] == "connected"

    disabled = await auth_client.put(f"/api/v1/im/channels/{cid}/disable")
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False


async def test_bind_agent_persona(auth_client):
    """绑定 agent persona。"""
    setup = await auth_client.post(
        "/api/v1/im/channels/telegram/setup", json={"config": {"bot_token": "t"}}
    )
    cid = setup.json()["id"]

    resp = await auth_client.put(
        f"/api/v1/im/channels/{cid}/agent", json={"agent_persona": "anxin"}
    )
    assert resp.status_code == 200
    assert resp.json()["bound_agent_persona"] == "anxin"


async def test_test_connection_ok_when_config_complete(auth_client):
    """config 完整 → /test 返回 ok=True。"""
    setup = await auth_client.post(
        "/api/v1/im/channels/feishu/setup", json={"config": FEISHU_FULL_CONFIG}
    )
    cid = setup.json()["id"]

    resp = await auth_client.get(f"/api/v1/im/channels/{cid}/test")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "message" in body


async def test_test_connection_fails_when_config_incomplete(auth_client):
    """config 缺字段 → /test 返回 ok=False + missing 列表。"""
    setup = await auth_client.post(
        "/api/v1/im/channels/dingtalk/setup", json={"config": {"app_key": "k"}}
    )
    cid = setup.json()["id"]

    resp = await auth_client.get(f"/api/v1/im/channels/{cid}/test")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert "app_secret" in body["detail"]["missing"]


# --------------------------------------------------------------------------- 404 / 越权


async def test_operations_on_missing_channel_404(auth_client):
    """对不存在的渠道操作返回 404。"""
    fake = "00000000-0000-0000-0000-000000000000"
    assert (await auth_client.put(f"/api/v1/im/channels/{fake}/enable")).status_code == 404
    assert (await auth_client.put(f"/api/v1/im/channels/{fake}/disable")).status_code == 404
    assert (await auth_client.get(f"/api/v1/im/channels/{fake}/test")).status_code == 404
    bind = await auth_client.put(
        f"/api/v1/im/channels/{fake}/agent", json={"agent_persona": "x"}
    )
    assert bind.status_code == 404


async def test_list_only_shows_own_org_channels(auth_client):
    """列表只返回本组织渠道（setup 后能看到刚建的）。"""
    await auth_client.post(
        "/api/v1/im/channels/wechat/setup",
        json={"config": {"corp_id": "c", "secret": "s"}},
    )
    resp = await auth_client.get("/api/v1/im/channels")
    types = {c["channel_type"] for c in resp.json()}
    assert "wechat" in types
