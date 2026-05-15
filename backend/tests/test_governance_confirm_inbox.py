# -*- coding: utf-8 -*-
"""
ConfirmInbox + ShadowRunner DB 集成测试

使用 in-memory SQLite + sqlalchemy.ext.asyncio 跑 ORM 集成测试，不依赖项目 Postgres。
覆盖：
  - create_ticket / approve / reject / cancel / expire
  - executor 注册 + 批准后回调
  - SoD：高敏 action 不允许自批
  - shadow_runner start / record / finalize + shadow_passed gate
"""
from __future__ import annotations

import asyncio
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.base import Base
# 让 Base.metadata 知道 governance 表
from src.models import governance as _gov  # noqa: F401
from src.models.governance import ConfirmTicket, ConfirmTicketStatus, ShadowRun, ShadowRunStatus
from src.services.governance import confirm_inbox, shadow_runner


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)
    # 只建 governance 三表，跳过其它需要 Postgres 的列（如 PGUUID）
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: _gov.ConfirmTicket.__table__.create(c))
        await conn.run_sync(lambda c: _gov.AuditEventDB.__table__.create(c))
        await conn.run_sync(lambda c: _gov.ShadowRun.__table__.create(c))
    SessionMaker = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionMaker() as s:
        yield s
    await engine.dispose()


# ─────────────────────────────────────────────────────────────────────
# ConfirmInbox
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_create_ticket(session: AsyncSession):
    requester = {"id": "usr_legal_1", "role": "legal_member", "tenant_id": "t1"}
    t = await confirm_inbox.create_ticket(
        session,
        requester=requester,
        action="connector.feishu.send",
        resource={"type": "connector", "id": "feishu/card", "classification": "L2", "jurisdiction": "CN"},
        pending_action={"method": "send_card", "target": "u_xyz"},
        decision_reasons=[{"rule": "global-gate", "value": "*.send → REQUIRE_CONFIRM"}],
        policy_snapshot_id="pol_test",
    )
    await session.commit()
    assert t.id.startswith("tk_")
    assert t.status == ConfirmTicketStatus.pending.value
    assert t.action == "connector.feishu.send"
    assert t.expires_at is not None


@pytest.mark.asyncio
async def test_approve_executes_callback(session: AsyncSession):
    requester = {"id": "usr_legal_1", "role": "legal_member", "tenant_id": "t1"}
    t = await confirm_inbox.create_ticket(
        session,
        requester=requester,
        action="connector.email.send",
        resource={"classification": "L2", "jurisdiction": "CN"},
        pending_action={"to": "client@example.com", "subject": "审查意见"},
    )

    side_effect: dict[str, Any] = {}

    def executor(ticket):
        side_effect["called"] = True
        side_effect["ticket_id"] = ticket.id
        return {"sent": True}

    confirm_inbox.register_executor("connector.email.send", executor)

    approver = {"id": "usr_admin_1", "role": "admin", "tenant_id": "t1"}
    result = await confirm_inbox.approve(session, t.id, approver=approver, note="OK to send")
    await session.commit()

    assert result["status"] == ConfirmTicketStatus.approved.value
    assert result["executed"] is True
    assert side_effect["called"]
    assert side_effect["ticket_id"] == t.id


@pytest.mark.asyncio
async def test_reject(session: AsyncSession):
    requester = {"id": "u1", "role": "growth_member", "tenant_id": "t1"}
    t = await confirm_inbox.create_ticket(
        session, requester=requester, action="connector.linkedin.send",
        resource={"classification": "L2", "jurisdiction": "global"},
    )
    approver = {"id": "u_admin", "role": "admin"}
    result = await confirm_inbox.reject(session, t.id, approver=approver, reason="违反沟通策略")
    await session.commit()
    assert result["status"] == ConfirmTicketStatus.rejected.value
    assert result["reason"] == "违反沟通策略"


@pytest.mark.asyncio
async def test_cannot_double_decision(session: AsyncSession):
    requester = {"id": "u1", "role": "legal_member", "tenant_id": "t1"}
    t = await confirm_inbox.create_ticket(
        session, requester=requester, action="connector.feishu.send",
        resource={"classification": "L2", "jurisdiction": "CN"},
    )
    await confirm_inbox.reject(session, t.id, approver={"id": "u_admin", "role": "admin"}, reason="x")
    with pytest.raises(ValueError):
        await confirm_inbox.approve(session, t.id, approver={"id": "u_admin", "role": "admin"})


