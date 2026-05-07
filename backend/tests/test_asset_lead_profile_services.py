from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import Organization, User
from src.services.asset_service import AssetService
from src.services.course_service import CourseService
from src.services.expert_service import ExpertService
from src.services.lead_service import LeadService
from src.services.user_profile_service import UserProfileService
from src.services.user_service import UserService


@pytest.mark.asyncio
async def test_asset_service_lifecycle(db_session: AsyncSession) -> None:
    org = Organization(name="Service Test Org")
    user = User(
        email=f"{uuid4()}@example.com",
        hashed_password="hashed",
        name="Asset Owner",
        org_id=org.id,
    )
    db_session.add_all([org, user])
    await db_session.flush()

    service = AssetService(db_session)
    asset = await service.create_asset(
        name="Office Building",
        asset_type="real_estate",
        original_value=1000.0,
        current_value=900.0,
        acquisition_date=date(2025, 1, 1),
        org_id=org.id,
        created_by=user.id,
    )

    assets = await service.list_assets(org.id)
    assert [item.id for item in assets] == [asset.id]

    updated = await service.update_asset(asset.id, org.id, current_value=950.0)
    assert updated is not None
    assert updated.current_value == 950.0

    assert await service.delete_asset(asset.id, org.id) is True
    assert await service.list_assets(org.id) == []


@pytest.mark.asyncio
async def test_lead_service_follow_up_lifecycle(db_session: AsyncSession) -> None:
    org = Organization(name="Lead Test Org")
    user = User(
        email=f"{uuid4()}@example.com",
        hashed_password="hashed",
        name="Lead Owner",
        org_id=org.id,
    )
    db_session.add_all([org, user])
    await db_session.flush()

    service = LeadService(db_session)
    lead = await service.create_lead(
        client_name="Prospect Co",
        contact_info="contact@example.com",
        stage="new",
        org_id=org.id,
        created_by=user.id,
        assignee_id=user.id,
    )

    leads, total = await service.list_leads(org_id=org.id)
    assert total == 1
    assert [item.id for item in leads] == [lead.id]

    followed = await service.add_follow_up(
        lead.id,
        {"note": "Called prospect"},
        org_id=org.id,
    )
    assert followed is not None
    assert followed.follow_ups is not None
    assert followed.follow_ups[0]["note"] == "Called prospect"
    assert followed.follow_ups[0]["id"]

    updated = await service.update_stage(lead.id, "qualified", org_id=org.id)
    assert updated is not None
    assert updated.stage == "qualified"

    assert await service.delete_lead(lead.id, org_id=org.id) is True


@pytest.mark.asyncio
async def test_user_profile_merges_partial_ai_profile(db_session: AsyncSession) -> None:
    user = User(
        email=f"{uuid4()}@example.com",
        hashed_password="hashed",
        name="Profile User",
        ai_profile={"interaction_stats": {"total_sessions": 2}},
    )
    db_session.add(user)
    await db_session.flush()

    profile = await UserProfileService(db_session).get_profile(user.id)

    assert profile["legal_sophistication"] == "intermediate"
    assert profile["interaction_stats"]["total_sessions"] == 2
    assert profile["interaction_stats"]["feedback_ratings_count"] == 0


@pytest.mark.asyncio
async def test_expert_service_lifecycle(db_session: AsyncSession) -> None:
    org = Organization(name="Expert Test Org")
    db_session.add(org)
    await db_session.flush()

    service = ExpertService(db_session)
    expert = await service.create_expert(
        name="Senior Lawyer",
        title="Partner",
        specialty=["contract"],
        rating=4.8,
        org_id=org.id,
    )

    experts, total = await service.list_experts(org_id=org.id, specialty="contract")
    assert total == 1
    assert [item.id for item in experts] == [expert.id]

    updated = await service.update_expert(expert.id, org.id, rating=4.9)
    assert updated is not None
    assert updated.rating == 4.9

    assert await service.delete_expert(expert.id, org.id) is True


@pytest.mark.asyncio
async def test_user_service_create_and_login_payload(db_session: AsyncSession) -> None:
    service = UserService(db_session)
    email = f"{uuid4()}@example.com"

    user = await service.create_user(
        email=email,
        password="Passw0rd!",
        name="Login User",
        user_type="platform_lawyer",
    )

    assert user.primary_client == "provider"

    payload = await service.login(email, "Passw0rd!")
    assert payload is not None
    assert payload["token_type"] == "bearer"
    assert payload["user"]["id"] == user.id
    assert await service.login(email, "wrong-password") is None


@pytest.mark.asyncio
async def test_course_service_lifecycle_and_progress(db_session: AsyncSession) -> None:
    user = User(
        email=f"{uuid4()}@example.com",
        hashed_password="hashed",
        name="Course User",
    )
    db_session.add(user)
    await db_session.flush()

    service = CourseService(db_session)
    course = await service.create_course(
        title="Contract Basics",
        category="practice",
        level="入门",
        tags=["contract"],
        created_by=user.id,
    )

    courses, total = await service.list_courses(category="practice", level="入门")
    assert total == 1
    assert [item.id for item in courses] == [course.id]

    progress = await service.update_progress(
        user.id,
        course.id,
        progress=40,
        completed_lessons=["lesson-1"],
    )
    assert progress.progress == 40
    assert progress.completed_lessons == ["lesson-1"]

    updated = await service.update_course(course.id, lessons=3)
    assert updated is not None
    assert updated.lessons == 3

    assert await service.delete_course(course.id) is True
