"""per-domain QPS 限流单测。"""

from __future__ import annotations

import asyncio
import time

import pytest

from src.services.fetch.rate_limiter import PerDomainRateLimiter


@pytest.mark.asyncio
async def test_first_token_immediate_due_to_full_bucket() -> None:
    limiter = PerDomainRateLimiter(default_qps=2.0)
    start = time.monotonic()
    ok = await limiter.acquire("example.com", timeout=1.0)
    elapsed = time.monotonic() - start
    assert ok is True
    assert elapsed < 0.1


@pytest.mark.asyncio
async def test_burst_then_throttled() -> None:
    """容量 = qps*2 = 4，前 4 次秒内通过；第 5 次需等待 ~0.5s（qps=2）。"""
    limiter = PerDomainRateLimiter(default_qps=2.0)
    start = time.monotonic()
    for _ in range(4):
        assert await limiter.acquire("example.com", timeout=2.0) is True
    burst_elapsed = time.monotonic() - start
    assert burst_elapsed < 0.2  # 突发应该秒过

    # 第 5 次：必须等令牌补充
    start2 = time.monotonic()
    assert await limiter.acquire("example.com", timeout=2.0) is True
    wait_elapsed = time.monotonic() - start2
    assert wait_elapsed >= 0.3  # ~0.5s（qps=2 → 0.5s/token）


@pytest.mark.asyncio
async def test_different_hosts_independent() -> None:
    limiter = PerDomainRateLimiter(default_qps=1.0)
    # 把 host A 的桶耗尽
    for _ in range(2):
        await limiter.acquire("a.com", timeout=1.0)

    # host B 不受影响
    start = time.monotonic()
    ok = await limiter.acquire("b.com", timeout=1.0)
    elapsed = time.monotonic() - start
    assert ok is True
    assert elapsed < 0.1


@pytest.mark.asyncio
async def test_acquire_timeout_returns_false() -> None:
    limiter = PerDomainRateLimiter(default_qps=0.1)  # 10s/token
    # 耗光初始 2 个令牌
    for _ in range(2):
        assert await limiter.acquire("slow.com", timeout=1.0) is True
    # 第 3 次 timeout 必然失败
    start = time.monotonic()
    ok = await limiter.acquire("slow.com", timeout=0.5)
    elapsed = time.monotonic() - start
    assert ok is False
    assert elapsed < 1.5


@pytest.mark.asyncio
async def test_configure_changes_rate() -> None:
    limiter = PerDomainRateLimiter(default_qps=0.1)
    # 先耗光
    for _ in range(2):
        await limiter.acquire("foo.com", timeout=1.0)

    # 提到 100 QPS — 下一次应几乎立即拿到
    limiter.configure("foo.com", 100.0)
    await asyncio.sleep(0.05)  # 让令牌补充
    start = time.monotonic()
    ok = await limiter.acquire("foo.com", timeout=1.0)
    assert ok is True
    assert time.monotonic() - start < 0.1
