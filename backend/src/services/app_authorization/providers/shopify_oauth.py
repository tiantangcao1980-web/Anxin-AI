# -*- coding: utf-8 -*-
"""Shopify OAuth 2.0 Provider（P4-E）。

参考文档：
- https://shopify.dev/docs/apps/auth/oauth
- https://shopify.dev/docs/api/admin-rest/2024-10/resources/shop

接口对齐 P4-A 框架（``BaseOAuthProvider`` / ``OAuthTokenBundle``）。Shopify
OAuth 与其他 Provider（飞书 / 钉钉 / Google）的核心差异：

1. **多租户域名**：每个商家有自己独立的 ``{shop}.myshopify.com`` 域，所有
   OAuth + Admin API 端点都包含该域名。``{shop}`` 必须在调用 ``authorize_url``
   时通过 ``shop=`` 关键字参数传入；后续 ``exchange_code`` / ``refresh_token``
   / ``revoke`` / ``get_user_info`` 同样需要知道是哪个商家。我们把 ``shop``
   持久化到 ``OAuthTokenBundle.raw["shop"]``，由上层 token store 一并落库；
   读回时再从 ``raw`` 回填到调用上下文。

2. **token 类型**：默认 **offline mode** 永不过期 — Shopify 颁发的
   access_token 是长期凭据，没有 ``refresh_token``，也没有 ``expires_in``。
   因此本 Provider 的 :meth:`refresh_token` **显式抛 NotImplementedError**：
   token 失效时只能引导用户重新授权（re-auth）。
   （online mode token 会带 ``expires_in``，按 OAuthTokenBundle.expires_at 落库。）

3. **鉴权头**：访问 Admin API 用自定义头
   ``X-Shopify-Access-Token: <access_token>``，**不是**标准
   ``Authorization: Bearer``。

4. **HMAC 回调验证**：Shopify 在 OAuth 回调 query string 中带 ``hmac`` 参数，
   是用 client_secret 对其余 query 参数（按字典序、URL-encoded）做的
   HMAC-SHA256。``exchange_code`` 之前 **必须** 调用
   :meth:`verify_callback_hmac` 校验，防止伪造回调。
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from loguru import logger


# ---------------------------------------------------------------------------
# Base 类导入：优先用 P4-A 框架，缺失时本地 fallback
# ---------------------------------------------------------------------------
try:  # pragma: no cover - 仅在 P4-A base 已合入时走真实路径
    from ..base import BaseOAuthProvider, OAuthTokenBundle  # type: ignore
except ImportError:  # pragma: no cover - 测试 / 框架未合入时使用 fallback
    from dataclasses import dataclass, field

    @dataclass
    class OAuthTokenBundle:  # type: ignore[no-redef]
        """OAuth token 三元组的标准化封装。

        ``expires_at`` 为 UTC，**含时区**。所有 Provider 必须返回该结构，
        让上层 ``AppAuthorizationService`` 能统一刷新与持久化。
        """

        access_token: str
        refresh_token: Optional[str] = None
        expires_at: Optional[datetime] = None
        scope: Optional[str] = None
        token_type: str = "Bearer"
        raw: dict[str, Any] = field(default_factory=dict)

    class BaseOAuthProvider:  # type: ignore[no-redef]
        """OAuth Provider 抽象基类（fallback 版本）。

        子类必须覆盖类属性 ``provider_id`` / ``display_name`` / ``category``
        / ``icon_url`` / ``default_scopes``，并实装 5 个异步方法。
        """

        provider_id: str = ""
        display_name: str = ""
        category: str = ""
        icon_url: str = ""
        default_scopes: list[str] = []

        def __init__(
            self,
            *,
            client_id: str,
            client_secret: str,
            redirect_uri: str,
            http_client: Optional[httpx.AsyncClient] = None,
        ) -> None:
            self.client_id = client_id
            self.client_secret = client_secret
            self.redirect_uri = redirect_uri
            self._http = http_client


# ---------------------------------------------------------------------------
# Shopify OAuth Provider 实装
# ---------------------------------------------------------------------------
class ShopifyOAuthProvider(BaseOAuthProvider):
    """Shopify Admin API OAuth 2.0（offline mode 默认）。

    使用方式::

        provider = ShopifyOAuthProvider(
            client_id=settings.SHOPIFY_API_KEY,
            client_secret=settings.SHOPIFY_API_SECRET,
            redirect_uri="https://anxin.example/oauth/callback/shopify",
        )
        # ① 生成授权 URL（必须传 shop）
        url = await provider.authorize_url(state="xyz", shop="acme.myshopify.com")

        # ② 回调时先校验 HMAC，再换 token
        assert provider.verify_callback_hmac(query_dict, settings.SHOPIFY_API_SECRET)
        bundle = await provider.exchange_code(
            code, state="xyz", shop="acme.myshopify.com"
        )
        # bundle.raw["shop"] == "acme.myshopify.com"  ← 必须落库

        # ③ 后续调用需要带 shop（从 bundle.raw 回读）
        info = await provider.get_user_info(
            bundle.access_token, shop=bundle.raw["shop"]
        )
    """

    # ---- Provider 元数据（被 ``providers/registry.py`` 反射使用） ----
    provider_id = "shopify"
    display_name = "Shopify"
    category = "ecommerce"
    icon_url = (
        "https://cdn.shopify.com/shopifycloud/brochure/assets/"
        "brand-assets/shopify-logo-primary-logo.svg"
    )
    # read_products / write_products  — 商品 CRUD（智能体上架、改价等）
    # read_orders   / write_orders    — 订单查询、退款、备注
    # read_customers                  — 客户档案（CRM 类智能体）
    default_scopes = [
        "read_products",
        "write_products",
        "read_orders",
        "write_orders",
        "read_customers",
    ]

    # ---- Shopify OAuth / Admin 端点模板（{shop} 占位） ----
    AUTHORIZE_URL_TEMPLATE = "https://{shop}/admin/oauth/authorize"
    TOKEN_URL_TEMPLATE = "https://{shop}/admin/oauth/access_token"
    REVOKE_URL_TEMPLATE = (
        "https://{shop}/admin/api/{api_version}/oauth/revoke.json"
    )
    SHOP_INFO_URL_TEMPLATE = (
        "https://{shop}/admin/api/{api_version}/shop.json"
    )

    # 默认 API 版本（Shopify 季度发布制；可被构造参数覆盖）
    DEFAULT_API_VERSION = "2024-10"

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        http_client: Optional[httpx.AsyncClient] = None,
        api_version: str = DEFAULT_API_VERSION,
    ) -> None:
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            http_client=http_client,
        )
        self.api_version = api_version

    # ============== 1. 授权 URL ==============
    async def authorize_url(
        self,
        state: str,
        *,
        scopes: Optional[list[str]] = None,
        extra_params: Optional[dict[str, str]] = None,
        shop: Optional[str] = None,
        **_kwargs: Any,
    ) -> str:
        """生成 Shopify 授权页 URL。

        必须通过关键字参数 ``shop=`` 传入商家域名（``acme.myshopify.com``）；
        缺失则抛 ``ValueError``。scope 用**逗号**分隔（Shopify 规范）。
        默认追加 ``grant_options[]=per-user`` 以请求 online-mode 二级 token；
        如需纯 offline，可通过 ``extra_params`` 覆盖。
        """
        if not shop:
            raise ValueError("shop required for Shopify")

        normalized_shop = self._normalize_shop(shop)
        scope_list = scopes or self.default_scopes

        params: dict[str, str] = {
            "client_id": self.client_id,
            "scope": ",".join(scope_list),
            "redirect_uri": self.redirect_uri,
            "state": state,
            # per-user (online mode) 让用户感知授权范围；如需 offline 由调用方覆盖
            "grant_options[]": "per-user",
        }
        if extra_params:
            params.update(extra_params)

        url = self.AUTHORIZE_URL_TEMPLATE.format(shop=normalized_shop)
        return f"{url}?{urlencode(params)}"

    # ============== 2. code → token ==============
    async def exchange_code(
        self,
        code: str,
        *,
        state: Optional[str] = None,  # noqa: ARG002 — 兼容签名
        shop: Optional[str] = None,
        **_kwargs: Any,
    ) -> OAuthTokenBundle:
        """用授权码换 access_token。

        Shopify 默认 offline mode 不返回 ``refresh_token`` 与 ``expires_in``。
        ``shop`` 必须传入，并写入返回 bundle 的 ``raw["shop"]``，由上层落库。
        """
        if not shop:
            raise ValueError("shop required for Shopify")

        normalized_shop = self._normalize_shop(shop)
        url = self.TOKEN_URL_TEMPLATE.format(shop=normalized_shop)
        body = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
        }
        data = await self._post_json(url, body)
        return self._bundle_from_response(data, shop=normalized_shop)

    # ============== 3. 刷新 token ==============
    async def refresh_token(
        self,
        refresh_token: str,  # noqa: ARG002
    ) -> OAuthTokenBundle:
        """Shopify offline tokens 永不过期 — 不支持刷新。

        若 online-mode token 过期或被商家在后台撤销，唯一办法是引导用户
        重新走授权流程（re-auth），不能用 refresh_token 续期。
        """
        raise NotImplementedError(
            "Shopify offline tokens never expire; use re-auth"
        )

    # ============== 4. 撤销 ==============
    async def revoke(
        self,
        access_token: str,
        *,
        shop: Optional[str] = None,
        **_kwargs: Any,
    ) -> None:
        """撤销 Shopify access_token。

        端点 ``DELETE /admin/api/{version}/oauth/revoke.json``，使用自定义
        鉴权头 ``X-Shopify-Access-Token``。``shop`` 必填，从上层 token store
        的 ``raw["shop"]`` 回读。
        """
        if not shop:
            raise ValueError("shop required for Shopify")

        normalized_shop = self._normalize_shop(shop)
        url = self.REVOKE_URL_TEMPLATE.format(
            shop=normalized_shop, api_version=self.api_version
        )
        headers = {"X-Shopify-Access-Token": access_token}
        client = self._client()
        owns_client = self._http is None
        try:
            resp = await client.delete(url, headers=headers)
            self._raise_for_shopify_error(resp)
        finally:
            if owns_client:
                await client.aclose()
        return None

    # ============== 5. 用户/Shop 信息 ==============
    async def get_user_info(
        self,
        access_token: str,
        *,
        shop: Optional[str] = None,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """拉取当前店铺元数据（name / email / country / timezone / currency）。

        Shopify 没有 OIDC ``userinfo`` 概念，最接近的是 ``GET shop.json`` 返回
        的店铺档案；这同时也能验证 token + shop 是否依然有效。
        """
        if not shop:
            raise ValueError("shop required for Shopify")

        normalized_shop = self._normalize_shop(shop)
        url = self.SHOP_INFO_URL_TEMPLATE.format(
            shop=normalized_shop, api_version=self.api_version
        )
        headers = {"X-Shopify-Access-Token": access_token}
        client = self._client()
        owns_client = self._http is None
        try:
            resp = await client.get(url, headers=headers)
            self._raise_for_shopify_error(resp)
            return resp.json()
        finally:
            if owns_client:
                await client.aclose()

    # ============== HMAC 回调验证（工具方法） ==============
    @classmethod
    def verify_callback_hmac(
        cls,
        query_dict: dict[str, Any],
        secret: str,
    ) -> bool:
        """校验 Shopify OAuth 回调的 HMAC 签名。

        Shopify 计算方式：
            1. 从 query string 中剔除 ``hmac`` 与 ``signature``；
            2. 剩余键按字典序排序，拼成 ``key=value&key=...`` 形式；
            3. 用 client_secret 做 HMAC-SHA256，hexdigest 与 query 中的
               ``hmac`` 字段做 **常量时间** 比较。

        参数：
            query_dict: 回调 URL 解析后的 query dict（Flask/FastAPI 的
                ``request.query_params`` 可直接传）；值若是 list 取第一个。
            secret: Shopify App 的 ``client_secret``。

        返回：``True`` 表示签名合法；``False`` 表示伪造或被篡改。
        """
        if not query_dict or "hmac" not in query_dict:
            return False

        # ----- 抽出受保护的 hmac 值，并归一化 dict（list -> str） -----
        normalized: dict[str, str] = {}
        provided_hmac: Optional[str] = None
        for key, value in query_dict.items():
            v = value[0] if isinstance(value, (list, tuple)) else value
            if v is None:
                continue
            v_str = str(v)
            if key == "hmac":
                provided_hmac = v_str
                continue
            if key == "signature":
                # legacy field — Shopify 文档明确剔除
                continue
            normalized[str(key)] = v_str

        if provided_hmac is None:
            return False

        # ----- 构造待签名字符串：字典序 + key=value& 拼接 -----
        message = "&".join(
            f"{k}={normalized[k]}" for k in sorted(normalized.keys())
        )
        digest = hmac.new(
            secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(digest, provided_hmac)

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_shop(shop: str) -> str:
        """归一化 shop 域名 — 去掉 https:// 前缀和尾部斜线。

        允许传入：
        - ``acme.myshopify.com``
        - ``https://acme.myshopify.com``
        - ``acme.myshopify.com/``
        """
        s = shop.strip()
        if s.startswith("https://"):
            s = s[len("https://"):]
        elif s.startswith("http://"):
            s = s[len("http://"):]
        return s.rstrip("/")

    def _client(self) -> httpx.AsyncClient:
        """返回 httpx client：测试可注入，生产临时创建。"""
        if self._http is not None:
            return self._http
        return httpx.AsyncClient(timeout=10.0)

    async def _post_json(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        client = self._client()
        owns_client = self._http is None
        try:
            resp = await client.post(url, json=body)
            self._raise_for_shopify_error(resp)
            return resp.json()
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    def _raise_for_shopify_error(resp: httpx.Response) -> None:
        """Shopify 错误体常见格式：``{"errors": "..."}`` 或 4xx/5xx。"""
        if resp.status_code >= 400:
            try:
                data = resp.json()
            except Exception:  # noqa: BLE001
                data = {"raw": resp.text}
            logger.error(f"[shopify_oauth] HTTP {resp.status_code} {data}")
            raise ValueError(
                f"Shopify OAuth 请求失败: HTTP {resp.status_code} - "
                f"{data.get('errors') or data.get('error') or data.get('raw', '未知错误')}"
            )

    def _bundle_from_response(
        self,
        data: dict[str, Any],
        *,
        shop: str,
    ) -> OAuthTokenBundle:
        """把 Shopify token 响应映射到 ``OAuthTokenBundle``。

        响应字段（offline 模式）::

            {"access_token": "shpat_xxx", "scope": "read_products,write_orders"}

        online 模式还会带 ``expires_in`` + ``associated_user`` + 第二段
        ``associated_user_scope``，这里统一保留到 ``raw``。

        关键：把 ``shop`` 写入 ``raw["shop"]`` — 后续 refresh / revoke /
        get_user_info 调用都从上层回读这个值。
        """
        access = data.get("access_token")
        if not access:
            raise ValueError(f"Shopify 返回缺少 access_token 字段: {data}")

        expire_in = data.get("expires_in")
        expires_at: Optional[datetime] = None
        if isinstance(expire_in, (int, float)):
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=int(expire_in) - 60  # 提前 60s 视为过期
            )

        # raw 必含 shop，并把原始响应一并保留供调试 / 二次处理
        raw: dict[str, Any] = dict(data)
        raw["shop"] = shop

        return OAuthTokenBundle(
            access_token=access,
            refresh_token=None,  # offline 模式无 RT；online 模式 Shopify 也不发 RT
            expires_at=expires_at,
            scope=data.get("scope"),
            token_type="Bearer",
            raw=raw,
        )
