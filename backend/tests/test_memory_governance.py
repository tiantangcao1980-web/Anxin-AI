"""Memory governance regressions for enterprise agent workspaces."""

import pytest

from src.services.memory_layer import (
    MemoryGovernanceContext,
    MemoryLayer,
    evaluate_memory_write,
)


@pytest.mark.asyncio
async def test_governed_session_artifact_blocks_local_and_top_secret_writes():
    memory = MemoryLayer()

    local = await memory.set_governed_session_artifact(
        "session-a",
        "summary",
        {"finding": "should not persist"},
        MemoryGovernanceContext(
            org_id="org-a",
            user_id="user-a",
            privacy_mode="local",
            consent=True,
        ),
    )
    top_secret = await memory.set_governed_session_artifact(
        "session-a",
        "summary",
        {"finding": "should not persist either"},
        MemoryGovernanceContext(
            org_id="org-a",
            user_id="user-a",
            privacy_mode="top_secret",
            consent=True,
        ),
    )

    assert local.allowed is False
    assert local.reason_code == "privacy_mode_blocks_memory"
    assert top_secret.allowed is False
    assert top_secret.reason_code == "privacy_mode_blocks_memory"
    assert await memory.get_session_artifact("session-a", "summary") is None


@pytest.mark.asyncio
async def test_governed_session_artifact_requires_scope_and_consent():
    memory = MemoryLayer()

    missing_org = await memory.set_governed_session_artifact(
        "session-b",
        "summary",
        {"finding": "missing org"},
        MemoryGovernanceContext(
            org_id=None,
            user_id="user-a",
            privacy_mode="hybrid",
            consent=True,
        ),
    )
    missing_user = evaluate_memory_write(
        MemoryGovernanceContext(
            org_id="org-a",
            user_id=None,
            privacy_mode="hybrid",
            consent=True,
        )
    )
    missing_consent = evaluate_memory_write(
        MemoryGovernanceContext(
            org_id="org-a",
            user_id="user-a",
            privacy_mode="hybrid",
            consent=False,
        )
    )

    assert missing_org.allowed is False
    assert missing_org.reason_code == "missing_org_scope"
    assert missing_user.allowed is False
    assert missing_user.reason_code == "missing_user_scope"
    assert missing_consent.allowed is False
    assert missing_consent.reason_code == "memory_consent_required"
    assert await memory.get_session_artifact("session-b", "summary") is None


@pytest.mark.asyncio
async def test_governed_session_artifact_redacts_sensitive_payload_and_records_policy():
    memory = MemoryLayer()

    decision = await memory.set_governed_session_artifact(
        "session-c",
        "summary",
        {
            "finding": "approved workspace summary",
            "api_key": "should-never-persist",
            "nested": {"client_secret": "also-secret", "safe": "ok"},
            "items": [{"raw_token": "token-value", "label": "safe"}],
        },
        MemoryGovernanceContext(
            org_id="org-a",
            user_id="user-a",
            privacy_mode="hybrid",
            consent=True,
            purpose="agent_workspace_artifact",
            retention="session",
        ),
    )
    artifact = await memory.get_session_artifact("session-c", "summary")

    assert decision.allowed is True
    assert decision.reason_code == "allowed"
    assert artifact is not None
    assert artifact == {
        "data": {
            "finding": "approved workspace summary",
            "api_key": "[redacted]",
            "nested": {"client_secret": "[redacted]", "safe": "ok"},
            "items": [{"raw_token": "[redacted]", "label": "safe"}],
        },
        "governance": {
            "org_id": "org-a",
            "user_id": "user-a",
            "privacy_mode": "hybrid",
            "purpose": "agent_workspace_artifact",
            "retention": "session",
            "consent": "true",
        },
        "recorded_at": artifact["recorded_at"],
    }
    assert "should-never-persist" not in str(artifact)
    assert "also-secret" not in str(artifact)
    assert "token-value" not in str(artifact)
