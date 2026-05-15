# -*- coding: utf-8 -*-
"""
受治理的飞书外发包装层

调用前自动过 PDP；触发 REQUIRE_CONFIRM 时落 ticket 不外发；ALLOW 时立即调底层
``FeishuAdapter.send_message``。

业务侧不应再直接 import ``FeishuAdapter.send_message``；应通过这里发起所有外发。
"""
from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.governance.external_send_gate import guard_external_send

# adapter 的获取：由调用方注入或通过工厂；这里只声明协议
FeishuLike = Any


async def send_message(
    db: AsyncSession,
    *,
    adapter: FeishuLike,
    requester: dict[str, Any],
    channel_id: str,
    content: str,
    msg_type: str = "text",
    receive_id_type: str = "chat_id",
    classification: str = "L2",
    jurisdiction: str = "CN",
    persona: str | None = None,
    trace_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """受治理的飞书发消息。

    返回：
      - ALLOW 路径：``{"executed": True, "result": <send_message 原 dict>}``
      - REQUIRE_CONFIRM：``{"executed": False, "ticket_id": "tk_...", "status": "pending"}``
      - DENY / STEP_UP：抛 ``PermissionError``
    """
    resource = {
        "type": "connector",
        "id": f"feishu/{msg_type}/{channel_id}",
        "classification": classification,
        "jurisdiction": jurisdiction,
    }
    pending_action = {
        "connector": "feishu",
        "method": "send_message",
        "params": {
            "channel_id": channel_id,
            "msg_type": msg_type,
            "receive_id_type": receive_id_type,
            # 飞书消息内容可能很长且含 PII；只在 pending_action 存摘要
            "content_preview": (content[:200] + "…") if len(content) > 200 else content,
            "content_length": len(content),
        },
    }

    async def _do_send() -> dict[str, Any]:
        return await adapter.send_message(
            channel_id=channel_id,
            content=content,
            msg_type=msg_type,
            receive_id_type=receive_id_type,
            **extra,
        )

    async with guard_external_send(
        db,
        requester=requester,
        action="connector.feishu.send",
        resource=resource,
        pending_action=pending_action,
        executor=_do_send,
        context={"trace_id": trace_id},
        persona=persona,
    ) as outcome:
        logger.info("governed feishu.send → executed={} ticket={}",
                    outcome.get("executed"), outcome.get("ticket_id"))
        return outcome


__all__ = ["send_message"]
