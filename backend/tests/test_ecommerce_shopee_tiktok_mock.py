# -*- coding: utf-8 -*-
"""Shopee + TikTok Shop mock source 测试（P6-D）。

补齐两个东南亚/短视频平台 mock 的契约测试，与 amazon/1688 的 mock 测试对称：

    - Shopee：5 条假商品分布在多国（VN/MY/TH/ID/PH），country 过滤命中
    - TikTok Shop：raw 含 viral_video_views + creator 字段，sort_by=newest
      按播放量降序
"""

from __future__ import annotations

import pytest

# SQLite/JSONB 兼容
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(JSONB, "sqlite")  # type: ignore[misc]
def _compile_jsonb_for_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


from src.services.fetch.sources.ecommerce.base import (  # noqa: E402
    ProductSearchQuery,
)
from src.services.fetch.sources.ecommerce.shopee import (  # noqa: E402
    ShopeeEcommerceSource,
)
from src.services.fetch.sources.ecommerce.tiktok_shop import (  # noqa: E402
    TikTokShopEcommerceSource,
)


# ---------------------------------------------------------------------------
# Shopee
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_shopee_returns_5_listings_across_countries():
    src = ShopeeEcommerceSource()
    results = await src.search_products(
        ProductSearchQuery(keyword="x", limit=20)
    )
    assert len(results) == 5
    countries = {p.raw["country"] for p in results}
    # 至少覆盖 4 个东南亚国家
    assert len(countries & {"VN", "MY", "TH", "ID", "PH"}) >= 4
    for p in results:
        assert p.source == "shopee"


@pytest.mark.asyncio
async def test_shopee_country_filter_narrows_results():
    src = ShopeeEcommerceSource()
    vn_results = await src.search_products(
        ProductSearchQuery(keyword="x", country="VN")
    )
    assert all(p.raw["country"] == "VN" for p in vn_results)
    assert len(vn_results) == 1
    assert vn_results[0].currency == "VND"


@pytest.mark.asyncio
async def test_shopee_health_check_requires_partner_credentials():
    assert await ShopeeEcommerceSource().health_check() is False
    assert (
        await ShopeeEcommerceSource(
            partner_id="123", partner_key="key"
        ).health_check()
        is True
    )


# ---------------------------------------------------------------------------
# TikTok Shop
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tiktok_returns_5_with_viral_video_metadata():
    src = TikTokShopEcommerceSource()
    results = await src.search_products(
        ProductSearchQuery(keyword="x", limit=20)
    )
    assert len(results) == 5
    for p in results:
        assert p.source == "tiktok_shop"
        # 短视频带货特征字段
        assert "viral_video_views" in p.raw
        assert "creator" in p.raw
        assert p.raw["creator"].startswith("@")


@pytest.mark.asyncio
async def test_tiktok_sort_newest_orders_by_viral_views_desc():
    """sort_by=newest 在 mock 中按播放量近似排序。"""
    src = TikTokShopEcommerceSource()
    results = await src.search_products(
        ProductSearchQuery(keyword="x", sort_by="newest")
    )
    views = [p.raw["viral_video_views"] for p in results]
    assert views == sorted(views, reverse=True)


@pytest.mark.asyncio
async def test_tiktok_sort_price_asc():
    src = TikTokShopEcommerceSource()
    results = await src.search_products(
        ProductSearchQuery(keyword="x", sort_by="price_asc")
    )
    prices = [p.price for p in results]
    assert prices == sorted(prices)


@pytest.mark.asyncio
async def test_tiktok_country_filter():
    src = TikTokShopEcommerceSource()
    uk_results = await src.search_products(
        ProductSearchQuery(keyword="x", country="UK")
    )
    assert all(p.raw["country"] == "UK" for p in uk_results)
    assert uk_results[0].currency == "GBP"


@pytest.mark.asyncio
async def test_tiktok_list_orders_status_diversity():
    src = TikTokShopEcommerceSource()
    orders = await src.list_orders(oauth_token="x")
    statuses = {o.status for o in orders}
    assert {"paid", "shipped", "delivered"}.issubset(statuses)


@pytest.mark.asyncio
async def test_tiktok_health_check_requires_app_credentials():
    assert await TikTokShopEcommerceSource().health_check() is False
    assert (
        await TikTokShopEcommerceSource(
            app_key="key", app_secret="secret"
        ).health_check()
        is True
    )
