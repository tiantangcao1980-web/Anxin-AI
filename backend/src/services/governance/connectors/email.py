# -*- coding: utf-8 -*-
"""受治理的邮件外发（SMTP / SES / SendGrid 通用）"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.governance.external_send_gate import guard_external_send

EmailLike = Any


async def send_email(
    db: AsyncSession,
    *,
    sender: EmailLike,
    requester: dict[str, Any],
    to: list[str],
    subject: str,
    body: str,
    classification: str = "L3",     # 邮件常含合同 / 客户信息，默认 L3
    jurisdiction: str = "CN",
    persona: str | None = None,
    trace_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    # 判别跨境收件人 → 升级 jurisdiction 字段
    if any(addr.split("@", 1)[-1].endswith((".eu", ".de", ".fr", ".uk", ".com.au", ".jp")) for addr in to):
        jurisdiction = "global"

    resource = {
        "type": "connector",
        "id": f"email/{','.join(to)[:120]}",
        "classification": classification,
        "jurisdiction": jurisdiction,
    }
    pending_action = {
        "connector": "email",
        "method": "send_email",
        "params": {
            "to": to,
            "subject": subject,
            "body_preview": (body[:300] + "…") if len(body) > 300 else body,
            "body_length": len(body),
        },
    }

    async def _do_send() -> dict[str, Any]:
        return await sender.send(to=to, subject=subject, body=body, **extra)

    async with guard_external_send(
        db,
        requester=requester,
        action="connector.email.send",
        resource=resource,
        pending_action=pending_action,
        executor=_do_send,
        context={"trace_id": trace_id},
        persona=persona,
    ) as outcome:
        return outcome


__all__ = ["send_email"]
