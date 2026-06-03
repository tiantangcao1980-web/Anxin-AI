"""案源市场——撤回投标端点测试

覆盖：
- 投标人撤回成功（状态 -> withdrawn，bid_count 回滚）
- 非投标人撤回返回 403
- 非法状态（已接受）撤回返回 409
"""

import pytest

from src.models.case_market import (
    BidStatus,
    CaseRequest,
    LawyerBid,
    RequestStatus,
)
from src.models.user import User

from .conftest import create_auth_headers


async def _create_lawyer(db_session, test_organization, email: str, name: str) -> User:
    lawyer = User(
        email=email,
        name=name,
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
        role="platform_lawyer",
    )
    db_session.add(lawyer)
    await db_session.flush()
    return lawyer


@pytest.mark.asyncio
async def test_withdraw_bid_success(
    client,
    db_session,
    test_user,
    test_organization,
):
    lawyer = await _create_lawyer(
        db_session, test_organization, "withdraw-lawyer@example.com", "撤回律师"
    )

    req = CaseRequest(
        user_id=test_user.id,
        org_id=test_organization.id,
        title="撤回投标测试需求",
        description="用于验证撤回投标的需求。",
        legal_area="contract",
        status=RequestStatus.PUBLISHED,
        bid_count=1,
    )
    db_session.add(req)
    await db_session.flush()

    bid = LawyerBid(
        case_request_id=req.id,
        lawyer_id=lawyer.id,
        proposal="我可以处理该需求",
        quoted_price=5000,
        status=BidStatus.PENDING,
    )
    db_session.add(bid)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/case-market/bids/{bid.id}/withdraw",
        headers=create_auth_headers(lawyer),
    )

    await db_session.refresh(bid)
    await db_session.refresh(req)

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert payload["data"]["status"] == BidStatus.WITHDRAWN.value
    assert bid.status == BidStatus.WITHDRAWN
    assert req.bid_count == 0


@pytest.mark.asyncio
async def test_withdraw_bid_forbidden_for_non_bidder(
    client,
    db_session,
    test_user,
    test_organization,
):
    bidder = await _create_lawyer(
        db_session, test_organization, "real-bidder@example.com", "真实投标人"
    )
    other_lawyer = await _create_lawyer(
        db_session, test_organization, "other-lawyer@example.com", "他人律师"
    )

    req = CaseRequest(
        user_id=test_user.id,
        org_id=test_organization.id,
        title="越权撤回测试需求",
        description="用于验证非投标人无法撤回。",
        legal_area="contract",
        status=RequestStatus.PUBLISHED,
        bid_count=1,
    )
    db_session.add(req)
    await db_session.flush()

    bid = LawyerBid(
        case_request_id=req.id,
        lawyer_id=bidder.id,
        proposal="我是投标人",
        status=BidStatus.PENDING,
    )
    db_session.add(bid)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/case-market/bids/{bid.id}/withdraw",
        headers=create_auth_headers(other_lawyer),
    )

    await db_session.refresh(bid)
    await db_session.refresh(req)

    assert response.status_code == 403
    assert "无权撤回" in response.json()["detail"]
    assert bid.status == BidStatus.PENDING
    assert req.bid_count == 1


@pytest.mark.asyncio
async def test_withdraw_bid_conflict_when_already_accepted(
    client,
    db_session,
    test_user,
    test_organization,
):
    lawyer = await _create_lawyer(
        db_session, test_organization, "accepted-lawyer@example.com", "已接受律师"
    )

    req = CaseRequest(
        user_id=test_user.id,
        org_id=test_organization.id,
        title="已接受投标撤回测试",
        description="用于验证已接受投标不可撤回。",
        legal_area="contract",
        status=RequestStatus.MATCHED,
        bid_count=1,
    )
    db_session.add(req)
    await db_session.flush()

    bid = LawyerBid(
        case_request_id=req.id,
        lawyer_id=lawyer.id,
        proposal="已被接受的投标",
        status=BidStatus.ACCEPTED,
    )
    db_session.add(bid)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/case-market/bids/{bid.id}/withdraw",
        headers=create_auth_headers(lawyer),
    )

    await db_session.refresh(bid)

    assert response.status_code == 409
    assert "不可撤回" in response.json()["detail"]
    assert bid.status == BidStatus.ACCEPTED
