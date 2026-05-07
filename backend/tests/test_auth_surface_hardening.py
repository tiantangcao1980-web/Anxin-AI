import hashlib
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from src.core.config import settings
from src.core.security import create_token_pair, get_password_hash, refresh_access_token
from src.models.user import PasswordResetToken, User


@pytest.mark.asyncio
async def test_forgot_password_rate_limited(client, db_session, test_organization):
    user = User(
        email="recover@example.com",
        name="Recover User",
        hashed_password=get_password_hash("RecoverPass1"),
        org_id=test_organization.id,
        role="individual_user",
        user_type="individual",
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    for _ in range(5):
        response = await client.post("/api/v1/auth/forgot-password", json={"email": user.email})
        assert response.status_code == 200

    limited = await client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    assert limited.status_code == 429


@pytest.mark.asyncio
async def test_login_requires_captcha_when_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, "CAPTCHA_ENABLED", True)
    monkeypatch.setattr(settings, "CAPTCHA_PROVIDER", "turnstile")
    monkeypatch.setattr(settings, "TURNSTILE_SITE_KEY", "site-key")
    monkeypatch.setattr(settings, "TURNSTILE_SECRET_KEY", "secret-key")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "Anything123"},
    )

    assert response.status_code == 400
    assert "人机验证" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_accepts_valid_captcha_token(client, monkeypatch):
    monkeypatch.setattr(settings, "CAPTCHA_ENABLED", True)
    monkeypatch.setattr(settings, "CAPTCHA_PROVIDER", "turnstile")
    monkeypatch.setattr(settings, "TURNSTILE_SITE_KEY", "site-key")
    monkeypatch.setattr(settings, "TURNSTILE_SECRET_KEY", "secret-key")
    monkeypatch.setattr(settings, "EMAIL_VERIFY_ENABLED", False)

    with patch("src.api.routes.auth.captcha_service.verify_token", new=AsyncMock(return_value=True)):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "captcha-user@example.com",
                "password": "StrongPass1",
                "name": "captcha-user",
                "user_type": "individual",
                "captcha_token": "token-ok",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "captcha-user@example.com"


@pytest.mark.asyncio
async def test_reset_password_requires_captcha_when_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, "CAPTCHA_ENABLED", True)
    monkeypatch.setattr(settings, "CAPTCHA_PROVIDER", "turnstile")
    monkeypatch.setattr(settings, "TURNSTILE_SITE_KEY", "site-key")
    monkeypatch.setattr(settings, "TURNSTILE_SECRET_KEY", "secret-key")

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "any-token", "new_password": "NewStrong1"},
    )

    assert response.status_code == 400
    assert "人机验证" in response.json()["detail"]


@pytest.mark.asyncio
async def test_resend_verification_requires_captcha_when_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, "CAPTCHA_ENABLED", True)
    monkeypatch.setattr(settings, "CAPTCHA_PROVIDER", "turnstile")
    monkeypatch.setattr(settings, "TURNSTILE_SITE_KEY", "site-key")
    monkeypatch.setattr(settings, "TURNSTILE_SECRET_KEY", "secret-key")

    response = await client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "captcha@example.com"},
    )

    assert response.status_code == 400
    assert "人机验证" in response.json()["detail"]


