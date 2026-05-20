"""飞书 OAuth Provider 单元测试（P4-B）。

覆盖：
    1. test_authorize_url_format            — URL 拼装正确（含 state/scope/redirect）
    2. test_exchange_code_success           — code → access_token + refresh_token
    3. test_refresh_token_success           — refresh → 新 access_token
    4. test_get_user_info_returns_open_id   — Bearer header + open_id 字段提取
    5. test_token_expired_raises_correct_error — 99991663 → OAuthTokenExpiredError

策略：完全 mock ``httpx.AsyncClient.request``，不发任何真实网络请求。
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qs, urlparse

import pytest

# ---------------------------------------------------------------------------
# 兼容：项目根 conftest 会跑 SQLAlchemy 的 create_all（对 PG JSONB 在 SQLite 下
# 编译会报错）。本测试不需要任何数据表，但导入路径上若触发 settings/models 加载
# 也可能间接导入 PG-only 类型。提前把 JSONB 在 sqlite 方言下渲染成 JSON。
# ---------------------------------------------------------------------------
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(JSONB, "sqlite")  # type: ignore[misc]
def _compile_jsonb_for_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


from src.services.app_authorization.base import (  # noqa: E402
    OAuthError,
    OAuthTokenBundle,
    OAuthTokenExpiredError,
)
from src.services.app_authorization.providers.feishu_oauth import (  # noqa: E402
    AUTHORIZE_URL,
    TOKEN_URL,
    USER_INFO_URL,
    FeishuOAuthProvider,
)


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def _mock_response(json_data: dict[str, Any], status: int = 200) -> MagicMock:
    """构造一个最小可用的 httpx response mock。"""
    resp = MagicMock()
    resp.status_code = status
    resp.json = MagicMock(return_value=json_data)
    resp.raise_for_status = MagicMock()
    return resp


def _make_provider(*, http_client: Any = None) -> FeishuOAuthProvider:
    return FeishuOAuthProvider(
        app_id="cli_test_app_id",
        app_secret="test_secret",
        http_client=http_client,
    )


# ===========================================================================
# 1. authorize_url
# ===========================================================================
@pytest.mark.asyncio
async def test_authorize_url_format() -> None:
    """生成的 URL 包含 app_id / state / redirect_uri / scope，且指向飞书授权页。"""
    provider = _make_provider()
    url = await provider.authorize_url(
        state="csrf_state_xyz",
        redirect_uri="https://anxin.example.com/oauth/feishu/callback",
        scopes=["contact:user.id:readonly", "calendar:calendar"],
    )

    parsed = urlparse(url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "open.feishu.cn"
    assert url.startswith(AUTHORIZE_URL + "?")

    qs = parse_qs(parsed.query)
    assert qs["app_id"] == ["cli_test_app_id"]
    assert qs["state"] == ["csrf_state_xyz"]
    assert qs["redirect_uri"] == ["https://anxin.example.com/oauth/feishu/callback"]
    # scope 用逗号拼接
    assert qs["scope"] == ["contact:user.id:readonly,calendar:calendar"]
    assert qs["response_type"] == ["code"]


@pytest.mark.asyncio
async def test_authorize_url_uses_default_scopes_when_not_provided() -> None:
    """不传 scopes 时使用 default_scopes（包含 3 个智能体核心 scope）。"""
    provider = _make_provider()
    url = await provider.authorize_url(
        state="s",
        redirect_uri="https://x/cb",
    )
    qs = parse_qs(urlparse(url).query)
    scope_csv = qs["scope"][0]
    assert "contact:user.id:readonly" in scope_csv
    assert "calendar:calendar" in scope_csv
    assert "drive:drive" in scope_csv


# ===========================================================================
# 2. exchange_code
# ===========================================================================
@pytest.mark.asyncio
async def test_exchange_code_success() -> None:
    """正常 code 换 token：返回完整 OAuthTokenBundle。"""
    fake_response = _mock_response(
        {
            "code": 0,
            "msg": "success",
            "access_token": "u-feishu-access-001",
            "refresh_token": "u-feishu-refresh-001",
            "expires_in": 7200,
            "scope": "contact:user.id:readonly calendar:calendar",
            "token_type": "Bearer",
        }
    )

    http_client = MagicMock()
    http_client.request = AsyncMock(return_value=fake_response)
    provider = _make_provider(http_client=http_client)

    bundle = await provider.exchange_code(
        code="auth_code_xxx",
        redirect_uri="https://anxin.example.com/oauth/feishu/callback",
    )

    assert isinstance(bundle, OAuthTokenBundle)
    assert bundle.access_token == "u-feishu-access-001"
    assert bundle.refresh_token == "u-feishu-refresh-001"
    assert bundle.expires_in == 7200
    assert bundle.token_type == "Bearer"
    assert "contact:user.id:readonly" in (bundle.scope or "")

    # 校验调用参数
    http_client.request.assert_awaited_once()
    args, kwargs = http_client.request.call_args
    assert args[0] == "POST"
    assert args[1] == TOKEN_URL
    body = kwargs["json"]
    assert body["grant_type"] == "authorization_code"
    assert body["code"] == "auth_code_xxx"
    assert body["client_id"] == "cli_test_app_id"
    assert body["client_secret"] == "test_secret"
    assert body["redirect_uri"].endswith("/oauth/feishu/callback")


@pytest.mark.asyncio
async def test_exchange_code_business_error_raises_oauth_error() -> None:
    """飞书业务非 0 错误（非 token_expired）应抛 OAuthError。"""
    fake_response = _mock_response({"code": 20002, "msg": "code expired"})
    http_client = MagicMock()
    http_client.request = AsyncMock(return_value=fake_response)
    provider = _make_provider(http_client=http_client)

    with pytest.raises(OAuthError) as exc:
        await provider.exchange_code(code="bad", redirect_uri="https://x/cb")
    assert "20002" in str(exc.value)


# ===========================================================================
# 3. refresh_token
# ===========================================================================
@pytest.mark.asyncio
async def test_refresh_token_success() -> None:
    """refresh_token 调用同一接口、grant_type=refresh_token。"""
    fake_response = _mock_response(
        {
            "code": 0,
            "msg": "success",
            "access_token": "u-feishu-access-002",
            "refresh_token": "u-feishu-refresh-002",
            "expires_in": 7200,
            "scope": "contact:user.id:readonly",
            "token_type": "Bearer",
        }
    )
    http_client = MagicMock()
    http_client.request = AsyncMock(return_value=fake_response)
    provider = _make_provider(http_client=http_client)

    bundle = await provider.refresh_token(refresh_token="old-refresh-token")

    assert bundle.access_token == "u-feishu-access-002"
    assert bundle.refresh_token == "u-feishu-refresh-002"

    args, kwargs = http_client.request.call_args
    assert args[1] == TOKEN_URL
    body = kwargs["json"]
    assert body["grant_type"] == "refresh_token"
    assert body["refresh_token"] == "old-refresh-token"
    assert body["client_id"] == "cli_test_app_id"


# ===========================================================================
# 4. get_user_info
# ===========================================================================
@pytest.mark.asyncio
async def test_get_user_info_returns_open_id() -> None:
    """get_user_info 通过 Bearer header 调用，返回包含 open_id 的 dict。"""
    fake_response = _mock_response(
        {
            "code": 0,
            "msg": "success",
            "data": {
                "name": "张三",
                "en_name": "Zhang San",
                "avatar_url": "https://avatar.example.com/zs.png",
                "email": "zhangsan@example.com",
                "open_id": "ou_test_open_id_123",
                "union_id": "on_test_union_id_456",
                "user_id": "user_xxx",
                "tenant_key": "tenant_xxx",
            },
        }
    )
    http_client = MagicMock()
    http_client.request = AsyncMock(return_value=fake_response)
    provider = _make_provider(http_client=http_client)

    info = await provider.get_user_info(access_token="u-feishu-access-001")
    assert info["open_id"] == "ou_test_open_id_123"
    assert info["union_id"] == "on_test_union_id_456"
    assert info["name"] == "张三"

    args, kwargs = http_client.request.call_args
    assert args[0] == "GET"
    assert args[1] == USER_INFO_URL
    headers = kwargs["headers"]
    assert headers["Authorization"] == "Bearer u-feishu-access-001"


@pytest.mark.asyncio
async def test_get_user_info_rejects_empty_token() -> None:
    """空 access_token 应直接拒绝，不发起请求。"""
    provider = _make_provider()
    with pytest.raises(OAuthError):
        await provider.get_user_info(access_token="")


# ===========================================================================
# 5. token_expired
# ===========================================================================
@pytest.mark.asyncio
@pytest.mark.parametrize("err_code", [99991663, 99991664])
async def test_token_expired_raises_correct_error(err_code: int) -> None:
    """飞书错误码 99991663/99991664 → OAuthTokenExpiredError。"""
    fake_response = _mock_response({"code": err_code, "msg": "access token expired"})
    http_client = MagicMock()
    http_client.request = AsyncMock(return_value=fake_response)
    provider = _make_provider(http_client=http_client)

    with pytest.raises(OAuthTokenExpiredError) as exc:
        await provider.get_user_info(access_token="any-token")

    assert exc.value.code == err_code
    assert exc.value.provider == "feishu"


# ===========================================================================
# 6. revoke 是 no-op（仅满足契约）
# ===========================================================================
@pytest.mark.asyncio
async def test_revoke_is_noop() -> None:
    """飞书没有 revoke API；本方法应静默成功，由上层 token_store 删除。"""
    provider = _make_provider()
    result = await provider.revoke(access_token="any")
    assert result is None
