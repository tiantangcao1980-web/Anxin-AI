# -*- coding: utf-8 -*-
"""L1HttpTier 单测 — mock httpx，验证 fetch + 抽取。"""

from __future__ import annotations

import httpx
import pytest

from src.services.fetch.models import (
    ExtractConfig,
    ExtractFormat,
    FetchRequest,
    FetchTier,
)
from src.services.fetch.tiers.l1_http import L1HttpTier


_HTML = """
<html><head><title>测试页</title></head>
<body>
  <h1 class="title">主标题</h1>
  <div class="article">
    <p class="para">段落 A</p>
    <p class="para">段落 B</p>
  </div>
  <a href="/x">链接</a>
</body></html>
"""


def _mock_transport(status: int = 200, body: str = _HTML) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text=body, headers={"content-type": "text/html"})

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_l1_basic_fetch_returns_text() -> None:
    client = httpx.AsyncClient(transport=_mock_transport())
    tier = L1HttpTier(client=client)

    resp = await tier.fetch(FetchRequest(url="https://example.com/"))

    assert resp.status_code == 200
    assert resp.tier_used == FetchTier.L1_HTTP
    assert resp.text is not None and "主标题" in resp.text
    assert resp.error is None
    await tier.aclose()


@pytest.mark.asyncio
async def test_l1_extract_with_css_selectors() -> None:
    client = httpx.AsyncClient(transport=_mock_transport())
    tier = L1HttpTier(client=client)

    resp = await tier.fetch(
        FetchRequest(
            url="https://example.com/",
            extract=ExtractConfig(
                css_selectors={"title": "h1.title", "paras": "p.para"},
                format=ExtractFormat.TEXT,
            ),
        )
    )

    assert resp.extracted is not None
    assert "主标题" in resp.extracted["title"]
    assert len(resp.extracted["paras"]) == 2
    assert "段落 A" in resp.extracted["paras"][0]
    assert "_text" in resp.extracted
    await tier.aclose()


@pytest.mark.asyncio
async def test_l1_timeout_returns_error_not_raise() -> None:
    def raising_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("simulated timeout", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(raising_handler))
    tier = L1HttpTier(client=client)

    resp = await tier.fetch(FetchRequest(url="https://example.com/", timeout=1))

    assert resp.status_code == 0
    assert resp.error is not None and "timeout" in resp.error.lower()
    await tier.aclose()


@pytest.mark.asyncio
async def test_l1_4xx_does_not_become_error() -> None:
    client = httpx.AsyncClient(transport=_mock_transport(status=404, body="not found"))
    tier = L1HttpTier(client=client)

    resp = await tier.fetch(FetchRequest(url="https://example.com/missing"))

    # 4xx 是有效的 HTTP 响应，不进入 error 字段
    assert resp.status_code == 404
    assert resp.error is None
    await tier.aclose()