@pytest.mark.asyncio
async def test_password_reset_token_is_high_entropy_single_use_and_context_bound(
    client,
    db_session,
    test_organization,
    monkeypatch,
):
    monkeypatch.setattr(settings, "DEV_MODE", True)
    user = User(
        email="context-reset@example.com",
        name="Context Reset",
        hashed_password=get_password_hash("OldStrong1"),
        org_id=test_organization.id,
        role="individual_user",
        user_type="individual",
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    headers = {"user-agent": "reset-agent-a", "x-forwarded-for": "198.51.100.10"}
    with patch("src.services.email_service.email_service.send_reset_code", new=AsyncMock()):
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": user.email},
            headers=headers,
        )

    assert response.status_code == 200
    token = response.json()["debug_token"]
    assert len(token) >= 32
    assert not token.isdigit()

    token_records = (
        await db_session.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        )
    ).scalars().all()
    assert len(token_records) == 1
    reset_record = token_records[0]
    assert reset_record.token_hash == hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert reset_record.token_hash != token
    assert reset_record.consumed_at is None

    mismatch = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewStrong1"},
        headers={"user-agent": "reset-agent-b", "x-forwarded-for": "198.51.100.10"},
    )
    assert mismatch.status_code == 400
    assert "上下文" in mismatch.json()["detail"]
    await db_session.refresh(reset_record)
    assert reset_record.consumed_at is None

    success = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewStrong1"},
        headers=headers,
    )
    assert success.status_code == 200
    await db_session.refresh(reset_record)
    assert reset_record.consumed_at is not None

    reused = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "AnotherStrong1"},
        headers=headers,
    )
    assert reused.status_code == 400


@pytest.mark.asyncio
async def test_auth_rate_limit_fails_closed_when_redis_down(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_REDIS_FAIL_CLOSED", True, raising=False)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production", raising=False)

    from src.core.security import get_rate_limiter

    async def redis_down():
        raise RuntimeError("redis down")

    limiter = get_rate_limiter()
    monkeypatch.setattr(limiter, "_get_redis", redis_down)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "Anything123"},
    )

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "60"
    assert "认证限流服务暂不可用" in response.json()["detail"]


@pytest.mark.asyncio
async def test_forgot_password_rate_limit_fails_closed_when_redis_down(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_REDIS_FAIL_CLOSED", True, raising=False)

    from src.core.security import get_rate_limiter

    async def redis_down():
        raise RuntimeError("redis down")

    limiter = get_rate_limiter()
    monkeypatch.setattr(limiter, "_get_redis", redis_down)

    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "someone@example.com"},
    )

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "300"


@pytest.mark.asyncio
async def test_refresh_token_blacklist_fails_closed_when_redis_down(monkeypatch):
    from src.core.security import get_token_blacklist

    async def redis_down():
        raise RuntimeError("redis down")

    blacklist = get_token_blacklist()
    monkeypatch.setattr(blacklist, "_get_redis", redis_down)

    tokens = create_token_pair("user-refresh-fail-closed")
    refreshed = await refresh_access_token(tokens.refresh_token)

    assert refreshed is None


