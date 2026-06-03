# -*- coding: utf-8 -*-
"""
ExternalSendGate —— PEP-4 在 connector 层的统一入口

所有 connector（feishu / dingtalk / email / amazon-sp / shopify / stripe ...）
要外发动作时必须走这个 gate，而不是直接调 SDK。

示例（feishu_send_card 改造）::

    async def send_card(requester, target, payload):
        from src.services.governance.external_send_gate import guard_external_send
        async with guard_external_send(
            requester=requester,
            action="connector.feishu.send",
            resource={"type": "connector", "id": "feishu/card", "classification": "L2", "jurisdiction": "CN"},
            pending_action={"method": "send_card", "target": target, "payload": payload},
            executor=lambda ticket: _do_send_card(target, payload),
        ) as outcome:
            return outcome
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.governance.audit import write_event
from src.services.governance.authz import Decision, decide
from src.services.governance.confirm_inbox import (
    create_ticket,
    register_executor,
)


@asynccontextmanager
async def guard_external_send(
    db: AsyncSession,
    *,
    requester: dict[str, Any],
    action: str,
    resource: dict[str, Any],
    pending_action: dict[str, Any],
    executor: Callable[..., Any | Awaitable[Any]],
    context: dict[str, Any] | None = None,
    persona: str | None = None,
):
    """异步上下文管理器：

    - PDP 判定 → ALLOW 直接调 executor
    - REQUIRE_CONFIRM → 落 ticket，**不外发**，返回 {ticket_id, status: 'pending'}
    - DENY / REQUIRE_STEP_UP → 抛异常

    Block 内代码（``async with ... as outcome:`` 后）拿到 outcome dict：
      - 已外发：{"executed": True, "result": ...}
      - 待审批：{"executed": False, "ticket_id": "..."}
    """
    context = context or {}
    pdp = decide(subject=requester, action=action, resource=resource, context=context)
    write_event({
        "event_type": "authz.decide",
        "actor": requester,
        "action": action,
        "resource": resource,
        "decision": pdp.decision.value,
        "decision_reasons": pdp.reasons,
        "policy_snapshot_id": pdp.policy_snapshot_id,
        "phase": "pep4_external_send",
    })

    if pdp.decision == Decision.DENY:
        raise PermissionError(f"external_send denied: {action}; reasons={pdp.reasons}")
    if pdp.decision == Decision.REQUIRE_STEP_UP:
        # 业务侧应拦截这条异常，引导 MFA / 重新认证
        raise PermissionError(f"external_send requires step-up: {action}")

    if pdp.decision == Decision.REQUIRE_CONFIRM:
        # 注册 executor（如未注册），便于 confirm_inbox.approve 时回调
        register_executor(action, executor)
        ticket = await create_ticket(
            db,
            requester=requester,
            action=action,
            resource=resource,
            context=context,
            pending_action=pending_action,
            decision_reasons=pdp.reasons,
            policy_snapshot_id=pdp.policy_snapshot_id,
            persona=persona,
        )
        outcome = {"executed": False, "ticket_id": ticket.id, "status": "pending"}
        logger.info("external_send staged → ticket={} action={}", ticket.id, action)
        yield outcome
        return

    # ALLOW — 立即执行
    try:
        result = executor() if not _looks_async(executor) else await executor()  # type: ignore[misc]
        outcome = {"executed": True, "result": result}
        write_event({
            "event_type": "external.send",
            "actor": requester,
            "action": action,
            "resource": resource,
            "decision": "ALLOW",
            "outcome": "success",
        })
    except Exception as e:  # noqa: BLE001
        write_event({
            "event_type": "external.send",
            "actor": requester,
            "action": action,
            "resource": resource,
            "decision": "ALLOW",
            "outcome": "failure",
            "error": repr(e),
        })
        raise
    yield outcome


def _looks_async(fn: Callable) -> bool:
    import asyncio
    return asyncio.iscoroutinefunction(fn)


__all__ = ["guard_external_send"]
