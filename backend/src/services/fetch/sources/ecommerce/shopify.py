"""Shopify Admin API 数据源（真实 HTTP 接入，复用 P4-E OAuth）。

参考文档
--------
- Admin REST API 2024-10：https://shopify.dev/docs/api/admin-rest/2024-10
- 商品搜索：``GET /admin/api/2024-10/products.json``
- 订单列表：``GET /admin/api/2024-10/orders.json``
- 库存调整：``PUT /admin/api/2024-10/inventory_levels/set.json``

多租户 shop 域名
----------------
P4-E 的 ``ShopifyOAuthProvider.exchange_code`` 把 shop 域名写入了
``OAuthTokenBundle.raw["shop"]``。本 source 在 OAuth-aware 调用链路里
**通过显式构造参数 ``shop`` 注入**：

    1. 在 P6-A FetchService 解密 token 时，会一并取出 ``raw["shop"]``；
    2. 实例化 ``ShopifyEcommerceSource(shop=...)``，再注入 ``oauth_token``；
    3. 构造时未传 shop，可在每次方法调用时通过 ``shop=`` kwarg 临时覆盖
       （主要给单测用）。

鉴权头
------
Shopify Admin API 用自定义头 ``X-Shopify-Access-Token``，不是标准 Bearer。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from loguru import logger

from .base import (
    BaseEcommerceSource,
    EcommerceSourceError,
    OAuthRequiredError,
    Order,
    Product,
    ProductSearchQuery,
)

# 默认 API 版本与 P4-E ``ShopifyOAuthProvider.DEFAULT_API_VERSION`` 对齐
DEFAULT_API_VERSION = "2024-10"


# ---------------------------------------------------------------------------
# Shopify 状态映射 → 统一态
# ---------------------------------------------------------------------------
# financial_status + fulfillment_status 联合判定订单整体状态
_SHOPIFY_STATUS_MAP: dict[tuple[str | None, str | None], str] = {
    ("pending", None): "pending",
    ("paid", None): "paid",
    ("paid", "fulfilled"): "shipped",
    ("paid", "partial"): "shipped",
    ("refunded", None): "cancelled",
    ("voided", None): "cancelled",
}


def _map_shopify_order_status(financial: str | None, fulfillment: str | None) -> str:
    """联合 financial_status + fulfillment_status 映射到统一态。

    映射策略（按优先级）：
        1. 直接命中 (financial, fulfillment) 元组；
        2. fulfillment == 'fulfilled' / 'shipped'  → shipped；
        3. fulfillment == 'delivered'              → delivered；
        4. financial   == 'voided' / 'refunded'    → cancelled；
        5. financial   == 'paid'                   → paid；
        6. 其他                                     → pending。
    """
    key = (financial, fulfillment)
    if key in _SHOPIFY_STATUS_MAP:
        return _SHOPIFY_STATUS_MAP[key]
    if fulfillment in ("fulfilled", "shipped"):
        return "shipped"
    if fulfillment == "delivered":
        return "delivered"
    if financial in ("voided", "refunded"):
        return "cancelled"
    if financial == "paid":
        return "paid"
    return "pending"


# ---------------------------------------------------------------------------
# Source 实装
# ---------------------------------------------------------------------------
class ShopifyEcommerceSource(BaseEcommerceSource):
    """Shopify Admin API 数据源 — 真实 HTTP 接入。

    用法::

        # FetchService 已从 P4-E token store 解密拿到 access_token + raw['shop']
        source = ShopifyEcommerceSource(
            shop="acme.myshopify.com",
            api_version="2024-10",          # 可选
            http_client=shared_httpx_client, # 可选；不传则按需创建
        )
        products = await source.search_products(
            ProductSearchQuery(keyword="hoodie", limit=10),
            oauth_token=decrypted_access_token,
        )
    """

    source_id = "shopify"
    display_name = "Shopify"
    requires_oauth = True

    def __init__(
        self,
        *,
        shop: str | None = None,
        api_version: str = DEFAULT_API_VERSION,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._shop_default = self._normalize_shop(shop) if shop else None
        self.api_version = api_version
        self._http = http_client

    # ===================================================================
    # 公共 API
    # ===================================================================
    async def search_products(
        self,
        query: ProductSearchQuery,
        oauth_token: str | None = None,
        *,
        shop: str | None = None,
    ) -> list[Product]:
        """``GET /admin/api/{ver}/products.json?title={kw}&limit={n}``。

        Shopify REST 不支持服务端按价格过滤；``price_min/max`` 由本端在
        客户端侧 filter。``sort_by`` 同理在客户端做（REST 没暴露排序参数）。
        """
        token = self._ensure_token(oauth_token)
        store = self._resolve_shop(shop)
        url = self._build_url(store, "products.json")

        # Shopify REST 上限 250；query.limit 截断到 [1, 250]
        limit = max(1, min(query.limit, 250))
        params: dict[str, Any] = {"limit": limit, "title": query.keyword}
        if query.category:
            params["product_type"] = query.category

        data = await self._get_json(url, token, params=params)
        items = data.get("products", []) if isinstance(data, dict) else []

        products = [self._product_from_shopify(p, store) for p in items]
        return self._client_side_filter_sort(products, query)

    async def get_product(
        self,
        sku: str,
        oauth_token: str | None = None,
        *,
        shop: str | None = None,
    ) -> Product | None:
        """按 product id 取单品（Shopify 的 sku 对外是 ``Product.id``）。"""
        token = self._ensure_token(oauth_token)
        store = self._resolve_shop(shop)
        url = self._build_url(store, f"products/{sku}.json")
        try:
            data = await self._get_json(url, token)
        except EcommerceSourceError as e:
            # 404 当作未命中
            if "404" in str(e):
                return None
            raise
        product = data.get("product") if isinstance(data, dict) else None
        if not product:
            return None
        return self._product_from_shopify(product, store)

    async def list_orders(
        self,
        oauth_token: str,
        since: datetime | None = None,
        limit: int = 50,
        *,
        shop: str | None = None,
    ) -> list[Order]:
        """``GET /admin/api/{ver}/orders.json?status=any&updated_at_min=...&limit=...``。"""
        token = self._ensure_token(oauth_token)
        store = self._resolve_shop(shop)
        url = self._build_url(store, "orders.json")
        params: dict[str, Any] = {
            "status": "any",
            "limit": max(1, min(limit, 250)),
        }
        if since is not None:
            params["updated_at_min"] = since.astimezone(UTC).isoformat()

        data = await self._get_json(url, token, params=params)
        items = data.get("orders", []) if isinstance(data, dict) else []
        return [self._order_from_shopify(o) for o in items]

    async def update_inventory(
        self,
        sku: str,
        qty: int,
        oauth_token: str,
        *,
        shop: str | None = None,
        location_id: int | None = None,
        inventory_item_id: int | None = None,
    ) -> bool:
        """更新库存 — 走 ``POST /inventory_levels/set.json``。

        Shopify 设计：商品 SKU → InventoryItem → InventoryLevel(location, item)。
        因此调用方需要同时提供 ``location_id`` + ``inventory_item_id``；
        如果没传 inventory_item_id，会用 ``sku`` 作为 inventory_item_id 的字符串
        别名（兼容简单接入场景，由下层 API 决定是否接受）。
        """
        token = self._ensure_token(oauth_token)
        store = self._resolve_shop(shop)
        url = self._build_url(store, "inventory_levels/set.json")

        body: dict[str, Any] = {
            "available": int(qty),
            "inventory_item_id": inventory_item_id or sku,
        }
        if location_id is not None:
            body["location_id"] = location_id

        client = self._client()
        owns_client = self._http is None
        try:
            resp = await client.post(
                url,
                json=body,
                headers=self._auth_headers(token),
            )
            self._raise_for_shopify_error(resp)
            return True
        finally:
            if owns_client:
                await client.aclose()

    async def health_check(
        self,
        oauth_token: str | None = None,
        *,
        shop: str | None = None,
    ) -> bool:
        """探活：``GET /admin/api/{ver}/shop.json`` —— 同时校验 token + shop 有效性。

        - 缺 token / shop 一律返回 False（不抛错），方便监控页展示"未连接"。
        """
        if not oauth_token:
            return False
        try:
            store = self._resolve_shop(shop)
        except OAuthRequiredError:
            return False

        url = self._build_url(store, "shop.json")
        try:
            await self._get_json(url, oauth_token)
            return True
        except EcommerceSourceError:
            return False

    # ===================================================================
    # 内部辅助
    # ===================================================================
    @staticmethod
    def _normalize_shop(shop: str) -> str:
        s = shop.strip()
        if s.startswith("https://"):
            s = s[len("https://") :]
        elif s.startswith("http://"):
            s = s[len("http://") :]
        return s.rstrip("/")

    def _resolve_shop(self, shop: str | None) -> str:
        """优先取方法级 ``shop`` kwarg，回退到构造时的默认值。

        两者都缺则抛 :class:`OAuthRequiredError` —— 因为 shop 同样是
        Shopify OAuth 上下文的一部分。
        """
        store = shop or self._shop_default
        if not store:
            raise OAuthRequiredError(
                "Shopify shop 域名缺失（应从 OAuth token store 的 raw['shop'] 读出）"
            )
        return self._normalize_shop(store)

    def _build_url(self, shop: str, endpoint: str) -> str:
        return f"https://{shop}/admin/api/{self.api_version}/{endpoint}"

    @staticmethod
    def _auth_headers(token: str) -> dict[str, str]:
        # Shopify 用自定义头，不是 Authorization: Bearer
        return {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _client(self) -> httpx.AsyncClient:
        if self._http is not None:
            return self._http
        return httpx.AsyncClient(timeout=15.0)

    async def _get_json(
        self,
        url: str,
        token: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = self._client()
        owns_client = self._http is None
        try:
            resp = await client.get(
                url,
                params=params,
                headers=self._auth_headers(token),
            )
            self._raise_for_shopify_error(resp)
            return resp.json()
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    def _raise_for_shopify_error(resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            try:
                body = resp.json()
            except Exception:  # noqa: BLE001
                body = {"raw": resp.text}
            logger.error(
                f"[shopify_source] HTTP {resp.status_code} {body}"
            )
            raise EcommerceSourceError(
                f"Shopify Admin API 请求失败: HTTP {resp.status_code} - "
                f"{body.get('errors') or body.get('error') or body.get('raw', '未知错误')}"
            )

    # ---- 数据模型转换 ----
    @staticmethod
    def _client_side_filter_sort(
        products: list[Product],
        query: ProductSearchQuery,
    ) -> list[Product]:
        """REST 不支持的 price 过滤 + sort，在 Python 侧做。"""
        out = products
        if query.price_min is not None:
            out = [p for p in out if p.price >= query.price_min]
        if query.price_max is not None:
            out = [p for p in out if p.price <= query.price_max]

        sort = query.sort_by
        if sort == "price_asc":
            out = sorted(out, key=lambda p: p.price)
        elif sort == "price_desc":
            out = sorted(out, key=lambda p: p.price, reverse=True)
        elif sort == "newest":
            # raw["created_at"] 由 _product_from_shopify 写入
            out = sorted(
                out,
                key=lambda p: p.raw.get("created_at") or "",
                reverse=True,
            )
        # best_match：保持 Shopify 原序
        return out

    @staticmethod
    def _product_from_shopify(item: dict[str, Any], shop: str) -> Product:
        variants = item.get("variants") or []
        first_variant = variants[0] if variants else {}
        # Shopify variant.price 是字符串
        try:
            price = float(first_variant.get("price", 0) or 0)
        except (TypeError, ValueError):
            price = 0.0

        images = [
            img.get("src", "")
            for img in (item.get("images") or [])
            if isinstance(img, dict) and img.get("src")
        ]

        product_id = item.get("id")
        product_handle = item.get("handle", "")
        url = f"https://{shop}/products/{product_handle}" if product_handle else ""

        return Product(
            source="shopify",
            sku=str(first_variant.get("sku") or product_id or ""),
            title=item.get("title", ""),
            description=item.get("body_html"),
            price=price,
            currency=first_variant.get("price_currency") or "USD",
            images=images,
            inventory_qty=first_variant.get("inventory_quantity"),
            rating=None,         # Shopify REST 默认不带评分
            review_count=None,   # 需要 Reviews app
            seller_name=item.get("vendor"),
            seller_rating=None,
            url=url,
            raw={
                "id": product_id,
                "handle": product_handle,
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "product_type": item.get("product_type"),
                "tags": item.get("tags"),
                "variants_count": len(variants),
            },
        )

    @staticmethod
    def _order_from_shopify(item: dict[str, Any]) -> Order:
        try:
            total = float(item.get("total_price", 0) or 0)
        except (TypeError, ValueError):
            total = 0.0

        placed_at_str = item.get("created_at") or item.get("processed_at")
        try:
            placed_at = (
                datetime.fromisoformat(placed_at_str.replace("Z", "+00:00"))
                if placed_at_str
                else datetime.now(UTC)
            )
        except (TypeError, ValueError, AttributeError):
            placed_at = datetime.now(UTC)

        customer = item.get("customer") or {}
        customer_name = None
        if isinstance(customer, dict):
            first = customer.get("first_name") or ""
            last = customer.get("last_name") or ""
            full = f"{first} {last}".strip()
            customer_name = full or customer.get("email")

        items_norm: list[dict[str, Any]] = []
        for li in item.get("line_items") or []:
            if not isinstance(li, dict):
                continue
            try:
                unit = float(li.get("price", 0) or 0)
            except (TypeError, ValueError):
                unit = 0.0
            items_norm.append(
                {
                    "sku": li.get("sku") or str(li.get("product_id", "")),
                    "title": li.get("title", ""),
                    "qty": int(li.get("quantity", 0) or 0),
                    "unit_price": unit,
                }
            )

        return Order(
            source="shopify",
            order_id=str(item.get("id", "")),
            customer_name=customer_name,
            total_amount=total,
            currency=item.get("currency") or "USD",
            status=_map_shopify_order_status(
                item.get("financial_status"),
                item.get("fulfillment_status"),
            ),
            placed_at=placed_at,
            items=items_norm,
        )


__all__ = ["ShopifyEcommerceSource"]
