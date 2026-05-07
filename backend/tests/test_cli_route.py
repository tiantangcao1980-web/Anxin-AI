import pytest
from sqlalchemy import select

from src.api.routes.cli import _api_keys, _rate_limits
from src.models.audit import AuditLog


@pytest.fixture(autouse=True)
def reset_cli_state():
    _api_keys.clear()
    _rate_limits.clear()
    yield
    _api_keys.clear()
    _rate_limits.clear()


@pytest.mark.asyncio
async def test_cli_keys_require_authenticated_user(client):
    response = await client.post(
        "/api/v1/cli/keys",
        json={"name": "ci-key", "scopes": ["read", "chat"], "expires_days": 30},
    )

    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_cli_keys_create_and_list_round_trip(auth_client, db_session, test_user):
    response = await auth_client.post(
        "/api/v1/cli/keys",
        json={"name": "ci-key", "scopes": ["read", "chat"], "expires_days": 30},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["key_id"]
    assert payload["api_key"].startswith("anxin_cli_")
    assert payload["created_at"]
    assert next(iter(_api_keys.values()))["user_id"] == str(test_user.id)

    listed = await auth_client.get("/api/v1/cli/keys")

    assert listed.status_code == 200
    list_payload = listed.json()
    assert list_payload["status"] == "ok"
    assert list_payload["data"] == [
        {
            "key_id": payload["key_id"],
            "api_key": None,
            "name": "ci-key",
            "scopes": ["read", "chat"],
            "expires_at": payload["expires_at"],
            "created_at": payload["created_at"],
        }
    ]
    audit_result = await db_session.execute(select(AuditLog).where(AuditLog.action == "cli.key.create"))
    audit_log = audit_result.scalar_one()
    assert audit_log.user_id == test_user.id
    assert audit_log.resource_id == payload["key_id"]
    assert audit_log.new_value == {
        "name": "ci-key",
        "scopes": ["read", "chat"],
        "expires_at": payload["expires_at"],
    }


@pytest.mark.asyncio
async def test_cli_execute_rejects_missing_scope(auth_client, db_session, test_user):
    create = await auth_client.post(
        "/api/v1/cli/keys",
        json={"name": "read-only", "scopes": ["read"], "expires_days": 7},
    )
    api_key = create.json()["api_key"]

    response = await auth_client.post(
        "/api/v1/cli/execute",
        headers={"X-API-Key": api_key},
        json={"command": "draft", "args": {"content": "合同草稿"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert "缺少 'chat' 权限" in payload["error"]
    audit_result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "cli.execute", AuditLog.status == "failed")
    )
    audit_log = audit_result.scalar_one()
    assert audit_log.user_id == test_user.id
    assert audit_log.extra_data["source"] == "cli"
    assert audit_log.extra_data["command"] == "draft"


@pytest.mark.asyncio
async def test_cli_key_export_scope_requires_export_permission(auth_client):
    response = await auth_client.post(
        "/api/v1/cli/keys",
        json={"name": "export-key", "scopes": ["export"], "expires_days": 7},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cli_key_revoke_scoped_to_owner(auth_client, admin_auth_client):
    create = await auth_client.post(
        "/api/v1/cli/keys",
        json={"name": "owner-key", "scopes": ["read"], "expires_days": 7},
    )
    key_id = create.json()["key_id"]

    forbidden = await admin_auth_client.delete(f"/api/v1/cli/keys/{key_id}")
    allowed = await auth_client.delete(f"/api/v1/cli/keys/{key_id}")

    assert forbidden.status_code == 404
    assert allowed.status_code == 200
