# -*- coding: utf-8 -*-
"""Notion OAuth Provider 单测 (P4-D)。

覆盖 5 个核心断言：

    1. authorize_url_format            — URL 拼装正确（必含字段、不含 scope）
    2. exchange_code_returns_workspace_meta
                                       — workspace 元信息全部进 OAuthTokenBundle.raw
    3. refresh_raises_not_implemented  — Notion 不支持 refresh，必须显式抛错
    4. revoke_uses_basic_auth          — DELETE /v1/oauth/revoke 头部 Basic Auth
    5. user_info_includes_notion_version_header
                                       — /v1/users/me 必带 Notion-Version 头

测试通过 ``httpx.MockTransport`` 拦截真实出网请求，CI 内零外部依赖。
"""

from __future__ import annotations

import base64
import json
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from src.services.app_authorization.providers.notion_oauth import (
    AUTHORIZE_URL,
    NOTION_VERSION,
    REVOKE_URL,
    TOKEN_URL,
    USER_INFO_URL,
    NotionOAuthProvider,
)


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# 测试夹具
# ---------------------------------------------------------------------------
TEST_CLIENT_ID = "test-notion-client-id"
TEST_CLIENT_SECRET = "test-notion-client-secret"
EXPECTED_BASIC_AUTH = "Basic " + base64.b64encode(
    f"{TEST_CLIENT_ID}:{TEST_CLIENT_SECRET}".encode("utf-8")
).decode("ascii")


def _make_provider(
    *, transport: httpx.MockTransport
) -> NotionOAuthProvider:
    """构造一个注入 MockTransport 的 provider，避免真出网。"""
    client = httpx.AsyncClient(transport=transport)
    return NotionOAuthProvider(
        client_id=TEST_CLIENT_ID,
        client_secret=TEST_CLIENT_SECRET,
        http_client=client,
    )


# ---------------------------------------------------------------------------
# 1. authorize_url 格式
# ---------------------------------------------------------------------------
async def test_authorize_url_format() -> None:
    """authorize_url 必须满足 Notion 文档要求且不携带 scope。"""
    provider = NotionOAuthProvider(
        client_id=TEST_CLIENT_ID,
        client_secret=TEST_CLIENT_SECRET,
    )
    url = await provider.authorize_url(
        state="csrf-xyz",
        redirect_uri="https://app.example.com/oauth/notion/callback",
        scopes=["should-be-ignored"],  # Notion 应忽略 scope
    )

    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    assert base == AUTHORIZE_URL, f"授权 URL 基址不对: {base}"

    qs = parse_qs(parsed.query)
    assert qs["client_id"] == [TEST_CLIENT_ID]
    assert qs["response_type"] == ["code"]
    assert qs["owner"] == ["user"]
    assert qs["state"] == ["csrf-xyz"]
    assert qs["redirect_uri"] == ["https://app.example.com/oauth/notion/callback"]
    # Notion 不使用 scope，必须不出现该参数
    assert "scope" not in qs, "Notion 授权 URL 不应携带 scope"