@pytest.mark.asyncio
async def test_sod_prevents_self_approve_on_sensitive_action(session: AsyncSession):
    requester = {"id": "usr_fin_1", "role": "finance_member", "tenant_id": "t1"}
    t = await confirm_inbox.create_ticket(
        session, requester=requester, action="connector.stripe.write",
        resource={"classification": "L3", "jurisdiction": "global"},
    )
    # 同一人批准自己的 stripe.write — 必拒
    with pytest.raises(PermissionError):
        await confirm_inbox.approve(session, t.id, approver=requester)


@pytest.mark.asyncio
async def test_user_can_cancel_own_ticket(session: AsyncSession):
    requester = {"id": "u_self", "role": "growth_member", "tenant_id": "t1"}
    t = await confirm_inbox.create_ticket(
        session, requester=requester, action="connector.feishu.send",
        resource={"classification": "L2", "jurisdiction": "CN"},
    )
    result = await confirm_inbox.cancel(session, t.id, actor=requester, reason="想清楚了不发了")
    await session.commit()
    assert result["status"] == ConfirmTicketStatus.cancelled.value


@pytest.mark.asyncio
async def test_other_cannot_cancel(session: AsyncSession):
    requester = {"id": "u_self", "role": "growth_member", "tenant_id": "t1"}
    other = {"id": "u_other", "role": "growth_member", "tenant_id": "t1"}
    t = await confirm_inbox.create_ticket(
        session, requester=requester, action="connector.feishu.send",
        resource={"classification": "L2", "jurisdiction": "CN"},
    )
    with pytest.raises(PermissionError):
        await confirm_inbox.cancel(session, t.id, actor=other)


@pytest.mark.asyncio
async def test_expire_overdue(session: AsyncSession):
    requester = {"id": "u1", "role": "growth_member", "tenant_id": "t1"}
    t = await confirm_inbox.create_ticket(
        session, requester=requester, action="connector.feishu.send",
        resource={"classification": "L2", "jurisdiction": "CN"},
    )
    # 强制把 expires_at 拨回到过去
    t.expires_at = datetime.now(UTC) - timedelta(hours=1)
    await session.flush()
    count = await confirm_inbox.expire_overdue(session)
    await session.commit()
    assert count == 1
    refreshed = await session.get(ConfirmTicket, t.id)
    assert refreshed.status == ConfirmTicketStatus.expired.value


# ─────────────────────────────────────────────────────────────────────
# ShadowRunner
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_shadow_record_and_pass(session: AsyncSession):
    run = await shadow_runner.start_shadow(
        session, skill_id="/legal-advisor:legal-research", review_version="2.0.0",
        baseline_version="1.5.0", window_hours=24,
    )
    await session.commit()
    # 录入 20 条样本 — 1 个 review 错误（5%）；不超阈值
    for i in range(20):
        await shadow_runner.record_invocation(
            session,
            skill_id="/legal-advisor:legal-research",
            input_hash=f"sha256:in_{i}",
            review_output_hash=f"sha256:rev_{i}",
            baseline_output_hash=f"sha256:base_{i}",
            review_error=(i == 0),  # 1/20 = 5% — 边界刚好通过
        )
    await session.commit()
    final = await shadow_runner.finalize_shadow(session, run_id=run.id)
    assert final.status == ShadowRunStatus.passed.value
    passed = await shadow_runner.shadow_passed(
        session, skill_id="/legal-advisor:legal-research", version="2.0.0",
    )
    assert passed is True


@pytest.mark.asyncio
async def test_shadow_security_violation_fails(session: AsyncSession):
    run = await shadow_runner.start_shadow(
        session, skill_id="/dd-expert:company-dd", review_version="1.1.0",
    )
    await session.commit()
    for i in range(10):
        await shadow_runner.record_invocation(
            session,
            skill_id="/dd-expert:company-dd",
            input_hash=f"in_{i}",
            review_output_hash=f"rev_{i}",
            baseline_output_hash=f"base_{i}",
            security_violation=(i == 5),
        )
    await session.commit()
    final = await shadow_runner.finalize_shadow(session, run_id=run.id)
    assert final.status == ShadowRunStatus.failed.value
    passed = await shadow_runner.shadow_passed(
        session, skill_id="/dd-expert:company-dd", version="1.1.0",
    )
    assert passed is False
