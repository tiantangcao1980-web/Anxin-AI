"""SkillGovernance API regressions for governed Skill lifecycle operations."""

import pytest

from src.services.skill_evolution_service import REQUIRED_SKILL_EVAL_CHECKS


def passing_checks() -> dict[str, bool]:
    return dict.fromkeys(REQUIRED_SKILL_EVAL_CHECKS, True)


@pytest.mark.asyncio
async def test_skill_governance_api_requires_auth(client):
    response = await client.post(
        "/api/v1/skill-governance/proposals",
        json={
            "skill_name": "contract-review",
            "current_version": "1.0.0",
            "proposed_version": "1.1.0",
            "source": "api:proposal",
        },
    )

    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_skill_governance_api_round_trip_and_audit_export(auth_client, admin_auth_client):
    created = await auth_client.post(
        "/api/v1/skill-governance/proposals",
        json={
            "skill_name": "contract-review",
            "current_version": "1.0.0",
            "proposed_version": "1.1.0",
            "source": "failed_case:case-1",
            "risk_level": "high",
        },
    )

    assert created.status_code == 200
    body = created.json()
    assert body["code"] == 200
    proposal_id = body["data"]["id"]
    assert body["data"]["status"] == "draft"

    before_release = await auth_client.get(
        "/api/v1/skill-governance/enabled",
        params={"skill_name": "contract-review", "version": "1.1.0"},
    )
    assert before_release.status_code == 200
    assert before_release.json()["data"]["enabled_version"] == "1.0.0"
    assert before_release.json()["data"]["enabled"] is False

    evaluated = await admin_auth_client.post(
        f"/api/v1/skill-governance/proposals/{proposal_id}/eval",
        json={"checks": passing_checks()},
    )
    approved = await admin_auth_client.post(f"/api/v1/skill-governance/proposals/{proposal_id}/approve")
    released = await admin_auth_client.post(
        f"/api/v1/skill-governance/proposals/{proposal_id}/gray-release",
        json={"percentage": 100},
    )
    enabled = await auth_client.get(
        "/api/v1/skill-governance/enabled",
        params={"skill_name": "contract-review", "version": "1.1.0"},
    )

    assert evaluated.status_code == 200
    assert evaluated.json()["data"]["status"] == "evaluated"
    assert approved.status_code == 200
    assert approved.json()["data"]["status"] == "approved"
    assert released.status_code == 200
    assert released.json()["data"]["status"] == "gray_released"
    assert enabled.status_code == 200
    assert enabled.json()["data"]["enabled_version"] == "1.1.0"
    assert enabled.json()["data"]["enabled"] is True

    audit_response = await auth_client.get(f"/api/v1/skill-governance/proposals/{proposal_id}/audit-events")
    export_response = await auth_client.get(f"/api/v1/skill-governance/proposals/{proposal_id}/audit-export")

    assert audit_response.status_code == 200
    assert [item["reason_code"] for item in audit_response.json()["data"]["items"]] == [
        "draft_created",
        "eval_passed",
        "approved",
        "gray_released",
    ]
    assert export_response.status_code == 200
    export_body = export_response.json()
    assert export_body["data"]["schema_version"] == "skill_governance_audit_export.v1"
    assert export_body["data"]["proposal"]["id"] == proposal_id
    assert export_body["data"]["total"] == 4
    assert "raw_token" not in str(export_body).lower()
    assert "api_key" not in str(export_body).lower()

    rolled_back = await admin_auth_client.post(
        f"/api/v1/skill-governance/proposals/{proposal_id}/rollback",
        json={"reason": "privacy regression"},
    )
    after_rollback = await auth_client.get(
        "/api/v1/skill-governance/enabled",
        params={"skill_name": "contract-review", "version": "1.0.0"},
    )

    assert rolled_back.status_code == 200
    assert rolled_back.json()["data"]["status"] == "rolled_back"
    assert after_rollback.json()["data"]["enabled_version"] == "1.0.0"
    assert after_rollback.json()["data"]["enabled"] is True


@pytest.mark.asyncio
async def test_skill_governance_api_employee_can_propose_but_not_administer(auth_client):
    created = await auth_client.post(
        "/api/v1/skill-governance/proposals",
        json={
            "skill_name": "tax-risk",
            "current_version": "2.0.0",
            "proposed_version": "2.1.0",
            "source": "feedback:fb-1",
        },
    )
    proposal_id = created.json()["data"]["id"]

    forbidden_eval = await auth_client.post(
        f"/api/v1/skill-governance/proposals/{proposal_id}/eval",
        json={"checks": passing_checks()},
    )
    visible = await auth_client.get(f"/api/v1/skill-governance/proposals/{proposal_id}")

    assert forbidden_eval.status_code == 200
    assert forbidden_eval.json()["code"] == 403
    assert visible.status_code == 200
    assert visible.json()["data"]["status"] == "draft"


