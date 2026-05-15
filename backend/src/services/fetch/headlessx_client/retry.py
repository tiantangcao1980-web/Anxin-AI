"""
HeadlessX 客户端重试策略。

仅对**可恢复**异常做指数退避：
- HeadlessXRateLimitError (429)
- HeadlessXTimeoutError    (5xx 渲染超时 / 网络 timeout)
- HeadlessXServerError     (5xx 后端错误)

不重试：
- HeadlessXAuthError    (401/403)
- HeadlessXClientError  (4xx 参数错)
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from .exceptions import (
    HeadlessXAuthError,
    HeadlessXClientError,
    HeadlessXError,
    HeadlessXRateLimitError,
    HeadlessXServerError,
    HeadlessXTimeoutError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

RETRYABLE: tuple[type[Exception], ...] = (
    HeadlessXTimeoutError,
    HeadlessXRateLimitError,
    HeadlessXServerError,
)
NON_RETRYABLE: tuple[type[Exception], ...] = (
    HeadlessXAuthError,
    HeadlessXClientError,
)


class RetryConfig:
    """指数退避配置。

    base_delay * (2 ** attempt) + jitter，封顶 max_delay。
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        jitter: float = 0.3,
    ) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def compute_delay(self, attempt: int, retry_after: float | None = None) -> float:
        """计算第 attempt 次（从 0 起）重试前的等待秒数。

        若服务端返回了 Retry-After，优先尊重它（HeadlessX 限流要求）。
        """
        if retry_after is not None and retry_after > 0:
            return min(retry_after, self.max_delay)
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        # 抖动避免 thundering herd
        jitter_amount = delay * self.jitter * random.random()
        return delay + jitter_amount


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    config: RetryConfig | None = None,
) -> T:
    """执行 async 函数 fn，按 RetryConfig 重试。

    用法::

        result = await with_retry(lambda: client._post("/render", payload))
    """
    cfg = config or RetryConfig()
    last_exc: Exception | None = None

    for attempt in range(cfg.max_attempts):
        try:
            return await fn()
        except NON_RETRYABLE:
            # 立即放弃 — 上层处理
            raise
        except RETRYABLE as exc:
            last_exc = exc
            if attempt + 1 >= cfg.max_attempts:
                logger.warning(
                    "HeadlessX retry exhausted attempts=%d last=%r",
                    cfg.max_attempts,
                    exc,
                )
                raise
            retry_after: float | None = None
            if isinstance(exc, HeadlessXRateLimitError):
                retry_after = exc.retry_after
            delay = cfg.compute_delay(attempt, retry_after=retry_after)
            logger.info(
                "HeadlessX retry attempt=%d/%d delay=%.2fs reason=%s",
                attempt + 1,
                cfg.max_attempts,
                delay,
                type(exc).__name__,
            )
            await asyncio.sleep(delay)
        except HeadlessXError:
            # 未分类的 HeadlessXError：默认不重试
            raise

    # 理论上不可达
    assert last_exc is not None
    raise last_exc
