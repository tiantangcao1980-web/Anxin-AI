# -*- coding: utf-8 -*-
"""
HeadlessXClient 重试策略测试。

覆盖：
- 429 + Retry-After → 退避后重试成功
- 503 → 指数退避重试成功
- 持续 5xx → 重试耗尽抛 HeadlessXServerError
- 401 出现在重试链路中 → 立即抛 HeadlessXAuthError，不再重试
- with_retry 函数的纯单元测试
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from src.services.fetch.headlessx_client import (
    HeadlessXAuthError,
    HeadlessXClient,
    HeadlessXRateLimitError,
    HeadlessXServerError,
    HeadlessXTimeoutError,
    RetryConfig,
    with_retry,
)


def _ok_payload() -> dict:
    return {
        "url": "https://x.com",
        "finalUrl": "https://x.com",
        "statusCode": 200,
        "html": "OK",
    }


def _make_client(handler, retry_config: RetryConfig | None = None) -> HeadlessXClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(
        base_url="http://headlessx-test:3000",
        transport=transport,
        headers={"x-api-key": "test-key"},
        timeout=10,
    )
    return HeadlessXClient(
        base_url="http://headlessx-test:3000",
        api_key="test-key",
        timeout=10,
        retry_config=retry_config or RetryConfig(
            max_attempts=3, base_delay=0.01, max_delay=0.1, jitter=0.0
        ),
        http_client=http_client,
    )


# ============ 重试成功路径 ============

@pytest.mark.asyncio
async def test_retry_on_429_then_success():
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["calls"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0.01"}, json={})
        return httpx.Response(200, json=_ok_payload())

    client = _make_client(handler)
    try:
        result = await client.render("https://x.com")
    finally:
        await client.aclose()
    assert result.status_code == 200
    assert state["calls"] == 2


@pytest.mark.asyncio
async def test_retry_on_503_then_success():
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["calls"] < 3:
            return httpx.Response(503, json={"error": "down"})
        return httpx.Response(200, json=_ok_payload())

    client = _make_client(handler)
    try:
        result = await client.render("https://x.com")
    finally:
        await client.aclose()
    assert result.status_code == 200
    assert state["calls"] == 3


# ============ 重试耗尽 ============

@pytest.mark.asyncio
async def test_retry_exhausts_on_persistent_503():
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        return httpx.Response(503, json={"error": "down"})

    client = _make_client(handler)
    try:
        with pytest.raises(HeadlessXServerError):
            await client.render("https://x.com")
    finally:
        await client.aclose()
    assert state["calls"] == 3  # max_attempts


@pytest.mark.asyncio
async def test_retry_exhausts_on_persistent_429():
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        return httpx.Response(429, headers={"Retry-After": "0.01"}, json={})

    client = _make_client(handler)
    try:
        with pytest.raises(HeadlessXRateLimitError) as ei:
            await client.render("https://x.com")
        assert ei.value.retry_after == 0.01
    finally:
        await client.aclose()
    assert state["calls"] == 3


# ============ 不可重试异常立即终止 ============

@pytest.mark.asyncio
async def test_auth_error_aborts_retry_immediately():
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        return httpx.Response(401, json={"error": "bad key"})

    client = _make_client(handler)
    try:
        with pytest.raises(HeadlessXAuthError):
            await client.render("https://x.com")
    finally:
        await client.aclose()
    assert state["calls"] == 1  # 不重试


# ============ 504 → TimeoutError ============

@pytest.mark.asyncio
async def test_504_classified_as_timeout_and_retried():
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        return httpx.Response(504)

    client = _make_client(handler)
    try:
        with pytest.raises(HeadlessXTimeoutError):
            await client.render("https://x.com")
    finally:
        await client.aclose()
    assert state["calls"] == 3


# ============ with_retry 纯函数测试 ============

@pytest.mark.asyncio
async def test_with_retry_succeeds_after_retries():
    state = {"calls": 0}

    async def fn():
        state["calls"] += 1
        if state["calls"] < 2:
            raise HeadlessXServerError("flaky", status_code=500)
        return "ok"

    result = await with_retry(
        fn,
        RetryConfig(max_attempts=3, base_delay=0.01, max_delay=0.1, jitter=0.0),
    )
    assert result == "ok"
    assert state["calls"] == 2


@pytest.mark.asyncio
async def test_with_retry_does_not_retry_auth_error():
    state = {"calls": 0}

    async def fn():
        state["calls"] += 1
        raise HeadlessXAuthError("nope")

    with pytest.raises(HeadlessXAuthError):
        await with_retry(
            fn,
            RetryConfig(max_attempts=5, base_delay=0.01, max_delay=0.1, jitter=0.0),
        )
    assert state["calls"] == 1


def test_compute_delay_uses_retry_after():
    cfg = RetryConfig(base_delay=10, max_delay=30, jitter=0.0)
    # retry_after 优先
    assert cfg.compute_delay(0, retry_after=2.0) == 2.0
    # retry_after > max_delay 时被 cap
    assert cfg.compute_delay(0, retry_after=999) == 30.0


def test_compute_delay_exponential():
    cfg = RetryConfig(base_delay=1, max_delay=100, jitter=0.0)
    assert cfg.compute_delay(0) == 1
    assert cfg.compute_delay(1) == 2
    assert cfg.compute_delay(2) == 4
    assert cfg.compute_delay(3) == 8
