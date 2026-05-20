"""阿里 1688 开放平台数据源 — mock + 接口契约（P6-D）。

为什么 mock？
-------------
1688 开放平台需要：
    1. 注册成为 ISV（独立软件开发商），通过阿里云市场审核；
    2. 申请 ``app_key`` / ``app_secret``，并完成「能力包」签约（商品/订单各自独立）；
    3. 调用前还需要走 OAuth 2.0 拿用户授权 token。

P6-D 阶段先把接口契约 + 假数据跑通，让前端能联调；真实接入排在 P7+。

业务关键
--------
1688 是 B2B 批发平台，与零售（Shopify / Amazon）的差异：
    - 商品有 **批发价区间**（``priceRange``）和 **起订量**（``moq``）；
    - 卖家是供应商，``seller_rating`` 用「金牌供应商」星级；
    - 物流偏向 **国内仓 + 跨境集货**。

mock 数据里把这些字段都放进 ``Product.raw``，前端可按 source 分支展示。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from .base import (
    BaseEcommerceSource,
    Order,
    Product,
    ProductSearchQuery,
)

# ---------------------------------------------------------------------------
# Mock 数据 — 5 条 deterministic 供应商商品（含批发价/起订量）
# ---------------------------------------------------------------------------
_MOCK_SUPPLIERS: list[dict] = [
    {
        "offer_id": "1688MOCK000001",
        "title": "TWS 蓝牙耳机 跨境出口爆款 私模可定制",
        "wholesale_price_min": 18.50,
        "wholesale_price_max": 35.00,
        "moq": 50,
        "supplier": "深圳市悦耳数码科技有限公司",
        "supplier_years": 8,
        "supplier_grade": "金牌供应商",
        "shipping": "深圳发货 / 跨境集货",
    },
    {
        "offer_id": "1688MOCK000002",
        "title": "304 不锈钢保温杯 32oz 大容量 出口欧美",
        "wholesale_price_min": 12.80,
        "wholesale_price_max": 22.50,
        "moq": 100,
        "supplier": "永康市优品保温器皿厂",
        "supplier_years": 12,
        "supplier_grade": "金牌供应商",
        "shipping": "义乌发货 / 海运空运",
    },
    {
        "offer_id": "1688MOCK000003",
        "title": "可升降桌面工作站 站立办公转换器 跨境款",
        "wholesale_price_min": 75.00,
        "wholesale_price_max": 130.00,
        "moq": 30,
        "supplier": "佛山市顺德爱康家具制造有限公司",
        "supplier_years": 5,
        "supplier_grade": "金牌供应商",
        "shipping": "广州发货 / 海运为主",
    },
    {
        "offer_id": "1688MOCK000004",
        "title": "有机抹茶粉 100g 食品级 OEM 代工",
        "wholesale_price_min": 6.50,
        "wholesale_price_max": 12.00,
        "moq": 200,
        "supplier": "杭州茗源食品有限公司",
        "supplier_years": 6,
        "supplier_grade": "实力商家",
        "shipping": "上海发货 / 跨境冷链",
    },
    {
        "offer_id": "1688MOCK000005",
        "title": "智能 LED 灯带 10m WiFi APP 跨境出口",
        "wholesale_price_min": 9.80,
        "wholesale_price_max": 18.00,
        "moq": 80,
        "supplier": "中山市古镇启明照明电器厂",
        "supplier_years": 10,
        "supplier_grade": "金牌供应商",
        "shipping": "中山发货 / 海空运",
    },
]


def _build_mock_product(item: dict) -> Product:
    return Product(
        source="alibaba_1688",
        sku=item["offer_id"],
        title=item["title"],
        description=f"[MOCK] {item['title']} —— 1688 开放平台占位数据",
        # 批发价取中位数作为「展示价」
        price=(item["wholesale_price_min"] + item["wholesale_price_max"]) / 2,
        currency="CNY",
        images=[
            f"https://cbu01.alicdn.com/img/ibank/{item['offer_id']}_main.jpg",
        ],
        inventory_qty=10000,  # 1688 通常库存充足
        rating=None,  # 1688 不展示零售评分
        review_count=None,
        seller_name=item["supplier"],
        # 「金牌供应商」=4.8，「实力商家」=4.5（启发式映射）
        seller_rating=4.8 if item["supplier_grade"] == "金牌供应商" else 4.5,
        url=f"https://detail.1688.com/offer/{item['offer_id']}.html",
        raw={
            "offer_id": item["offer_id"],
            "wholesale_price_min": item["wholesale_price_min"],
            "wholesale_price_max": item["wholesale_price_max"],
            "moq": item["moq"],
            "supplier_years": item["supplier_years"],
            "supplier_grade": item["supplier_grade"],
            "shipping": item["shipping"],
            "_mock": True,
            "_real_endpoint": "alibaba.icbu.product.search.query",
        },
    )


# ---------------------------------------------------------------------------
# Source
# ---------------------------------------------------------------------------
class Alibaba1688EcommerceSource(BaseEcommerceSource):
    """阿里 1688 开放平台数据源（mock）。

    构造参数对齐真实 ISV 接入：

        - ``app_key`` / ``app_secret``：1688 开放平台 ISV 凭据
        - ``api_endpoint``：``https://gw.open.1688.com/openapi``
        - ``protocol``：``param2`` 是阿里旧体系；新接入推荐 ``rest`` 风格

    ⚠️ 当前所有方法 **完全 mock**，不发任何 HTTP 请求。
    """

    source_id = "alibaba_1688"
    display_name = "阿里 1688"
    requires_oauth = True

    DEFAULT_API_ENDPOINT = "https://gw.open.1688.com/openapi"

    def __init__(
        self,
        *,
        app_key: str = "",
        app_secret: str = "",
        api_endpoint: str = DEFAULT_API_ENDPOINT,
    ) -> None:
        self.app_key = app_key
        self.app_secret = app_secret
        self.api_endpoint = api_endpoint

    # ===================================================================
    # 接口实装（全 mock）
    # ===================================================================
    async def search_products(
        self,
        query: ProductSearchQuery,
        oauth_token: str | None = None,
    ) -> list[Product]:
        """Mock —— 5 条 deterministic 供应商商品（含批发价 + 起订量）。

        真实端点：``alibaba.icbu.product.search.query``
        """
        products = [_build_mock_product(item) for item in _MOCK_SUPPLIERS]
        for p in products:
            p.raw["_query_keyword"] = query.keyword
        return products[: max(1, min(query.limit, len(products)))]

    async def get_product(
        self,
        sku: str,
        oauth_token: str | None = None,
    ) -> Product | None:
        """Mock —— offer_id 命中即返回。

        真实端点：``alibaba.icbu.product.get``
        """
        for item in _MOCK_SUPPLIERS:
            if item["offer_id"] == sku:
                return _build_mock_product(item)
        return None

    async def list_orders(
        self,
        oauth_token: str,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[Order]:
        """Mock —— 返回 2 条假采购单。

        真实端点：``alibaba.trade.getBuyerOrderList``
        """
        now = datetime.now(UTC)
        base_since = since or (now - timedelta(days=14))
        return [
            Order(
                source="alibaba_1688",
                order_id=f"1688-MOCK-{i:08d}",
                customer_name=f"采购方-MOCK-{i}",
                total_amount=_MOCK_SUPPLIERS[i]["wholesale_price_min"] * _MOCK_SUPPLIERS[i]["moq"],
                currency="CNY",
                status=("paid", "shipped")[i],
                placed_at=base_since + timedelta(days=i),
                items=[
                    {
                        "sku": _MOCK_SUPPLIERS[i]["offer_id"],
                        "title": _MOCK_SUPPLIERS[i]["title"],
                        "qty": _MOCK_SUPPLIERS[i]["moq"],
                        "unit_price": _MOCK_SUPPLIERS[i]["wholesale_price_min"],
                    }
                ],
            )
            for i in range(min(2, limit))
        ]

    async def update_inventory(
        self,
        sku: str,
        qty: int,
        oauth_token: str,
    ) -> bool:
        """Mock —— 总是 True。

        真实端点：``alibaba.icbu.product.inventory.update``
        """
        return True

    async def health_check(
        self,
        oauth_token: str | None = None,
    ) -> bool:
        """Mock —— ISV 凭据齐 → True。

        真实端点：``alibaba.icbu.account.basic.get``
        """
        return bool(self.app_key and self.app_secret)


__all__ = ["Alibaba1688EcommerceSource"]
