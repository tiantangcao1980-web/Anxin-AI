# -*- coding: utf-8 -*-
"""
per-domain QPS 限流 — 基于内存令牌桶。

设计要点：
- 每个域名独立令牌桶（默认 1 QPS、容量 2，允许小突发）
- 令牌按 wall-clock 增长，不需要后台 task
- ``acquire(host)`` 阻塞直到拿到令牌；超时由调用方设置
- 故意不接 Redis：FetchService 的部署模型是单实例 + 多 worker，
  每个 worker 独立内存桶在「礼貌抓取」语义下足够；
  跨实例严格全局限流可在 P6-D 接 Redis 替换。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass
class _Bucket:
    """简单令牌桶。

    refill_rate 单位：tokens/sec。capacity：桶大小（突发上限）。
    """

    capacity: float
    refill_rate: float
    tokens: float
    last_refill: float

    def refill(self, now: float) -> None:
        elapsed = now - self.last_refill
        if elapsed <= 0:
            return
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def take(self, n: float = 1.0) -> bool:
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False

    def time_to_available(self, n: float = 1.0) -> float:
        deficit = n - self.tokens
        if deficit <= 0:
            return 0.0
        return deficit / self.refill_rate


class PerDomainRateLimiter:
    """per-domain 令牌桶集合。

    Args:
        default_qps: 缺省每秒令牌数（FetchService 默认 1.0）
        default_capacity: 桶容量（默认 = qps * 2，允许 ~2 个突发）
        per_domain_qps: 域名 → QPS 的覆盖配置
    """

    def __init__(
        self,
        *,
        default_qps: float = 1.0,
        default_capacity: float | None = None,
        per_domain_qps: dict[str, float] | None = None,
    ) -> None:
        self._default_qps = default_qps
        self._default_capacity = default_capacity or max(2.0, default_qps * 2)
        self._overrides = per_domain_qps or {}
        self._buckets: dict[str, _Bucket] = {}
        self._global_lock = asyncio.Lock()
        self._domain_locks: dict[str, asyncio.Lock] = {}

    def _get_or_create_bucket(self, host: str) -> _Bucket:
        if host not in self._buckets:
            qps = self._overrides.get(host, self._default_qps)
            capacity = max(2.0, qps * 2)
            self._buckets[host] = _Bucket(
                capacity=capacity,
                refill_rate=qps,
                tokens=capacity,  # 启动时桶满
                last_refill=time.monotonic(),
            )
        return self._buckets[host]

    async def acquire(self, host: str, *, timeout: float = 30.0) -> bool:
        """阻塞直到拿到一个令牌；超时返回 False。"""
        host = host.lower()
        async with self._global_lock:
            if host not in self._domain_locks:
                self._domain_locks[host] = asyncio.Lock()
            lock = self._domain_locks[host]

        deadline = time.monotonic() + timeout
        async with lock:
            while True:
                now = time.monotonic()
                bucket = self._get_or_create_bucket(host)
                bucket.refill(now)
                if bucket.take():
                    return True
                wait = bucket.time_to_available()
                if now + wait > deadline:
                    return False
                await asyncio.sleep(min(wait, 0.5))

    def configure(self, host: str, qps: float) -> None:
        """运行时调整某域名的 QPS（管理后台用）。"""
        host = host.lower()
        self._overrides[host] = qps
        if host in self._buckets:
            bucket = self._buckets[host]
            bucket.refill_rate = qps
            bucket.capacity = max(2.0, qps * 2)
