# -*- coding: utf-8 -*-
"""
IM Gateway 治理统一外发入口

业务侧调用任何 IM channel（飞书 / 钉钉 / 微信 / Slack / Telegram）外发时，
应**只**通过本模块的 ``send`` 函数，不直接调用 adapter.send_message。

```python
from src.services.im_gateway.governed_sender import send

result = await send(
    db,
    channel_type="feishu",   # 或 dingtalk / wechat / slack / telegram
    requester=user_subject,
    channel_id="oc_xxx",
    content="审查意见草稿…",
    msg_type="text",
    persona="contract-steward",
)

# result["executed"] is False → result["ticket_id"] 已落 confirm_tickets
# result["executed"] is True  → result["result"] = adapter 返回的原始 dict
```

实现：根据 channel_type 路由到 governance.connectors.* 的对应包装，
后者经过 ``guard_external_send`` 走 PDP + Inbox。
"""
from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.im_gateway.registry import IMAdapterRegistry


async def send(
    db: AsyncSession,
    *,
    channel_type: str,
    requester: dict[str, Any],
    channel_id: str,
    content: str,
    msg_type: str = "text",
    adapter_config: dict[str, Any] | None = None,
    classification: str = "L2",
    jurisdiction: str = "CN",
    persona: str | None = None,
    trace_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """统一治理外发入口。

    参数:
      channel_type    : feishu / dingtalk / wechat / slack / telegram
      requester       : PDP subject（id / role / tenant_id / clearance / primary_jurisdiction）
      channel_id      : 频道 ID（飞书 chat_id / 钉钉 conversationId / wechat group_id）
      content         : 消息内容
      msg_type        : text / interactive(卡片) / post 等（具体依 channel）
      adapter_config  : 给 ``IMAdapterRegistry.build`` 用的配置（app_id/secret 等）
      classification  : 资源分级（默认 L2）；含合同 / 客户名单时调 L3+
      jurisdiction    : 资源法域（默认 CN）；跨境时显式声明
      persona         : 发起 persona（审计与 inbox 路由用）
      trace_id        : 调用方追踪 id

    返回：
      ALLOW          → {"executed": True, "result": <adapter 原始 dict>}
      REQUIRE_CONFIRM→ {"executed": False, "ticket_id": "tk_...", "status": "pending"}
      DENY / STEP_UP → 抛 ``PermissionError``
    """
    registry = IMAdapterRegistry.default()
    adapter_cls = registry.get(channel_type)
    adapter = adapter_cls(config=adapter_config or {}) if adapter_config is not None else adapter_cls()

    # 按 channel 类型路由到具体 governance wrapper
    if channel_type == "feishu":
        from src.services.governance.connectors.feishu import send_message as gov_send
        return await gov_send(
            db, adapter=adapter, requester=requester,
            channel_id=channel_id, content=content, msg_type=msg_type,
            classification=classification, jurisdiction=jurisdiction,
            persona=persona, trace_id=trace_id, **extra,
        )
    if channel_type == "dingtalk":
        from src.services.governance.connectors.dingtalk import send_message as gov_send
        return await gov_send(
            db, adapter=adapter, requester=requester,
            target=channel_id, content=content, msg_type=msg_type,
            classification=classification, jurisdiction=jurisdiction,
            persona=persona, trace_id=trace_id, **extra,
        )
    # 其它（wechat / slack / telegram）→ 通用 guard
    from src.services.governance.external_send_gate import guard_external_send

    async def _do_send() -> dict[str, Any]:
        return await adapter.send_message(channel_id, content, **extra)

    async with guard_external_send(
        db,
        requester=requester,
        action=f"connector.{channel_type}.send",
        resource={
            "type": "connector", "id": f"{channel_type}/{channel_id}",
            "classification": classification, "jurisdiction": jurisdiction,
        },
        pending_action={
            "connector": channel_type, "method": "send_message",
            "params": {
                "channel_id": channel_id, "msg_type": msg_type,
                "content_preview": (content[:200] + "…") if len(content) > 200 else content,
                "content_length": len(content),
            },
        },
        executor=_do_send,
        context={"trace_id": trace_id},
        persona=persona,
    ) as outcome:
        logger.info("governed im.{}.send → executed={} ticket={}",
                    channel_type, outcome.get("executed"), outcome.get("ticket_id"))
        return outcome


__all__ = ["send"]
