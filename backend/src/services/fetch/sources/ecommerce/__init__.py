# -*- coding: utf-8 -*-
"""跨境电商数据源插件包（P6-D）。

5 个 source：

    - :class:`shopify.ShopifyEcommerceSource`        — Shopify Admin API（真实接入）
    - :class:`amazon_sp.AmazonSPEcommerceSource`    — Amazon SP-API（mock + 接口契约）
    - :class:`alibaba_1688.Alibaba1688EcommerceSource` — 1688 开放平台（mock）
    - :class:`shopee.ShopeeEcommerceSource`         — Shopee Open Platform（mock）
    - :class:`tiktok_shop.TikTokShopEcommerceSource` — TikTok Shop API（mock）

通过下方的 ``ALL_SOURCES`` 元组让 P6-A FetchService 注册器一行扫描即可加载。
"""

from __future__ import annotations

from .alibaba_1688 import Alibaba1688EcommerceSource
from .amazon_sp import AmazonSPEcommerceSource
from .base import (
    BaseEcommerceSource,
    EcommerceSourceError,
    OAuthRequiredError,
    Order,
    Product,
    ProductSearchQuery,
)
from .shopee import ShopeeEcommerceSource
from .shopify import ShopifyEcommerceSource
from .tiktok_shop import TikTokShopEcommerceSource

ALL_SOURCES: tuple[type[BaseEcommerceSource], ...] = (
    ShopifyEcommerceSource,
    AmazonSPEcommerceSource,
    Alibaba1688EcommerceSource,
    ShopeeEcommerceSource,
    TikTokShopEcommerceSource,
)

__all__ = [
    "BaseEcommerceSource",
    "Product",
    "ProductSearchQuery",
    "Order",
    "EcommerceSourceError",
    "OAuthRequiredError",
    "ShopifyEcommerceSource",
    "AmazonSPEcommerceSource",
    "Alibaba1688EcommerceSource",
    "ShopeeEcommerceSource",
    "TikTokShopEcommerceSource",
    "ALL_SOURCES",
]
