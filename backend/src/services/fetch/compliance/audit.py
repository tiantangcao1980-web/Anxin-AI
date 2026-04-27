# -*- coding: utf-8 -*-
"""
抓取审计日志 — 90 天保留，独立于业务 audit_service。

最小可用实现：内存环形缓冲 + 可插拔持久化钩子。
- 单元测试只用内存版即可
- 生产部署可注入 ``persist_callback`` 写入独立 ``fetch_audit_log`` 表 / OSS
- 故意不动 ``src/services/audit_service.py``（业务侧审计），保持职责隔离
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

from src.services.fetch.models import FetchTier

PersistCallback = Callable[["AuditRecord"], Awaitable[None]]


@dataclass
class AuditRecord:
    """单条抓取审计记录（90 天保留）。"""

    request_ts: datetime
    user_id: str | None
    url: str
    tier_used: FetchTier
    status_code: int
    duration_ms: int
    blocked_reason: str | None = None
    error: str | None = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["request_ts"] = self.request_ts.isoformat()
        d["tier_used"] = self.tier_used.value
        return d


class AuditLogger:
    """轻量审计记录器。

    - 默认环形缓冲 ``maxlen``（避免长跑进程内存爆）
    - ``retention_days`` 控制内存中保留时长（90d 默认）
    - ``persist_callback`` 异步钩子，由部署方注入持久化（DB / OSS）
    """

    DEFAULT_MAXLEN = 10_000
    DEFAULT_RETENTION_DAYS = 90

    def __init__(
        self,
        *,
        maxlen: int = DEFAULT_MAXLEN,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        persist_callback: PersistCallback | None = None,
    ) -> None:
        self._buffer: deque[AuditRecord] = deque(maxlen=maxlen)
        self._retention = timedelta(days=retention_days)
        self._persist_callback = persist_callback
        self._lock = asyncio.Lock()

    async def record(self, record: AuditRecord) -> None:
        """记录一条审计；写入内存 + 触发持久化钩子。"""
        async with self._lock:
            self._buffer.append(record)
            self._evict_expired_locked()

        if self._persist_callback:
            try:
                await self._persist_callback(record)
            except Exception:  # noqa: BLE001 — 持久化失败不影响主流程
                pass

    def _evict_expired_locked(self) -> None:
        """删除超过 retention 的旧记录（已持锁）。"""
        cutoff = datetime.now(timezone.utc) - self._retention
        while self._buffer and self._buffer[0].request_ts < cutoff:
            self._buffer.popleft()

    async def query(
        self,
        *,
        user_id: str | None = None,
        tier: FetchTier | None = None,
        blocked_only: bool = False,
        limit: int = 100,
    ) -> list[AuditRecord]:
        """查询审计记录（管理后台用）。"""
        async with self._lock:
            records = list(self._buffer)
        out: list[AuditRecord] = []
        for r in reversed(records):  # 最新在前
            if user_id and r.user_id != user_id:
                continue
            if tier and r.tier_used != tier:
                continue
            if blocked_only and not r.blocked_reason:
                continue
            out.append(r)
            if len(out) >= limit:
                break
        return out

    async def stats(self) -> dict[str, int]:
        async with self._lock:
            records = list(self._buffer)
        stats: dict[str, int] = {
            "total": len(records),
            "blocked": sum(1 for r in records if r.blocked_reason),
            "errors": sum(1 for r in records if r.error),
        }
        for tier in FetchTier:
            stats[f"tier_{tier.value}"] = sum(1 for r in records if r.tier_used == tier)
        return stats

    def clear(self) -> None:
        """测试用：同步清空。"""
        self._buffer.clear()
