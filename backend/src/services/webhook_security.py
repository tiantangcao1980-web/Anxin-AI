"""Shared webhook signature and replay protection helpers.

P16-C 安全加固（2026-04-28）：
    - 之前的 ``_seen_signatures: dict`` 仅在单进程内存生效，多 worker 部署
      下攻击者可通过负载均衡轮询绕过 replay 检测；改为 Redis ``SETNX`` +
      TTL（默认 600s）。
    - Redis 不可用时 fail-closed：直接拒绝所有 webhook，避免回退到内存
      cache 时的安全降级。
    - ``verify`` 改为 async；旧的同步入口保留为 ``verify_sync`` 兜底（仅
      用于非 async 上下文，例如脚本调用）。
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import time
from typing import Any

from loguru import logger

from src.core.config import settings

# Redis client 单例（lazy 初始化）。测试时可以通过 _set_redis_client_for_test
# 注入 mock 或 fakeredis 实例。
_redis_client: Any = None
_redis_lock: asyncio.Lock | None = None


async def _get_redis() -> Any:
    """惰性创建 Redis 客户端。失败抛 RuntimeError → 调用方 fail-closed。"""
    global _redis_client, _redis_lock
    if _redis_client is not None:
        return _redis_client
    if _redis_lock is None:
        _redis_lock = asyncio.Lock()
    async with _redis_lock:
        if _redis_client is not None:
            return _redis_client
        try:
            import redis.asyncio as aioredis  # noqa: WPS433

            redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
            client = aioredis.from_url(redis_url, decode_responses=True)
            await client.ping()
            _redis_client = client
            return _redis_client
        except Exception as e:
            raise RuntimeError(f"webhook replay cache Redis unavailable: {e}") from e


def _set_redis_client_for_test(client: Any) -> None:
    """测试 hook：注入一个 mock / fakeredis client 或 ``None`` 模拟不可用。"""
    global _redis_client
    _redis_client = client


def _replay_key(scope: str, signature: str) -> str:
    """统一的 replay key 命名：``webhook:replay:{scope}:{signature_hash}``。"""
    sig_hash = hashlib.sha256(signature.encode("utf-8")).hexdigest()
    return f"webhook:replay:{scope}:{sig_hash}"


class WebhookSecurity:
    # 兼容性占位（已不再用作生产 replay cache，仅为旧测试可读到属性）
    _seen_signatures: dict[str, float] = {}

    @classmethod
    async def verify(
        cls,
        *,
        scope: str,
        body: bytes,
        signature: str | None,
        secret: str | None,
        timestamp: str | None,
    ) -> bool:
        """异步：HMAC + 新鲜度 + Redis SETNX replay。Redis 不可用 fail-closed。"""
        if not secret:
            return not settings.is_production()
        if not signature or not timestamp:
            return False

        try:
            ts_value = int(timestamp)
        except (TypeError, ValueError):
            logger.info(f"{scope} webhook timestamp 非法: {timestamp}")
            return False

        now = int(time.time())
        max_age = settings.WEBHOOK_SIGNATURE_MAX_AGE_SECONDS
        if abs(now - ts_value) > max_age:
            logger.info(f"{scope} webhook timestamp 过期: age={abs(now - ts_value)}")
            return False

        payload = f"{ts_value}.".encode() + body
        expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature.strip(), expected):
            return False

        key = _replay_key(scope, signature.strip())
        ttl = max(60, int(max_age) * 2)  # 至少覆盖 timestamp 窗口两倍
        try:
            redis = await _get_redis()
            ok = await redis.set(key, "1", ex=ttl, nx=True)
            if not ok:
                logger.warning(f"{scope} webhook 检测到重放 (Redis SETNX miss)")
                return False
        except Exception as e:
            logger.error(
                f"[WebhookSecurity] Redis 不可用，fail-closed 拒绝 webhook: {e}"
            )
            return False
        return True