# ---------------------------------------------------------------------------
# 2. exchange_code 返回 workspace 元信息
# ---------------------------------------------------------------------------
async def test_exchange_code_returns_workspace_meta() -> None:
    """exchange_code 应把 workspace_* / bot_id / owner 全部塞入 bundle.raw。"""
    captured: dict[str, Any] = {}

    notion_response = {
        "access_token": "secret_xxx",
        "bot_id": "bot-123",
        "workspace_name": "Acme Co",
        "workspace_icon": "https://www.notion.so/images/acme.png",
        "workspace_id": "ws-456",
        "owner": {"type": "user", "user": {"id": "user-789"}},
        "duplicated_template_id": None,
        "token_type": "bearer",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json=notion_response)

    provider = _make_provider(transport=httpx.MockTransport(handler))
    bundle = await provider.exchange_code(
        code="auth-code-abc",
        redirect_uri="https://app.example.com/oauth/notion/callback",
    )

    # —— 接口请求面 ——
    assert captured["method"] == "POST"
    assert captured["url"] == TOKEN_URL
    assert captured["headers"]["authorization"] == EXPECTED_BASIC_AUTH
    assert captured["headers"]["notion-version"] == NOTION_VERSION
    assert captured["body"] == {
        "grant_type": "authorization_code",
        "code": "auth-code-abc",
        "redirect_uri": "https://app.example.com/oauth/notion/callback",
    }
    # client_secret 绝不应出现在 body 里（必须走 Basic Auth）
    assert "client_secret" not in captured["body"]

    # —— 返回 bundle ——
    assert bundle.access_token == "secret_xxx"
    assert bundle.refresh_token is None       # Notion 不返回 refresh
    assert bundle.expires_in is None          # access_token 永久有效
    assert bundle.scope is None               # Notion 不用 scope
    # workspace 元信息全部留在 raw
    assert bundle.raw["workspace_name"] == "Acme Co"
    assert bundle.raw["workspace_id"] == "ws-456"
    assert bundle.raw["bot_id"] == "bot-123"
    assert bundle.raw["owner"]["user"]["id"] == "user-789"


# ---------------------------------------------------------------------------
# 3. refresh_token 必须显式不支持
# ---------------------------------------------------------------------------
async def test_refresh_raises_not_implemented() -> None:
    """Notion 不支持 refresh_token，调用必须抛 NotImplementedError。"""
    provider = NotionOAuthProvider(
        client_id=TEST_CLIENT_ID,
        client_secret=TEST_CLIENT_SECRET,
    )
    with pytest.raises(NotImplementedError) as exc_info:
        await provider.refresh_token("anything")
    assert "never expires" in str(exc_info.value).lower() or "notion" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# 4. revoke 使用 Basic Auth + DELETE
# ---------------------------------------------------------------------------
async def test_revoke_uses_basic_auth() -> None:
    """revoke 必须走 DELETE /v1/oauth/revoke + Basic Auth + body.token。"""
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={})

    provider = _make_provider(transport=httpx.MockTransport(handler))
    result = await provider.revoke("secret_to_revoke")

    assert result is None
    assert captured["method"] == "DELETE"
    assert captured["url"] == REVOKE_URL
    # 关键断言：Basic Auth（不是 Bearer）
    assert captured["headers"]["authorization"] == EXPECTED_BASIC_AUTH
    assert captured["headers"]["authorization"].startswith("Basic ")
    assert captured["headers"]["notion-version"] == NOTION_VERSION
    assert captured["body"] == {"token": "secret_to_revoke"}


# ---------------------------------------------------------------------------
# 5. get_user_info 必带 Notion-Version 头
# ---------------------------------------------------------------------------
async def test_user_info_includes_notion_version_header() -> None:
    """/v1/users/me 必须使用 Bearer token + Notion-Version: 2022-06-28。"""
    captured: dict[str, Any] = {}

    bot_user = {
        "object": "user",
        "id": "bot-user-001",
        "type": "bot",
        "bot": {
            "owner": {"type": "user", "user": {"id": "real-user-9"}},
            "workspace_name": "Acme Co",
        },
        "name": "My Integration",
        "avatar_url": None,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json=bot_user)

    provider = _make_provider(transport=httpx.MockTransport(handler))
    info = await provider.get_user_info("user-access-token")

    assert captured["method"] == "GET"
    assert captured["url"] == USER_INFO_URL
    # 关键断言：Bearer + Notion-Version
    assert captured["headers"]["authorization"] == "Bearer user-access-token"
    assert captured["headers"]["notion-version"] == NOTION_VERSION
    # 不应误用 Basic Auth
    assert not captured["headers"]["authorization"].startswith("Basic ")

    # 返回结构透传
    assert info["id"] == "bot-user-001"
    assert info["bot"]["workspace_name"] == "Acme Co"
