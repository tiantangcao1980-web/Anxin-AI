"""跨境电商 base 数据类合法性测试（P6-D）。

仅校验 ``base.py`` 的纯数据类与抽象，不触达任何 source 实装。
覆盖：

    1. ProductSearchQuery — 默认值 / 必填字段
    2. Product            — 字段齐全 + raw 为可写 dict
    3. Order              — items 接受 list[dict]
    4. BaseEcommerceSource._ensure_token — 缺 token 抛 OAuthRequiredError
    5. EcommerceSourceError / OAuthRequiredError 继承关系
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

# 兼容 conftest：SQLite 编译 JSONB（其他 P4 provider 测试同款）
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(JSONB, "sqlite")  # type: ignore[misc]
def _compile_jsonb_for_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


from src.services.fetch.sources.ecommerce.base import (  # noqa: E402
    BaseEcommerceSource,
    EcommerceSourceError,
    OAuthRequiredError,
    Order,
    Product,
    ProductSearchQuery,
)


def test_product_search_query_defaults():
    q = ProductSearchQuery(keyword="hoodie")
    assert q.keyword == "hoodie"
    assert q.category is None
    assert q.price_min is None and q.price_max is None
    assert q.country is None
    assert q.sort_by == "best_match"
    assert q.limit == 20


def test_product_search_query_full():
    q = ProductSearchQuery(
        keyword="bottle",
        category="kitchen",
        price_min=10.0,
        price_max=50.0,
        country="US",
        sort_by="price_asc",
        limit=100,
    )
    assert q.sort_by == "price_asc"
    assert q.limit == 100


def test_product_dataclass_shape():
    p = Product(
        source="shopify",
        sku="SKU-001",
        title="Test Hoodie",
        description="warm",
        price=39.99,
        currency="USD",
        images=["https://cdn/x.jpg"],
        inventory_qty=10,
        rating=4.5,
        review_count=120,
        seller_name="Anxin Store",
        seller_rating=4.8,
        url="https://acme.myshopify.com/products/test",
    )
    # raw 默认空 dict 且可写（每实例独立）
    assert p.raw == {}
    p.raw["foo"] = 1
    p2 = Product(
        source="shopify",
        sku="SKU-002",
        title="t",
        description=None,
        price=1.0,
        currency="USD",
        images=[],
        inventory_qty=None,
        rating=None,
        review_count=None,
        seller_name=None,
        seller_rating=None,
        url="",
    )
    assert p2.raw == {}, "raw 必须是 per-instance 而非共享引用"


def test_order_items_list():
    o = Order(
        source="shopify",
        order_id="OD-1",
        customer_name="Alice",
        total_amount=88.0,
        currency="USD",
        status="paid",
        placed_at=datetime.now(UTC),
        items=[{"sku": "X", "title": "x", "qty": 2, "unit_price": 44.0}],
    )
    assert o.items[0]["qty"] == 2


@pytest.mark.asyncio
async def test_ensure_token_raises_when_missing():
    """``_ensure_token`` 在 requires_oauth=True 且 token 为 None 时抛错。"""

    class _Dummy(BaseEcommerceSource):
        source_id = "dummy"
        display_name = "Dummy"
        requires_oauth = True

        async def search_products(self, query, oauth_token=None):
            return []

        async def get_product(self, sku, oauth_token=None):
            return None

        async def list_orders(self, oauth_token, since=None, limit=50):
            return []

        async def update_inventory(self, sku, qty, oauth_token):
            return True

        async def health_check(self, oauth_token=None):
            return False

    d = _Dummy()
    with pytest.raises(OAuthRequiredError):
        d._ensure_token(None)
    assert d._ensure_token("abc") == "abc"


def test_oauth_required_error_is_ecommerce_error():
    assert issubclass(OAuthRequiredError, EcommerceSourceError)
    assert issubclass(EcommerceSourceError, RuntimeError)


def test_base_class_cannot_instantiate():
    """抽象基类不可直接实例化。"""
    with pytest.raises(TypeError):
        BaseEcommerceSource()  # type: ignore[abstract]
