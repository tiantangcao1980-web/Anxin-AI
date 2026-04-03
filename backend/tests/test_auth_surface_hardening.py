import pytest
from unittest.mock import AsyncMock, patch

from src.core.config import settings
from src.models.user import User
from src.core.security import get_password_hash


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
