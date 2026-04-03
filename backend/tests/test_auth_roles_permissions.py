import pytest

from src.core.config import settings
from src.core.security import get_password_hash
from src.models.user import User

from .conftest import create_auth_headers


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("user_type", "expected_role"),
    [
        ("individual", "individual_user"),
        ("enterprise", "enterprise_user"),
        ("platform_lawyer", "viewer"),
        ("institution", "viewer"),
    ],
)
async def test_register_assigns_initial_role_by_user_type(
    client,
    monkeypatch,
    user_type: str,
    expected_role: str,
):
    monkeypatch.setattr(settings, "EMAIL_VERIFY_ENABLED", False)

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{user_type}@example.com",
            "password": "StrongPass1",
            "name": f"{user_type}-tester",
            "user_type": user_type,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == expected_role
    assert payload["user_type"] == user_type
    assert payload["email_verified"] is True


@pytest.mark.asyncio
async def test_login_locks_account_after_repeated_failures(
    client,
    db_session,
    test_organization,
):
    user = User(
        email="lockme@example.com",
        name="Lock Me",
        hashed_password=get_password_hash("CorrectPass1"),
        org_id=test_organization.id,
        role="individual_user",
        user_type="individual",
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    for _ in range(5):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "WrongPass1"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "邮箱或密码错误"

    locked_response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "CorrectPass1"},
    )

    assert locked_response.status_code == 403
    assert "账号已被锁定" in locked_response.json()["detail"]


@pytest.mark.asyncio
async def test_member_cannot_access_firm_management_list(client, test_user):
    response = await client.get(
        "/api/v1/firm/teams",
        headers=create_auth_headers(test_user),
    )

    assert response.status_code == 403
    assert "manage:crm" in response.json()["detail"]


@pytest.mark.asyncio
async def test_partner_can_access_firm_management_list(
    client,
    db_session,
    test_organization,
):
    partner = User(
        email="partner@example.com",
        name="Partner User",
        hashed_password=get_password_hash("PartnerPass1"),
        org_id=test_organization.id,
        role="partner",
        user_type="internal",
        is_active=True,
        email_verified=True,
    )
    db_session.add(partner)
    await db_session.flush()

    response = await client.get(
        "/api/v1/firm/teams",
        headers=create_auth_headers(partner),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert payload["data"]["items"] == []
    assert payload["data"]["total"] == 0
