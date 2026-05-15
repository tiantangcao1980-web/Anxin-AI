# -*- coding: utf-8 -*-
"""
ConfirmInbox —— PEP-4：等待人工 confirm 的外发 / 写动作落表 + 审批

调用约定（业务侧）::

    from src.services.governance.confirm_inbox import create_ticket, approve, reject

    # 1. 业务在 PDP 返回 REQUIRE_CONFIRM 时调用：
    ticket = await create_ticket(
        db, requester=user, action="connector.feishu.send",
        resource={...}, pending_action={"method": "send_card", "params": {...}},
        decision_reasons=[...], policy_snapshot_id="pol_...",
    )
    # ticket 落库后 push 一条提醒到 owner persona inbox / 飞书 / 企微

    # 2. 审批人在 UI 上点 Approve：
    result = await approve(db, ticket_id, approver=user, note="OK to send")
    # 触发挂起动作（exec_callback），随后 audit log
"""
from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.governance import ConfirmTicket, ConfirmTicketStatus
from src.services.governance.audit import write_event


def _publish(kind: str, ticket: ConfirmTicket) -> None:
    try:
        from src.services.governance.realtime import publish_ticket_event
        publish_ticket_event(
            kind, ticket={
                "id": ticket.id, "action": ticket.action,
                "status": ticket.status,
                "persona": ticket.persona, "skill_id": ticket.skill_id,
                "cookbook_name": ticket.cookbook_name,
                "requester_id": ticket.requester_id, "requester_role": ticket.requester_role,
                "approver_id": ticket.approver_id,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "decision_at": ticket.decision_at.isoformat() if ticket.decision_at else None,
            },
            tenant_id=ticket.tenant_id,
        )
    except Exception:  # noqa: BLE001
        pass


# 注册表：action → exec_callback
# 业务侧调 register_executor("connector.feishu.send", real_send_fn) 把"批准后真正执行的函数"注入；
# approve() 时按 action 派发。
_EXECUTORS: dict[str, Callable[[ConfirmTicket], Awaitable[dict[str, Any]] | dict[str, Any]]] = {}


def register_executor(action: str, fn: Callable[[ConfirmTicket], Any]) -> None:
    _EXECUTORS[action] = fn


# ─────────────────────────────────────────────────────────────────────
# create
# ─────────────────────────────────────────────────────────────────────
async def create_ticket(
    db: AsyncSession,
    *,
    requester: dict[str, Any],
    action: str,
    resource: dict[str, Any],
    context: dict[str, Any] | None = None,
    pending_action: dict[str, Any] | None = None,
    decision_reasons: list[dict[str, Any]] | None = None,
    policy_snapshot_id: str | None = None,
    persona: str | None = None,
    skill_id: str | None = None,
    cookbook_name: str | None = None,
    draft_path: str | None = None,
    ttl_hours: int = 72,
) -> ConfirmTicket:
    """落库一条待 confirm ticket，并写一条 `confirm.created` 审计。"""
    now = datetime.now(UTC)
    ticket_id = "tk_" + secrets.token_hex(16)
    ticket = ConfirmTicket(
        id=ticket_id,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=ttl_hours),
        tenant_id=str(requester.get("tenant_id", "unknown")),
        requester_id=str(requester.get("id", "anon")),
        requester_role=str(requester.get("role", "guest")),
        persona=persona,
        skill_id=skill_id,
        cookbook_name=cookbook_name,
        action=action,
        resource=resource or {},
        context=context or {},
        decision_reasons=decision_reasons or [],
        policy_snapshot_id=policy_snapshot_id,
        pending_action=pending_action or {},
        draft_path=draft_path,
        status=ConfirmTicketStatus.pending.value,
    )
    db.add(ticket)
    await db.flush()

    event_id = write_event({
        "event_type": "confirm.created",
        "actor": requester,
        "action": action,
        "resource": resource,
        "decision": "REQUIRE_CONFIRM",
        "outcome": "pending",
        "trace_id": context.get("trace_id") if context else None,
        "ticket_id": ticket_id,
    })
    ticket.create_audit_event_id = event_id
    await db.flush()
    logger.info("ConfirmTicket created id={} action={} requester={}",
                ticket_id, action, requester.get("id"))
    _publish("created", ticket)
    return ticket


