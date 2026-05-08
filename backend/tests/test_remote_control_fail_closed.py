import pytest
from sqlalchemy import select

from src.models.sync import RemoteControlCommand
from src.services.agent_governance_service import AgentGovernanceService


def _detail(response):
    return response.json()["detail"]


@pytest.mark.asyncio
async def test_remote_control_status_is_explicitly_not_configured(auth_client):
    response = await auth_client.get("/api/v1/sync/remote-control/status?desktop_device_id=desktop-a")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["status"] == "not_configured"
    assert body["desktop_device_id"] == "desktop-a"
    assert "device_pairing" in body["required_controls"]
    assert "capability_route_token" in body["required_controls"]
    assert "审计" in body["message"]


@pytest.mark.asyncio
async def test_remote_control_pairing_rejects_top_secret_mode(auth_client):
    response = await auth_client.post(
        "/api/v1/sync/remote-control/pairings",
        json={
            "mobile_device_id": "mobile-a",
            "desktop_device_id": "desktop-a",
            "requested_scopes": ["view_status", "start_task"],
            "privacy_mode": "top-secret",
        },
    )

    assert response.status_code == 403
    detail = _detail(response)
    assert detail["code"] == "remote_control_privacy_mode_blocked"
    assert "绝密" in detail["message"]
    assert "desktop_confirmation" in detail["required_controls"]


