# -*- coding: utf-8 -*-
"""跨境电商 source — OAuth token 缺失场景测试（P6-D）。

约定：

    - **真实接入** 的 source（``shopify``）：缺 token 一律抛 OAuthRequiredError；
    - **mock 阶段** 的 source（``amazon_sp`` / ``alibaba_1688`` / ``shopee``
      / ``tiktok_shop``）：为方便联调，缺 token 不抛错，但 ``health_check``
      在凭据未配齐时 **必须** 返回 False（避免错误地汇报"健康"）。
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# SQLite/JSONB 兼容
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(JSONB, "sqlite")  # type: ignore[misc]
def _compile_jsonb_for_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


from src.services.fetch.sources.ecommerce import (  # noqa: E402
    Alibaba1688EcommerceSource,
    AmazonSPEcommerceSource,
    ShopeeEcommerceSource,
    ShopifyEcommerceSource,
    TikTokShopEcommerceSource,
)
from src.services.fetch.sources.ecommerce.base import (  # noqa: E402
    OAuthRequiredError,
    ProductSearchQuery,
)


def _safe_client():
    client = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(return_value={"products": []})
    resp.text = ""
    client.get = AsyncMock(return_value=resp)
    client.aclose = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# Shopify：真实接入，缺 token / shop 必须抛 OAuthRequiredError
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_shopify_search_without_token_raises():
    src = ShopifyEcommerceSource(shop="acme.myshopify.com", http_client=_safe_client())
    with pytest.raises(OAuthRequiredError):
        await src.search_products(
            ProductSearchQuery(keyword="x"), oauth_token=None
        )


@pytest.mark.asyncio
async def test_shopify_list_orders_without_token_raises():
    src = ShopifyEcommerceSource(shop="acme.myshopify.com", http_client=_safe_client())
    with pytest.raises(OAuthRequiredError):
        # type: ignore[arg-type]  — 故意传 None 触发校验
        await src.list_orders(oauth_token=None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_shopify_search_without_shop_raises():
    src = ShopifyEcommerceSource(http_client=_safe_client())
    with pytest.raises(OAuthRequiredError) as ei:
        await src.search_products(
            ProductSearchQuery(keyword="x"), oauth_token="shpat_xxx"
        )
    assert "shop" in str(ei.value).lower()


# ---------------------------------------------------------------------------
# Mock sources：缺 token 不抛错，但 health_check 缺凭据应返 False
# ---------------------------------------------------------------------------
MOCK_SOURCE_CLASSES = [
    AmazonSPEcommerceSource,
    Alibaba1688EcommerceSource,
    ShopeeEcommerceSource,
    TikTokShopEcommerceSource,
]


@pytest.mark.parametrize("source_cls", MOCK_SOURCE_CLASSES)
@pytest.mark.asyncio
async def test_mock_source_search_works_without_token(source_cls):
    """mock 阶段允许联调 — 不传 token 也不应抛错。"""
    src = source_cls()
    products = await src.search_products(
        ProductSearchQuery(keyword="x", limit=5), oauth_token=None
    )
    assert isinstance(products, list)
    assert len(products) > 0


@pytest.mark.parametrize("source_cls", MOCK_SOURCE_CLASSES)
@pytest.mark.asyncio
async def test_mock_source_health_check_false_without_credentials(source_cls):
    """缺凭据 health_check 必须 False — 否则监控面板会误报"健康"。"""
    src = source_cls()
    assert await src.health_check() is False


def test_all_sources_have_unique_source_id():
    from src.services.fetch.sources.ecommerce import ALL_SOURCES

    ids = [cls.source_id for cls in ALL_SOURCES]
    assert len(ids) == len(set(ids)), f"source_id 必须唯一: {ids}"
    assert "shopify" in ids
    assert "amazon_sp" in ids
    assert "alibaba_1688" in ids
    assert "shopee" in ids
    assert "tiktok_shop" in ids
