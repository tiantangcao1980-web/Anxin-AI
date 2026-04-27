# -*- coding: utf-8 -*-
"""跨境电商数据源抽象（P6-D）。

本模块定义了一组 **平台无关** 的数据类与抽象基类，作为 5 个具体 source
（Shopify / Amazon SP-API / 阿里 1688 / Shopee / TikTok Shop）的统一入口。

设计取舍
--------
- **OAuth 与 source 解耦**：所有需要鉴权的方法都把 ``oauth_token`` 作为
  显式参数传入，由上层 ``FetchService``（P6-A）从 P4-E 的 token store 取出
  解密后注入；source 自身不读 DB、也不持有用户态。
- **多租户域名（如 Shopify shop）通过 ``raw["shop"]`` 在 token bundle 中携带**：
  source 内部从调用上下文（``oauth_token`` + 可选 ``extra``）获取，不维护
  租户级状态。
- **mock 平台**：Amazon SP-API / 1688 / Shopee / TikTok Shop 在 P6-D 仅交付
  接口契约 + 假数据，真实接入复杂度（LWA SigV4、ISV 审核）留给下一阶段。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Optional


# ---------------------------------------------------------------------------
# 数据模型 — 平台无关
# ---------------------------------------------------------------------------
@dataclass
class ProductSearchQuery:
    """商品搜索请求模型。

    各平台支持度不同：
    - ``country`` 在 Amazon / Shopee / TikTok Shop 上是市场切换关键字；
      Shopify / 1688 不直接消费（Shopify 由 store 域名决定，1688 主要 CN）。
    - ``sort_by`` 取值统一为 4 种枚举字符串，由 source 内部翻译成各平台原生值；
      不支持的取值降级回 ``best_match``。
    - ``limit`` 在多数平台被 source 内部 clip 到平台允许的最大页大小。
    """

    keyword: str
    category: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    country: Optional[str] = None
    sort_by: str = "best_match"  # best_match | price_asc | price_desc | newest
    limit: int = 20


@dataclass
class Product:
    """跨平台统一商品模型。

    - ``source`` 与具体 source 的 ``source_id`` 一致（``shopify``/``amazon_sp``/...）。
    - ``raw`` 保留平台原始响应（已剥离敏感字段），方便上层做差异化展示与回溯。
    """

    source: str
    sku: str
    title: str
    description: Optional[str]
    price: float
    currency: str
    images: list[str]
    inventory_qty: Optional[int]
    rating: Optional[float]
    review_count: Optional[int]
    seller_name: Optional[str]
    seller_rating: Optional[float]
    url: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Order:
    """跨平台统一订单模型。

    - ``status`` 归一到 5 个状态：``pending`` / ``paid`` / ``shipped`` /
      ``delivered`` / ``cancelled``；source 内部做平台→统一态映射。
    - ``items`` 为 list[dict]：每项至少包含 ``sku``/``title``/``qty``/
      ``unit_price``，其余字段平台自带。
    """

    source: str
    order_id: str
    customer_name: Optional[str]
    total_amount: float
    currency: str
    status: str
    placed_at: datetime
    items: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------
class EcommerceSourceError(RuntimeError):
    """source 层通用异常 — 平台错误 / 鉴权失败 / 网络错误统一抛此类型。"""


class OAuthRequiredError(EcommerceSourceError):
    """需要 OAuth token 但调用方未提供。

    被 ``FetchService`` 捕获后，应该返回 401/403 给前端，提示用户先在
    「应用授权」页面完成对应平台的连接（P4 系列 OAuth provider）。
    """


# ---------------------------------------------------------------------------
# 抽象基类
# ---------------------------------------------------------------------------
class BaseEcommerceSource(ABC):
    """跨境电商数据源抽象基类。

    子类必须覆盖 ClassVar ``source_id`` 与 ``display_name``；如果该平台不
    需要 OAuth（例如未来支持纯公开搜索），可把 ``requires_oauth`` 改成 ``False``。

    所有方法约定 **异步** —— 因为下层 HTTP 调用普遍 IO-bound，且 P6-A
    FetchService 的事件循环是 async 的。
    """

    source_id: ClassVar[str] = ""
    display_name: ClassVar[str] = ""
    requires_oauth: ClassVar[bool] = True

    # ---------------------------------------------------------------
    # 5 个核心能力
    # ---------------------------------------------------------------
    @abstractmethod
    async def search_products(
        self,
        query: ProductSearchQuery,
        oauth_token: Optional[str] = None,
    ) -> list[Product]:
        """按关键词/筛选条件搜索商品。

        ``oauth_token`` 在 ``requires_oauth=True`` 的 source 上必传；否则
        子类应在入口校验并抛 :class:`OAuthRequiredError`。
        """

    @abstractmethod
    async def get_product(
        self,
        sku: str,
        oauth_token: Optional[str] = None,
    ) -> Optional[Product]:
        """取单个 SKU 详情。命中返回 :class:`Product`，未命中返回 ``None``。"""

    @abstractmethod
    async def list_orders(
        self,
        oauth_token: str,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[Order]:
        """拉取订单列表。

        ``oauth_token`` 必传 —— 订单是商家私域数据，不存在公开访问场景。
        ``since`` 用于增量同步：传入则取 ``updated_at_min=since`` 的订单。
        """

    @abstractmethod
    async def update_inventory(
        self,
        sku: str,
        qty: int,
        oauth_token: str,
    ) -> bool:
        """更新指定 SKU 的库存数量。返回 ``True`` 表示平台侧已确认更新。"""

    @abstractmethod
    async def health_check(
        self,
        oauth_token: Optional[str] = None,
    ) -> bool:
        """探活：返回 ``True`` 表示该 source（或其凭据）当前可用。

        - ``requires_oauth=True`` 的 source：未传 token 时应返回 ``False``
          而不是抛错 —— 监控面板会把它作为「未连接」状态展示。
        """

    # ---------------------------------------------------------------
    # 通用辅助（子类可覆盖）
    # ---------------------------------------------------------------
    def _ensure_token(self, oauth_token: Optional[str]) -> str:
        """子类在需要 token 的方法入口调用 —— 缺失时抛 :class:`OAuthRequiredError`。

        返回非空 token，方便子类直接拿来用。
        """
        if self.requires_oauth and not oauth_token:
            raise OAuthRequiredError(
                f"source={self.source_id} 需要 OAuth token，请先完成应用授权"
            )
        return oauth_token or ""


__all__ = [
    "BaseEcommerceSource",
    "Product",
    "ProductSearchQuery",
    "Order",
    "EcommerceSourceError",
    "OAuthRequiredError",
]
