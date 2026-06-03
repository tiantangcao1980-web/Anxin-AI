# -*- coding: utf-8 -*-
"""
通用滑窗 burst 限流工具 — A10 (2026-05-14) + F2 Redis adapter (2026-05-14)

设计:
  - 默认: 内存滑动窗口 (适用单进程 / 单机部署)
  - 可选: Redis sorted-set 后端 (RATE_LIMIT_REDIS_URL 环境变量启用, 多节点共享)
  - 通过 check_burst(...) 单点判定, 实现细节透明给调用方
  - 配套 fingerprint_preview 工具生成简单的 (url, message) 指纹

Redis 后端工作机制:
  - ZADD <key> <now> <member>: 把当前 timestamp 写入 sorted-set
  - ZREMRANGEBYSCORE <key> 0 <cutoff>: 弹出过期成员
  - ZCARD <key>: 当前窗口内的请求数
  - EXPIRE <key> <window>: 自然清理无活动 bucket
"""

from __future__ import annotations

import hashlib
import os
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any

_FINGERPRINT_WINDOW_SECONDS = 60
_FINGERPRINT_BURST_LIMIT = 20
_USER_WINDOW_SECONDS = 60
_USER_BURST_LIMIT = 30


fingerprint_buckets: dict[str, deque[float]] = defaultdict(deque)
user_buckets: dict[str, deque[float]] = defaultdict(deque)
rate_lock = Lock()


def check_burst(bucket: deque[float], window_seconds: int, limit: int) -> bool:
    """滑动窗口判定; True=超限。

    把过期 timestamp 弹出后, 如果剩余 >= limit 则返回 True (本次不放行),
    否则记录当前 timestamp 并返回 False。
    """
    now = time.monotonic()
    cutoff = now - window_seconds
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= limit:
        return True
    bucket.append(now)
    return False


def fingerprint_preview(url: str | None, message: str | None) -> str:
    """前置指纹预估; 与 collector 内部 fingerprint 不强耦合, 仅用于限流分桶。"""
    raw = f"{url or ''}|{message or ''}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


# ============================================================
# F2 (2026-05-14): Redis 后端预留
# ============================================================
# 启用方式: 设置环境变量 RATE_LIMIT_REDIS_URL=redis://host:port/db
# 不设置时使用内存 deque (默认), 设置后所有调用路径自动切换 Redis sorted-set

_redis_client: Any = None
_redis_init_attempted: bool = False


def _get_redis_client() -> Any | None:
    """惰性初始化 Redis 客户端; 失败时返回 None, 调用方继续走内存。"""
    global _redis_client, _redis_init_attempted
    if _redis_init_attempted:
        return _redis_client
    _redis_init_attempted = True

    url = os.environ.get("RATE_LIMIT_REDIS_URL", "").strip()
    if not url:
        return None

    try:
        import redis  # type: ignore[import-not-found]

        _redis_client = redis.from_url(url, decode_responses=True)
        # ping 一次确认连通
        _redis_client.ping()
        return _redis_client
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning(
            "rate_limit_burst: Redis 后端初始化失败, 退回内存模式: %s", exc
        )
        _redis_client = None
        return None


def check_burst_redis(
    redis_key: str,
    window_seconds: int,
    limit: int,
) -> bool:
    """Redis sorted-set 滑窗版本; 适合多节点共享。

    True=超限. 比内存版多承担一次 redis 网络往返 (~1ms LAN), 但跨节点一致.
    """
    client = _get_redis_client()
    if client is None:
        # Redis 不可用 → 退回内存
        return check_burst(_redis_fallback_buckets[redis_key], window_seconds, limit)

    now = time.time()
    cutoff = now - window_seconds
    member = f"{now}:{os.getpid()}"  # PID 防同毫秒冲突

    try:
        pipe = client.pipeline()
        pipe.zremrangebyscore(redis_key, 0, cutoff)
        pipe.zcard(redis_key)
        pipe.zadd(redis_key, {member: now})
        pipe.expire(redis_key, window_seconds + 1)
        _, count_before_add, _, _ = pipe.execute()
        if int(count_before_add or 0) >= limit:
            # 已超限 → 撤销刚才的 add, 保持一致
            client.zrem(redis_key, member)
            return True
        return False
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning(
            "rate_limit_burst: Redis check 失败, 退回内存: %s", exc
        )
        return check_burst(_redis_fallback_buckets[redis_key], window_seconds, limit)


# Redis 不可用 / 故障时的 fallback bucket (与主 buckets 分离, 避免污染)
_redis_fallback_buckets: dict[str, deque[float]] = defaultdict(deque)
