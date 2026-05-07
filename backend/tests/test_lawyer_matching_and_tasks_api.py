from unittest.mock import AsyncMock

import pytest

from src.models.case import Case, CasePriority, CaseStatus, CaseType
from src.models.case_market import CaseRequest, RequestStatus
from src.models.lawyer_matching import Consultation, ConsultationStatus, LawyerProfile
from src.models.task import Task
from src.models.user import Organization, User
from src.services.lawyer_matching_service import (
    _MATCHING_EXPOSURE_COUNTER,
    lawyer_matching_service,
)

from .conftest import create_auth_headers


@pytest.mark.asyncio
async def test_create_consultation_returns_anonymous_summary(
    client,
    test_user,
    monkeypatch,
):
    mock_analyze_case = AsyncMock(
        return_value={
            "anonymous_summary": "劳动争议匿名摘要",
            "legal_domain": "labor",
            "recommended_specializations": ["劳动争议"],
            "domain_label": "劳动争议",
            "domain_confidence": 0.91,
            "risk_level": "high",
            "legal_elements": {"claim": "未签劳动合同赔偿"},
        }
    )
    monkeypatch.setattr(
        "src.services.lawyer_matching_service.lawyer_matching_service.analyze_case",
        mock_analyze_case,
    )

    response = await client.post(
        "/api/v1/lawyer/consultations",
        headers=create_auth_headers(test_user),
        json={
            "description": "员工主张公司未签劳动合同并要求赔偿，我们需要尽快处理。",
            "urgency": "high",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["anonymous_summary"] == "劳动争议匿名摘要"
    assert payload["legal_domain"] == "labor"
    assert payload["risk_level"] == "high"


@pytest.mark.asyncio
async def test_create_consultation_rejects_local_mode(
    client,
    test_user,
):
    response = await client.post(
        "/api/v1/lawyer/consultations",
        headers={**create_auth_headers(test_user), "X-Privacy-Mode": "local"},
        json={
            "description": "员工主张公司未签劳动合同并要求赔偿，我们需要尽快处理。",
            "urgency": "high",
        },
    )

    assert response.status_code == 403
    assert "本地模式不支持律师撮合" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delegation_requires_matched_lawyer(
    client,
    db_session,
    test_user,
):
    consultation = Consultation(
        user_id=test_user.id,
        original_description="合同争议，希望咨询律师。",
        anonymous_summary="合同争议匿名摘要",
        legal_domain="contract",
        status=ConsultationStatus.PENDING.value,
        privacy_level=0,
        urgency="medium",
    )
    db_session.add(consultation)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/lawyer/consultations/{consultation.id}/delegate",
        headers=create_auth_headers(test_user),
        json={
            "title": "合同争议委托",
            "description": "请尽快处理",
            "service_type": "instant",
        },
    )

    assert response.status_code == 400
    assert "尚未匹配律师" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_delegation_updates_consultation_status(
    client,
    db_session,
    test_user,
    test_organization,
):
    lawyer_user = User(
        email="lawyer-api@example.com",
        name="接单律师",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
        role="platform_lawyer",
    )
    db_session.add(lawyer_user)
    await db_session.flush()

    lawyer_profile = LawyerProfile(
        user_id=lawyer_user.id,
        real_name="接单律师",
        license_number="LIC-API-001",
        years_of_practice=6,
        is_verified=True,
        is_online=True,
        specializations=["contract"],
    )
    db_session.add(lawyer_profile)

    consultation = Consultation(
        user_id=test_user.id,
        original_description="合同争议，希望咨询律师。",
        anonymous_summary="合同争议匿名摘要",
        legal_domain="contract",
        status=ConsultationStatus.MATCHED.value,
        privacy_level=0,
        urgency="medium",
        matched_lawyer_id=lawyer_user.id,
    )
    db_session.add(consultation)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/lawyer/consultations/{consultation.id}/delegate",
        headers=create_auth_headers(test_user),
        json={
            "title": "合同争议委托",
            "description": "请尽快处理",
            "service_type": "instant",
        },
    )

    await db_session.refresh(consultation)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "draft"
    assert consultation.status == ConsultationStatus.DELEGATION.value
    assert consultation.privacy_level == 2


