from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.security import create_access_token
from src.models.approval import Approval, ApprovalStatus
from src.models.investigation import Investigation
from src.models.lawyer_matching import Delegation, DelegationStatus, LawyerProfile
from src.models.user import Organization, User


@pytest_asyncio.fixture
async def outsider_user_with_client(db_session):
    org = Organization(id=str(uuid4()), name="外部业务组织")
    db_session.add(org)
    await db_session.flush()

    user = User(
        id=str(uuid4()),
        email=f"biz-outsider-{uuid4().hex[:8]}@example.com",
        name="业务外部用户",
        hashed_password="hashed_password",
        org_id=org.id,
        is_active=True,
        role="member",
    )
    db_session.add(user)
    await db_session.flush()

    from src.api.main import app
    from src.core.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(user_id=user.id)
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield user, ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_approval_requires_current_approver(auth_client, db_session, test_user, outsider_user_with_client):
    outsider_user, outsider_client = outsider_user_with_client

    approval = Approval(
        title="审批测试",
        approval_type="custom",
        status=ApprovalStatus.pending.value,
        requester_id=str(test_user.id),
        approver_id=str(test_user.id),
        org_id=str(test_user.org_id),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(approval)
    await db_session.flush()

    forbidden = await outsider_client.put(f"/api/v1/approvals/{approval.id}/approve", json={"comment": "越权审批"})
    assert forbidden.status_code == 200
    assert forbidden.json()["code"] == 403

    allowed = await auth_client.put(f"/api/v1/approvals/{approval.id}/approve", json={"comment": "正常审批"})
    assert allowed.status_code == 200
    assert allowed.json()["code"] == 200


@pytest.mark.asyncio
async def test_investigation_detail_requires_owner(auth_client, db_session, test_user, outsider_user_with_client):
    outsider_user, outsider_client = outsider_user_with_client

    investigation = Investigation(
        id=str(uuid4()),
        company_name="测试企业",
        user_id=str(test_user.id),
        status="completed",
        basic_info={"name": "测试企业"},
    )
    db_session.add(investigation)
    await db_session.flush()

    forbidden = await outsider_client.get(f"/api/v1/due-diligence/investigations/{investigation.id}")
    assert forbidden.status_code == 200
    assert forbidden.json()["code"] != 200

    allowed = await auth_client.get(f"/api/v1/due-diligence/investigations/{investigation.id}")
    assert allowed.status_code == 200
    assert allowed.json()["code"] == 200


@pytest.mark.asyncio
async def test_review_rejects_duplicate_delegation_review(client, db_session, test_user, test_organization):
    lawyer_user = User(
        id=str(uuid4()),
        email=f"dup-lawyer-{uuid4().hex[:8]}@example.com",
        name="重复评价律师",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
        role="platform_lawyer",
    )
    db_session.add(lawyer_user)
    await db_session.flush()

    lawyer_profile = LawyerProfile(
        user_id=lawyer_user.id,
        real_name="重复评价律师",
        license_number="LIC-REVIEW-DUP-001",
        years_of_practice=10,
        is_verified=True,
        specializations=["corporate"],
        rating=5.0,
        total_reviews=0,
    )
    db_session.add(lawyer_profile)
    await db_session.flush()

    delegation = Delegation(
        id=str(uuid4()),
        client_id=test_user.id,
        lawyer_id=lawyer_user.id,
        title="重复评价委托",
        status=DelegationStatus.COMPLETED.value,
    )
    db_session.add(delegation)
    await db_session.flush()

    headers = {"Authorization": f"Bearer {create_access_token(user_id=test_user.id)}"}

    first = await client.post(
        f"/api/v1/lawyer/lawyers/{lawyer_profile.id}/reviews",
        headers=headers,
        json={"rating": 5, "content": "第一次评价", "delegation_id": delegation.id},
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/lawyer/lawyers/{lawyer_profile.id}/reviews",
        headers=headers,
        json={"rating": 5, "content": "第二次评价", "delegation_id": delegation.id},
    )
    assert second.status_code == 400
    assert "重复提交" in second.json()["detail"]
