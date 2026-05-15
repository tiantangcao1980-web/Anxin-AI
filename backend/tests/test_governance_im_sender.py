# -*- coding: utf-8 -*-
"""
IM Gateway 治理外发入口测试。

不真连 adapter（adapter 用 stub）；只验证：
  - feishu 路径 → REQUIRE_CONFIRM 落 ticket
  - dingtalk 路径 → REQUIRE_CONFIRM 落 ticket
  - 通用 channel（slack/wechat/telegram）→ guard_external_send 落 ticket
"""
from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models import governance as _gov  # noqa: F401


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: _gov.ConfirmTicket.__table__.create(c))
        await conn.run_sync(lambda c: _gov.AuditEventDB.__table__.create(c))
        await conn.run_sync(lambda c: _gov.ShadowRun.__table__.create(c))
    SessionMaker = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionMaker() as s:
        yield s
    await engine.dispose()


class _FakeAdapter:
    channel_type = "feishu"

    def __init__(self, **_: Any) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send_message(self, channel_id: str = "", content: str = "", **extra: Any) -> dict[str, Any]:
        self.sent.append({"channel_id": channel_id, "content": content, **extra})
        return {"message_id": "fake_msg_1"}


@pytest.mark.asyncio
async def test_governed_send_feishu_creates_ticket(session: AsyncSession, monkeypatch):
    """feishu 路径：*.send 命中 REQUIRE_CONFIRM → 落 ticket。"""
    # patch registry.get → 返回 _FakeAdapter
    from src.services.im_gateway import governed_sender, registry

    class _R:
        @staticmethod
        def get(ct: str):
            return _FakeAdapter
    monkeypatch.setattr(registry.IMAdapterRegistry, "default", lambda: _R())

    requester = {"id": "u1", "role": "legal_member", "tenant_id": "t1",
                 "clearance": "L4", "primary_jurisdiction": "CN"}
    out = await governed_sender.send(
        session, channel_type="feishu", requester=requester,
        channel_id="chat_xyz", content="审查意见",
        persona="contract-steward",
    )
    assert out["executed"] is False
    assert out["ticket_id"].startswith("tk_")


@pytest.mark.asyncio
async def test_governed_send_dingtalk_creates_ticket(session: AsyncSession, monkeypatch):
    from src.services.im_gateway import governed_sender, registry

    class _R:
        @staticmethod
        def get(ct: str):
            return _FakeAdapter
    monkeypatch.setattr(registry.IMAdapterRegistry, "default", lambda: _R())

    # admin 通过 connector.*.send + global gate *.send → REQUIRE_CONFIRM
    requester = {"id": "u_admin", "role": "admin", "tenant_id": "t1",
                 "clearance": "L4", "primary_jurisdiction": "CN"}
    out = await governed_sender.send(
        session, channel_type="dingtalk", requester=requester,
        channel_id="conv_abc", content="提醒：合同到期",
        persona="contract-steward",
    )
    assert out["executed"] is False
    assert out["ticket_id"].startswith("tk_")


@pytest.mark.asyncio
async def test_governed_send_unknown_channel_falls_back_to_guard(session: AsyncSession, monkeypatch):
    """slack 等无显式 wrapper 的 channel → 走通用 guard_external_send。"""
    from src.services.im_gateway import governed_sender, registry

    class _R:
        @staticmethod
        def get(ct: str):
            return _FakeAdapter
    monkeypatch.setattr(registry.IMAdapterRegistry, "default", lambda: _R())

    requester = {"id": "u1", "role": "admin", "tenant_id": "t1",
                 "clearance": "L4", "primary_jurisdiction": "CN"}
    out = await governed_sender.send(
        session, channel_type="slack", requester=requester,
        channel_id="C12345", content="hello",
        persona="growth_member",
    )
    assert out["executed"] is False
    assert out["ticket_id"].startswith("tk_")
