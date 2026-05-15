# -*- coding: utf-8 -*-
"""Amazon Selling Partner OAuth 2.0 Provider（P4-J）。

Amazon SP-API 用 **LWA (Login with Amazon)** 做 OAuth；与 Shopify / 飞书的关键差别：

1. **3 个区域 endpoint**（NA / EU / FE），由 ``marketplace_region`` 选择；
   token URL 全球统一为 ``https://api.amazon.com/auth/o2/token``，但
   API endpoint 按区域走 ``sellingpartnerapi-{na,eu,fe}.amazon.com``。

2. **token 类型**：
   - ``access_token`` 1 小时过期
   - ``refresh_token`` 不过期（可一直刷）
   - 必须用 refresh_token 续期；不刷就 401

3. **请求签名**：Amazon SP-API 用 AWS Signature V4（IAM Role）+ LWA token
   两套鉴权。本 provider 只负责 LWA token；签名由请求层（``boto3`` /
   ``sp-api`` SDK）负责。

4. **scope**：写在 ``application/x-www-form-urlencoded`` body，不是 query
   string。

参考文档：
- https://developer-docs.amazon.com/sp-api/docs/authorizing-selling-partner-api-applications
- https://developer-docs.amazon.com/sp-api/docs/registering-your-application

使用示例（pricing radar 注入 token）::

    bundle = await TokenStore.get(org_id=tnt, provider_id="amazon-sp")
    headers = {
        "x-amz-access-token": bundle.access_token,
        "Content-Type": "application/json",
    }
    r = await client.get(SP_API_ENDPOINTS["NA"] + "/products/pricing/v0/...", headers=headers)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from loguru import logger


# ----- Base 类 + 注册装饰器 -----
try:  # pragma: no cover
    from ..base import BaseOAuthProvider, OAuthTokenBundle  # type: ignore
    from ..registry import register_provider  # type: ignore
except ImportError:  # pragma: no cover - 单元测试 / 框架未合入时使用 fallback
    from dataclasses import dataclass, field

    @dataclass
    class OAuthTokenBundle:  # type: ignore[no-redef]
        access_token: str
        refresh_token: Optional[str] = None
        token_type: str = "bearer"
        expires_at: Optional[datetime] = None
        raw: dict[str, Any] = field(default_factory=dict)

    class BaseOAuthProvider:  # type: ignore[no-redef]
        provider_id: str = ""
        default_scopes: list[str] = []

        def __init__(self, **kwargs: Any) -> None:
            self.client_id = kwargs.get("client_id", "")
            self.client_secret = kwargs.get("client_secret", "")
            self.redirect_uri = kwargs.get("redirect_uri", "")
            self.http_client = kwargs.get("http_client")

    def register_provider(cls):  # type: ignore[no-redef]
        return cls


SP_API_ENDPOINTS = {
    "NA": "https://sellingpartnerapi-na.amazon.com",
    "EU": "https://sellingpartnerapi-eu.amazon.com",
    "FE": "https://sellingpartnerapi-fe.amazon.com",
}

SELLER_CENTRAL_URLS = {
    "NA": "https://sellercentral.amazon.com",
    "EU": "https://sellercentral-europe.amazon.com",
    "FE": "https://sellercentral.amazon.co.jp",
}


@register_provider
class AmazonSPOAuthProvider(BaseOAuthProvider):
    """Amazon Selling Partner LWA OAuth Provider。"""

    provider_id = "amazon-sp"
    display_name = "Amazon Selling Partner"
    category = "ecommerce"
    icon_url = "https://m.media-amazon.com/images/G/01/sell/images/sp-api-logo._CB1565913824_.svg"

    # 默认 scope；可被构造时覆盖
    default_scopes: list[str] = [
        # 注意：Amazon SP-API 不在 LWA 请求里传 scope；
        # 商户授权范围由 Amazon Seller Central app 配置决定。
        # 这里保留空表，仅作元数据。
    ]

    LWA_AUTHORIZE_URL = "https://sellercentral.amazon.com/apps/authorize/consent"
    LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"

    DEFAULT_REGION = "NA"

    def __init__(
        self,
        *,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        app_id: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        marketplace_region: str = DEFAULT_REGION,
        **kwargs: Any,
    ) -> None:
        """构造 Amazon SP OAuth provider。

        Args:
            client_id: LWA Client ID（``settings.AMAZON_SP_LWA_CLIENT_ID``）
            client_secret: LWA Client Secret
            redirect_uri: 回调 URL（必须在 Seller Central 白名单）
            app_id: Amazon Application ID（在 LWA 授权 URL 内）
            marketplace_region: ``NA`` / ``EU`` / ``FE``
        """
        settings_id = settings_secret = settings_redirect = settings_app = ""
        try:  # pragma: no cover
            from src.core.config import settings as _settings
            settings_id = getattr(_settings, "AMAZON_SP_LWA_CLIENT_ID", "") or ""
            settings_secret = getattr(_settings, "AMAZON_SP_LWA_CLIENT_SECRET", "") or ""
            settings_redirect = getattr(_settings, "AMAZON_SP_OAUTH_REDIRECT_URI", "") or ""
            settings_app = getattr(_settings, "AMAZON_SP_APP_ID", "") or ""
        except Exception:
            pass

        super().__init__(
            http_client=http_client,
            client_id=client_id or settings_id,
            client_secret=client_secret or settings_secret,
            redirect_uri=redirect_uri or settings_redirect,
            **kwargs,
        )
        self.app_id = app_id or settings_app
        if marketplace_region not in SP_API_ENDPOINTS:
            raise ValueError(f"unsupported marketplace_region: {marketplace_region}")
        self.marketplace_region = marketplace_region

    @property
    def api_endpoint(self) -> str:
        return SP_API_ENDPOINTS[self.marketplace_region]

    # ============ 1. 授权 URL ============
    async def authorize_url(
        self,
        state: str,
        *,
        version: str = "beta",
        scope: Optional[list[str]] = None,
        **_: Any,
    ) -> str:
        """生成 Seller Central 授权同意页 URL。

        卖家点击后跳转到 Amazon 同意页；同意后回调到 ``redirect_uri`` 带 query
        参数 ``spapi_oauth_code`` / ``selling_partner_id`` / ``state``。
        """
        if not self.app_id:
            raise ValueError("AmazonSP authorize_url 需要 app_id（settings.AMAZON_SP_APP_ID）")
        params = {
            "application_id": self.app_id,
            "state": state,
            "redirect_uri": self.redirect_uri,
            "version": version,
        }
        base = SELLER_CENTRAL_URLS.get(self.marketplace_region, SELLER_CENTRAL_URLS["NA"])
        return f"{base}/apps/authorize/consent?{urlencode(params)}"

    # ============ 2. exchange_code ============
    async def exchange_code(
        self,
        code: str,
        state: Optional[str] = None,
        **_: Any,
    ) -> OAuthTokenBundle:
        """用 spapi_oauth_code 换 access_token + refresh_token。"""
        if not self.client_id or not self.client_secret:
            raise ValueError("AmazonSP exchange_code 需要 client_id / client_secret")
        body = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
        }
        return await self._token_request(body)

    # ============ 3. refresh_token ============
    async def refresh_token(self, refresh_token: str, **_: Any) -> OAuthTokenBundle:
        """用 refresh_token 刷新 access_token（1 小时过期，必须刷）。"""
        body = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        bundle = await self._token_request(body)
        if not bundle.refresh_token:
            bundle.refresh_token = refresh_token  # Amazon 续期不返回新 refresh_token
        return bundle

    # ============ 4. get_user_info ============
    async def get_user_info(self, access_token: str, **_: Any) -> dict[str, Any]:
        """SP-API 没有标准 user-info 端点。返回 marketplace 元数据。"""
        return {
            "provider_id": self.provider_id,
            "marketplace_region": self.marketplace_region,
            "api_endpoint": self.api_endpoint,
        }

    # ============ 5. revoke ============
    async def revoke(self, token: str, **_: Any) -> None:
        """LWA 不暴露 revoke 端点；卖家需在 Seller Central 手动解绑。"""
        logger.warning("AmazonSP revoke: LWA token 撤销需卖家手动在 Seller Central 解绑")

    # ============ 内部：token 请求 ============
    async def _token_request(self, body: dict[str, str]) -> OAuthTokenBundle:
        client = self.http_client or httpx.AsyncClient(timeout=15.0)
        try:
            r = await client.post(
                self.LWA_TOKEN_URL,
                data=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "Anxin-AI amazon-sp-oauth/1.0",
                },
            )
            r.raise_for_status()
            data = r.json()
        finally:
            if self.http_client is None:
                await client.aclose()

        expires_at = None
        if data.get("expires_in"):
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(data["expires_in"]))
        return OAuthTokenBundle(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            token_type=data.get("token_type", "bearer"),
            expires_at=expires_at,
            raw={"marketplace_region": self.marketplace_region, **data},
        )


# ────────────────────────────────────────────────────────────────────
# 便利函数：给 pricing radar 等 cookbook 注入 access_token
# ────────────────────────────────────────────────────────────────────
async def get_access_token(
    *,
    org_id: str,
    region: str = "NA",
) -> Optional[str]:
    """从 TokenStore 取出某租户的 amazon-sp access_token；过期自动刷新。

    Returns None 时：表示该租户没绑定 Amazon Seller / token store 没就绪 / 网络异常。
    cookbook / 业务层应按 None 降级（生成 staged draft 但不真调 SP-API）。
    """
    try:
        from src.services.app_authorization.token_store import TokenStore
    except ImportError:
        return None
    try:
        bundle = await TokenStore.instance().get(
            org_id=org_id, provider_id="amazon-sp",
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("amazon-sp token store 不可用：{}", e)
        return None
    if bundle is None:
        return None
    # 过期或临期（< 5 分钟）→ 刷新
    if bundle.expires_at and bundle.expires_at <= datetime.now(timezone.utc) + timedelta(minutes=5):
        if not bundle.refresh_token:
            logger.warning("amazon-sp token 已临期且无 refresh_token → 卖家需重新授权")
            return None
        provider = AmazonSPOAuthProvider(marketplace_region=region)
        try:
            bundle = await provider.refresh_token(bundle.refresh_token)
            await TokenStore.instance().put(
                org_id=org_id, provider_id="amazon-sp", bundle=bundle,
            )
        except (httpx.HTTPError, ValueError) as e:
            logger.warning("amazon-sp token refresh 失败：{}", e)
            return None
    return bundle.access_token


__all__ = [
    "AmazonSPOAuthProvider",
    "SP_API_ENDPOINTS",
    "SELLER_CENTRAL_URLS",
    "get_access_token",
]
