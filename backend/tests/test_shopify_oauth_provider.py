# -*- coding: utf-8 -*-
"""Shopify OAuth Provider 单元测试（P4-E）。

覆盖 7 个用例：

    1. test_authorize_url_requires_shop                — 缺 shop 抛 ValueError
    2. test_authorize_url_format_per_shop              — URL 含 {shop} 域名+逗号 scope
    3. test_exchange_code_persists_shop_in_raw         — bundle.raw["shop"] 持久化
    4. test_hmac_verification_correct_secret           — 合法 HMAC 通过
    5. test_hmac_verification_tampered_query_rejected  — 篡改 query 被拒
    6. test_revoke_uses_x_shopify_access_token_header  — 必须用 X-Shopify-Access-Token
    7. test_get_user_info_returns_shop_meta            — 返回 shop 元数据
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qs, urlparse

import pytest

# ---------------------------------------------------------------------------
# 兼容性：项目根 conftest.py 会触发 SQLAlchemy 在 SQLite 下编译 JSONB，
# 这里提前注册编译钩子（与其他 P4 provider 测试同款），避免无关报错。
# ---------------------------------------------------------------------------
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(JSONB, "sqlite")  # type: ignore[misc]
def _compile_jsonb_for_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


from src.services.app_authorization.providers.shopify_oauth import (  # noqa: E402
    OAuthTokenBundle,
    ShopifyOAuthProvider,
)


# ---------------------------------------------------------------------------
# 工具：构造 provider + mock httpx response
# ---------------------------------------------------------------------------
def _make_provider(http_client: Any = None) -> ShopifyOAuthProvider:
    return ShopifyOAuthProvider(
        client_id="shopify_api_key_test",
        client_secret="shopify_api_secret_test",
        redirect_uri="https://anxin.example/oauth/callback/shopify",
        http_client=http_client,
    )


def _mock_http_response(json_data: dict[str, Any], status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json = MagicMock(return_value=json_data)
    return resp


def _build_signed_query(
    query_params: dict[str, str],
    secret: str,
) -> dict[str, str]:
    """复刻 Shopify 的 HMAC 计算逻辑，给受测代码生成合法回调 query。"""
    message = "&".join(f"{k}={query_params[k]}" for k in sorted(query_params))
    digest = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    out = dict(query_params)
    out["hmac"] = digest
    return out


# ===========================================================================
# 1. authorize_url 缺 shop 抛错
# ===========================================================================
@pytest.mark.asyncio
async def test_authorize_url_requires_shop() -> None:
    """Shopify 是多租户：必须传 shop=，否则不知道往哪个商家域名跳。"""
    provider = _make_provider()
    with pytest.raises(ValueError) as exc:
        await provider.authorize_url(state="state-abc")
    assert "shop" in str(exc.value).lower()


# ===========================================================================
# 2. authorize_url 格式（多租户域名 + 逗号 scope）
# ===========================================================================
@pytest.mark.asyncio
async def test_authorize_url_format_per_shop() -> None:
    """authorize_url 应：
    - 指向 ``https://{shop}/admin/oauth/authorize``（每个商家独立域名）
    - 带 client_id / redirect_uri / state
    - scope 用**逗号**分隔（Shopify 规范，不是空格）
    - 默认带 grant_options[]=per-user
    """
    provider = _make_provider()
    url = await provider.authorize_url(
        state="state-xyz",
        shop="acme.myshopify.com",
    )

    parsed = urlparse(url)
    assert parsed.scheme == "https"
    # 关键 — netloc 是商家自己的域名
    assert parsed.netloc == "acme.myshopify.com"
    assert parsed.path == "/admin/oauth/authorize"

    qs = parse_qs(parsed.query)
    assert qs["client_id"] == ["shopify_api_key_test"]
    assert qs["redirect_uri"] == [
        "https://anxin.example/oauth/callback/shopify"
    ]
    assert qs["state"] == ["state-xyz"]
    assert qs["grant_options[]"] == ["per-user"]
    # scope 逗号分隔，5 项默认
    assert qs["scope"] == [
        "read_products,write_products,read_orders,write_orders,read_customers"
    ]

    # 兼容传入 https:// 前缀
    url2 = await provider.authorize_url(
        state="s2",
        shop="https://other.myshopify.com/",
    )
    assert urlparse(url2).netloc == "other.myshopify.com"

    # Provider 元数据
    assert ShopifyOAuthProvider.provider_id == "shopify"
    assert ShopifyOAuthProvider.display_name == "Shopify"
    assert ShopifyOAuthProvider.category == "ecommerce"
    assert ShopifyOAuthProvider.icon_url.startswith("https://cdn.shopify.com")


# ===========================================================================
# 3. exchange_code 把 shop 写入 bundle.raw（多租户关键）
# ===========================================================================
@pytest.mark.asyncio
async def test_exchange_code_persists_shop_in_raw() -> None:
    """exchange_code 应：
    - POST 到 ``https://{shop}/admin/oauth/access_token``
    - body 含 client_id / client_secret / code（无 grant_type，Shopify 不要求）
    - 把 ``shop`` 写入 ``bundle.raw["shop"]`` — 这样 token store 落库时就能保留，
      后续 revoke / get_user_info 才知道往哪个商家域名调
    - offline 模式：bundle.refresh_token 必须为 None
    """
    captured: dict[str, Any] = {}

    async def fake_post(url: str, json: dict[str, Any]) -> MagicMock:  # noqa: A002
        captured["url"] = url
        captured["body"] = json
        # offline 模式典型响应：只有 access_token + scope
        return _mock_http_response(
            {
                "access_token": "shpat_offline_001",
                "scope": "read_products,write_orders",
            }
        )

    http = MagicMock()
    http.post = AsyncMock(side_effect=fake_post)

    provider = _make_provider(http_client=http)
    bundle = await provider.exchange_code(
        "auth_code_abc",
        shop="acme.myshopify.com",
    )

    assert isinstance(bundle, OAuthTokenBundle)
    assert bundle.access_token == "shpat_offline_001"
    assert bundle.refresh_token is None  # offline 永不过期、无 RT
    assert bundle.expires_at is None     # offline 无 expires_in
    assert bundle.scope == "read_products,write_orders"
    assert bundle.token_type == "Bearer"

    # 关键断言 — shop 必须落到 raw 里
    assert bundle.raw["shop"] == "acme.myshopify.com"
    # 原始响应字段也保留
    assert bundle.raw["access_token"] == "shpat_offline_001"

    # URL & body 校验
    assert captured["url"] == (
        "https://acme.myshopify.com/admin/oauth/access_token"
    )
    assert captured["body"] == {
        "client_id": "shopify_api_key_test",
        "client_secret": "shopify_api_secret_test",
        "code": "auth_code_abc",
    }

    # 缺 shop 同样应抛错
    with pytest.raises(ValueError):
        await provider.exchange_code("any", shop=None)


# ===========================================================================
# 4. HMAC 验证 — 合法签名通过
# ===========================================================================
def test_hmac_verification_correct_secret() -> None:
    """用正确 secret 签出来的 query 应通过验证。"""
    secret = "shopify_api_secret_test"
    raw_query = {
        "code": "auth_code_xyz",
        "shop": "acme.myshopify.com",
        "state": "state-1",
        "timestamp": "1714000000",
    }
    signed = _build_signed_query(raw_query, secret)

    assert ShopifyOAuthProvider.verify_callback_hmac(signed, secret) is True

    # legacy ``signature`` 字段应被跳过、不影响校验
    signed_with_signature = dict(signed)
    signed_with_signature["signature"] = "legacy-noise"
    assert (
        ShopifyOAuthProvider.verify_callback_hmac(
            signed_with_signature, secret
        )
        is True
    )


# ===========================================================================
# 5. HMAC 验证 — 篡改 query 应被拒
# ===========================================================================
def test_hmac_verification_tampered_query_rejected() -> None:
    """改了任意一个字段，HMAC 不再匹配 → 必须 False。"""
    secret = "shopify_api_secret_test"
    raw_query = {
        "code": "auth_code_xyz",
        "shop": "acme.myshopify.com",
        "state": "state-1",
        "timestamp": "1714000000",
    }
    signed = _build_signed_query(raw_query, secret)

    # ① 篡改 shop（攻击者把回调指向自己的店）
    tampered = dict(signed)
    tampered["shop"] = "evil.myshopify.com"
    assert ShopifyOAuthProvider.verify_callback_hmac(tampered, secret) is False

    # ② 篡改 code
    tampered2 = dict(signed)
    tampered2["code"] = "stolen_code"
    assert (
        ShopifyOAuthProvider.verify_callback_hmac(tampered2, secret) is False
    )

    # ③ 用错 secret（密钥泄漏后被 rotate 的场景）
    assert (
        ShopifyOAuthProvider.verify_callback_hmac(signed, "wrong_secret")
        is False
    )

    # ④ 缺 hmac 字段
    no_hmac = {k: v for k, v in signed.items() if k != "hmac"}
    assert ShopifyOAuthProvider.verify_callback_hmac(no_hmac, secret) is False

    # ⑤ 空 dict
    assert ShopifyOAuthProvider.verify_callback_hmac({}, secret) is False


# ===========================================================================
# 6. revoke 必须使用 X-Shopify-Access-Token 头
# ===========================================================================
@pytest.mark.asyncio
async def test_revoke_uses_x_shopify_access_token_header() -> None:
    """revoke 应：
    - DELETE ``https://{shop}/admin/api/2024-10/oauth/revoke.json``
    - **必须**用自定义头 ``X-Shopify-Access-Token``，不是 Authorization: Bearer
    - 缺 shop 抛 ValueError
    """
    captured: dict[str, Any] = {}

    async def fake_delete(
        url: str,
        headers: dict[str, str] | None = None,
    ) -> MagicMock:
        captured["url"] = url
        captured["headers"] = headers or {}
        # Shopify revoke 成功通常 200 + 空 body
        return _mock_http_response({})

    http = MagicMock()
    http.delete = AsyncMock(side_effect=fake_delete)

    provider = _make_provider(http_client=http)
    result = await provider.revoke(
        "shpat_offline_001",
        shop="acme.myshopify.com",
    )
    assert result is None

    assert captured["url"] == (
        "https://acme.myshopify.com/admin/api/2024-10/oauth/revoke.json"
    )
    # 关键断言 — Shopify 自定义鉴权头
    assert captured["headers"].get("X-Shopify-Access-Token") == (
        "shpat_offline_001"
    )
    # 反向断言 — 不应有 Authorization: Bearer
    assert "Authorization" not in captured["headers"]

    # 缺 shop 抛错
    with pytest.raises(ValueError):
        await provider.revoke("token", shop=None)

    # refresh_token 显式不支持
    with pytest.raises(NotImplementedError) as exc:
        await provider.refresh_token("any-token")
    assert "re-auth" in str(exc.value).lower()


# ===========================================================================
# 7. get_user_info 返回 shop 元数据
# ===========================================================================
@pytest.mark.asyncio
async def test_get_user_info_returns_shop_meta() -> None:
    """get_user_info 应：
    - GET ``shop.json`` 返回店铺档案（name / email / country / timezone / currency）
    - 用 X-Shopify-Access-Token 鉴权
    - 路径里带正确 api_version
    """
    captured: dict[str, Any] = {}

    async def fake_get(
        url: str,
        headers: dict[str, str] | None = None,
    ) -> MagicMock:
        captured["url"] = url
        captured["headers"] = headers or {}
        return _mock_http_response(
            {
                "shop": {
                    "id": 1234567890,
                    "name": "Acme Goods",
                    "email": "owner@acme.example",
                    "country": "US",
                    "country_name": "United States",
                    "iana_timezone": "America/New_York",
                    "currency": "USD",
                    "domain": "acme.myshopify.com",
                    "myshopify_domain": "acme.myshopify.com",
                }
            }
        )

    http = MagicMock()
    http.get = AsyncMock(side_effect=fake_get)

    provider = _make_provider(http_client=http)
    info = await provider.get_user_info(
        "shpat_offline_001",
        shop="acme.myshopify.com",
    )

    # 返回结构包含 shop 元数据五要素
    shop_meta = info["shop"]
    assert shop_meta["name"] == "Acme Goods"
    assert shop_meta["email"] == "owner@acme.example"
    assert shop_meta["country_name"] == "United States"
    assert shop_meta["iana_timezone"] == "America/New_York"
    assert shop_meta["currency"] == "USD"

    # URL 含 api_version；鉴权头正确
    assert captured["url"] == (
        "https://acme.myshopify.com/admin/api/2024-10/shop.json"
    )
    assert captured["headers"].get("X-Shopify-Access-Token") == (
        "shpat_offline_001"
    )
    assert "Authorization" not in captured["headers"]

    # 缺 shop 抛错
    with pytest.raises(ValueError):
        await provider.get_user_info("token", shop=None)
