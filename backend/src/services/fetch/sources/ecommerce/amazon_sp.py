"""Amazon Selling Partner API（SP-API）数据源 — mock + 接口契约（P6-D）。

为什么 mock？
-------------
SP-API 真实接入门槛极高，远超 OAuth2：

    1. **LWA**（Login with Amazon）—— 需要 Amazon Seller Central 注册开发者账号、
       通过 SP-API 申请审核，颁发 ``LWA_CLIENT_ID`` + ``REFRESH_TOKEN``；
    2. **AWS SigV4 签名** —— 每个请求要用 SellingPartner 的 IAM Role，
       通过 STS AssumeRole 取临时凭据，再对完整 HTTP 请求做 SigV4 签名；
    3. **Marketplace + Region 路由** —— 不同区域对应不同 endpoint
       （NA: ``sellingpartnerapi-na.amazon.com``，EU/FE 各自独立），
       且每个 marketplace 有自己的 ``MarketplaceId``；
    4. **Restricted PII** —— 敏感数据（地址、电话）需走 RDT
       （Restricted Data Token）二次授权。

P6-D 阶段先把 **接口契约 + 假数据** 跑通，让前端能联调；真实接入排在
P7+（"出海全链路"阶段）。

接口契约
--------
本类的 ``search_products`` 对齐 SP-API ``GET /catalog/v2022-04-01/items``
的字段语义，``list_orders`` 对齐 ``GET /orders/v0/orders``。所有方法都
**忽略真实 HTTP 调用**，直接生成 5 条 deterministic 假数据。
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
# Mock 数据 — 5 条 deterministic 假商品
# ---------------------------------------------------------------------------
_MOCK_PRODUCTS_TEMPLATE: list[dict] = [
    {
        "asin": "B0CMOCK001",
        "title": "Wireless Bluetooth Earbuds — Pro Edition",
        "price": 49.99,
        "currency": "USD",
        "rating": 4.5,
        "reviews": 12453,
        "seller": "AnxinTechStore",
        "seller_rating": 4.8,
    },
    {
        "asin": "B0CMOCK002",
        "title": "Stainless Steel Insulated Water Bottle 32oz",
        "price": 24.50,
        "currency": "USD",
        "rating": 4.7,
        "reviews": 8921,
        "seller": "GlobalHomeGoods",
        "seller_rating": 4.6,
    },
    {
        "asin": "B0CMOCK003",
        "title": "Adjustable Standing Desk Converter",
        "price": 189.00,
        "currency": "USD",
        "rating": 4.3,
        "reviews": 3215,
        "seller": "ErgoOfficeOutlet",
        "seller_rating": 4.4,
    },
    {
        "asin": "B0CMOCK004",
        "title": "Organic Matcha Green Tea Powder 100g",
        "price": 18.75,
        "currency": "USD",
        "rating": 4.6,
        "reviews": 5640,
        "seller": "WellnessImports",
        "seller_rating": 4.9,
    },
    {
        "asin": "B0CMOCK005",
        "title": "Smart LED Strip Lights 10m WiFi App-Controlled",
        "price": 32.99,
        "currency": "USD",
        "rating": 4.4,
        "reviews": 21088,
        "seller": "BrightHomeDeals",
        "seller_rating": 4.5,
    },
]


def _build_mock_product(item: dict, marketplace: str) -> Product:
    return Product(
        source="amazon_sp",
        sku=item["asin"],
        title=item["title"],
        description=f"[MOCK] {item['title']} —— Amazon SP-API 占位数据",
        price=item["price"],
        currency=item["currency"],
        images=[
            f"https://m.media-amazon.com/images/I/{item['asin']}_L.jpg",
            f"https://m.media-amazon.com/images/I/{item['asin']}_M.jpg",
        ],
        inventory_qty=100,
        rating=item["rating"],
        review_count=item["reviews"],
        seller_name=item["seller"],
        seller_rating=item["seller_rating"],
        url=f"https://www.amazon.com/dp/{item['asin']}",
        raw={
            "asin": item["asin"],
            "marketplace_id": marketplace,
            "_mock": True,
            "_real_endpoint": "GET /catalog/v2022-04-01/items",
        },
    )


# ---------------------------------------------------------------------------
# Source
# ---------------------------------------------------------------------------
class AmazonSPEcommerceSource(BaseEcommerceSource):
    """Amazon SP-API 数据源（mock）。

    构造参数对齐真实接入所需，方便未来 P7 切换到真实实装时只改方法体：

        - ``lwa_client_id`` / ``lwa_client_secret`` / ``refresh_token``：LWA 凭据
        - ``aws_region``：``us-east-1`` / ``eu-west-1`` / ``us-west-2``
        - ``marketplace_id``：默认 ``ATVPDKIKX0DER``（amazon.com）

    ⚠️ 当前所有方法 **完全 mock**，不发任何 HTTP 请求。
    """

    source_id = "amazon_sp"
    display_name = "Amazon SP-API"
    requires_oauth = True

    # 美国 marketplace
    DEFAULT_MARKETPLACE_ID = "ATVPDKIKX0DER"

    def __init__(
        self,
        *,
        lwa_client_id: str = "",
        lwa_client_secret: str = "",
        refresh_token: str = "",
        aws_region: str = "us-east-1",
        marketplace_id: str = DEFAULT_MARKETPLACE_ID,
    ) -> None:
        self.lwa_client_id = lwa_client_id
        self.lwa_client_secret = lwa_client_secret
        self.refresh_token = refresh_token
        self.aws_region = aws_region
        self.marketplace_id = marketplace_id

    # ===================================================================
    # 接口实装（全 mock）
    # ===================================================================
    async def search_products(
        self,
        query: ProductSearchQuery,
        oauth_token: str | None = None,
    ) -> list[Product]:
        """Mock —— 永远返回 5 条假商品（按 limit 截断），keyword 写进 raw 备查。

        真实端点：``GET /catalog/v2022-04-01/items?keywords={kw}&marketplaceIds={id}``
        """
        # 真实接入时这里抛 OAuthRequiredError；mock 阶段为方便联调，允许无 token
        marketplace = query.country or self.marketplace_id
        products = [_build_mock_product(p, marketplace) for p in _MOCK_PRODUCTS_TEMPLATE]
        for p in products:
            p.raw["_query_keyword"] = query.keyword
        # limit 截断（最少 1 条）
        return products[: max(1, min(query.limit, len(products)))]

    async def get_product(
        self,
        sku: str,
        oauth_token: str | None = None,
    ) -> Product | None:
        """Mock —— ASIN 命中假数据集即返回，否则 None。

        真实端点：``GET /catalog/v2022-04-01/items/{asin}?marketplaceIds={id}``
        """
        for item in _MOCK_PRODUCTS_TEMPLATE:
            if item["asin"] == sku:
                return _build_mock_product(item, self.marketplace_id)
        return None

    async def list_orders(
        self,
        oauth_token: str,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[Order]:
        """Mock —— 永远返回 3 条假订单。

        真实端点：``GET /orders/v0/orders?MarketplaceIds={id}&CreatedAfter={iso}``
        """
        # 故意不调 _ensure_token —— mock 阶段允许联调；真实接入要求 token 必传
        now = datetime.now(UTC)
        base_since = since or (now - timedelta(days=7))
        return [
            Order(
                source="amazon_sp",
                order_id=f"114-MOCK-{i:07d}",
                customer_name=f"Mock Buyer {i}",
                total_amount=49.99 + i * 10.5,
                currency="USD",
                status=("paid", "shipped", "delivered")[i],
                placed_at=base_since + timedelta(hours=i * 6),
                items=[
                    {
                        "sku": _MOCK_PRODUCTS_TEMPLATE[i]["asin"],
                        "title": _MOCK_PRODUCTS_TEMPLATE[i]["title"],
                        "qty": 1 + i,
                        "unit_price": _MOCK_PRODUCTS_TEMPLATE[i]["price"],
                    }
                ],
            )
            for i in range(min(3, limit))
        ]

    async def update_inventory(
        self,
        sku: str,
        qty: int,
        oauth_token: str,
    ) -> bool:
        """Mock —— 总是返回 True（不改任何状态）。

        真实端点：feeds_2021-06-30 提交 ``POST_INVENTORY_AVAILABILITY_DATA``。
        """
        return True

    async def health_check(
        self,
        oauth_token: str | None = None,
    ) -> bool:
        """Mock —— 只要 LWA 三件套都配齐，返回 True；否则 False。

        真实端点：``GET /sellers/v1/marketplaceParticipations``。
        """
        return bool(self.lwa_client_id and self.lwa_client_secret and self.refresh_token)


__all__ = ["AmazonSPEcommerceSource"]
