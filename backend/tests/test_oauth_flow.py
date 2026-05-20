"""
OAuthFlowService 单元测试（P4-A）

覆盖 5 项核心行为：
    - start：生成 state + 缓存 + 返回 authorize_url
    - callback：state 校验通过 + 写入 AppAuthorization + AppToken（加密）
    - callback：state 不匹配 / 过期 → OAuthStateError
    - refresh：刷新成功 → 更新 AppToken
    - disconnect：标记 status=revoked 且 provider.revoke 被调用

注意：通过 monkeypatch 注入一个 ``StubProvider`` 模拟外部 OAuth 平台，
不发任何真实 HTTP；用 SQLite 内存库（conftest 提供 db_session）。
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
import pytest_asyncio
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.app_authorization import (
    BaseOAuthProvider,
    OAuthFlowService,
    OAuthProviderError,
    OAuthProviderRegistry,
    OAuthStateError,
    OAuthTokenBundle,
    TokenStore,
)

# 触发表注册到 Base.metadata（conftest setup_test_db 会 create_all）
from src.services.app_authorization.models import (  # noqa: F401
    AppAuthorization,
    AppAuthorizationStatus,
    AppToken,
)

# ---------------------------------------------------------------------------
# Stub Provider — 不打真实 HTTP
# ---------------------------------------------------------------------------


class _StubProvider(BaseOAuthProvider):
    provider_id = "stub_office"
    display_name = "Stub Office"
    category = "office"
    default_scopes = ["read", "write"]

    # 用类属性记录调用，方便断言
    revoke_calls: list[str] = []
    refresh_calls: list[str] = []
    refresh_should_fail: bool = False

    async def authorize_url(self, state, redirect_uri, scopes=None):
        s = ",".join(scopes or self.default_scopes)
        return (
            f"https://stub.example/oauth/authorize?state={state}&scope={s}&redirect={redirect_uri}"
        )

    async def exchange_code(self, code, redirect_uri):
        return OAuthTokenBundle(
            access_token=f"access_for_{code}",
            refresh_token=f"refresh_for_{code}",
            token_type="Bearer",
            expires_at=datetime.now(UTC) + timedelta(hours=2),
            scopes=["read", "write"],
            raw={"code": code},
        )

    async def refresh_token(self, refresh_token):
        _StubProvider.refresh_calls.append(refresh_token)
        if _StubProvider.refresh_should_fail:
            raise RuntimeError("provider says invalid_grant")
        return OAuthTokenBundle(
            access_token=f"new_access_after_{refresh_token}",
            refresh_token=f"rotated_{refresh_token}",
            token_type="Bearer",
            expires_at=datetime.now(UTC) + timedelta(hours=2),
            scopes=["read", "write"],
        )

    async def revoke(self, access_token):
        _StubProvider.revoke_calls.append(access_token)

    async def get_user_info(self, access_token):
        return {"id": "stub-user-1", "name": "Stub User"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_registry():
    """每个用例隔离 registry，避免 provider 全局污染。"""
    OAuthProviderRegistry.reset_default()
    reg = OAuthProviderRegistry.default()
    reg.register(_StubProvider)
    # 重置 stub 状态
    _StubProvider.revoke_calls = []
    _StubProvider.refresh_calls = []
    _StubProvider.refresh_should_fail = False
    yield reg
    OAuthProviderRegistry.reset_default()


@pytest.fixture
def token_store() -> TokenStore:
    """全测试共用一把临时 Fernet key。"""
    return TokenStore(keys=[Fernet.generate_key().decode()])


@pytest.fixture
def in_memory_state_cache():
    """强制使用本地内存 state cache（避免依赖 Redis）。"""
    from src.services.app_authorization.oauth_flow import _StateCache

    cache = _StateCache()

    # 关闭 Redis：把 ensure_redis 强行返回 None
    async def _no_redis(self):
        self._redis_ready = True
        return None

    _StateCache._ensure_redis = _no_redis  # type: ignore[assignment]
    yield cache


@pytest_asyncio.fixture
async def test_user_for_oauth(db_session: AsyncSession):
    """创建一个独立测试用户（避免与 conftest test_user 互相绑定 org fixture）。"""
    from uuid import uuid4

    from src.models.user import User

    user = User(
        id=str(uuid4()),
        email=f"o_{uuid4().hex[:6]}@x.com",
        name="oauth tester",
        hashed_password="x",
        is_active=True,
        role="member",
    )
    db_session.add(user)
    await db_session.flush()
    return user


# ---------------------------------------------------------------------------
# 用例
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_returns_authorize_url_and_caches_state(
    db_session: AsyncSession,
    token_store: TokenStore,
    in_memory_state_cache,
    test_user_for_oauth,
):
    service = OAuthFlowService(
        db_session,
        token_store=token_store,
        state_cache=in_memory_state_cache,
    )
    out = await service.start(
        provider_id="stub_office",
        user_id=str(test_user_for_oauth.id),
        redirect_uri="http://localhost:8001/cb",
    )

    assert out["authorize_url"].startswith("https://stub.example/oauth/authorize")
    assert f"state={out['state']}" in out["authorize_url"]
    # state 已落缓存
    cached_uid = await in_memory_state_cache.pop("stub_office", out["state"])
    assert cached_uid == str(test_user_for_oauth.id)


@pytest.mark.asyncio
async def test_callback_with_invalid_state_raises(
    db_session: AsyncSession,
    token_store: TokenStore,
    in_memory_state_cache,
):
    service = OAuthFlowService(
        db_session,
        token_store=token_store,
        state_cache=in_memory_state_cache,
    )
    with pytest.raises(OAuthStateError):
        await service.callback(
            provider_id="stub_office",
            state="never_issued_state",
            code="any_code",
        )


@pytest.mark.asyncio
async def test_callback_persists_authorization_and_encrypted_token(
    db_session: AsyncSession,
    token_store: TokenStore,
    in_memory_state_cache,
    test_user_for_oauth,
):
    service = OAuthFlowService(
        db_session,
        token_store=token_store,
        state_cache=in_memory_state_cache,
    )

    started = await service.start(
        provider_id="stub_office",
        user_id=str(test_user_for_oauth.id),
    )
    auth = await service.callback(
        provider_id="stub_office",
        state=started["state"],
        code="auth_code_xyz",
    )

    assert auth.user_id == str(test_user_for_oauth.id)
    assert auth.provider_id == "stub_office"
    assert auth.status == AppAuthorizationStatus.CONNECTED
    assert auth.connected_at is not None
    assert "read" in (auth.scopes or [])

    # token 被加密存储 + 可解密回原文
    token_row = await service._load_token_row(auth.id)
    assert token_row is not None
    assert isinstance(token_row.encrypted_access_token, (bytes, bytearray, memoryview))
    decrypted_access = token_store.decrypt(token_row.encrypted_access_token)
    assert decrypted_access == "access_for_auth_code_xyz"
    assert token_store.decrypt(token_row.encrypted_refresh_token) == "refresh_for_auth_code_xyz"


@pytest.mark.asyncio
async def test_refresh_updates_token_and_marks_connected(
    db_session: AsyncSession,
    token_store: TokenStore,
    in_memory_state_cache,
    test_user_for_oauth,
):
    service = OAuthFlowService(
        db_session,
        token_store=token_store,
        state_cache=in_memory_state_cache,
    )
    started = await service.start(
        provider_id="stub_office",
        user_id=str(test_user_for_oauth.id),
    )
    auth = await service.callback(
        provider_id="stub_office",
        state=started["state"],
        code="cccc",
    )

    refreshed = await service.refresh(auth.id)
    assert refreshed.status == AppAuthorizationStatus.CONNECTED
    assert refreshed.last_refresh_at is not None
    assert _StubProvider.refresh_calls == ["refresh_for_cccc"]

    token_row = await service._load_token_row(auth.id)
    assert token_store.decrypt(token_row.encrypted_access_token) == (
        "new_access_after_refresh_for_cccc"
    )

    # refresh 失败时标 EXPIRED
    _StubProvider.refresh_should_fail = True
    with pytest.raises(OAuthProviderError):
        await service.refresh(auth.id)
    auth_after_fail = await service._load_authorization(auth.id)
    assert auth_after_fail.status == AppAuthorizationStatus.EXPIRED


@pytest.mark.asyncio
async def test_disconnect_revokes_remote_and_marks_revoked(
    db_session: AsyncSession,
    token_store: TokenStore,
    in_memory_state_cache,
    test_user_for_oauth,
):
    service = OAuthFlowService(
        db_session,
        token_store=token_store,
        state_cache=in_memory_state_cache,
    )
    started = await service.start(
        provider_id="stub_office",
        user_id=str(test_user_for_oauth.id),
    )
    auth = await service.callback(
        provider_id="stub_office",
        state=started["state"],
        code="dddd",
    )

    revoked = await service.disconnect(auth.id)
    assert revoked.status == AppAuthorizationStatus.REVOKED
    assert _StubProvider.revoke_calls == ["access_for_dddd"]
