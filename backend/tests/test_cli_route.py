import pytest
from sqlalchemy import select

from src.api.routes.cli import _api_keys, _rate_limits
from src.models import AgentAuditEvent
from src.models.audit import AuditLog
from src.services.agent_governance_service import AgentGovernanceService


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
    audit_result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "cli.key.create")
    )
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


@pytest.mark.asyncio
async def test_cli_execute_requires_route_token_in_commercial_environment(
    monkeypatch,
    auth_client,
    db_session,
):
    from src.api.routes import cli

    monkeypatch.setattr(cli.settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(cli.settings, "CLI_ROUTE_TOKEN_REQUIRED", False)
    create = await auth_client.post(
        "/api/v1/cli/keys",
        json={"name": "commercial-cli", "scopes": ["read"], "expires_days": 7},
    )
    api_key = create.json()["api_key"]

    response = await auth_client.post(
        "/api/v1/cli/execute",
        headers={"X-API-Key": api_key},
        json={"command": "status", "args": {}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert "CLI route token required" in payload["error"]
    audit_result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "cli.execute", AuditLog.status == "failed")
    )
    audit_log = audit_result.scalar_one()
    assert audit_log.extra_data["route_reason"] == "missing_route_token"
    assert audit_log.extra_data["route_scope"] == "cli:read"


@pytest.mark.asyncio
async def test_cli_execute_accepts_db_backed_route_token(
    monkeypatch,
    auth_client,
    db_session,
    test_organization,
):
    from src.api.routes import cli

    monkeypatch.setattr(cli.settings, "ENVIRONMENT", "production")
    create = await auth_client.post(
        "/api/v1/cli/keys",
        json={"name": "governed-cli", "scopes": ["read"], "expires_days": 7},
    )
    payload = create.json()
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="cli-status-route",
        route_type="cli",
        allowed_consumers=[payload["key_id"]],
        allowed_scopes=["cli:read"],
    )
    issued = await governance.issue_route_token(
        org_id=test_organization.id,
        route_key="cli-status-route",
        consumer_id=payload["key_id"],
        requested_scopes=["cli:read"],
    )

    response = await auth_client.post(
        "/api/v1/cli/execute",
        headers={
            "X-API-Key": payload["api_key"],
            "X-Capability-Route-Token": issued.token,
        },
        json={"command": "status", "args": {}},
    )
    audits = (
        (
            await db_session.execute(
                select(AgentAuditEvent).where(AgentAuditEvent.org_id == test_organization.id)
            )
        )
        .scalars()
        .all()
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["result"]["system"] == "ok"
    assert [event.reason_code for event in audits] == ["issued", "allowed"]


@pytest.mark.asyncio
async def test_cli_route_token_endpoint_issues_key_bound_token(
    monkeypatch,
    auth_client,
    db_session,
    test_organization,
):
    from src.api.routes import cli

    monkeypatch.setattr(cli.settings, "ENVIRONMENT", "production")
    create = await auth_client.post(
        "/api/v1/cli/keys",
        json={"name": "desktop-cli", "scopes": ["read"], "expires_days": 7},
    )
    payload = create.json()
    route_key = f"cli:{payload['key_id']}"
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key=route_key,
        route_type="cli",
        allowed_consumers=[payload["key_id"]],
        allowed_scopes=["cli:read"],
    )

    token_response = await auth_client.post(
        "/api/v1/cli/route-token",
        headers={"X-API-Key": payload["api_key"]},
        json={"scope": "read"},
    )
    token_body = token_response.json()
    execute_response = await auth_client.post(
        "/api/v1/cli/execute",
        headers={
            "X-API-Key": payload["api_key"],
            "X-Capability-Route-Token": token_body["route_token"],
        },
        json={"command": "status", "args": {}},
    )
    audits = (
        (
            await db_session.execute(
                select(AgentAuditEvent).where(AgentAuditEvent.org_id == test_organization.id)
            )
        )
        .scalars()
        .all()
    )

    assert token_response.status_code == 200
    assert token_body["success"] is True
    assert token_body["required"] is True
    assert token_body["route_key"] == route_key
    assert token_body["scope"] == "read"
    assert token_body["route_token"].startswith("anxin_route_")
    assert execute_response.json()["success"] is True
    assert [event.reason_code for event in audits] == ["issued", "allowed"]


@pytest.mark.asyncio
async def test_cli_route_token_endpoint_is_optional_when_governance_not_required(
    monkeypatch,
    auth_client,
):
    from src.api.routes import cli

    monkeypatch.setattr(cli.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(cli.settings, "CLI_ROUTE_TOKEN_REQUIRED", False)
    create = await auth_client.post(
        "/api/v1/cli/keys",
        json={"name": "dev-cli", "scopes": ["read"], "expires_days": 7},
    )
    payload = create.json()

    response = await auth_client.post(
        "/api/v1/cli/route-token",
        headers={"X-API-Key": payload["api_key"]},
        json={"scope": "read"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["required"] is False
    assert "unknown_capability_route" in body["error"]


@pytest.mark.asyncio
async def test_cli_execute_enforces_route_token_consumer(
    monkeypatch,
    auth_client,
    db_session,
    test_organization,
):
    from src.api.routes import cli

    monkeypatch.setattr(cli.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(cli.settings, "CLI_ROUTE_TOKEN_REQUIRED", True)
    create = await auth_client.post(
        "/api/v1/cli/keys",
        json={"name": "consumer-bound-cli", "scopes": ["read"], "expires_days": 7},
    )
    payload = create.json()
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="cli-consumer-bound-route",
        route_type="cli",
        allowed_consumers=["another-cli-key"],
        allowed_scopes=["cli:read"],
    )
    issued = await governance.issue_route_token(
        org_id=test_organization.id,
        route_key="cli-consumer-bound-route",
        consumer_id="another-cli-key",
        requested_scopes=["cli:read"],
    )

    response = await auth_client.post(
        "/api/v1/cli/execute",
        headers={
            "X-API-Key": payload["api_key"],
            "X-Capability-Route-Token": issued.token,
        },
        json={"command": "status", "args": {}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert "route_token_consumer_mismatch" in body["error"]
