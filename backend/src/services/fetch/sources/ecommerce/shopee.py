"""Shopee Open Platform 数据源 — mock + 接口契约（P6-D）。

Shopee 是东南亚 + 拉美的主流电商平台（SG/MY/TH/ID/PH/VN/BR/MX/CO 等），
真实接入需要：

    1. Shopee Partner 平台审核 + 拿到 ``partner_id`` / ``partner_key``；
    2. OAuth：商家在店铺侧授权后回调拿 ``shop_id`` + ``access_token``；
    3. 每个请求要附 ``sign = HMAC-SHA256(partner_key, "...")``；
    4. region 决定 endpoint：``partner.shopeemobile.com`` 是测试环境，
       生产是 ``partner.shopee.cn``。

P6-D 阶段全部 mock，返回 5 条东南亚市场的假商品。
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
# Mock 数据 — 5 条东南亚市场假商品
# ---------------------------------------------------------------------------
_MOCK_LISTINGS: list[dict] = [
    {
        "item_id": "SHOPEEMOCK001",
        "title": "Tai Nghe Bluetooth Pro Cao Cấp",
        "price": 280000,  # VND
        "currency": "VND",
        "country": "VN",
        "rating": 4.7,
        "reviews": 5421,
        "shop_name": "TechVN_Official",
        "shop_rating": 4.9,
    },
    {
        "item_id": "SHOPEEMOCK002",
        "title": "Botol Air Stainless 32oz Tahan Panas",
        "price": 89.90,  # MYR
        "currency": "MYR",
        "country": "MY",
        "rating": 4.6,
        "reviews": 2104,
        "shop_name": "HomeStyleMY",
        "shop_rating": 4.8,
    },
    {
        "item_id": "SHOPEEMOCK003",
        "title": "โต๊ะยืนทำงาน ปรับระดับได้ 2 ชั้น",
        "price": 4990.00,  # THB
        "currency": "THB",
        "country": "TH",
        "rating": 4.4,
        "reviews": 812,
        "shop_name": "ErgoOfficeTH",
        "shop_rating": 4.7,
    },
    {
        "item_id": "SHOPEEMOCK004",
        "title": "Bubuk Matcha Organik 100g Premium Jepang",
        "price": 165000,  # IDR
        "currency": "IDR",
        "country": "ID",
        "rating": 4.8,
        "reviews": 3902,
        "shop_name": "WellnessImportID",
        "shop_rating": 4.9,
    },
    {
        "item_id": "SHOPEEMOCK005",
        "title": "LED Smart Strip Lights 10m WiFi App Control",
        "price": 1450.00,  # PHP
        "currency": "PHP",
        "country": "PH",
        "rating": 4.5,
        "reviews": 6321,
        "shop_name": "BrightHomePH",
        "shop_rating": 4.6,
    },
]


def _build_mock_product(item: dict) -> Product:
    return Product(
        source="shopee",
        sku=item["item_id"],
        title=item["title"],
        description=f"[MOCK] Shopee {item['country']} —— 占位数据",
        price=item["price"],
        currency=item["currency"],
        images=[
            f"https://cf.shopee.{item['country'].lower()}/file/{item['item_id']}.jpg",
        ],
        inventory_qty=500,
        rating=item["rating"],
        review_count=item["reviews"],
        seller_name=item["shop_name"],
        seller_rating=item["shop_rating"],
        url=(f"https://shopee.{item['country'].lower()}" f"/product/{item['item_id']}"),
        raw={
            "item_id": item["item_id"],
            "country": item["country"],
            "_mock": True,
            "_real_endpoint": "/api/v2/product/search_item",
        },
    )


class ShopeeEcommerceSource(BaseEcommerceSource):
    """Shopee Open Platform 数据源（mock）。

    构造参数（对齐真实接入）：

        - ``partner_id`` / ``partner_key``：Shopee Partner 平台凭据
        - ``shop_id``：商家店铺 ID（OAuth 回调取得）
        - ``region``：``sg``/``my``/``th``/``id``/``vn``/``ph``/``br``/``mx``

    ⚠️ 全 mock，不发任何 HTTP 请求。
    """

    source_id = "shopee"
    display_name = "Shopee"
    requires_oauth = True

    DEFAULT_REGION = "sg"

    def __init__(
        self,
        *,
        partner_id: str = "",
        partner_key: str = "",
        shop_id: str = "",
        region: str = DEFAULT_REGION,
    ) -> None:
        self.partner_id = partner_id
        self.partner_key = partner_key
        self.shop_id = shop_id
        self.region = region

    async def search_products(
        self,
        query: ProductSearchQuery,
        oauth_token: str | None = None,
    ) -> list[Product]:
        """Mock —— 5 条东南亚 listing；country 过滤命中后只返该国，否则全返。

        真实端点：``POST /api/v2/product/search_item``
        """
        items = _MOCK_LISTINGS
        if query.country:
            country = query.country.upper()
            items = [i for i in items if i["country"] == country] or items
        products = [_build_mock_product(i) for i in items]
        for p in products:
            p.raw["_query_keyword"] = query.keyword
        return products[: max(1, min(query.limit, len(products)))]

    async def get_product(
        self,
        sku: str,
        oauth_token: str | None = None,
    ) -> Product | None:
        """Mock —— item_id 命中即返回。

        真实端点：``GET /api/v2/product/get_item_base_info``
        """
        for item in _MOCK_LISTINGS:
            if item["item_id"] == sku:
                return _build_mock_product(item)
        return None

    async def list_orders(
        self,
        oauth_token: str,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[Order]:
        """Mock —— 返回 3 条订单。

        真实端点：``GET /api/v2/order/get_order_list``
        """
        now = datetime.now(UTC)
        base_since = since or (now - timedelta(days=7))
        return [
            Order(
                source="shopee",
                order_id=f"SHOPEEMOCK-OD-{i:06d}",
                customer_name=f"shopee_buyer_{i}",
                total_amount=_MOCK_LISTINGS[i]["price"],
                currency=_MOCK_LISTINGS[i]["currency"],
                status=("pending", "paid", "shipped")[i],
                placed_at=base_since + timedelta(days=i),
                items=[
                    {
                        "sku": _MOCK_LISTINGS[i]["item_id"],
                        "title": _MOCK_LISTINGS[i]["title"],
                        "qty": 1,
                        "unit_price": _MOCK_LISTINGS[i]["price"],
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
        """Mock —— True。

        真实端点：``POST /api/v2/product/update_stock``
        """
        return True

    async def health_check(
        self,
        oauth_token: str | None = None,
    ) -> bool:
        """Mock —— Partner 凭据齐 → True。

        真实端点：``GET /api/v2/shop/get_shop_info``
        """
        return bool(self.partner_id and self.partner_key)


__all__ = ["ShopeeEcommerceSource"]
