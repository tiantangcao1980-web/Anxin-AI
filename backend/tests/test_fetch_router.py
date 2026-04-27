# -*- coding: utf-8 -*-
"""URL → Tier 路由规则单测（纯函数，无 IO）。"""

from __future__ import annotations

import pytest

from src.services.fetch.models import FetchRequest, FetchTier
from src.services.fetch.router import (
    is_l1_gov,
    is_l3_domain,
    is_static_feed,
    route,
)


@pytest.mark.parametrize(
    "url,expected",
    [
        # 政府 / 司法 → L1
        ("https://www.npc.gov.cn/abc", FetchTier.L1_HTTP),
        ("https://www.court.gov.cn/case/123", FetchTier.L1_HTTP),
        ("https://www.miit.gov.cn/policy", FetchTier.L1_HTTP),
        ("https://www.creditchina.gov.cn/info", FetchTier.L1_HTTP),
        # RSS / atom / sitemap → L1
        ("https://example.com/feed", FetchTier.L1_HTTP),
        ("https://example.com/rss/news.xml", FetchTier.L1_HTTP),
        ("https://example.com/sitemap.xml", FetchTier.L1_HTTP),
        ("https://example.com/atom.xml", FetchTier.L1_HTTP),
        # 强反爬电商 → L3
        ("https://www.amazon.com/dp/B0001", FetchTier.L3_HEADLESSX),
        ("https://detail.1688.com/offer/abc.html", FetchTier.L3_HEADLESSX),
        ("https://test-shop.myshopify.com/products/x", FetchTier.L3_HEADLESSX),
        ("https://www.tiktok.com/@user", FetchTier.L3_HEADLESSX),
        ("https://shopee.com/foo", FetchTier.L3_HEADLESSX),
        # 默认 → L2
        ("https://www.iyiou.com/news/123", FetchTier.L2_CRAWL4AI),
        ("https://example.com/article", FetchTier.L2_CRAWL4AI),
    ],
)
def test_route_default_rules(url: str, expected: FetchTier) -> None:
    req = FetchRequest(url=url)
    assert route(req) == expected


def test_route_tier_hint_overrides() -> None:
    req = FetchRequest(
        url="https://www.amazon.com/dp/B0001",
        tier_hint=FetchTier.L1_HTTP,
    )
    assert route(req) == FetchTier.L1_HTTP


def test_is_l3_domain_subdomain_match() -> None:
    assert is_l3_domain("test-shop.myshopify.com")
    assert is_l3_domain("www.amazon.com")
    assert is_l3_domain("amazon.com")
    assert not is_l3_domain("example.com")


def test_is_l1_gov_subdomain_match() -> None:
    assert is_l1_gov("www.npc.gov.cn")
    assert is_l1_gov("policy.miit.gov.cn")
    assert not is_l1_gov("example.com")


def test_is_static_feed_path_hints() -> None:
    assert is_static_feed("/feed")
    assert is_static_feed("/rss/abc")
    assert is_static_feed("/sitemap.xml")
    assert is_static_feed("/atom.xml")
    assert not is_static_feed("/article/123.html")
