"""fetch 路由 4 endpoint 集成测试 — 全部 mock，不发真实网络请求。"""

from __future__ import annotations

import socket
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from src.services.fetch.models import (
    FetchRequest,
    FetchResponse,
    FetchTier,
)


# P16-B: 路由层会做 SSRF DNS 校验；测试环境 DNS 可能解析到 198.18/15 测试网段
# (被 is_reserved 拦截)。统一 mock 成公网 IP，让 mock 的 service 调用得以发生。
@pytest.fixture(autouse=True)
def _mock_ssrf_dns():
    fake = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]
    with patch("src.services.fetch.ssrf_guard.socket.getaddrinfo", return_value=fake):
        yield


def _mock_response(url: str, **overrides) -> FetchResponse:
    base = {
        "request": FetchRequest(url=url),
        "status_code": 200,
        "headers": {},
        "body": b"<html>ok</html>",
        "text": "<html>ok</html>",
        "tier_used": FetchTier.L1_HTTP,
        "duration_ms": 12,
        "extracted": {"_text": "ok"},
    }
    base.update(overrides)
    return FetchResponse(**base)


@pytest.mark.asyncio
async def test_post_fetch_returns_response(auth_client: AsyncClient) -> None:
    fake = _mock_response("https://www.npc.gov.cn/abc")
    with patch("src.api.routes.fetch.fetch_service.fetch", new=AsyncMock(return_value=fake)):
        resp = await auth_client.post(
            "/api/v1/fetch",
            json={
                "url": "https://www.npc.gov.cn/abc",
                "extract": {"css_selectors": {"title": "h1"}, "format": "text"},
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["url"] == "https://www.npc.gov.cn/abc"
    assert body["status_code"] == 200
    assert body["tier_used"] == "L1_HTTP"
    assert body["ok"] is True


@pytest.mark.asyncio
async def test_post_fetch_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/fetch", json={"url": "https://example.com"})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_post_fetch_batch(auth_client: AsyncClient) -> None:
    urls = ["https://www.npc.gov.cn/a", "https://www.iyiou.com/b"]
    fakes = [_mock_response(u) for u in urls]

    async def _batch_mock(reqs, concurrency=5):
        return fakes

    with patch(
        "src.api.routes.fetch.fetch_service.fetch_batch",
        new=AsyncMock(side_effect=_batch_mock),
    ):
        resp = await auth_client.post(
            "/api/v1/fetch/batch",
            json={"requests": [{"url": u} for u in urls], "concurrency": 3},
        )
    assert resp.status_code == 200
    arr = resp.json()
    assert len(arr) == 2
    assert {item["url"] for item in arr} == set(urls)


@pytest.mark.asyncio
async def test_post_fetch_batch_size_limit(auth_client: AsyncClient) -> None:
    payload = {"requests": [{"url": f"https://example.com/{i}"} for i in range(101)]}
    resp = await auth_client.post("/api/v1/fetch/batch", json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_compliance_check_blocked(auth_client: AsyncClient) -> None:
    resp = await auth_client.get(
        "/api/v1/fetch/compliance/check",
        params={"url": "https://wenshu.court.gov.cn/abc"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["blocked"] is True
    assert body["block_reason"]["code"] == "WENSHU_FORBIDDEN"


@pytest.mark.asyncio
async def test_get_compliance_check_invalid_url(auth_client: AsyncClient) -> None:
    resp = await auth_client.get(
        "/api/v1/fetch/compliance/check",
        params={"url": "not-a-url"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_audit_requires_admin(auth_client: AsyncClient) -> None:
    """普通用户访问 /audit 应被拒绝。"""
    resp = await auth_client.get("/api/v1/fetch/audit")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_audit_admin_succeeds(admin_auth_client: AsyncClient) -> None:
    fake_records: list = []
    fake_stats = {
        "total": 0,
        "blocked": 0,
        "errors": 0,
        "tier_L0_CACHE": 0,
        "tier_L1_HTTP": 0,
        "tier_L2_CRAWL4AI": 0,
        "tier_L3_HEADLESSX": 0,
        "tier_L4_OFFICIAL_API": 0,
    }
    with (
        patch(
            "src.api.routes.fetch.fetch_service.get_audit_logs",
            new=AsyncMock(return_value=fake_records),
        ),
        patch(
            "src.api.routes.fetch.fetch_service.get_audit_stats",
            new=AsyncMock(return_value=fake_stats),
        ),
    ):
        resp = await admin_auth_client.get("/api/v1/fetch/audit")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["stats"]["total"] == 0
