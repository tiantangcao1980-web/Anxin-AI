# -*- coding: utf-8 -*-
"""
GovernanceRealtime —— 单进程 in-memory pub/sub

把治理事件（ticket 创建 / 批准 / 撤回 / 审计 / shadow 等）实时推给已连接的 dashboard。

设计权衡：
  - **不引入 Redis pub/sub** —— 治理事件量低（每天几百），单进程内 asyncio.Queue 已足够。
  - 多实例部署时由各实例独立向自己的连接广播；治理 dashboard 通常只开 1-2 个 tab。
  - 若未来需要跨实例同步，可把 ``Broadcaster.publish()`` 实现替换成走 Redis。
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from loguru import logger


@dataclass
class Event:
    """推送给前端的事件信封。"""

    type: str           # confirm.created / confirm.granted / confirm.denied / audit / shadow.* / lifecycle.*
    payload: dict[str, Any] = field(default_factory=dict)
    tenant_id: str | None = None
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json(self) -> str:
        return json.dumps(
            {"type": self.type, "ts": self.ts, "tenant_id": self.tenant_id, "payload": self.payload},
            ensure_ascii=False, default=str,
        )


class Broadcaster:
    """订阅 / 取消订阅 / 广播。线程不安全（asyncio 单 loop 内使用）。"""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[Event]] = set()

    def subscribe(self, *, queue_size: int = 100) -> asyncio.Queue[Event]:
        q: asyncio.Queue[Event] = asyncio.Queue(maxsize=queue_size)
        self._subscribers.add(q)
        logger.debug("governance realtime: subscriber+ {} (total={})", id(q), len(self._subscribers))
        return q

    def unsubscribe(self, q: asyncio.Queue[Event]) -> None:
        self._subscribers.discard(q)
        logger.debug("governance realtime: subscriber- {} (total={})", id(q), len(self._subscribers))

    def publish(self, event: Event) -> None:
        """非阻塞广播。订阅者队列满时丢弃该条（不阻塞 publisher）。"""
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("governance realtime: subscriber {} queue 满 → 丢弃事件 {}",
                               id(q), event.type)

    async def stream(self, *, queue_size: int = 100, tenant_id: str | None = None) -> AsyncIterator[Event]:
        """单订阅者的事件流（生成器）。"""
        q = self.subscribe(queue_size=queue_size)
        try:
            while True:
                ev = await q.get()
                # 多租户过滤：未指定 tenant_id 或匹配的事件才推
                if tenant_id and ev.tenant_id and ev.tenant_id != tenant_id:
                    continue
                yield ev
        finally:
            self.unsubscribe(q)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


# 单例
_BROADCASTER: Broadcaster | None = None


def get_broadcaster() -> Broadcaster:
    global _BROADCASTER
    if _BROADCASTER is None:
        _BROADCASTER = Broadcaster()
    return _BROADCASTER


# ────────────────────────────────────────────────────────────────────
# 便利函数 —— audit / confirm_inbox 调用一行就广播
# ────────────────────────────────────────────────────────────────────
def publish_audit_event(event: dict[str, Any]) -> None:
    """从 audit.write_event 调用：把审计事件广播给 dashboard。"""
    actor = event.get("actor") or {}
    get_broadcaster().publish(Event(
        type=event.get("event_type", "audit"),
        tenant_id=str(actor.get("tenant_id")) if actor.get("tenant_id") else None,
        payload={
            "event_id": event.get("event_id"),
            "ts": event.get("ts"),
            "actor": actor,
            "action": event.get("action"),
            "resource": event.get("resource"),
            "decision": event.get("decision"),
            "outcome": event.get("outcome"),
            "trace_id": event.get("trace_id"),
        },
    ))


def publish_ticket_event(kind: str, ticket: dict[str, Any], tenant_id: str | None = None) -> None:
    """从 confirm_inbox.create_ticket / approve / reject / cancel 调用。"""
    get_broadcaster().publish(Event(
        type=f"ticket.{kind}",
        tenant_id=tenant_id,
        payload=ticket,
    ))


__all__ = [
    "Broadcaster",
    "Event",
    "get_broadcaster",
    "publish_audit_event",
    "publish_ticket_event",
]