# ─────────────────────────────────────────────────────────────────────
# approve / reject / cancel / expire
# ─────────────────────────────────────────────────────────────────────
async def approve(
    db: AsyncSession,
    ticket_id: str,
    *,
    approver: dict[str, Any],
    note: str | None = None,
    cosigner: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """审批通过 → 执行挂起动作 → 写两条审计（granted + executed）。"""
    ticket = await _get(db, ticket_id)
    _ensure_pending(ticket)
    _ensure_not_self_approve(ticket, approver)

    now = datetime.now(UTC)
    ticket.status = ConfirmTicketStatus.approved.value
    ticket.approver_id = str(approver.get("id"))
    ticket.approver_role = str(approver.get("role"))
    ticket.decision_at = now
    ticket.decision_note = note
    if cosigner:
        ticket.cosigner_id = str(cosigner.get("id"))
        ticket.cosigner_at = now
    ticket.updated_at = now

    granted_event = write_event({
        "event_type": "confirm.granted",
        "actor": approver,
        "action": ticket.action,
        "resource": ticket.resource,
        "decision": "ALLOW",
        "outcome": "approved",
        "ticket_id": ticket.id,
        "cosigner": cosigner or {},
        "note": note,
    })
    ticket.decision_audit_event_id = granted_event

    # 执行挂起动作
    exec_outcome: dict[str, Any] = {"executed": False, "reason": "no_executor_registered"}
    executor = _EXECUTORS.get(ticket.action)
    if executor:
        try:
            result = executor(ticket)
            if hasattr(result, "__await__"):
                result = await result  # type: ignore[assignment]
            exec_outcome = {"executed": True, "result": result}
        except Exception as e:  # noqa: BLE001
            exec_outcome = {"executed": False, "error": repr(e)}
            logger.exception("ConfirmTicket {} executor 失败", ticket.id)

    write_event({
        "event_type": "external.send" if ticket.action.startswith("connector.") else "skill.execute",
        "actor": approver,
        "action": ticket.action,
        "resource": ticket.resource,
        "decision": "ALLOW",
        "outcome": "success" if exec_outcome.get("executed") else "failure",
        "ticket_id": ticket.id,
        "exec": exec_outcome,
    })

    await db.flush()
    _publish("granted", ticket)
    return {"ticket_id": ticket.id, "status": ticket.status, **exec_outcome}


async def reject(
    db: AsyncSession,
    ticket_id: str,
    *,
    approver: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    ticket = await _get(db, ticket_id)
    _ensure_pending(ticket)
    now = datetime.now(UTC)
    ticket.status = ConfirmTicketStatus.rejected.value
    ticket.approver_id = str(approver.get("id"))
    ticket.approver_role = str(approver.get("role"))
    ticket.decision_at = now
    ticket.decision_note = reason
    ticket.updated_at = now

    eid = write_event({
        "event_type": "confirm.denied",
        "actor": approver,
        "action": ticket.action,
        "resource": ticket.resource,
        "decision": "DENY",
        "outcome": "rejected",
        "ticket_id": ticket.id,
        "reason": reason,
    })
    ticket.decision_audit_event_id = eid
    await db.flush()
    _publish("denied", ticket)
    return {"ticket_id": ticket.id, "status": ticket.status, "reason": reason}


async def cancel(
    db: AsyncSession, ticket_id: str, *, actor: dict[str, Any], reason: str | None = None,
) -> dict[str, Any]:
    """请求人主动撤回。"""
    ticket = await _get(db, ticket_id)
    _ensure_pending(ticket)
    if str(actor.get("id")) != ticket.requester_id:
        raise PermissionError("只有请求人本人可以取消 ticket")
    now = datetime.now(UTC)
    ticket.status = ConfirmTicketStatus.cancelled.value
    ticket.decision_at = now
    ticket.decision_note = reason
    ticket.updated_at = now
    write_event({
        "event_type": "confirm.cancelled",
        "actor": actor,
        "action": ticket.action,
        "decision": "CANCELLED",
        "outcome": "user_cancelled",
        "ticket_id": ticket.id,
    })
    await db.flush()
    _publish("cancelled", ticket)
    return {"ticket_id": ticket.id, "status": ticket.status}


async def expire_overdue(db: AsyncSession) -> int:
    """后台扫描 — 把过期未处理的 ticket 标为 expired。"""
    now = datetime.now(UTC)
    stmt = select(ConfirmTicket).where(
        ConfirmTicket.status == ConfirmTicketStatus.pending.value,
        ConfirmTicket.expires_at.isnot(None),
        ConfirmTicket.expires_at < now,
    )
    res = await db.execute(stmt)
    count = 0
    for t in res.scalars():
        t.status = ConfirmTicketStatus.expired.value
        t.updated_at = now
        write_event({
            "event_type": "confirm.expired",
            "action": t.action,
            "ticket_id": t.id,
            "decision": "DENY",
            "outcome": "expired",
        })
        _publish("expired", t)
        count += 1
    if count:
        await db.flush()
        logger.info("ConfirmInbox: expired {} tickets", count)
    return count


# ─────────────────────────────────────────────────────────────────────
# query
# ─────────────────────────────────────────────────────────────────────
async def list_tickets(
    db: AsyncSession,
    *,
    tenant_id: str | None = None,
    status: str | None = None,
    persona: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ConfirmTicket]:
    stmt = select(ConfirmTicket).order_by(ConfirmTicket.created_at.desc())
    if tenant_id:
        stmt = stmt.where(ConfirmTicket.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(ConfirmTicket.status == status)
    if persona:
        stmt = stmt.where(ConfirmTicket.persona == persona)
    stmt = stmt.limit(limit).offset(offset)
    res = await db.execute(stmt)
    return list(res.scalars())


# ─────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────
async def _get(db: AsyncSession, ticket_id: str) -> ConfirmTicket:
    stmt = select(ConfirmTicket).where(ConfirmTicket.id == ticket_id)
    res = await db.execute(stmt)
    ticket = res.scalar_one_or_none()
    if ticket is None:
        raise LookupError(f"ConfirmTicket not found: {ticket_id}")
    return ticket


def _ensure_pending(ticket: ConfirmTicket) -> None:
    if ticket.status != ConfirmTicketStatus.pending.value:
        raise ValueError(f"ticket 状态={ticket.status}, 不可操作")


def _ensure_not_self_approve(ticket: ConfirmTicket, approver: dict[str, Any]) -> None:
    """SoD：高敏 action 禁止自批自审。"""
    sensitive_prefixes = ("data.privileged", "connector.stripe", "connector.amazon-sp.write")
    if any(ticket.action.startswith(p) for p in sensitive_prefixes):
        if str(approver.get("id")) == ticket.requester_id:
            raise PermissionError(f"action={ticket.action} 不允许自批自审（SoD）")


__all__ = [
    "create_ticket",
    "approve",
    "reject",
    "cancel",
    "expire_overdue",
    "list_tickets",
    "register_executor",
]