@pytest.mark.asyncio
async def test_skill_governance_api_regular_user_only_lists_own_proposals(auth_client, admin_auth_client):
    own = await auth_client.post(
        "/api/v1/skill-governance/proposals",
        json={
            "skill_name": "labor-dispute",
            "current_version": "1.0.0",
            "proposed_version": "1.1.0",
            "source": "feedback:own",
        },
    )
    admin_created = await admin_auth_client.post(
        "/api/v1/skill-governance/proposals",
        json={
            "skill_name": "external-mcp",
            "proposed_version": "0.1.0",
            "source": "admin:proposal",
        },
    )

    own_list = await auth_client.get("/api/v1/skill-governance/proposals")
    admin_list = await admin_auth_client.get("/api/v1/skill-governance/proposals")

    assert own.status_code == 200
    assert admin_created.status_code == 200
    own_ids = {item["id"] for item in own_list.json()["data"]["items"]}
    admin_ids = {item["id"] for item in admin_list.json()["data"]["items"]}
    assert own.json()["data"]["id"] in own_ids
    assert admin_created.json()["data"]["id"] not in own_ids
    assert {own.json()["data"]["id"], admin_created.json()["data"]["id"]} <= admin_ids


@pytest.mark.asyncio
async def test_skill_connector_config_api_masks_credentials_and_preserves_saved_keys(admin_auth_client):
    created = await admin_auth_client.post(
        "/api/v1/skill-governance/connectors",
        json={
            "skill_name": "contract-review",
            "connector_name": "court-data",
            "connector_type": "http_api",
            "endpoint_url": "https://court.example.test/api",
            "auth_type": "api_key",
            "credentials": {
                "API_KEY": "sk-skill-connector-secret",
                "CLIENT_SECRET": "client-secret-value",
            },
            "is_enabled": True,
        },
    )

    assert created.status_code == 200
    body = created.json()
    assert body["code"] == 200
    connector_id = body["data"]["id"]
    assert body["data"]["credential_keys"] == ["API_KEY", "CLIENT_SECRET"]
    assert "credentials" not in body["data"]
    assert "encrypted_fields" not in body["data"]
    assert "sk-skill-connector-secret" not in str(body)
    assert "client-secret-value" not in str(body)

    metadata_update = await admin_auth_client.put(
        f"/api/v1/skill-governance/connectors/{connector_id}",
        json={"endpoint_url": "https://court.example.test/v2", "is_enabled": False},
    )
    listed = await admin_auth_client.get(
        "/api/v1/skill-governance/connectors",
        params={"skill_name": "contract-review"},
    )

    assert metadata_update.status_code == 200
    assert metadata_update.json()["data"]["credential_keys"] == ["API_KEY", "CLIENT_SECRET"]
    assert metadata_update.json()["data"]["endpoint_url"] == "https://court.example.test/v2"
    assert metadata_update.json()["data"]["is_enabled"] is False

    cleared_endpoint = await admin_auth_client.put(
        f"/api/v1/skill-governance/connectors/{connector_id}",
        json={"endpoint_url": None},
    )
    assert cleared_endpoint.status_code == 200
    assert cleared_endpoint.json()["data"]["endpoint_url"] is None
    assert cleared_endpoint.json()["data"]["credential_keys"] == ["API_KEY", "CLIENT_SECRET"]

    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 1
    assert listed.json()["data"]["items"][0]["credential_keys"] == ["API_KEY", "CLIENT_SECRET"]
    assert "sk-skill-connector-secret" not in str(listed.json())


@pytest.mark.asyncio
async def test_skill_connector_config_api_requires_admin_and_supports_replace_delete(auth_client, admin_auth_client):
    forbidden = await auth_client.post(
        "/api/v1/skill-governance/connectors",
        json={
            "skill_name": "tax-risk",
            "connector_name": "tax-bureau",
            "credentials": {"API_KEY": "sk-should-not-save"},
        },
    )

    assert forbidden.status_code == 200
    assert forbidden.json()["code"] == 403

    created = await admin_auth_client.post(
        "/api/v1/skill-governance/connectors",
        json={
            "skill_name": "tax-risk",
            "connector_name": "tax-bureau",
            "credentials": {"API_KEY": "sk-original-secret"},
        },
    )
    connector_id = created.json()["data"]["id"]
    replaced = await admin_auth_client.put(
        f"/api/v1/skill-governance/connectors/{connector_id}",
        json={"credentials": {"TOKEN": "replacement-token"}},
    )
    deleted = await admin_auth_client.delete(f"/api/v1/skill-governance/connectors/{connector_id}")
    listed = await admin_auth_client.get("/api/v1/skill-governance/connectors", params={"skill_name": "tax-risk"})

    assert replaced.status_code == 200
    assert replaced.json()["data"]["credential_keys"] == ["TOKEN"]
    assert "replacement-token" not in str(replaced.json())
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted"] is True
    assert listed.json()["data"]["total"] == 0
