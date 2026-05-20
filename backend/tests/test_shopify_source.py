"""Shopify 数据源 — 真实 HTTP 调用结构验证（mock httpx）。

不依赖网络：注入 mock ``httpx.AsyncClient``，验证：

    1. search_products 走 GET /admin/api/{ver}/products.json，URL/header 正确
    2. 返回值映射到 Product，价格/url/images 字段正确
    3. price_min/price_max 客户端过滤生效
    4. sort_by=price_asc 客户端排序生效
    5. list_orders 走 GET /admin/api/{ver}/orders.json，含 updated_at_min
    6. update_inventory 用 X-Shopify-Access-Token 头 POST set.json
"""

from __future__ import annotations

from datetime import UTC, datetime
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
    ProductSearchQuery,
)
from src.services.fetch.sources.ecommerce.shopify import (  # noqa: E402
    ShopifyEcommerceSource,
)


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def _make_response(status: int, json_data: dict[str, Any]) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json = MagicMock(return_value=json_data)
    resp.text = ""
    return resp


def _make_client(get_payload=None, post_payload=None) -> MagicMock:
    client = MagicMock()
    client.get = AsyncMock(return_value=_make_response(200, get_payload or {}))
    client.post = AsyncMock(return_value=_make_response(200, post_payload or {}))
    client.delete = AsyncMock(return_value=_make_response(200, {}))
    client.aclose = AsyncMock()
    return client


SAMPLE_PRODUCTS = {
    "products": [
        {
            "id": 9001,
            "title": "Hoodie Black",
            "handle": "hoodie-black",
            "body_html": "<p>cozy</p>",
            "vendor": "AnxinApparel",
            "product_type": "Apparel",
            "tags": "spring",
            "created_at": "2026-04-01T10:00:00-04:00",
            "updated_at": "2026-04-10T10:00:00-04:00",
            "variants": [
                {"sku": "HOODIE-BK-M", "price": "39.99", "inventory_quantity": 12},
            ],
            "images": [{"src": "https://cdn.shopify.com/img1.jpg"}],
        },
        {
            "id": 9002,
            "title": "Hoodie White",
            "handle": "hoodie-white",
            "body_html": "<p>light</p>",
            "vendor": "AnxinApparel",
            "created_at": "2026-04-05T10:00:00-04:00",
            "variants": [
                {"sku": "HOODIE-WH-M", "price": "59.99", "inventory_quantity": 7},
            ],
            "images": [],
        },
    ]
}


# ---------------------------------------------------------------------------
# 测试
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_search_products_hits_correct_url_and_headers():
    client = _make_client(get_payload=SAMPLE_PRODUCTS)
    src = ShopifyEcommerceSource(shop="acme.myshopify.com", http_client=client)

    results = await src.search_products(
        ProductSearchQuery(keyword="hoodie", limit=10),
        oauth_token="shpat_test_xxx",
    )

    # URL & method
    client.get.assert_called_once()
    args, kwargs = client.get.call_args
    url = args[0] if args else kwargs.get("url")
    assert url == "https://acme.myshopify.com/admin/api/2024-10/products.json"
    # 鉴权头：必须是自定义头，不是 Bearer
    assert kwargs["headers"]["X-Shopify-Access-Token"] == "shpat_test_xxx"
    assert "Authorization" not in kwargs["headers"]
    # query 参数
    assert kwargs["params"]["title"] == "hoodie"
    assert kwargs["params"]["limit"] == 10

    # 映射结果
    assert len(results) == 2
    p = results[0]
    assert p.source == "shopify"
    assert p.sku == "HOODIE-BK-M"
    assert p.title == "Hoodie Black"
    assert p.price == 39.99
    assert p.images == ["https://cdn.shopify.com/img1.jpg"]
    assert p.url == "https://acme.myshopify.com/products/hoodie-black"
    assert p.raw["created_at"] == "2026-04-01T10:00:00-04:00"


@pytest.mark.asyncio
async def test_search_products_client_side_price_filter():
    client = _make_client(get_payload=SAMPLE_PRODUCTS)
    src = ShopifyEcommerceSource(shop="acme.myshopify.com", http_client=client)
    results = await src.search_products(
        ProductSearchQuery(keyword="hoodie", price_min=50.0),
        oauth_token="shpat_xxx",
    )
    # 39.99 被过滤掉，只剩 White 59.99
    assert len(results) == 1
    assert results[0].sku == "HOODIE-WH-M"


@pytest.mark.asyncio
async def test_search_products_client_side_sort_asc():
    client = _make_client(get_payload=SAMPLE_PRODUCTS)
    src = ShopifyEcommerceSource(shop="acme.myshopify.com", http_client=client)
    results = await src.search_products(
        ProductSearchQuery(keyword="hoodie", sort_by="price_asc"),
        oauth_token="shpat_xxx",
    )
    assert [p.price for p in results] == [39.99, 59.99]


@pytest.mark.asyncio
async def test_list_orders_includes_updated_at_min_param():
    payload = {
        "orders": [
            {
                "id": 7001,
                "total_price": "99.50",
                "currency": "USD",
                "financial_status": "paid",
                "fulfillment_status": "fulfilled",
                "created_at": "2026-04-15T10:00:00-04:00",
                "customer": {"first_name": "Alice", "last_name": "X"},
                "line_items": [
                    {"sku": "HOODIE-BK-M", "title": "Hoodie", "quantity": 2, "price": "39.99"},
                    {"sku": "ACC-CAP", "title": "Cap", "quantity": 1, "price": "19.52"},
                ],
            }
        ]
    }
    client = _make_client(get_payload=payload)
    src = ShopifyEcommerceSource(shop="acme.myshopify.com", http_client=client)
    since = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)

    orders = await src.list_orders(oauth_token="shpat_xxx", since=since, limit=20)

    args, kwargs = client.get.call_args
    assert (args[0] if args else kwargs.get("url")).endswith("/orders.json")
    assert kwargs["params"]["status"] == "any"
    assert kwargs["params"]["updated_at_min"] == "2026-04-10T12:00:00+00:00"

    o = orders[0]
    assert o.source == "shopify"
    assert o.order_id == "7001"
    assert o.customer_name == "Alice X"
    assert o.total_amount == 99.50
    assert o.status == "shipped"  # paid + fulfilled → shipped
    assert len(o.items) == 2
    assert o.items[0]["unit_price"] == 39.99


@pytest.mark.asyncio
async def test_update_inventory_uses_inventory_levels_endpoint():
    client = _make_client(post_payload={"inventory_level": {"available": 50}})
    src = ShopifyEcommerceSource(shop="acme.myshopify.com", http_client=client)

    ok = await src.update_inventory(
        sku=12345,
        qty=50,
        oauth_token="shpat_xxx",
        location_id=98765,
        inventory_item_id=12345,
    )

    assert ok is True
    args, kwargs = client.post.call_args
    url = args[0] if args else kwargs.get("url")
    assert url.endswith("/inventory_levels/set.json")
    assert kwargs["headers"]["X-Shopify-Access-Token"] == "shpat_xxx"
    assert kwargs["json"]["available"] == 50
    assert kwargs["json"]["location_id"] == 98765
    assert kwargs["json"]["inventory_item_id"] == 12345
