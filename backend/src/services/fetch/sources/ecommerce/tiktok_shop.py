# -*- coding: utf-8 -*-
"""TikTok Shop API 数据源 — mock + 接口契约（P6-D）。

TikTok Shop 通过短视频/直播带货完成购买闭环，是 Z 世代主战场。真实接入：

    1. TikTok Partner Center 注册开发者账号；
    2. App Key + App Secret + OAuth 授权拿 ``shop_cipher`` + ``access_token``；
    3. 请求签名：``sign = HMAC-SHA256(app_secret, sorted_params)``；
    4. region：``Open-API.TikTokGlobalShop.com``（全球）/ 各市场分 endpoint。

P6-D 阶段全部 mock，返回 5 条短视频带货风格的假商品。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from .base import (
    BaseEcommerceSource,
    Order,
    Product,
    ProductSearchQuery,
)

# ---------------------------------------------------------------------------
# Mock 数据 — 5 条短视频带货商品（含播放量、达人字段写在 raw）
# ---------------------------------------------------------------------------
_MOCK_TIKTOK_LISTINGS: list[dict] = [
    {
        "product_id": "TTSMOCK00001",
        "title": "Viral TikTok Beauty Blender Sponge Set",
        "price": 12.99,
        "currency": "USD",
        "country": "US",
        "rating": 4.6,
        "reviews": 28452,
        "shop_name": "GlowUpCosmetics",
        "shop_rating": 4.7,
        "viral_video_views": 12_300_000,
        "creator": "@beautybyjade",
    },
    {
        "product_id": "TTSMOCK00002",
        "title": "Cordless Mini Hair Straightener TikTok Made Me Buy",
        "price": 24.50,
        "currency": "USD",
        "country": "US",
        "rating": 4.5,
        "reviews": 17321,
        "shop_name": "HairTechStore",
        "shop_rating": 4.6,
        "viral_video_views": 8_900_000,
        "creator": "@haircarequeen",
    },
    {
        "product_id": "TTSMOCK00003",
        "title": "Reusable Face Roller — Ice Cooling Edition",
        "price": 9.99,
        "currency": "GBP",
        "country": "UK",
        "rating": 4.4,
        "reviews": 6201,
        "shop_name": "WellnessUK",
        "shop_rating": 4.5,
        "viral_video_views": 4_200_000,
        "creator": "@selfcaresam",
    },
    {
        "product_id": "TTSMOCK00004",
        "title": "Retro Polaroid Style Mini Camera",
        "price": 35.00,
        "currency": "USD",
        "country": "US",
        "rating": 4.7,
        "reviews": 9842,
        "shop_name": "RetroVibeShop",
        "shop_rating": 4.8,
        "viral_video_views": 15_600_000,
        "creator": "@vintageaddict",
    },
    {
        "product_id": "TTSMOCK00005",
        "title": "Stanley-Style 40oz Tumbler with Handle",
        "price": 28.00,
        "currency": "USD",
        "country": "US",
        "rating": 4.6,
        "reviews": 33210,
        "shop_name": "HydrateDaily",
        "shop_rating": 4.7,
        "viral_video_views": 22_400_000,
        "creator": "@dailyhydration",
    },
]


def _build_mock_product(item: dict) -> Product:
    return Product(
        source="tiktok_shop",
        sku=item["product_id"],
        title=item["title"],
        description=f"[MOCK] TikTok Shop —— 占位数据（{item['creator']} 带货）",
        price=item["price"],
        currency=item["currency"],
        images=[
            f"https://p16-tiktokshop.tiktokcdn.com/{item['product_id']}_main.webp",
        ],
        inventory_qty=300,
        rating=item["rating"],
        review_count=item["reviews"],
        seller_name=item["shop_name"],
        seller_rating=item["shop_rating"],
        url=f"https://shop.tiktok.com/view/product/{item['product_id']}",
        raw={
            "product_id": item["product_id"],
            "country": item["country"],
            "viral_video_views": item["viral_video_views"],
            "creator": item["creator"],
            "_mock": True,
            "_real_endpoint": "/product/202309/products/search",
        },
    )


class TikTokShopEcommerceSource(BaseEcommerceSource):
    """TikTok Shop 数据源（mock）。

    构造参数（对齐真实接入）：

        - ``app_key`` / ``app_secret``：TikTok Partner Center 凭据
        - ``shop_cipher``：商家店铺密文（OAuth 回调取得）
        - ``region``：``us`` / ``uk`` / ``id`` / ``th`` / ``vn`` / ``my`` / ``ph``

    ⚠️ 全 mock，不发任何 HTTP 请求。
    """

    source_id = "tiktok_shop"
    display_name = "TikTok Shop"
    requires_oauth = True

    DEFAULT_REGION = "us"

    def __init__(
        self,
        *,
        app_key: str = "",
        app_secret: str = "",
        shop_cipher: str = "",
        region: str = DEFAULT_REGION,
    ) -> None:
        self.app_key = app_key
        self.app_secret = app_secret
        self.shop_cipher = shop_cipher
        self.region = region

    async def search_products(
        self,
        query: ProductSearchQuery,
        oauth_token: Optional[str] = None,
    ) -> list[Product]:
        """Mock —— 5 条短视频带货商品；country 命中只返该国。

        真实端点：``POST /product/202309/products/search``
        """
        items = _MOCK_TIKTOK_LISTINGS
        if query.country:
            country = query.country.upper()
            items = [i for i in items if i["country"] == country] or items
        # newest 排序：按 viral_video_views 降序近似
        if query.sort_by == "newest":
            items = sorted(items, key=lambda x: x["viral_video_views"], reverse=True)
        elif query.sort_by == "price_asc":
            items = sorted(items, key=lambda x: x["price"])
        elif query.sort_by == "price_desc":
            items = sorted(items, key=lambda x: x["price"], reverse=True)
        products = [_build_mock_product(i) for i in items]
        for p in products:
            p.raw["_query_keyword"] = query.keyword
        return products[: max(1, min(query.limit, len(products)))]

    async def get_product(
        self,
        sku: str,
        oauth_token: Optional[str] = None,
    ) -> Optional[Product]:
        """Mock —— product_id 命中即返。

        真实端点：``GET /product/202309/products/{product_id}``
        """
        for item in _MOCK_TIKTOK_LISTINGS:
            if item["product_id"] == sku:
                return _build_mock_product(item)
        return None

    async def list_orders(
        self,
        oauth_token: str,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[Order]:
        """Mock —— 3 条假订单。

        真实端点：``POST /order/202309/orders/search``
        """
        now = datetime.now(timezone.utc)
        base_since = since or (now - timedelta(days=3))
        return [
            Order(
                source="tiktok_shop",
                order_id=f"TTSMOCK-OD-{i:08d}",
                customer_name=f"tiktok_user_{i}",
                total_amount=_MOCK_TIKTOK_LISTINGS[i]["price"],
                currency=_MOCK_TIKTOK_LISTINGS[i]["currency"],
                status=("paid", "shipped", "delivered")[i],
                placed_at=base_since + timedelta(hours=i * 8),
                items=[
                    {
                        "sku": _MOCK_TIKTOK_LISTINGS[i]["product_id"],
                        "title": _MOCK_TIKTOK_LISTINGS[i]["title"],
                        "qty": 1,
                        "unit_price": _MOCK_TIKTOK_LISTINGS[i]["price"],
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

        真实端点：``POST /product/202309/inventory/update``
        """
        return True

    async def health_check(
        self,
        oauth_token: Optional[str] = None,
    ) -> bool:
        """Mock —— App Key/Secret 齐 → True。

        真实端点：``GET /seller/202309/shops``
        """
        return bool(self.app_key and self.app_secret)


__all__ = ["TikTokShopEcommerceSource"]
