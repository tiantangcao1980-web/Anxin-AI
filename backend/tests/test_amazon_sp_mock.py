# -*- coding: utf-8 -*-
"""Amazon SP-API mock source 测试（P6-D）。

验证 mock 阶段的契约稳定：

    1. search_products 返回 5 条假商品
    2. 商品字段齐全（asin / 价格 / 评分 / 卖家）
    3. get_product 命中 / 未命中
    4. list_orders 返回 3 条假订单
    5. update_inventory 总是 True
    6. health_check 在 LWA 三件套齐时 True，否则 False
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

# SQLite/JSONB 兼容
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(JSONB, "sqlite")  # type: ignore[misc]
def _compile_jsonb_for_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


from src.services.fetch.sources.ecommerce.amazon_sp import (  # noqa: E402
    AmazonSPEcommerceSource,
)
from src.services.fetch.sources.ecommerce.base import (  # noqa: E402
    ProductSearchQuery,
)


@pytest.mark.asyncio
async def test_search_products_returns_5_mock():
    src = AmazonSPEcommerceSource()
    results = await src.search_products(
        ProductSearchQuery(keyword="earbuds", limit=20)
    )
    assert len(results) == 5
    asins = {p.sku for p in results}
    assert asins == {f"B0CMOCK00{i}" for i in range(1, 6)}


@pytest.mark.asyncio
async def test_search_products_full_fields_present():
    src = AmazonSPEcommerceSource()
    results = await src.search_products(
        ProductSearchQuery(keyword="x", limit=20)
    )
    p = results[0]
    assert p.source == "amazon_sp"
    assert p.sku.startswith("B0CMOCK")
    assert p.price > 0
    assert p.currency == "USD"
    assert p.rating is not None
    assert p.review_count is not None
    assert p.seller_name and p.seller_rating
    assert p.url.startswith("https://www.amazon.com/dp/")
    assert p.raw["_mock"] is True
    assert p.raw["_query_keyword"] == "x"


@pytest.mark.asyncio
async def test_search_products_respects_limit():
    src = AmazonSPEcommerceSource()
    results = await src.search_products(
        ProductSearchQuery(keyword="x", limit=2)
    )
    assert len(results) == 2


@pytest.mark.asyncio
async def test_get_product_hit_and_miss():
    src = AmazonSPEcommerceSource()
    hit = await src.get_product("B0CMOCK001")
    assert hit is not None
    assert hit.sku == "B0CMOCK001"

    miss = await src.get_product("DOES-NOT-EXIST")
    assert miss is None


@pytest.mark.asyncio
async def test_list_orders_returns_three_with_status_diversity():
    src = AmazonSPEcommerceSource()
    orders = await src.list_orders(
        oauth_token="lwa_token_xxx",
        since=datetime(2026, 4, 1, tzinfo=timezone.utc),
        limit=50,
    )
    assert len(orders) == 3
    statuses = {o.status for o in orders}
    # 至少覆盖 paid / shipped / delivered 三个不同态
    assert {"paid", "shipped", "delivered"}.issubset(statuses)
    for o in orders:
        assert o.source == "amazon_sp"
        assert o.order_id.startswith("114-MOCK-")
        assert o.items and o.items[0]["unit_price"] > 0


@pytest.mark.asyncio
async def test_update_inventory_always_true_in_mock():
    src = AmazonSPEcommerceSource()
    assert await src.update_inventory("B0CMOCK001", 50, oauth_token="x") is True


@pytest.mark.asyncio
async def test_health_check_requires_lwa_credentials():
    # 缺凭据 → False
    src_empty = AmazonSPEcommerceSource()
    assert await src_empty.health_check() is False

    # 三件套齐 → True
    src_full = AmazonSPEcommerceSource(
        lwa_client_id="amzn1.app-ck.x",
        lwa_client_secret="secret",
        refresh_token="Atzr|x",
    )
    assert await src_full.health_check() is True


@pytest.mark.asyncio
async def test_country_overrides_marketplace_id():
    src = AmazonSPEcommerceSource()
    results = await src.search_products(
        ProductSearchQuery(keyword="x", country="A1PA6795UKMFR9")  # DE marketplace
    )
    assert results[0].raw["marketplace_id"] == "A1PA6795UKMFR9"
