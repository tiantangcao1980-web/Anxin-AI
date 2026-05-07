import pytest

from src.api.routes.cli import _api_keys, _rate_limits


@pytest.fixture(autouse=True)
def reset_cli_state():
    _api_keys.clear()
    _rate_limits.clear()
    yield
    _api_keys.clear()
    _rate_limits.clear()


@pytest.mark.asyncio
async def test_cli_keys_create_and_list_round_trip(client):
    response = await client.post(
        "/api/v1/cli/keys",
        json={"name": "ci-key", "scopes": ["read", "chat"], "expires_days": 30},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["key_id"]
    assert payload["api_key"].startswith("anxin_cli_")
    assert payload["created_at"]

    listed = await client.get("/api/v1/cli/keys")

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


@pytest.mark.asyncio
async def test_cli_execute_rejects_missing_scope(client):
    create = await client.post(
        "/api/v1/cli/keys",
        json={"name": "read-only", "scopes": ["read"], "expires_days": 7},
    )
    api_key = create.json()["api_key"]

    response = await client.post(
        "/api/v1/cli/execute",
        headers={"X-API-Key": api_key},
        json={"command": "draft", "args": {"content": "合同草稿"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert "缺少 'chat' 权限" in payload["error"]