@pytest.mark.asyncio
async def test_task_transition_supports_frontend_status_flow(
    client,
    db_session,
    test_user,
    test_organization,
):
    task = Task(
        title="审查供应商合同",
        description="补充付款条款与违约责任",
        status="todo",
        priority="high",
        created_by=test_user.id,
        org_id=test_organization.id,
    )
    db_session.add(task)
    await db_session.flush()

    response = await client.put(
        f"/api/v1/tasks/{task.id}/transition",
        headers=create_auth_headers(test_user),
        json={"status": "in_progress"},
    )

    await db_session.refresh(task)

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert payload["data"]["status"] == "in_progress"
    assert task.status == "in_progress"


@pytest.mark.asyncio
async def test_task_transition_rejects_invalid_status_flow(
    client,
    db_session,
    test_user,
    test_organization,
):
    task = Task(
        title="归档历史合同",
        description="已完成任务",
        status="done",
        priority="low",
        created_by=test_user.id,
        org_id=test_organization.id,
    )
    db_session.add(task)
    await db_session.flush()

    response = await client.put(
        f"/api/v1/tasks/{task.id}/transition",
        headers=create_auth_headers(test_user),
        json={"status": "in_progress"},
    )

    await db_session.refresh(task)

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 400
    assert "无效状态转换" in payload["message"]
    assert task.status == "done"


@pytest.mark.asyncio
async def test_task_transition_blocks_cross_org_access(
    client,
    db_session,
    test_user,
):
    outsider_org = Organization(
        name="外部组织",
    )
    db_session.add(outsider_org)
    await db_session.flush()

    task = Task(
        title="外部组织任务",
        description="不应允许跨组织流转",
        status="todo",
        priority="medium",
        created_by=test_user.id,
        org_id=outsider_org.id,
    )
    db_session.add(task)
    await db_session.flush()

    response = await client.put(
        f"/api/v1/tasks/{task.id}/transition",
        headers=create_auth_headers(test_user),
        json={"status": "in_progress"},
    )

    await db_session.refresh(task)

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 404
    assert task.status == "todo"


@pytest.mark.asyncio
async def test_task_batch_update_blocks_cross_org_items(
    client,
    db_session,
    test_user,
):
    outsider_org = Organization(
        name="批量外部组织",
    )
    db_session.add(outsider_org)
    await db_session.flush()

    local_task = Task(
        title="本组织任务",
        status="todo",
        priority="medium",
        created_by=test_user.id,
        org_id=test_user.org_id,
    )
    foreign_task = Task(
        title="外部任务",
        status="todo",
        priority="medium",
        created_by=test_user.id,
        org_id=outsider_org.id,
    )
    db_session.add_all([local_task, foreign_task])
    await db_session.flush()

    response = await client.post(
        "/api/v1/tasks/batch-update",
        headers=create_auth_headers(test_user),
        json={
            "updates": [
                {"task_id": local_task.id, "status": "in_progress"},
                {"task_id": foreign_task.id, "status": "in_progress"},
            ]
        },
    )

    await db_session.refresh(local_task)
    await db_session.refresh(foreign_task)

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert payload["data"]["success"] == 1
    assert payload["data"]["failed"] == 1
    assert local_task.status == "in_progress"
    assert foreign_task.status == "todo"


