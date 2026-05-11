# -*- coding: utf-8 -*-
"""
im_pairing 路由 API 测试（P3-B）

走 ASGITransport，复用 conftest 的 ``auth_client`` / ``admin_auth_client``。
"""

from __future__ import annotations

# SQLite ↔ JSONB 兼容补丁，详见 test_pairing_service.py 同样块的说明。
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler as _SQLiteTC

if not hasattr(_SQLiteTC, "visit_JSONB"):
    def _visit_JSONB(self, type_, **kw):  # noqa: N802
        return self.visit_JSON(type_, **kw)

    _SQLiteTC.visit_JSONB = _visit_JSONB  # type: ignore[attr-defined]


from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# 触发 ORM 表注册
from src.services.im_gateway.models import (  # noqa: F401
    IMBinding,
    IMChannel,
    IMChannelType,
    PairingRequest,
    PairingStatus,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def im_channel(db_session: AsyncSession) -> IMChannel:
    """创建一个测试通道（im_gateway_* 表由 conftest setup_test_db 全局 create_all）。"""
    channel = IMChannel(
        id=str(uuid4()),
        channel_type=IMChannelType.FEISHU,
        name="API 测试飞书通道",
        config={"app_id": "cli_test"},
        enabled=True,
    )
    db_session.add(channel)
    await db_session.flush()
    return channel


@pytest.fixture(autouse=True)
def _stub_feishu_send(monkeypatch):
    """避免 approve 触发真实飞书回执 HTTP 调用。"""
    from src.services.im_gateway import feishu_adapter as fa_mod

    async def _noop_send(self, *args, **kwargs):
        return {"ok": True}

    monkeypatch.setattr(fa_mod.FeishuAdapter, "send_message", _noop_send, raising=False)


# ---------------------------------------------------------------------------
# 用例
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pending_endpoint_admin_only(
    auth_client: AsyncClient,
    admin_auth_client: AsyncClient,
    im_channel: IMChannel,
) -> None:
    """普通用户不能看待审核列表，管理员可以。"""
    # 普通用户 — 403
    resp = await auth_client.get("/api/v1/im/pairing/pending")
    assert resp.status_code == 403, resp.text

    # 管理员 — 200 (空列表)
    resp = await admin_auth_client.get("/api/v1/im/pairing/pending")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["items"] == []
    assert body["limit"] == 50

    # 创建一条 PENDING（用 auth_client 走 webhook 内部接口）
    create_resp = await auth_client.post(
        "/api/v1/im/pairing/request",
        json={
            "channel_id": im_channel.id,
            "external_user_id": "ou_pending_001",
            "external_user_name": "李四",
        },
    )
    assert create_resp.status_code == 201, create_resp.text

    # 管理员看到这条
    resp = await admin_auth_client.get(
        "/api/v1/im/pairing/pending",
        params={"channel_id": im_channel.id},
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["external_user_id"] == "ou_pending_001"
    assert items[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_approve_endpoint(
    auth_client: AsyncClient,
    admin_auth_client: AsyncClient,
    im_channel: IMChannel,
) -> None:
    create_resp = await auth_client.post(
        "/api/v1/im/pairing/request",
        json={
            "channel_id": im_channel.id,
            "external_user_id": "ou_approve_001",
        },
    )
    assert create_resp.status_code == 201
    request_id = create_resp.json()["id"]

    # 普通用户 approve — 403
    resp = await auth_client.post(f"/api/v1/im/pairing/{request_id}/approve")
    assert resp.status_code == 403

    # 管理员 approve — 200，返回 binding
    resp = await admin_auth_client.post(
        f"/api/v1/im/pairing/{request_id}/approve",
        json={"reason": "OK"},
    )
    assert resp.status_code == 200, resp.text
    binding = resp.json()
    assert binding["channel_id"] == im_channel.id
    assert binding["external_user_id"] == "ou_approve_001"
    assert binding["internal_user_id"]  # admin user id

    # 不存在的 request — 404
    resp = await admin_auth_client.post(
        f"/api/v1/im/pairing/{uuid4()}/approve",
        json={},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reject_endpoint_requires_reason(
    auth_client: AsyncClient,
    admin_auth_client: AsyncClient,
    im_channel: IMChannel,
) -> None:
    create_resp = await auth_client.post(
        "/api/v1/im/pairing/request",
        json={
            "channel_id": im_channel.id,
            "external_user_id": "ou_reject_001",
        },
    )
    request_id = create_resp.json()["id"]

    # 缺 reason — 422 校验失败
    resp = await admin_auth_client.post(
        f"/api/v1/im/pairing/{request_id}/reject",
        json={},
    )
    assert resp.status_code == 422

    # 空 reason — 422 (min_length=1)
    resp = await admin_auth_client.post(
        f"/api/v1/im/pairing/{request_id}/reject",
        json={"reason": ""},
    )
    assert resp.status_code == 422

    # 正常驳回
    resp = await admin_auth_client.post(
        f"/api/v1/im/pairing/{request_id}/reject",
        json={"reason": "外部账号无对应内部员工"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "rejected"

    # 重复驳回 — 409
    resp = await admin_auth_client.post(
        f"/api/v1/im/pairing/{request_id}/reject",
        json={"reason": "已驳回过"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_authorized_list(
    auth_client: AsyncClient,
    admin_auth_client: AsyncClient,
    im_channel: IMChannel,
) -> None:
    # 创建 + 通过两条
    for ext in ("ou_auth_a", "ou_auth_b"):
        create = await auth_client.post(
            "/api/v1/im/pairing/request",
            json={"channel_id": im_channel.id, "external_user_id": ext},
        )
        rid = create.json()["id"]
        approve = await admin_auth_client.post(
            f"/api/v1/im/pairing/{rid}/approve",
            json={},
        )
        assert approve.status_code == 200

    # 已授权列表 — 普通用户也能看
    resp = await auth_client.get(
        "/api/v1/im/pairing/authorized",
        params={"channel_id": im_channel.id},
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    ext_ids = {item["external_user_id"] for item in items}
    assert {"ou_auth_a", "ou_auth_b"} <= ext_ids
