"""
app_authorizations 路由 API 测试（P4-A）

mock 一个 _StubProvider，覆盖 6 个 endpoint 的关键路径：
    - GET    /providers
    - GET    /
    - POST   /{provider_id}/start
    - GET    /{provider_id}/callback
    - POST   /{id}/refresh
    - DELETE /{id}
"""

from __future__ import annotations

# SQLite ↔ JSONB 兼容补丁（必须在 import models 前生效）
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler as _SQLiteTC

if not hasattr(_SQLiteTC, "visit_JSONB"):

    def _visit_JSONB(self, type_, **kw):  # noqa: N802
        return self.visit_JSON(type_, **kw)

    _SQLiteTC.visit_JSONB = _visit_JSONB  # type: ignore[attr-defined]


from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet
from httpx import AsyncClient

from src.services.app_authorization import (
    BaseOAuthProvider,
    OAuthProviderRegistry,
    OAuthTokenBundle,
)

# 触发 ORM 注册（conftest setup_test_db 会 create_all）
from src.services.app_authorization.models import (  # noqa: F401
    AppAuthorization,
    AppToken,
)

# ---------------------------------------------------------------------------
# Stub provider + Fixtures
# ---------------------------------------------------------------------------


class _StubAPIProvider(BaseOAuthProvider):
    provider_id = "stub_api"
    display_name = "Stub API Provider"
    category = "office"
    icon_url = "https://example.com/icon.png"
    default_scopes = ["read"]

    def __init__(self, **kwargs):
        # 视为"已配置"：注入非空凭据，避免触发 OAuthConfigError fail-fast。
        kwargs.setdefault("client_id", "stub-api-client-id")
        kwargs.setdefault("client_secret", "stub-api-client-secret")
        super().__init__(**kwargs)

    async def authorize_url(self, state, redirect_uri, scopes=None):
        return f"https://stub.example/auth?state={state}&redirect={redirect_uri}"

    async def exchange_code(self, code, redirect_uri):
        return OAuthTokenBundle(
            access_token=f"acc_{code}",
            refresh_token=f"ref_{code}",
            token_type="Bearer",
            expires_at=datetime.now(UTC) + timedelta(hours=2),
            scopes=["read"],
        )

    async def refresh_token(self, refresh_token):
        return OAuthTokenBundle(
            access_token=f"acc_new_{refresh_token}",
            refresh_token=f"ref_new_{refresh_token}",
            token_type="Bearer",
            expires_at=datetime.now(UTC) + timedelta(hours=2),
            scopes=["read"],
        )

    async def revoke(self, access_token):
        return None

    async def get_user_info(self, access_token):
        return {"id": "u1"}


@pytest.fixture(autouse=True)
def _setup_oauth_env(monkeypatch):
    """每个用例隔离 registry + 注入临时 Fernet key + 强制 state cache 走内存。"""
    # 1. registry
    OAuthProviderRegistry.reset_default()
    reg = OAuthProviderRegistry.default()
    reg.register(_StubAPIProvider)

    # 2. settings: 临时 key
    from src.core.config import settings

    monkeypatch.setattr(
        settings,
        "OAUTH_TOKEN_ENCRYPTION_KEY",
        Fernet.generate_key().decode(),
        raising=False,
    )
    monkeypatch.setattr(
        settings,
        "APP_AUTH_REDIRECT_BASE_URL",
        "http://test",
        raising=False,
    )

    # 3. 关闭 state cache 的 Redis 兜底
    from src.services.app_authorization.oauth_flow import (
        _StateCache,
    )

    async def _no_redis(self):
        self._redis_ready = True
        return None

    monkeypatch.setattr(_StateCache, "_ensure_redis", _no_redis, raising=False)
    # 重置进程级 state cache 单例
    import src.services.app_authorization.oauth_flow as flow_mod

    flow_mod._state_cache = None

    yield

    OAuthProviderRegistry.reset_default()
    flow_mod._state_cache = None


# ---------------------------------------------------------------------------
# 用例
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_providers_returns_registered_metadata(
    auth_client: AsyncClient,
):
    """GET /providers 返回已注册 provider 的元数据。"""
    r = await auth_client.get("/api/v1/app-authorizations/providers")
    assert r.status_code == 200, r.text
    data = r.json()
    pids = [p["provider_id"] for p in data["items"]]
    assert "stub_api" in pids

    stub = next(p for p in data["items"] if p["provider_id"] == "stub_api")
    assert stub["display_name"] == "Stub API Provider"
    assert stub["category"] == "office"
    assert stub["icon_url"] == "https://example.com/icon.png"
    assert stub["default_scopes"] == ["read"]


@pytest.mark.asyncio
async def test_list_authorizations_empty_for_new_user(auth_client: AsyncClient):
    """GET / 新用户应返回空列表。"""
    r = await auth_client.get("/api/v1/app-authorizations")
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_start_then_callback_full_roundtrip(auth_client: AsyncClient):
    """POST /start → GET /callback 完整走通：列表里能看到 connected 状态。"""
    # start
    r = await auth_client.post(
        "/api/v1/app-authorizations/stub_api/start",
        json={},
    )
    assert r.status_code == 200, r.text
    started = r.json()
    assert started["provider_id"] == "stub_api"
    assert started["authorize_url"].startswith("https://stub.example/auth")
    assert started["state"]

    # callback（无需 auth header — state 已绑 user_id）
    r2 = await auth_client.get(
        "/api/v1/app-authorizations/stub_api/callback",
        params={"code": "abc123", "state": started["state"]},
    )
    assert r2.status_code == 200, r2.text
    cb = r2.json()
    assert cb["success"] is True
    assert cb["authorization"]["status"] == "connected"
    assert cb["authorization"]["provider_id"] == "stub_api"

    # list
    r3 = await auth_client.get("/api/v1/app-authorizations")
    assert r3.status_code == 200
    items = r3.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "connected"


@pytest.mark.asyncio
async def test_start_with_unknown_provider_returns_404(auth_client: AsyncClient):
    """POST /start 用未注册 provider_id → 404。"""
    r = await auth_client.post(
        "/api/v1/app-authorizations/never_exists/start",
        json={},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_callback_with_bad_state_returns_400(auth_client: AsyncClient):
    """GET /callback state 校验失败 → 400。"""
    r = await auth_client.get(
        "/api/v1/app-authorizations/stub_api/callback",
        params={"code": "any", "state": "bogus_state"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_refresh_and_disconnect_flow(auth_client: AsyncClient):
    """POST /{id}/refresh + DELETE /{id} 路径。"""
    # 先建一个 connected 授权
    r = await auth_client.post(
        "/api/v1/app-authorizations/stub_api/start",
        json={},
    )
    state = r.json()["state"]
    r2 = await auth_client.get(
        "/api/v1/app-authorizations/stub_api/callback",
        params={"code": "code1", "state": state},
    )
    auth_id = r2.json()["authorization"]["id"]

    # refresh
    r3 = await auth_client.post(
        f"/api/v1/app-authorizations/{auth_id}/refresh",
    )
    assert r3.status_code == 200, r3.text
    assert r3.json()["status"] == "connected"
    assert r3.json()["last_refresh_at"] is not None

    # disconnect
    r4 = await auth_client.delete(f"/api/v1/app-authorizations/{auth_id}")
    assert r4.status_code == 200, r4.text
    assert r4.json()["status"] == "revoked"

    # 404 边界
    r5 = await auth_client.delete("/api/v1/app-authorizations/00000000-0000-0000-0000-000000000000")
    assert r5.status_code == 404
