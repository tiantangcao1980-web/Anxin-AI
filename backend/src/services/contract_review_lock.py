"""Contract review lock helpers."""

import asyncio
import secrets
from dataclasses import dataclass, field
from typing import Any, cast

from loguru import logger

from src.core.config import settings


class ContractReviewLockError(RuntimeError):
    """Base class for contract review lock failures."""


class ContractReviewAlreadyRunning(ContractReviewLockError):  # noqa: N818
    """Raised when another review is already running for the same contract round."""


class ContractReviewLockUnavailable(ContractReviewLockError):  # noqa: N818
    """Raised when the lock backend cannot be used safely."""


_LOCAL_LOCK = asyncio.Lock()
_LOCAL_LOCKS: dict[str, str] = {}


@dataclass(slots=True)
class ContractReviewLock:
    """Redis-backed review lock with development/test local fallback."""

    redis_url: str | None = None
    _redis: Any | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.redis_url = self.redis_url or settings.REDIS_URL

    async def acquire(self, key: str, ttl_seconds: int) -> str:
        token = secrets.token_urlsafe(24)
        redis_client = await self._get_redis_or_none()
        if redis_client is not None:
            try:
                acquired = await redis_client.set(key, token, nx=True, ex=ttl_seconds)
            except Exception as exc:
                raise ContractReviewLockUnavailable("合同审查锁服务不可用") from exc
            if not acquired:
                raise ContractReviewAlreadyRunning("合同正在审查中，请稍后重试")
            return token

        async with _LOCAL_LOCK:
            if key in _LOCAL_LOCKS:
                raise ContractReviewAlreadyRunning("合同正在审查中，请稍后重试")
            _LOCAL_LOCKS[key] = token
        return token

    async def release(self, key: str, token: str) -> None:
        redis_client = await self._get_redis_or_none()
        if redis_client is not None:
            script = """
            if redis.call('GET', KEYS[1]) == ARGV[1] then
                return redis.call('DEL', KEYS[1])
            end
            return 0
            """
            try:
                await redis_client.eval(script, 1, key, token)
            except Exception as exc:
                logger.warning("释放合同审查 Redis 锁失败: {}", exc)
            return

        async with _LOCAL_LOCK:
            if _LOCAL_LOCKS.get(key) == token:
                _LOCAL_LOCKS.pop(key, None)

    async def _get_redis_or_none(self) -> Any | None:
        backend = settings.CONTRACT_REVIEW_LOCK_BACKEND.lower()
        if backend == "local":
            return None
        if not self.redis_url:
            return None
        if backend == "redis" or settings.ENVIRONMENT in {"production", "staging"}:
            return await self._get_redis()
        if backend == "auto":
            return None

        try:
            return await self._get_redis()
        except Exception as exc:
            logger.warning("合同审查锁使用本地开发兜底: {}", exc)
            return None

    async def _get_redis(self) -> Any:
        if self._redis is None:
            import redis.asyncio as redis

            redis_module = cast(Any, redis)
            self._redis = redis_module.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=3,
            )
            await self._redis.ping()
        return self._redis