@pytest.mark.asyncio
async def test_refresh_endpoint_rejects_body_token_after_compat_sunset(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_REFRESH_BODY_COMPAT_ENABLED", False)
    tokens = create_token_pair("refresh-user")

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens.refresh_token},
    )

    assert response.status_code == 400
    assert "兼容期已结束" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_endpoint_still_accepts_cookie_when_body_compat_disabled(client, monkeypatch):
    from src.core.security import get_token_blacklist

    monkeypatch.setattr(settings, "AUTH_REFRESH_BODY_COMPAT_ENABLED", False)
    blacklist = get_token_blacklist()
    monkeypatch.setattr(blacklist, "is_blacklisted", AsyncMock(return_value=False))
    monkeypatch.setattr(blacklist, "add_to_blacklist", AsyncMock(return_value=True))
    tokens = create_token_pair("refresh-user")
    client.cookies.set("refresh_token", tokens.refresh_token)

    response = await client.post(
        "/api/v1/auth/refresh",
        json={},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


@pytest.mark.asyncio
async def test_refresh_endpoint_accepts_cookie_without_request_body(client, monkeypatch):
    from src.core.security import get_token_blacklist

    monkeypatch.setattr(settings, "AUTH_REFRESH_BODY_COMPAT_ENABLED", False)
    blacklist = get_token_blacklist()
    monkeypatch.setattr(blacklist, "is_blacklisted", AsyncMock(return_value=False))
    monkeypatch.setattr(blacklist, "add_to_blacklist", AsyncMock(return_value=True))
    tokens = create_token_pair("refresh-user")
    client.cookies.set("refresh_token", tokens.refresh_token)

    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    assert response.json()["access_token"]


@pytest.mark.asyncio
async def test_oauth_callback_requires_matching_state(client, monkeypatch):
    monkeypatch.setattr(settings, "OAUTH_WECHAT_ENABLED", True)

    response = await client.post(
        "/api/v1/auth/oauth/wechat/callback",
        json={"code": "abc123", "state": "invalid-state"},
    )

    assert response.status_code == 400
    assert "state" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_oauth_callback_accepts_issued_state(client, monkeypatch):
    monkeypatch.setattr(settings, "OAUTH_WECHAT_ENABLED", True)

    issue_response = await client.get("/api/v1/auth/oauth/wechat/url")
    assert issue_response.status_code == 200
    state = issue_response.json()["state"]

    with patch("src.api.routes.auth.WeChatOAuth.get_access_token", new=AsyncMock(return_value={
        "access_token": "token",
        "openid": "openid-1",
    })), patch("src.api.routes.auth.WeChatOAuth.get_user_info", new=AsyncMock(return_value={
        "openid": "openid-1",
        "nickname": "微信用户",
        "headimgurl": "",
    })):
        callback = await client.post(
            "/api/v1/auth/oauth/wechat/callback",
            json={"code": "abc123", "state": state},
        )

    assert callback.status_code == 200
    body = callback.json()
    assert "access_token" in body


@pytest.mark.asyncio
async def test_wechat_mini_code2session_requires_feature_flag(client, monkeypatch):
    monkeypatch.setattr(settings, "OAUTH_WECHAT_ENABLED", False)

    response = await client.post(
        "/api/v1/auth/wechat/code2session",
        json={"code": "wx-code"},
    )

    assert response.status_code == 404
    assert "微信登录未启用" in response.json()["detail"]


@pytest.mark.asyncio
async def test_wechat_mini_code2session_issues_jwt_without_session_key(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(settings, "OAUTH_WECHAT_ENABLED", True)
    monkeypatch.setattr(settings, "WECHAT_MINI_APP_ID", "wx-mini-app")
    monkeypatch.setattr(settings, "WECHAT_MINI_APP_SECRET", "wx-mini-secret")

    with patch(
        "src.api.routes.auth.WeChatMiniProgramOAuth.code2session",
        new=AsyncMock(return_value={
            "openid": "mini-openid-1",
            "unionid": "mini-union-1",
            "session_key": "server-only-session-key",
        }),
    ):
        response = await client.post(
            "/api/v1/auth/wechat/code2session",
            json={"code": "wx-code"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert "session_key" not in body
    assert body["user"]["nickname"] == "微信用户"
    assert body["user"]["login_type"] == "wechat"

    result = await db_session.execute(
        select(User).where(User.wechat_openid == "mini-openid-1")
    )
    user = result.scalar_one()
    assert user.wechat_unionid == "mini-union-1"
    assert user.email.startswith("wx_mini-openid-1")


@pytest.mark.asyncio
async def test_sync_endpoints_require_auth_and_are_isolated(client, auth_client):
    unauth = await client.post("/api/v1/sync/push", json={"records": [], "device_id": "d1", "last_sync_version": 0})
    assert unauth.status_code == 401

    authed = await auth_client.post("/api/v1/sync/push", json={"records": [], "device_id": "d1", "last_sync_version": 0})
    assert authed.status_code == 200
    assert authed.json()["accepted"] == 0


@pytest.mark.asyncio
async def test_lic_crawl_blocks_localhost(auth_client):
    response = await auth_client.post(
        "/api/v1/lic/crawl",
        json={"url": "http://127.0.0.1:8000/private", "keyword": "test", "task_id": "task-1"},
    )

    assert response.status_code == 403
