import pytest

from src.models.lawyer_matching import (
    Consultation,
    ConsultationStatus,
    Delegation,
    DelegationStatus,
    LawyerProfile,
)
from src.models.review import LawyerReview
from src.models.user import User

from .conftest import create_auth_headers


@pytest.mark.asyncio
async def test_create_review_requires_real_service_relation(
    client,
    db_session,
    test_user,
    test_organization,
):
    lawyer_user = User(
        email="review-lawyer@example.com",
        name="被评价律师",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
        role="platform_lawyer",
    )
    db_session.add(lawyer_user)
    await db_session.flush()

    lawyer_profile = LawyerProfile(
        user_id=lawyer_user.id,
        real_name="被评价律师",
        license_number="LIC-REVIEW-001",
        years_of_practice=8,
        is_verified=True,
        specializations=["contract"],
    )
    db_session.add(lawyer_profile)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/lawyer/lawyers/{lawyer_profile.id}/reviews",
        headers=create_auth_headers(test_user),
        json={
            "rating": 5,
            "content": "非常专业",
        },
    )

    assert response.status_code == 400
    assert "真实咨询或委托记录" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_review_rejects_mismatched_consultation(
    client,
    db_session,
    test_user,
    test_organization,
):
    lawyer_user = User(
        email="matched-lawyer@example.com",
        name="匹配律师",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
        role="platform_lawyer",
    )
    other_lawyer_user = User(
        email="other-lawyer@example.com",
        name="其他律师",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
        role="platform_lawyer",
    )
    db_session.add_all([lawyer_user, other_lawyer_user])
    await db_session.flush()

    target_profile = LawyerProfile(
        user_id=lawyer_user.id,
        real_name="匹配律师",
        license_number="LIC-REVIEW-002",
        years_of_practice=5,
        is_verified=True,
        specializations=["labor"],
    )
    other_profile = LawyerProfile(
        user_id=other_lawyer_user.id,
        real_name="其他律师",
        license_number="LIC-REVIEW-003",
        years_of_practice=6,
        is_verified=True,
        specializations=["labor"],
    )
    db_session.add_all([target_profile, other_profile])
    await db_session.flush()

    consultation = Consultation(
        user_id=test_user.id,
        original_description="劳动争议咨询",
        anonymous_summary="匿名摘要",
        legal_domain="labor",
        status=ConsultationStatus.IN_PROGRESS.value,
        privacy_level=0,
        urgency="medium",
        matched_lawyer_id=other_lawyer_user.id,
    )
    db_session.add(consultation)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/lawyer/lawyers/{target_profile.id}/reviews",
        headers=create_auth_headers(test_user),
        json={
            "rating": 4,
            "content": "服务不错",
            "consultation_id": consultation.id,
        },
    )

    assert response.status_code == 400
    assert "咨询记录与律师档案不匹配" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_review_accepts_valid_delegation(
    client,
    db_session,
    test_user,
    test_organization,
):
    lawyer_user = User(
        email="delegation-lawyer@example.com",
        name="委托律师",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
        role="platform_lawyer",
    )
    db_session.add(lawyer_user)
    await db_session.flush()

    lawyer_profile = LawyerProfile(
        user_id=lawyer_user.id,
        real_name="委托律师",
        license_number="LIC-REVIEW-004",
        years_of_practice=10,
        is_verified=True,
        specializations=["corporate"],
        rating=5.0,
        total_reviews=0,
    )
    db_session.add(lawyer_profile)
    await db_session.flush()

    delegation = Delegation(
        client_id=test_user.id,
        lawyer_id=lawyer_user.id,
        title="公司治理委托",
        status=DelegationStatus.COMPLETED.value,
    )
    db_session.add(delegation)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/lawyer/lawyers/{lawyer_profile.id}/reviews",
        headers=create_auth_headers(test_user),
        json={
            "rating": 5,
            "content": "沟通专业，推进高效",
            "delegation_id": delegation.id,
        },
    )

    await db_session.refresh(lawyer_profile)

    assert response.status_code == 200
    payload = response.json()
    assert payload["rating"] == 5
    assert lawyer_profile.total_reviews == 1
    assert lawyer_profile.rating == 5.0


@pytest.mark.asyncio
async def test_reply_review_blocks_other_lawyer(
    client,
    db_session,
    test_user,
    test_organization,
):
    owner_lawyer = User(
        email="reply-owner@example.com",
        name="归属律师",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
        role="platform_lawyer",
    )
    outsider_lawyer = User(
        email="reply-outsider@example.com",
        name="外部律师",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
        role="platform_lawyer",
    )
    db_session.add_all([owner_lawyer, outsider_lawyer])
    await db_session.flush()

    owner_profile = LawyerProfile(
        user_id=owner_lawyer.id,
        real_name="归属律师",
        license_number="LIC-REPLY-001",
        years_of_practice=6,
        is_verified=True,
        specializations=["contract"],
    )
    outsider_profile = LawyerProfile(
        user_id=outsider_lawyer.id,
        real_name="外部律师",
        license_number="LIC-REPLY-002",
        years_of_practice=6,
        is_verified=True,
        specializations=["contract"],
    )
    db_session.add_all([owner_profile, outsider_profile])
    await db_session.flush()

    review = LawyerReview(
        lawyer_profile_id=owner_profile.id,
        reviewer_id=test_user.id,
        rating=4,
        content="回复权限测试",
    )
    db_session.add(review)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/lawyer/lawyers/reviews/{review.id}/reply",
        headers=create_auth_headers(outsider_lawyer),
        json={"content": "这不是我的评价"},
    )

    assert response.status_code == 403
    assert "只有该律师本人才能回复评价" in response.json()["detail"]


@pytest.mark.asyncio
async def test_reply_review_accepts_owner_lawyer(
    client,
    db_session,
    test_user,
    test_organization,
):
    owner_lawyer = User(
        email="reply-ok@example.com",
        name="可回复律师",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
        role="platform_lawyer",
    )
    db_session.add(owner_lawyer)
    await db_session.flush()

    owner_profile = LawyerProfile(
        user_id=owner_lawyer.id,
        real_name="可回复律师",
        license_number="LIC-REPLY-003",
        years_of_practice=9,
        is_verified=True,
        specializations=["corporate"],
    )
    db_session.add(owner_profile)
    await db_session.flush()

    review = LawyerReview(
        lawyer_profile_id=owner_profile.id,
        reviewer_id=test_user.id,
        rating=5,
        content="回复成功测试",
    )
    db_session.add(review)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/lawyer/lawyers/reviews/{review.id}/reply",
        headers=create_auth_headers(owner_lawyer),
        json={"content": "感谢认可，我们会继续跟进。"},
    )

    await db_session.refresh(review)

    assert response.status_code == 200
    payload = response.json()
    assert payload["reply_content"] == "感谢认可，我们会继续跟进。"
    assert review.reply_content == "感谢认可，我们会继续跟进。"
