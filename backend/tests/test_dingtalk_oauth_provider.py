"""钉钉 OAuth Provider 单元测试（P4-C）。

覆盖 5 个用例：

    1. test_authorize_url_format         — URL 拼接、scope 空格分隔、prompt=consent
    2. test_exchange_code_success        — code → token 调用 ``userAccessToken``
    3. test_refresh_token_success        — grantType=refresh_token，沿用旧 RT
    4. test_user_info_uses_x_acs_header  — 必须用 ``x-acs-dingtalk-access-token``
    5. test_revoke_only_marks_local      — revoke 不发 HTTP，仅本地标记
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qs, urlparse

import pytest

# ---------------------------------------------------------------------------
# 兼容性：项目根 conftest.py 会触发 SQLAlchemy 在 SQLite 下编译 JSONB，
# 这里提前注册编译钩子（与 test_feishu_adapter.py 同款），避免无关报错。
# ---------------------------------------------------------------------------
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(JSONB, "sqlite")  # type: ignore[misc]
def _compile_jsonb_for_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


from src.services.app_authorization.providers.dingtalk_oauth import (  # noqa: E402
    DingTalkOAuthProvider,
    OAuthTokenBundle,
)


# ---------------------------------------------------------------------------
# 工具：构造一个测试用 provider（注入 mock httpx client）
# ---------------------------------------------------------------------------
def _make_provider(http_client: Any = None) -> DingTalkOAuthProvider:
    return DingTalkOAuthProvider(
        client_id="dingtest_app_key",
        client_secret="dingtest_app_secret",
        redirect_uri="https://anxin.example/oauth/callback/dingtalk",
        http_client=http_client,
    )


def _mock_http_response(json_data: dict[str, Any], status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json = MagicMock(return_value=json_data)
    return resp


# ===========================================================================
# 1. 授权 URL 格式
# ===========================================================================
@pytest.mark.asyncio
async def test_authorize_url_format() -> None:
    """authorize_url 应：
    - 指向 ``https://login.dingtalk.com/oauth2/auth``
    - 带 client_id / redirect_uri / response_type=code / state
    - scope 用**空格**分隔（钉钉规范，不是逗号）
    - 强制 prompt=consent，每次都让用户确认授权
    """
    provider = _make_provider()
    url = await provider.authorize_url(state="state-xyz")

    parsed = urlparse(url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "login.dingtalk.com"
    assert parsed.path == "/oauth2/auth"

    qs = parse_qs(parsed.query)
    assert qs["client_id"] == ["dingtest_app_key"]
    assert qs["redirect_uri"] == ["https://anxin.example/oauth/callback/dingtalk"]
    assert qs["response_type"] == ["code"]
    assert qs["state"] == ["state-xyz"]
    assert qs["prompt"] == ["consent"]
    # 默认 scope 三项，空格分隔
    assert qs["scope"] == ["openid Contact.User.Read Calendar.Read"]

    # Provider 元数据
    assert DingTalkOAuthProvider.provider_id == "dingtalk"
    assert DingTalkOAuthProvider.display_name == "钉钉"
    assert DingTalkOAuthProvider.category == "office"
    assert DingTalkOAuthProvider.icon_url.startswith("https://")


# ===========================================================================
# 2. exchange_code 成功路径
# ===========================================================================
@pytest.mark.asyncio
async def test_exchange_code_success() -> None:
    """exchange_code 应：
    - POST 到 ``api.dingtalk.com/v1.0/oauth2/userAccessToken``
    - body 用驼峰：clientId / clientSecret / code / grantType="authorization_code"
    - 返回 ``OAuthTokenBundle``，accessToken / refreshToken 正确解析
    - expires_at 含时区，约等于 now+expireIn-60s
    """
    captured: dict[str, Any] = {}

    async def fake_post(url: str, json: dict[str, Any]) -> MagicMock:  # noqa: A002
        captured["url"] = url
        captured["body"] = json
        return _mock_http_response(
            {
                "accessToken": "ding-access-001",
                "refreshToken": "ding-refresh-001",
                "expireIn": 7200,
                "corpId": "ding-corp-id",
            }
        )

    http = MagicMock()
    http.post = AsyncMock(side_effect=fake_post)

    provider = _make_provider(http_client=http)
    bundle = await provider.exchange_code("auth_code_abc")

    assert isinstance(bundle, OAuthTokenBundle)
    assert bundle.access_token == "ding-access-001"
    assert bundle.refresh_token == "ding-refresh-001"
    assert bundle.token_type == "Bearer"
    assert bundle.raw["corpId"] == "ding-corp-id"

    # expires_at 时区 + 时长校验
    assert bundle.expires_at is not None
    assert bundle.expires_at.tzinfo is not None
    delta = (bundle.expires_at - datetime.now(UTC)).total_seconds()
    # 7200 - 60 = 7140，留 5s 容差应付测试运行抖动
    assert 7100 <= delta <= 7150, f"expires_at delta out of range: {delta}"

    # URL & body 校验
    assert captured["url"] == ("https://api.dingtalk.com/v1.0/oauth2/userAccessToken")
    assert captured["body"] == {
        "clientId": "dingtest_app_key",
        "clientSecret": "dingtest_app_secret",
        "code": "auth_code_abc",
        "grantType": "authorization_code",
    }


# ===========================================================================
# 3. refresh_token 成功路径
# ===========================================================================
@pytest.mark.asyncio
async def test_refresh_token_success() -> None:
    """refresh_token 应：
    - 同样 POST 到 ``userAccessToken``
    - body 含 ``refreshToken`` + ``grantType=refresh_token``
    - 钉钉若不返回新 RT，沿用旧 RT
    """
    captured: dict[str, Any] = {}

    async def fake_post(url: str, json: dict[str, Any]) -> MagicMock:  # noqa: A002
        captured["url"] = url
        captured["body"] = json
        # 模拟钉钉只返新 access token、不返新 refresh token 的情况
        return _mock_http_response(
            {
                "accessToken": "ding-access-002",
                "expireIn": 3600,
            }
        )

    http = MagicMock()
    http.post = AsyncMock(side_effect=fake_post)

    provider = _make_provider(http_client=http)
    bundle = await provider.refresh_token("old-refresh-token")

    assert bundle.access_token == "ding-access-002"
    # 没返回新 RT → 沿用旧的，避免下次刷新没有凭据
    assert bundle.refresh_token == "old-refresh-token"

    assert captured["body"] == {
        "clientId": "dingtest_app_key",
        "clientSecret": "dingtest_app_secret",
        "refreshToken": "old-refresh-token",
        "grantType": "refresh_token",
    }
    assert captured["url"] == ("https://api.dingtalk.com/v1.0/oauth2/userAccessToken")


# ===========================================================================
# 4. get_user_info 必须使用 x-acs-dingtalk-access-token 头
# ===========================================================================
@pytest.mark.asyncio
async def test_user_info_uses_x_acs_header() -> None:
    """get_user_info 应：
    - GET ``contact/users/me``
    - **必须**使用钉钉自定义头 ``x-acs-dingtalk-access-token``
    - **不**使用 OAuth 标准 ``Authorization: Bearer``
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
                "nick": "张三",
                "unionId": "union-abc",
                "openId": "open-123",
                "mobile": "13800138000",
            }
        )

    http = MagicMock()
    http.get = AsyncMock(side_effect=fake_get)

    provider = _make_provider(http_client=http)
    user = await provider.get_user_info("ding-access-001")

    assert user["nick"] == "张三"
    assert user["unionId"] == "union-abc"

    assert captured["url"] == ("https://api.dingtalk.com/v1.0/contact/users/me")
    # 关键断言 — 钉钉特殊鉴权头
    assert captured["headers"].get("x-acs-dingtalk-access-token") == ("ding-access-001")
    # 反向断言 — 不应有 Authorization: Bearer
    assert "Authorization" not in captured["headers"]


# ===========================================================================
# 5. revoke 仅本地标记（钉钉无远端撤销接口）
# ===========================================================================
@pytest.mark.asyncio
async def test_revoke_only_marks_local() -> None:
    """revoke 不应发出任何 HTTP 请求，由上层把绑定标记为 revoked 即可。"""
    http = MagicMock()
    http.post = AsyncMock(side_effect=AssertionError("revoke 不应触发 HTTP"))
    http.get = AsyncMock(side_effect=AssertionError("revoke 不应触发 HTTP"))
    http.request = AsyncMock(side_effect=AssertionError("revoke 不应触发 HTTP"))

    provider = _make_provider(http_client=http)
    result = await provider.revoke("ding-access-001")

    assert result is None
    http.post.assert_not_awaited()
    http.get.assert_not_awaited()
    http.request.assert_not_awaited()
