# -*- coding: utf-8 -*-
"""受治理的钉钉外发（与 feishu 同构）"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.governance.external_send_gate import guard_external_send

DingLike = Any


async def send_message(
    db: AsyncSession,
    *,
    adapter: DingLike,
    requester: dict[str, Any],
    target: str,
    content: str,
    msg_type: str = "text",
    classification: str = "L2",
    jurisdiction: str = "CN",
    persona: str | None = None,
    trace_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    resource = {
        "type": "connector",
        "id": f"dingtalk/{msg_type}/{target}",
        "classification": classification,
        "jurisdiction": jurisdiction,
    }
    pending_action = {
        "connector": "dingtalk",
        "method": "send_message",
        "params": {
            "target": target,
            "msg_type": msg_type,
            "content_preview": (content[:200] + "…") if len(content) > 200 else content,
            "content_length": len(content),
        },
    }

    async def _do_send() -> dict[str, Any]:
        return await adapter.send_message(target=target, content=content, msg_type=msg_type, **extra)

    async with guard_external_send(
        db,
        requester=requester,
        action="connector.dingtalk.send",
        resource=resource,
        pending_action=pending_action,
        executor=_do_send,
        context={"trace_id": trace_id},
        persona=persona,
    ) as outcome:
        return outcome


__all__ = ["send_message"]
