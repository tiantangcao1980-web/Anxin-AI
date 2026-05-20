"""
P19-A ObservabilityMiddleware 测试

覆盖：
- request_id 生成 / 透传
- prometheus 计时（counter +1，histogram observe）
- 慢请求 WARN 日志
- sentry breadcrumb 添加（mock sentry_sdk）
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.middleware.observability import REQUEST_ID_HEADER, ObservabilityMiddleware
from src.services.monitoring.prometheus_metrics import HTTP_REQUESTS_TOTAL


def _build_app(slow_threshold: float = 1.0) -> FastAPI:
    app = FastAPI()
    app.add_middleware(ObservabilityMiddleware, slow_threshold_seconds=slow_threshold)

    @app.get("/fast")
    async def fast():
        return {"ok": True}

    @app.get("/slow")
    async def slow():
        await asyncio.sleep(0.05)
        return {"ok": True}

    @app.get("/boom")
    async def boom():
        raise ValueError("boom")

    return app


# ==================== 1. request_id 自动生成 ====================
async def test_request_id_generated_when_absent():
    app = _build_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/fast")
    assert resp.status_code == 200
    rid = resp.headers.get(REQUEST_ID_HEADER)
    assert rid and len(rid) >= 8


async def test_request_id_propagated_when_provided():
    app = _build_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/fast", headers={REQUEST_ID_HEADER: "test-rid-123"})
    assert resp.headers[REQUEST_ID_HEADER] == "test-rid-123"


# ==================== 2. prometheus 计时 ====================
async def test_prometheus_counter_increments():
    app = _build_app()
    before = HTTP_REQUESTS_TOTAL.labels(method="GET", endpoint="/fast", status="200")._value.get()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/fast")
    assert resp.status_code == 200
    after = HTTP_REQUESTS_TOTAL.labels(method="GET", endpoint="/fast", status="200")._value.get()
    assert after == before + 1


# ==================== 3. 慢请求 WARN ====================
async def test_slow_request_emits_warn(caplog):
    """slow_threshold=0.01s，sleep 50ms 必然触发 WARN。"""
    app = _build_app(slow_threshold=0.01)

    captured = []

    def capture(message):
        captured.append(str(message))

    from loguru import logger as loguru_logger

    handler_id = loguru_logger.add(capture, level="WARNING")
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/slow")
        assert resp.status_code == 200
    finally:
        loguru_logger.remove(handler_id)

    assert any("slow-request" in m for m in captured)


# ==================== 4. sentry breadcrumb ====================
async def test_sentry_breadcrumb_added():
    """断言 sentry_sdk.add_breadcrumb 被调用（不需要真 SDK 启用）。"""
    app = _build_app()
    with (
        patch("sentry_sdk.add_breadcrumb") as mock_breadcrumb,
        patch("sentry_sdk.set_tag") as _mock_tag,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            await ac.get("/fast")
        assert mock_breadcrumb.called
        kwargs = mock_breadcrumb.call_args.kwargs
        assert kwargs["category"] == "http"
        assert kwargs["data"]["endpoint"] == "/fast"
        assert kwargs["data"]["status"] == 200
