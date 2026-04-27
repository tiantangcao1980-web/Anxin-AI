# -*- coding: utf-8 -*-
"""
HeadlessXClient 主路径测试 — render / screenshot / pdf / health

策略：用 httpx.MockTransport 拦截 HTTP，避免依赖真实 HeadlessX。
"""

from __future__ import annotations

import base64
import json

import httpx
import pytest

from src.services.fetch.headlessx_client import (
    HeadlessXAuthError,
    HeadlessXClient,
    HeadlessXClientError,
    HeadlessXError,
)


# ============ 测试辅助 ============

def _make_client(handler) -> HeadlessXClient:
    """构造一个用 MockTransport 的 HeadlessXClient。"""
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
        http_client=http_client,
    )


PNG_BYTES = b"\x89PNG\r\n\x1a\nfake-png"
PDF_BYTES = b"%PDF-1.4 fake"


# ============ render ============

@pytest.mark.asyncio
async def test_render_success_minimal():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/render"
        assert request.headers["x-api-key"] == "test-key"
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "url": "https://example.com",
                "finalUrl": "https://example.com/",
                "statusCode": 200,
                "html": "<html><body>OK</body></html>",
                "cookies": [],
                "durationMs": 234,
                "botScore": 0.12,
            },
        )

    client = _make_client(handler)
    try:
        result = await client.render("https://example.com")
    finally:
        await client.aclose()

    assert result.status_code == 200
    assert result.html == "<html><body>OK</body></html>"
    assert result.bot_score == 0.12
    assert result.is_blocked is False
    assert captured["body"]["url"] == "https://example.com"
    assert captured["body"]["viewport"] == {"width": 1920, "height": 1080}
    # 默认参数不应注入空 selector
    assert "waitForSelector" not in captured["body"]


@pytest.mark.asyncio
async def test_render_passes_advanced_options():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "url": "https://x.com",
                "finalUrl": "https://x.com",
                "statusCode": 200,
                "html": "",
                "screenshot": base64.b64encode(PNG_BYTES).decode(),
                "cookies": [{"name": "a", "value": "1"}],
                "durationMs": 100,
            },
        )

    client = _make_client(handler)
    try:
        result = await client.render(
            "https://x.com",
            wait_for_selector=".loaded",
            wait_ms=200,
            screenshot=True,
            full_page=False,
            viewport=(1280, 720),
            user_agent="custom-ua",
            proxy="socks5://127.0.0.1:1080",
            cookies=[{"name": "session", "value": "abc"}],
            headers={"X-Custom": "1"},
            execute_js="window.scrollTo(0, 1000)",
        )
    finally:
        await client.aclose()

    body = captured["body"]
    assert body["waitForSelector"] == ".loaded"
    assert body["waitMs"] == 200
    assert body["screenshot"] is True
    assert body["fullPage"] is False
    assert body["viewport"] == {"width": 1280, "height": 720}
    assert body["userAgent"] == "custom-ua"
    assert body["proxy"] == "socks5://127.0.0.1:1080"
    assert body["cookies"] == [{"name": "session", "value": "abc"}]
    assert body["headers"] == {"X-Custom": "1"}
    assert body["executeJs"] == "window.scrollTo(0, 1000)"

    assert result.screenshot_png == PNG_BYTES
    assert result.cookies == [{"name": "a", "value": "1"}]


@pytest.mark.asyncio
async def test_render_bot_score_blocked():
    """bot_score >= 0.7 → is_blocked True。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "url": "https://blocked.com",
                "finalUrl": "https://blocked.com",
                "statusCode": 200,
                "html": "<html>captcha</html>",
                "botScore": 0.85,
            },
        )

    client = _make_client(handler)
    try:
        result = await client.render("https://blocked.com")
    finally:
        await client.aclose()

    assert result.bot_score == 0.85
    assert result.is_blocked is True


# ============ screenshot ============

@pytest.mark.asyncio
async def test_screenshot_returns_bytes():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["screenshot"] is True
        return httpx.Response(
            200,
            json={
                "url": "https://x.com",
                "finalUrl": "https://x.com",
                "statusCode": 200,
                "html": "",
                "screenshot": base64.b64encode(PNG_BYTES).decode(),
            },
        )

    client = _make_client(handler)
    try:
        png = await client.screenshot("https://x.com")
    finally:
        await client.aclose()
    assert png == PNG_BYTES


@pytest.mark.asyncio
async def test_screenshot_missing_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "url": "https://x.com",
                "finalUrl": "https://x.com",
                "statusCode": 200,
                "html": "",
                # 缺 screenshot 字段
            },
        )

    client = _make_client(handler)
    try:
        with pytest.raises(HeadlessXError):
            await client.screenshot("https://x.com")
    finally:
        await client.aclose()


# ============ pdf ============

@pytest.mark.asyncio
async def test_pdf_returns_bytes():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["pdf"] is True
        return httpx.Response(
            200,
            json={
                "url": "https://x.com",
                "finalUrl": "https://x.com",
                "statusCode": 200,
                "html": "",
                "pdf": base64.b64encode(PDF_BYTES).decode(),
            },
        )

    client = _make_client(handler)
    try:
        pdf = await client.pdf("https://x.com")
    finally:
        await client.aclose()
    assert pdf == PDF_BYTES


# ============ health ============

@pytest.mark.asyncio
async def test_health():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        return httpx.Response(200, json={"status": "ok", "queue": 2})

    client = _make_client(handler)
    try:
        h = await client.health()
    finally:
        await client.aclose()
    assert h["status"] == "ok"
    assert h["queue"] == 2


# ============ 鉴权 / 客户端错误 ============

@pytest.mark.asyncio
async def test_render_401_raises_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid api key"})

    client = _make_client(handler)
    try:
        with pytest.raises(HeadlessXAuthError) as ei:
            await client.render("https://x.com")
        assert ei.value.status_code == 401
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_render_400_raises_client_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "bad url"})

    client = _make_client(handler)
    try:
        with pytest.raises(HeadlessXClientError) as ei:
            await client.render("not-a-url")
        assert ei.value.status_code == 400
    finally:
        await client.aclose()


# ============ 构造校验 ============

def test_client_requires_base_url():
    with pytest.raises(ValueError):
        HeadlessXClient(base_url="", api_key="k")


def test_client_requires_api_key():
    with pytest.raises(ValueError):
        HeadlessXClient(base_url="http://x", api_key="")
