# -*- coding: utf-8 -*-
"""Shopify 数据源 — 多租户 shop 域名贯穿测试（P6-D）。

验证：

    1. 构造未传 shop + 调用未传 shop  → OAuthRequiredError
    2. 构造传了 shop 默认值          → 调用走默认
    3. 调用时 shop= kwarg 覆盖默认值
    4. shop 归一化（去 https:// 前缀 / 尾部 /）
    5. health_check 在缺 shop 时返回 False（不抛错）
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


from src.services.fetch.sources.ecommerce.base import (  # noqa: E402
    OAuthRequiredError,
    ProductSearchQuery,
)
from src.services.fetch.sources.ecommerce.shopify import (  # noqa: E402
    ShopifyEcommerceSource,
)


def _make_client() -> MagicMock:
    client = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(return_value={"products": []})
    resp.text = ""
    client.get = AsyncMock(return_value=resp)
    client.post = AsyncMock(return_value=resp)
    client.aclose = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_missing_shop_raises_oauth_required():
    src = ShopifyEcommerceSource(http_client=_make_client())
    with pytest.raises(OAuthRequiredError) as ei:
        await src.search_products(
            ProductSearchQuery(keyword="x"), oauth_token="shpat_xxx"
        )
    assert "shop" in str(ei.value).lower()


@pytest.mark.asyncio
async def test_default_shop_used_when_no_kwarg():
    client = _make_client()
    src = ShopifyEcommerceSource(shop="acme.myshopify.com", http_client=client)
    await src.search_products(
        ProductSearchQuery(keyword="x"), oauth_token="shpat_xxx"
    )
    url = client.get.call_args.args[0] if client.get.call_args.args else client.get.call_args.kwargs["url"]
    assert url.startswith("https://acme.myshopify.com/admin/api/")


@pytest.mark.asyncio
async def test_shop_kwarg_overrides_default():
    client = _make_client()
    src = ShopifyEcommerceSource(shop="default.myshopify.com", http_client=client)
    # 明确把 shop 注入到方法
    await src.search_products(
        ProductSearchQuery(keyword="x"),
        oauth_token="shpat_xxx",
        shop="override.myshopify.com",
    )
    url = client.get.call_args.args[0] if client.get.call_args.args else client.get.call_args.kwargs["url"]
    assert "override.myshopify.com" in url
    assert "default.myshopify.com" not in url


@pytest.mark.asyncio
async def test_shop_normalization_strips_protocol_and_trailing_slash():
    client = _make_client()
    # 模拟从 OAuthTokenBundle.raw["shop"] 读出来可能带 https:// 前缀
    src = ShopifyEcommerceSource(
        shop="https://acme.myshopify.com/", http_client=client
    )
    await src.search_products(
        ProductSearchQuery(keyword="x"), oauth_token="shpat_xxx"
    )
    url = client.get.call_args.args[0] if client.get.call_args.args else client.get.call_args.kwargs["url"]
    # 不应出现双 slash 或残留 https:// 前缀
    assert url == "https://acme.myshopify.com/admin/api/2024-10/products.json"


@pytest.mark.asyncio
async def test_health_check_returns_false_when_no_token_or_shop():
    src = ShopifyEcommerceSource(http_client=_make_client())
    assert await src.health_check(oauth_token=None) is False
    assert await src.health_check(oauth_token="shpat_xxx") is False  # 没 shop


@pytest.mark.asyncio
async def test_health_check_calls_shop_endpoint_with_token():
    client = _make_client()
    # shop.json 返回 200 即可
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(return_value={"shop": {"name": "Acme"}})
    resp.text = ""
    client.get = AsyncMock(return_value=resp)

    src = ShopifyEcommerceSource(shop="acme.myshopify.com", http_client=client)
    ok = await src.health_check(oauth_token="shpat_xxx")
    assert ok is True
    url = client.get.call_args.args[0] if client.get.call_args.args else client.get.call_args.kwargs["url"]
    assert url.endswith("/shop.json")
