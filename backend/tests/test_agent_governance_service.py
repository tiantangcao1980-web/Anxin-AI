"""Database-backed Agent governance service regressions."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.models import AgentAuditEvent, CapabilityRoute, CapabilityRouteTokenLease, Organization
from src.models.base import Base
from src.services.agent_governance_service import AgentGovernanceService


@pytest.mark.asyncio
async def test_route_token_lease_persists_hash_only_and_validates_after_service_restart(db_session, test_organization):
    service = AgentGovernanceService(db_session)
    await service.create_capability_route(
        org_id=test_organization.id,
        route_key="mcp-approved-route",
        route_type="mcp",
        allowed_consumers=["worker-1"],
        allowed_scopes=["mcp:call", "knowledge:read"],
    )

    issued = await service.issue_route_token(
        org_id=test_organization.id,
        route_key="mcp-approved-route",
        consumer_id="worker-1",
        requested_scopes=["mcp:call"],
    )
    restarted_service = AgentGovernanceService(db_session)
    decision = await restarted_service.validate_route_token(
        org_id=test_organization.id,
        raw_token=issued.token,
        required_scope="mcp:call",
    )

    leases = (
        await db_session.execute(
            select(CapabilityRouteTokenLease).where(CapabilityRouteTokenLease.org_id == test_organization.id)
        )
    ).scalars().all()
    audits = (
        await db_session.execute(select(AgentAuditEvent).where(AgentAuditEvent.org_id == test_organization.id))
    ).scalars().all()

    assert issued.allowed is True
    assert issued.token is not None
    assert issued.token.startswith("anxin_route_")
    assert decision.allowed is True
    assert decision.consumer_id == "worker-1"
    assert len(leases) == 1
    assert leases[0].token_hash != issued.token
    assert issued.token not in repr(leases[0])
    assert all(issued.token not in str(event.metadata_json) for event in audits)
    assert [event.reason_code for event in audits] == ["issued", "allowed"]


@pytest.mark.asyncio
async def test_route_revocation_refreshes_stale_worker_session_across_processes(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'agent-governance.db'}", echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    org_id = str(uuid4())
    route_key = "approved-materials"
    consumer_id = "legal-advisor-worker"

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_factory() as issuer_session:
            issuer_session.add(Organization(id=org_id, name="Cross Process Rehearsal Org"))
            await issuer_session.flush()
            issuer = AgentGovernanceService(issuer_session)
            await issuer.create_capability_route(
                org_id=org_id,
                route_key=route_key,
                route_type="mcp",
                provider="local-mock-mcp",
                risk_level="l3",
                allowed_consumers=[consumer_id],
                allowed_scopes=["mcp:call"],
                policy={"api_key": "should-never-persist"},
            )
            issued = await issuer.issue_route_token(
                org_id=org_id,
                route_key=route_key,
                consumer_id=consumer_id,
                requested_scopes=["mcp:call"],
                actor_type="issuer_process",
            )
            await issuer_session.commit()

        async with session_factory() as worker_session, session_factory() as admin_session:
            worker = AgentGovernanceService(worker_session)
            first = await worker.validate_route_token(
                org_id=org_id,
                raw_token=issued.token,
                required_scope="mcp:call",
                required_route_key=route_key,
                consumer_id=consumer_id,
                actor_type="worker_process",
            )
            await worker_session.commit()

            admin = AgentGovernanceService(admin_session)
            revoked = await admin.revoke_capability_route(
                org_id=org_id,
                route_key=route_key,
                reason="admin_cross_process_rehearsal",
                actor_type="admin_control_plane",
            )
            await admin_session.commit()

            second = await worker.validate_route_token(
                org_id=org_id,
                raw_token=issued.token,
                required_scope="mcp:call",
                required_route_key=route_key,
                consumer_id=consumer_id,
                actor_type="worker_process",
            )
            await worker_session.commit()

        async with session_factory() as verifier_session:
            lease = (
                await verifier_session.execute(
                    select(CapabilityRouteTokenLease).where(CapabilityRouteTokenLease.org_id == org_id)
                )
            ).scalar_one()
            route = (
                await verifier_session.execute(select(CapabilityRoute).where(CapabilityRoute.org_id == org_id))
            ).scalar_one()
            audits = (
                await verifier_session.execute(
                    select(AgentAuditEvent)
                    .where(AgentAuditEvent.org_id == org_id)
                    .order_by(AgentAuditEvent.created_at.asc(), AgentAuditEvent.id.asc())
                )
            ).scalars().all()

        assert issued.allowed is True
        assert issued.token is not None
        assert first.allowed is True
        assert revoked.revoked is True
        assert revoked.revoked_lease_count == 1
        assert second.allowed is False
        assert second.reason_code == "capability_route_revoked"
        assert route.revoked_reason == "admin_cross_process_rehearsal"
        assert lease.revoked_reason == "admin_cross_process_rehearsal"
        assert lease.token_hash != issued.token
        assert issued.token not in repr(lease)
        assert issued.token not in repr([event.metadata_json for event in audits])
        assert [event.reason_code for event in audits] == [
            "issued",
            "allowed",
            "revoked",
            "capability_route_revoked",
        ]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_route_token_validation_is_org_scoped(db_session, test_organization):
    other_org = Organization(id=str(uuid4()), name="Other Org")
    db_session.add(other_org)
    await db_session.flush()
    service = AgentGovernanceService(db_session)
    await service.create_capability_route(
        org_id=test_organization.id,
        route_key="desktop-control",
        route_type="desktop-control",
        allowed_consumers=["worker-1"],
        allowed_scopes=["desktop:control"],
    )
    issued = await service.issue_route_token(
        org_id=test_organization.id,
        route_key="desktop-control",
        consumer_id="worker-1",
        requested_scopes=["desktop:control"],
    )

    wrong_org_decision = await service.validate_route_token(
        org_id=other_org.id,
        raw_token=issued.token,
        required_scope="desktop:control",
    )

    assert wrong_org_decision.allowed is False
    assert wrong_org_decision.reason_code == "unknown_route_token"


@pytest.mark.asyncio
async def test_revoked_capability_route_fails_next_validation_and_audits(db_session, test_organization):
    service = AgentGovernanceService(db_session)
    await service.create_capability_route(
        org_id=test_organization.id,
        route_key="high-risk-mcp",
        route_type="mcp",
        allowed_consumers=["worker-2"],
        allowed_scopes=["mcp:call"],
    )
    issued = await service.issue_route_token(
        org_id=test_organization.id,
        route_key="high-risk-mcp",
        consumer_id="worker-2",
        requested_scopes=["mcp:call"],
    )

    before = await service.validate_route_token(
        org_id=test_organization.id,
        raw_token=issued.token,
        required_scope="mcp:call",
    )
    revocation = await service.revoke_capability_route(
        org_id=test_organization.id,
        route_key="high-risk-mcp",
        reason="owner_revoked",
    )
    after = await service.validate_route_token(
        org_id=test_organization.id,
        raw_token=issued.token,
        required_scope="mcp:call",
    )

    lease = (
        await db_session.execute(
            select(CapabilityRouteTokenLease).where(CapabilityRouteTokenLease.org_id == test_organization.id)
        )
    ).scalar_one()
    audits = (
        await db_session.execute(
            select(AgentAuditEvent)
            .where(AgentAuditEvent.org_id == test_organization.id)
            .order_by(AgentAuditEvent.created_at)
        )
    ).scalars().all()

    assert before.allowed is True
    assert revocation.revoked is True
    assert revocation.revoked_lease_count == 1
    assert after.allowed is False
    assert after.reason_code == "capability_route_revoked"
    assert lease.revoked_reason == "owner_revoked"
    assert [event.reason_code for event in audits] == [
        "issued",
        "allowed",
        "revoked",
        "capability_route_revoked",
    ]


@pytest.mark.asyncio
async def test_issue_route_token_enforces_consumer_and_scope(db_session, test_organization):
    service = AgentGovernanceService(db_session)
    await service.create_capability_route(
        org_id=test_organization.id,
        route_key="limited-route",
        route_type="browser",
        allowed_consumers=["worker-allowed"],
        allowed_scopes=["browser:read"],
    )

    bad_consumer = await service.issue_route_token(
        org_id=test_organization.id,
        route_key="limited-route",
        consumer_id="worker-denied",
        requested_scopes=["browser:read"],
    )
    bad_scope = await service.issue_route_token(
        org_id=test_organization.id,
        route_key="limited-route",
        consumer_id="worker-allowed",
        requested_scopes=["browser:write"],
    )

    # 按 org_id 过滤，避免与全运行时其它测试在同 SQLite memory DB 中的 lease 残留冲突
    # （test_session 是 StaticPool + 共享 in-memory DB；其它测试虽各自 rollback，但
    # 若 autoflush 时序不对仍可能跨测试可见）
    leases = (
        await db_session.execute(
            select(CapabilityRouteTokenLease).where(
                CapabilityRouteTokenLease.org_id == test_organization.id
            )
        )
    ).scalars().all()

    assert bad_consumer.allowed is False
    assert bad_consumer.reason_code == "consumer_not_allowed"
    assert bad_scope.allowed is False
    assert bad_scope.reason_code == "missing_route_scope"
    assert leases == []


@pytest.mark.asyncio
async def test_validate_route_token_enforces_bound_consumer(db_session, test_organization):
    service = AgentGovernanceService(db_session)
    await service.create_capability_route(
        org_id=test_organization.id,
        route_key="bound-consumer-route",
        route_type="mcp",
        allowed_consumers=["worker-bound"],
        allowed_scopes=["mcp:call"],
    )
    issued = await service.issue_route_token(
        org_id=test_organization.id,
        route_key="bound-consumer-route",
        consumer_id="worker-bound",
        requested_scopes=["mcp:call"],
    )

    allowed = await service.validate_route_token(
        org_id=test_organization.id,
        raw_token=issued.token,
        required_scope="mcp:call",
        consumer_id="worker-bound",
    )
    denied = await service.validate_route_token(
        org_id=test_organization.id,
        raw_token=issued.token,
        required_scope="mcp:call",
        consumer_id="worker-other",
    )

    assert allowed.allowed is True
    assert denied.allowed is False
    assert denied.reason_code == "route_token_consumer_mismatch"


@pytest.mark.asyncio
async def test_expired_route_token_fails_closed(db_session, test_organization):
    issued_at = datetime(2026, 5, 8, tzinfo=UTC)
    service = AgentGovernanceService(db_session)
    await service.create_capability_route(
        org_id=test_organization.id,
        route_key="short-route",
        route_type="skill",
        allowed_consumers=["worker-1"],
        allowed_scopes=["skill:run"],
        token_ttl_seconds=30,
    )
    issued = await service.issue_route_token(
        org_id=test_organization.id,
        route_key="short-route",
        consumer_id="worker-1",
        requested_scopes=["skill:run"],
        now=issued_at,
    )

    expired = await service.validate_route_token(
        org_id=test_organization.id,
        raw_token=issued.token,
        required_scope="skill:run",
        now=issued_at + timedelta(seconds=31),
    )

    assert expired.allowed is False
    assert expired.reason_code == "route_token_expired"


@pytest.mark.asyncio
async def test_update_capability_route_policy_sanitizes_policy_and_revokes_leases(db_session, test_organization):
    service = AgentGovernanceService(db_session)
    await service.create_capability_route(
        org_id=test_organization.id,
        route_key="org-mcp-admin",
        route_type="mcp",
        allowed_consumers=["admin-agent"],
        allowed_scopes=["mcp:call"],
        status="enabled",
        policy={"required_feature": "mcp_pack"},
    )
    issued = await service.issue_route_token(
        org_id=test_organization.id,
        route_key="org-mcp-admin",
        consumer_id="admin-agent",
        requested_scopes=["mcp:call"],
    )

    changed = await service.update_capability_route_policy(
        org_id=test_organization.id,
        route_key="org-mcp-admin",
        actor_user_id=None,
        status="disabled",
        allowed_consumers=["owner-agent"],
        allowed_scopes=["mcp:call", "mcp:admin"],
        risk_level="l4",
        token_ttl_seconds=7200,
        policy={
            "required_feature": "enterprise_agent_governance",
            "api_key": "should-never-persist",
            "nested": {"client_secret": "also-secret", "mode": "approval_required"},
        },
    )
    after = await service.validate_route_token(
        org_id=test_organization.id,
        raw_token=issued.token,
        required_scope="mcp:call",
        consumer_id="admin-agent",
    )
    route = (
        await db_session.execute(
            select(CapabilityRoute).where(
                CapabilityRoute.org_id == test_organization.id,
                CapabilityRoute.route_key == "org-mcp-admin",
            )
        )
    ).scalar_one()
    lease = (
        await db_session.execute(
            select(CapabilityRouteTokenLease).where(CapabilityRouteTokenLease.org_id == test_organization.id)
        )
    ).scalar_one()
    audits = (
        await db_session.execute(
            select(AgentAuditEvent)
            .where(AgentAuditEvent.org_id == test_organization.id)
            .order_by(AgentAuditEvent.created_at)
        )
    ).scalars().all()

    assert changed.allowed is True
    assert changed.revoked_lease_count == 1
    assert route.status == "disabled"
    assert route.allowed_consumers == ["owner-agent"]
    assert route.allowed_scopes == ["mcp:admin", "mcp:call"]
    assert route.risk_level == "l4"
    assert route.token_ttl_seconds == 3600
    assert route.policy == {
        "required_feature": "enterprise_agent_governance",
        "api_key": "[redacted]",
        "nested": {"client_secret": "[redacted]", "mode": "approval_required"},
    }
    assert lease.revoked_reason == "policy_disabled"
    assert after.allowed is False
    assert after.reason_code == "capability_route_disabled"
    assert "should-never-persist" not in str(route.policy)
    assert [event.reason_code for event in audits] == [
        "issued",
        "updated",
        "capability_route_disabled",
    ]