@pytest.mark.asyncio
async def test_task_list_hides_same_org_tasks_from_non_owner(
    client,
    db_session,
    test_user,
    test_organization,
):
    other_user = User(
        email="task-owner@example.com",
        name="任务所有者",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.flush()

    own_task = Task(
        title="本人创建任务",
        status="todo",
        priority="medium",
        created_by=test_user.id,
        org_id=test_user.org_id,
    )
    assigned_task = Task(
        title="指派给本人任务",
        status="todo",
        priority="medium",
        created_by=other_user.id,
        assignee_id=test_user.id,
        org_id=test_user.org_id,
    )
    hidden_task = Task(
        title="他人私有任务",
        status="todo",
        priority="medium",
        created_by=other_user.id,
        assignee_id=other_user.id,
        org_id=test_user.org_id,
    )
    db_session.add_all([own_task, assigned_task, hidden_task])
    await db_session.flush()

    response = await client.get(
        "/api/v1/tasks/",
        headers=create_auth_headers(test_user),
    )

    assert response.status_code == 200
    titles = {item["title"] for item in response.json()["data"]["items"]}
    assert "本人创建任务" in titles
    assert "指派给本人任务" in titles
    assert "他人私有任务" not in titles


@pytest.mark.asyncio
async def test_task_update_blocks_same_org_non_owner(
    client,
    db_session,
    test_user,
    test_organization,
):
    other_user = User(
        email="task-update-owner@example.com",
        name="任务更新所有者",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.flush()

    task = Task(
        title="他人任务",
        status="todo",
        priority="medium",
        created_by=other_user.id,
        assignee_id=other_user.id,
        org_id=test_user.org_id,
    )
    db_session.add(task)
    await db_session.flush()

    response = await client.put(
        f"/api/v1/tasks/{task.id}",
        headers=create_auth_headers(test_user),
        json={"title": "越权修改"},
    )

    await db_session.refresh(task)

    assert response.status_code == 200
    assert response.json()["code"] == 404
    assert task.title == "他人任务"


@pytest.mark.asyncio
async def test_lawyer_hall_blocks_non_lawyer_user(
    client,
    test_user,
):
    response = await client.get(
        "/api/v1/lawyer/hall",
        headers=create_auth_headers(test_user),
    )

    assert response.status_code == 403
    assert "仅入驻律师可访问接单大厅" in response.json()["detail"]


@pytest.mark.asyncio
async def test_lawyer_hall_returns_pending_consultations_for_lawyer(
    client,
    db_session,
    test_user,
    test_organization,
):
    lawyer_user = User(
        email="hall-lawyer@example.com",
        name="大厅律师",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
        role="platform_lawyer",
    )
    db_session.add(lawyer_user)
    await db_session.flush()

    lawyer_profile = LawyerProfile(
        user_id=lawyer_user.id,
        real_name="大厅律师",
        license_number="LIC-HALL-001",
        years_of_practice=7,
        is_verified=True,
        specializations=["contract"],
    )
    db_session.add(lawyer_profile)

    pending_consultation = Consultation(
        user_id=test_user.id,
        original_description="采购合同争议",
        anonymous_summary="采购合同争议匿名摘要",
        legal_domain="contract",
        status=ConsultationStatus.PENDING.value,
        privacy_level=0,
        urgency="medium",
    )
    matched_consultation = Consultation(
        user_id=test_user.id,
        original_description="已被接单的咨询",
        anonymous_summary="不应出现在大厅中",
        legal_domain="contract",
        status=ConsultationStatus.IN_PROGRESS.value,
        privacy_level=0,
        urgency="high",
        matched_lawyer_id=lawyer_user.id,
    )
    db_session.add_all([pending_consultation, matched_consultation])
    await db_session.flush()

    response = await client.get(
        "/api/v1/lawyer/hall",
        headers=create_auth_headers(lawyer_user),
    )

    assert response.status_code == 200
    payload = response.json()
    ids = {item["id"] for item in payload["items"]}
    assert pending_consultation.id in ids
    assert matched_consultation.id not in ids


@pytest.mark.asyncio
async def test_accept_consultation_updates_match_and_status(
    client,
    db_session,
    test_user,
    test_organization,
):
    lawyer_user = User(
        email="accept-lawyer@example.com",
        name="接单大厅律师",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
        role="platform_lawyer",
    )
    db_session.add(lawyer_user)
    await db_session.flush()

    lawyer_profile = LawyerProfile(
        user_id=lawyer_user.id,
        real_name="接单大厅律师",
        license_number="LIC-HALL-002",
        years_of_practice=7,
        is_verified=True,
        specializations=["labor"],
    )
    db_session.add(lawyer_profile)

    consultation = Consultation(
        user_id=test_user.id,
        original_description="劳动争议咨询",
        anonymous_summary="劳动争议匿名摘要",
        legal_domain="labor",
        status=ConsultationStatus.PENDING.value,
        privacy_level=0,
        urgency="urgent",
    )
    db_session.add(consultation)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/lawyer/hall/{consultation.id}/accept",
        headers=create_auth_headers(lawyer_user),
    )

    await db_session.refresh(consultation)

    assert response.status_code == 200
    assert consultation.matched_lawyer_id == lawyer_user.id
    assert consultation.status == ConsultationStatus.IN_PROGRESS.value


@pytest.mark.asyncio
async def test_accept_consultation_rejects_already_taken_request(
    client,
    db_session,
    test_user,
    test_organization,
):
    lawyer_user = User(
        email="accept-taken-lawyer@example.com",
        name="接单大厅律师2",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
        role="platform_lawyer",
    )
    db_session.add(lawyer_user)
    await db_session.flush()

    lawyer_profile = LawyerProfile(
        user_id=lawyer_user.id,
        real_name="接单大厅律师2",
        license_number="LIC-HALL-003",
        years_of_practice=6,
        is_verified=True,
        specializations=["labor"],
    )
    db_session.add(lawyer_profile)

    consultation = Consultation(
        user_id=test_user.id,
        original_description="已接单咨询",
        anonymous_summary="已接单匿名摘要",
        legal_domain="labor",
        status=ConsultationStatus.IN_PROGRESS.value,
        privacy_level=0,
        urgency="high",
        matched_lawyer_id=lawyer_user.id,
    )
    db_session.add(consultation)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/lawyer/hall/{consultation.id}/accept",
        headers=create_auth_headers(lawyer_user),
    )

    assert response.status_code == 400
    assert "已被其他律师接单" in response.json()["detail"]