@pytest.mark.asyncio
async def test_remote_control_pairing_creates_pending_request_and_audit(auth_client):
    response = await auth_client.post(
        "/api/v1/sync/remote-control/pairings",
        json={
            "mobile_device_id": "mobile-a",
            "desktop_device_id": "desktop-a",
            "requested_scopes": ["view_status"],
            "privacy_mode": "hybrid",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pairing_id"]
    assert body["status"] == "pending_desktop_confirmation"
    assert body["desktop_device_id"] == "desktop-a"

    audit = await auth_client.get("/api/v1/sync/remote-control/audit-events")
    assert audit.status_code == 200
    assert audit.json()["items"][0]["reason_code"] == "pending_desktop_confirmation"


@pytest.mark.asyncio
async def test_remote_control_command_requires_second_confirmation_before_queue(auth_client):
    response = await auth_client.post(
        "/api/v1/sync/remote-control/commands",
        json={
            "desktop_device_id": "desktop-a",
            "command_type": "export_sensitive_files",
            "payload": {"path": "/case-files"},
            "pairing_id": "pairing-a",
            "route_token": "route-token-a",
            "privacy_mode": "hybrid",
            "risk_level": "l4",
            "second_confirmed": False,
        },
    )

    assert response.status_code == 403
    detail = _detail(response)
    assert detail["code"] == "remote_control_second_confirmation_required"
    assert "二次确认" in detail["message"]


@pytest.mark.asyncio
async def test_remote_control_command_rejects_unpaired_device(auth_client):
    response = await auth_client.post(
        "/api/v1/sync/remote-control/commands",
        json={
            "desktop_device_id": "desktop-a",
            "command_type": "open_case_review",
            "payload": {"case_id": "case-a"},
            "privacy_mode": "hybrid",
            "risk_level": "l3",
        },
    )

    assert response.status_code == 403
    detail = _detail(response)
    assert detail["code"] == "remote_control_pairing_required"
    assert "不会入队" in detail["message"]


@pytest.mark.asyncio
async def test_remote_control_command_requires_route_token(auth_client):
    response = await auth_client.post(
        "/api/v1/sync/remote-control/commands",
        json={
            "desktop_device_id": "desktop-a",
            "command_type": "open_case_review",
            "payload": {"case_id": "case-a"},
            "pairing_id": "pairing-a",
            "privacy_mode": "hybrid",
            "risk_level": "l3",
        },
    )

    assert response.status_code == 403
    detail = _detail(response)
    assert detail["code"] == "remote_control_route_token_required"
    assert "CapabilityRoute token" in detail["message"]


@pytest.mark.asyncio
async def test_remote_control_command_rejects_unknown_pairing_without_crashing(auth_client):
    response = await auth_client.post(
        "/api/v1/sync/remote-control/commands",
        json={
            "desktop_device_id": "desktop-a",
            "command_type": "open_case_review",
            "payload": {"case_id": "case-a"},
            "pairing_id": "pairing-a",
            "route_token": "route-token-a",
            "privacy_mode": "hybrid",
            "risk_level": "l3",
            "second_confirmed": True,
        },
    )

    assert response.status_code == 404
    detail = _detail(response)
    assert detail["code"] == "remote_control_pairing_not_found"


@pytest.mark.asyncio
async def test_remote_control_pairing_confirm_route_token_queue_cancel_and_audit(
    auth_client,
    db_session,
    test_organization,
):
    pairing_response = await auth_client.post(
        "/api/v1/sync/remote-control/pairings",
        json={
            "mobile_device_id": "mobile-a",
            "desktop_device_id": "desktop-a",
            "requested_scopes": ["desktop:control"],
            "privacy_mode": "hybrid",
        },
    )
    pairing_id = pairing_response.json()["pairing_id"]

    confirm_response = await auth_client.post(
        f"/api/v1/sync/remote-control/pairings/{pairing_id}/confirm",
        json={"desktop_device_id": "desktop-a"},
    )

    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "confirmed"

    await AgentGovernanceService(db_session).create_capability_route(
        org_id=str(test_organization.id),
        route_key="desktop-control",
        route_type="desktop_control",
        allowed_consumers=[pairing_id],
        allowed_scopes=["desktop:control"],
        status="enabled",
    )
    await db_session.flush()

    token_response = await auth_client.post(
        "/api/v1/sync/remote-control/route-token",
        json={"pairing_id": pairing_id, "ttl_seconds": 300},
    )

    assert token_response.status_code == 200
    route_token = token_response.json()["route_token"]
    assert route_token
    assert token_response.json()["required_scope"] == "desktop:control"

    unsupported_response = await auth_client.post(
        "/api/v1/sync/remote-control/commands",
        json={
            "desktop_device_id": "desktop-a",
            "command_type": "open_case_review",
            "payload": {"case_id": "case-a"},
            "pairing_id": pairing_id,
            "route_token": route_token,
            "privacy_mode": "hybrid",
            "risk_level": "l3",
            "second_confirmed": True,
        },
    )
    assert unsupported_response.status_code == 403
    assert _detail(unsupported_response)["code"] == "remote_control_command_type_not_supported"

    command_response = await auth_client.post(
        "/api/v1/sync/remote-control/commands",
        json={
            "desktop_device_id": "desktop-a",
            "command_type": "desktop.status_probe",
            "payload": {"case_id": "case-a", "route_token": "must-redact"},
            "pairing_id": pairing_id,
            "route_token": route_token,
            "privacy_mode": "hybrid",
            "risk_level": "l3",
            "second_confirmed": True,
        },
    )

    assert command_response.status_code == 200
    command = command_response.json()
    assert command["status"] == "queued"
    assert command["route_consumer_id"] == pairing_id
    command_id = command["command_id"]
    stored_command = (
        await db_session.execute(select(RemoteControlCommand).where(RemoteControlCommand.id == command_id))
    ).scalar_one()
    assert stored_command.payload["route_token"] == "[REDACTED]"

    status = await auth_client.get("/api/v1/sync/remote-control/status?desktop_device_id=desktop-a")
    assert status.status_code == 200
    assert status.json()["status"] == "queue_ready_execution_pending"
    assert status.json()["queued_command_count"] == 1

    cancel_response = await auth_client.post(
        f"/api/v1/sync/remote-control/commands/{command_id}/cancel",
        json={"reason": "user revoked before desktop pickup"},
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    audit = await auth_client.get("/api/v1/sync/remote-control/audit-events")
    reason_codes = [item["reason_code"] for item in audit.json()["items"]]
    assert "unsupported_command_type" in reason_codes
    assert "queued" in reason_codes
    assert "cancelled" in reason_codes
    assert "must-redact" not in str(audit.json())


@pytest.mark.asyncio
async def test_remote_control_desktop_host_claims_and_reports_execution_status(
    auth_client,
    db_session,
    test_organization,
):
    pairing_response = await auth_client.post(
        "/api/v1/sync/remote-control/pairings",
        json={
            "mobile_device_id": "mobile-b",
            "desktop_device_id": "desktop-b",
            "requested_scopes": ["desktop:control"],
            "privacy_mode": "hybrid",
        },
    )
    pairing_id = pairing_response.json()["pairing_id"]
    confirm_response = await auth_client.post(
        f"/api/v1/sync/remote-control/pairings/{pairing_id}/confirm",
        json={"desktop_device_id": "desktop-b"},
    )
    assert confirm_response.status_code == 200

    await AgentGovernanceService(db_session).create_capability_route(
        org_id=str(test_organization.id),
        route_key="desktop-control",
        route_type="desktop_control",
        allowed_consumers=[pairing_id],
        allowed_scopes=["desktop:control"],
        status="enabled",
    )
    await db_session.flush()
    token_response = await auth_client.post(
        "/api/v1/sync/remote-control/route-token",
        json={"pairing_id": pairing_id, "ttl_seconds": 300},
    )
    route_token = token_response.json()["route_token"]

    command_response = await auth_client.post(
        "/api/v1/sync/remote-control/commands",
        json={
            "desktop_device_id": "desktop-b",
            "command_type": "desktop.status_probe",
            "payload": {"case_id": "case-b", "secret": "client-secret"},
            "pairing_id": pairing_id,
            "route_token": route_token,
            "privacy_mode": "hybrid",
            "risk_level": "l3",
            "second_confirmed": True,
        },
    )
    command_id = command_response.json()["command_id"]

    claim_response = await auth_client.post(
        "/api/v1/sync/remote-control/commands/claim",
        json={
            "desktop_device_id": "desktop-b",
            "pairing_id": pairing_id,
            "route_token": route_token,
            "host_instance_id": "desktop-host-b",
            "limit": 5,
        },
    )
    assert claim_response.status_code == 200
    claimed = claim_response.json()
    assert claimed["total"] == 1
    assert claimed["items"][0]["command_id"] == command_id
    assert claimed["items"][0]["status"] == "claimed"
    assert claimed["items"][0]["payload"]["secret"] == "[REDACTED]"

    running_response = await auth_client.post(
        f"/api/v1/sync/remote-control/commands/{command_id}/status",
        json={
            "desktop_device_id": "desktop-b",
            "pairing_id": pairing_id,
            "route_token": route_token,
            "host_instance_id": "desktop-host-b",
            "status": "running",
        },
    )
    assert running_response.status_code == 200
    assert running_response.json()["status"] == "running"
    assert running_response.json()["started_at"]

    completed_response = await auth_client.post(
        f"/api/v1/sync/remote-control/commands/{command_id}/status",
        json={
            "desktop_device_id": "desktop-b",
            "pairing_id": pairing_id,
            "route_token": route_token,
            "host_instance_id": "desktop-host-b",
            "status": "completed",
            "result_summary": {"ok": True, "route_token": "must-redact-result"},
        },
    )
    assert completed_response.status_code == 200
    completed = completed_response.json()
    assert completed["status"] == "completed"
    assert completed["completed_at"]

    stored_command = (
        await db_session.execute(select(RemoteControlCommand).where(RemoteControlCommand.id == command_id))
    ).scalar_one()
    assert stored_command.result_summary == {"ok": True, "route_token": "[REDACTED]"}

    cancel_response = await auth_client.post(
        f"/api/v1/sync/remote-control/commands/{command_id}/cancel",
        json={"reason": "too late"},
    )
    assert cancel_response.status_code == 409
    assert _detail(cancel_response)["code"] == "remote_control_command_not_cancellable"

    audit = await auth_client.get("/api/v1/sync/remote-control/audit-events")
    reason_codes = [item["reason_code"] for item in audit.json()["items"]]
    assert "claimed" in reason_codes
    assert "running" in reason_codes
    assert "completed" in reason_codes
    assert "must-redact-result" not in str(audit.json())
