import pytest


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
async def test_remote_control_pairing_rejects_fake_success_until_store_exists(auth_client):
    response = await auth_client.post(
        "/api/v1/sync/remote-control/pairings",
        json={
            "mobile_device_id": "mobile-a",
            "desktop_device_id": "desktop-a",
            "requested_scopes": ["view_status"],
            "privacy_mode": "hybrid",
        },
    )

    assert response.status_code == 409
    detail = _detail(response)
    assert detail["code"] == "remote_control_pairing_store_missing"
    assert "假成功" in detail["message"]


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
async def test_remote_control_command_rejects_until_queue_and_audit_exist(auth_client):
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

    assert response.status_code == 409
    detail = _detail(response)
    assert detail["code"] == "remote_control_command_queue_missing"
    assert "审计" in detail["message"]
