"""阿里 1688 mock source 测试（P6-D）。

重点验证 B2B 批发平台的差异化字段：

    1. 5 条假供应商商品
    2. raw 含 wholesale_price_min / max / moq（起订量）
    3. 货币是 CNY
    4. 金牌供应商映射 4.8，实力商家 4.5
    5. list_orders 返回采购单（含 MOQ × 批发价计算的 total）
"""

from __future__ import annotations

import pytest

# SQLite/JSONB 兼容
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(JSONB, "sqlite")  # type: ignore[misc]
def _compile_jsonb_for_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


from src.services.fetch.sources.ecommerce.alibaba_1688 import (  # noqa: E402
    Alibaba1688EcommerceSource,
)
from src.services.fetch.sources.ecommerce.base import (  # noqa: E402
    ProductSearchQuery,
)


@pytest.mark.asyncio
async def test_search_products_returns_5_supplier_offers():
    src = Alibaba1688EcommerceSource()
    results = await src.search_products(ProductSearchQuery(keyword="蓝牙耳机", limit=20))
    assert len(results) == 5
    for p in results:
        assert p.source == "alibaba_1688"
        assert p.sku.startswith("1688MOCK")
        assert p.currency == "CNY"


@pytest.mark.asyncio
async def test_wholesale_price_and_moq_in_raw():
    """B2B 关键字段必须保留在 raw 里（前端按 source 分支展示）。"""
    src = Alibaba1688EcommerceSource()
    results = await src.search_products(ProductSearchQuery(keyword="x"))
    p = results[0]
    assert "wholesale_price_min" in p.raw
    assert "wholesale_price_max" in p.raw
    assert "moq" in p.raw
    assert isinstance(p.raw["moq"], int) and p.raw["moq"] > 0
    # 展示价是批发价区间中位数
    assert p.price == (p.raw["wholesale_price_min"] + p.raw["wholesale_price_max"]) / 2


@pytest.mark.asyncio
async def test_supplier_grade_mapped_to_seller_rating():
    src = Alibaba1688EcommerceSource()
    results = await src.search_products(ProductSearchQuery(keyword="x"))
    grades = {p.raw["supplier_grade"]: p.seller_rating for p in results}
    assert grades.get("金牌供应商") == 4.8
    assert grades.get("实力商家") == 4.5


@pytest.mark.asyncio
async def test_get_product_hit_and_miss():
    src = Alibaba1688EcommerceSource()
    hit = await src.get_product("1688MOCK000001")
    assert hit is not None and hit.title.startswith("TWS")
    assert await src.get_product("nonexistent") is None


@pytest.mark.asyncio
async def test_list_orders_uses_moq_times_wholesale_min_for_total():
    src = Alibaba1688EcommerceSource()
    orders = await src.list_orders(oauth_token="x")
    assert len(orders) == 2
    o = orders[0]
    assert o.source == "alibaba_1688"
    assert o.currency == "CNY"
    # B2B 大单：金额 = MOQ × 单价
    assert o.items[0]["qty"] >= 50
    assert o.total_amount == o.items[0]["qty"] * o.items[0]["unit_price"]


@pytest.mark.asyncio
async def test_health_check_requires_isv_credentials():
    assert await Alibaba1688EcommerceSource().health_check() is False
    assert (
        await Alibaba1688EcommerceSource(app_key="appkey", app_secret="secret").health_check()
        is True
    )


@pytest.mark.asyncio
async def test_update_inventory_mock_true():
    src = Alibaba1688EcommerceSource()
    assert await src.update_inventory("1688MOCK000001", 100, oauth_token="x") is True
