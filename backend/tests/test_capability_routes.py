"""Capability route token broker regressions."""

from datetime import UTC, datetime, timedelta

from src.services.capability_route_service import CapabilityRouteService


def test_route_token_stores_only_hash_and_validates_scope():
    service = CapabilityRouteService()

    issued = service.issue_route_token(
        route_id="mcp-approved-route",
        consumer_id="worker-1",
        scopes={"mcp:call", "knowledge:read"},
    )

    record = service.get_record_for_token(issued.token)
    decision = service.validate_route_token(issued.token, required_scope="mcp:call")

    assert issued.token.startswith("anxin_route_")
    assert record is not None
    assert record.token_hash != issued.token
    assert issued.token not in repr(record)
    assert decision.allowed is True
    assert decision.route_id == "mcp-approved-route"
    assert decision.consumer_id == "worker-1"


def test_revoked_route_token_fails_next_validation_and_audits():
    service = CapabilityRouteService()
    issued = service.issue_route_token(
        route_id="desktop-control-route",
        consumer_id="worker-2",
        scopes={"desktop:control"},
    )

    assert service.validate_route_token(issued.token, required_scope="desktop:control").allowed
    assert service.revoke_route_token(issued.token, reason="owner_revoked") is True
    after_revoke = service.validate_route_token(issued.token, required_scope="desktop:control")

    assert after_revoke.allowed is False
    assert after_revoke.reason_code == "route_token_revoked"
    assert [event.reason_code for event in service.get_audit_events()] == [
        "issued",
        "allowed",
        "revoked",
        "route_token_revoked",
    ]


def test_missing_scope_and_expired_route_token_fail_closed():
    service = CapabilityRouteService()
    issued_at = datetime(2026, 5, 8, tzinfo=UTC)
    issued = service.issue_route_token(
        route_id="limited-route",
        consumer_id="worker-3",
        scopes={"knowledge:read"},
        ttl_seconds=30,
        now=issued_at,
    )

    missing_scope = service.validate_route_token(issued.token, required_scope="mcp:call", now=issued_at)
    expired = service.validate_route_token(
        issued.token,
        required_scope="knowledge:read",
        now=issued_at + timedelta(seconds=31),
    )

    assert missing_scope.allowed is False
    assert missing_scope.reason_code == "missing_route_scope"
    assert expired.allowed is False
    assert expired.reason_code == "route_token_expired"


def test_unknown_or_missing_route_token_fails_closed():
    service = CapabilityRouteService()

    missing = service.validate_route_token(None, required_scope="mcp:call")
    unknown = service.validate_route_token("anxin_route_not-real", required_scope="mcp:call")

    assert missing.allowed is False
    assert missing.reason_code == "missing_route_token"
    assert unknown.allowed is False
    assert unknown.reason_code == "unknown_route_token"