@pytest.mark.asyncio
async def test_case_market_bid_rejects_conflicted_lawyer(
    client,
    db_session,
    test_user,
    test_organization,
):
    lawyer_user = User(
        email="conflict-lawyer@example.com",
        name="冲突律师",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
        role="platform_lawyer",
    )
    db_session.add(lawyer_user)
    await db_session.flush()

    market_request = CaseRequest(
        user_id=test_user.id,
        org_id=test_organization.id,
        title="甲方科技有限公司合同争议",
        description="需要处理与甲方科技有限公司之间的合同争议。",
        legal_area="contract",
        tags=["甲方科技有限公司"],
        status=RequestStatus.PUBLISHED,
    )
    historical_case = Case(
        title="历史代理案件",
        case_number="CASE-CONFLICT-001",
        case_type=CaseType.CONTRACT,
        status=CaseStatus.IN_PROGRESS,
        priority=CasePriority.MEDIUM,
        description="历史上曾代理甲方科技有限公司。",
        org_id=test_organization.id,
        assignee_id=lawyer_user.id,
        parties={"client": "甲方科技有限公司"},
    )
    db_session.add_all([market_request, historical_case])
    await db_session.flush()

    response = await client.post(
        f"/api/v1/case-market/market/{market_request.id}/bid",
        headers=create_auth_headers(lawyer_user),
        json={"proposal": "我可以处理该合同争议", "quoted_price": 5000},
    )

    await db_session.refresh(market_request)

    assert response.status_code == 409
    assert response.json()["detail"]["conflict"]["has_conflict"] is True
    assert market_request.bid_count == 0


@pytest.mark.asyncio
async def test_case_market_rejects_local_mode(
    client,
    test_user,
):
    response = await client.get(
        "/api/v1/case-market/market",
        headers={**create_auth_headers(test_user), "X-Privacy-Mode": "local"},
    )

    assert response.status_code == 403
    assert "本地模式不支持案源市场" in response.json()["detail"]


@pytest.mark.asyncio
async def test_matching_service_rotates_equal_score_lawyer_exposure(
    db_session,
    test_organization,
):
    lawyers = []
    for index in range(3):
        lawyer_user = User(
            email=f"fair-lawyer-{index}@example.com",
            name=f"公平律师{index}",
            hashed_password="hashed_password",
            org_id=test_organization.id,
            is_active=True,
            role="platform_lawyer",
        )
        db_session.add(lawyer_user)
        await db_session.flush()
        profile = LawyerProfile(
            user_id=lawyer_user.id,
            real_name=f"公平律师{index}",
            license_number=f"LIC-FAIR-{index}",
            years_of_practice=5,
            is_verified=True,
            is_accepting=True,
            is_online=True,
            specializations=["合同纠纷"],
            rating=5.0,
            total_cases=20,
        )
        db_session.add(profile)
        lawyers.append(profile)
    await db_session.flush()

    for profile in lawyers:
        _MATCHING_EXPOSURE_COUNTER.pop(str(profile.id), None)

    top_counts = {str(profile.id): 0 for profile in lawyers}
    for _ in range(30):
        result = await lawyer_matching_service.match_lawyers(
            db_session,
            domain="contract",
            limit=1,
        )
        top_counts[result[0]["id"]] += 1

    assert max(top_counts.values()) - min(top_counts.values()) <= 1
