"""Crawler compliance gate regression tests."""

import time
import urllib.robotparser

import pytest
from sqlalchemy import select

from src.config.crawler import LEGAL_CRAWLER_USER_AGENT
from src.core.config import settings
from src.models import AgentAuditEvent
from src.services.agent_governance_service import AgentGovernanceService
from src.services.crawler_service import (
    BROWSER_FETCH_ROUTE_SCOPE,
    CrawlerComplianceError,
    CrawlerRouteAuthorizationError,
    CrawlerService,
)


def _allow_public_dns(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.services.crawler_service.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
    )


async def _allowing_robot_parser(_url: str):
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(["User-agent: *", "Allow: /"])
    return parser


@pytest.mark.asyncio
async def test_crawler_rejects_non_whitelisted_host(monkeypatch):
    monkeypatch.setattr(settings, "LIC_ALLOWED_HOSTS", ["court.gov.cn"], raising=False)
    service = CrawlerService()

    with pytest.raises(CrawlerComplianceError):
        await service.fetch("https://example.com/legal", dry_run=True)


@pytest.mark.asyncio
async def test_crawler_respects_robots_disallow(monkeypatch):
    _allow_public_dns(monkeypatch)
    monkeypatch.setattr(settings, "LIC_ALLOWED_HOSTS", ["court.gov.cn"], raising=False)
    service = CrawlerService()

    async def disallowing_robot_parser(_url: str):
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(["User-agent: *", "Disallow: /blocked"])
        return parser

    monkeypatch.setattr(service, "_get_robot_parser", disallowing_robot_parser)

    with pytest.raises(CrawlerComplianceError, match="robots"):
        await service.fetch("https://www.court.gov.cn/blocked", dry_run=True)


@pytest.mark.asyncio
async def test_crawler_dry_run_records_ua_and_host_rate_limit(monkeypatch):
    _allow_public_dns(monkeypatch)
    monkeypatch.setattr(settings, "LIC_ALLOWED_HOSTS", ["court.gov.cn"], raising=False)
    service = CrawlerService()
    service._host_last_request_at["www.court.gov.cn"] = time.monotonic()
    sleeps: list[float] = []

    monkeypatch.setattr(service, "_get_robot_parser", _allowing_robot_parser)

    async def fake_sleep(seconds: float):
        sleeps.append(seconds)

    monkeypatch.setattr(service, "_sleep", fake_sleep)

    result = await service.fetch("https://www.court.gov.cn/fabu.html", dry_run=True)

    assert result["success"] is True
    assert result["text"] == ""
    assert result["compliance"]["user_agent"] == LEGAL_CRAWLER_USER_AGENT
    assert result["compliance"]["robots_allowed"] is True
    assert sleeps and sleeps[0] >= 0.5


@pytest.mark.asyncio
async def test_crawler_fetch_uses_legal_user_agent(monkeypatch):
    _allow_public_dns(monkeypatch)
    monkeypatch.setattr(settings, "LIC_ALLOWED_HOSTS", ["court.gov.cn"], raising=False)
    service = CrawlerService()
    captured: dict[str, str] = {}

    monkeypatch.setattr(service, "_get_robot_parser", _allowing_robot_parser)

    class Response:
        status_code = 200
        text = "<html><title>ok</title><body>content</body></html>"
        url = "https://www.court.gov.cn/fabu.html"

    async def fake_http_get(_url: str, _timeout: float, headers: dict[str, str]):
        captured.update(headers)
        return Response()

    monkeypatch.setattr(service, "_http_get", fake_http_get)

    result = await service.fetch("https://www.court.gov.cn/fabu.html")

    assert result["status_code"] == 200
    assert captured["User-Agent"] == LEGAL_CRAWLER_USER_AGENT


@pytest.mark.asyncio
async def test_crawler_fetch_requires_route_token_in_commercial_environment(monkeypatch):
    _allow_public_dns(monkeypatch)
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(settings, "BROWSER_FETCH_ROUTE_TOKEN_REQUIRED", False)
    monkeypatch.setattr(settings, "LIC_ALLOWED_HOSTS", ["court.gov.cn"], raising=False)
    service = CrawlerService()

    async def should_not_fetch_robots(_url: str):
        raise AssertionError("route authorization must happen before robots fetch")

    monkeypatch.setattr(service, "_get_robot_parser", should_not_fetch_robots)

    with pytest.raises(CrawlerRouteAuthorizationError, match="Browser route token required"):
        await service.fetch("https://www.court.gov.cn/fabu.html")


@pytest.mark.asyncio
async def test_crawler_fetch_uses_db_backed_route_token(monkeypatch, db_session, test_organization):
    _allow_public_dns(monkeypatch)
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(settings, "LIC_ALLOWED_HOSTS", ["court.gov.cn"], raising=False)
    service = CrawlerService()
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="browser-fetch",
        route_type="browser",
        allowed_consumers=["browser-worker"],
        allowed_scopes=[BROWSER_FETCH_ROUTE_SCOPE],
    )
    issued = await governance.issue_route_token(
        org_id=test_organization.id,
        route_key="browser-fetch",
        consumer_id="browser-worker",
        requested_scopes=[BROWSER_FETCH_ROUTE_SCOPE],
    )

    monkeypatch.setattr(service, "_get_robot_parser", _allowing_robot_parser)

    class Response:
        status_code = 200
        text = "<html><title>ok</title><body>content</body></html>"
        url = "https://www.court.gov.cn/fabu.html"

    async def fake_http_get(_url: str, _timeout: float, _headers: dict[str, str]):
        return Response()

    monkeypatch.setattr(service, "_http_get", fake_http_get)

    result = await service.fetch(
        "https://www.court.gov.cn/fabu.html",
        org_id=test_organization.id,
        route_token=issued.token,
        consumer_id="browser-worker",
        db=db_session,
    )
    audits = (
        (
            await db_session.execute(
                select(AgentAuditEvent).where(AgentAuditEvent.org_id == test_organization.id)
            )
        )
        .scalars()
        .all()
    )

    assert result["success"] is True
    assert result["status_code"] == 200
    assert [event.reason_code for event in audits] == ["issued", "allowed"]


@pytest.mark.asyncio
async def test_crawler_fetch_fails_after_route_revocation(
    monkeypatch, db_session, test_organization
):
    _allow_public_dns(monkeypatch)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "LIC_ALLOWED_HOSTS", ["court.gov.cn"], raising=False)
    service = CrawlerService()
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="browser-fetch-revoked",
        route_type="browser",
        allowed_consumers=["browser-worker"],
        allowed_scopes=[BROWSER_FETCH_ROUTE_SCOPE],
    )
    issued = await governance.issue_route_token(
        org_id=test_organization.id,
        route_key="browser-fetch-revoked",
        consumer_id="browser-worker",
        requested_scopes=[BROWSER_FETCH_ROUTE_SCOPE],
    )
    await governance.revoke_capability_route(
        org_id=test_organization.id,
        route_key="browser-fetch-revoked",
        reason="owner_revoked",
    )

    async def should_not_fetch_robots(_url: str):
        raise AssertionError("revoked route must fail before robots fetch")

    monkeypatch.setattr(service, "_get_robot_parser", should_not_fetch_robots)

    with pytest.raises(CrawlerRouteAuthorizationError, match="capability_route_revoked"):
        await service.fetch(
            "https://www.court.gov.cn/fabu.html",
            org_id=test_organization.id,
            route_token=issued.token,
            consumer_id="browser-worker",
            db=db_session,
        )
