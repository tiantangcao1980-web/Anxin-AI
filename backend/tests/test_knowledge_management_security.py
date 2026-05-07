from uuid import uuid4

import pytest

from src.core.security import create_access_token
from src.models.user import User
from src.services.knowledge_management import (
    KnowledgeManagementService,
    knowledge_management_service,
)

SENSITIVE_TEXT = "联系人手机号13812345678，身份证11010119900101123X，邮箱zhang.san@example.com。"


@pytest.fixture(autouse=True)
def clear_knowledge_management_singleton():
    knowledge_management_service._experiences.clear()
    knowledge_management_service._custom_templates.clear()
    yield
    knowledge_management_service._experiences.clear()
    knowledge_management_service._custom_templates.clear()


@pytest.mark.asyncio
async def test_knowledge_management_service_redacts_outputs_and_keeps_org_scope():
    service = KnowledgeManagementService()
    org_id = "org-a"

    experience = await service.add_experience(
        org_id=org_id,
        title="劳动合同解除经验",
        category="labor_dispute",
        summary=SENSITIVE_TEXT,
        key_points=[SENSITIVE_TEXT],
        lessons_learned=SENSITIVE_TEXT,
        tags=["劳动", "联系人13812345678"],
    )
    await service.add_custom_template(
        org_id=org_id,
        name="解除通知模板",
        content=SENSITIVE_TEXT,
        template_type="notice",
        author_id="user-a",
    )

    results = await service.search_experiences(org_id=org_id, query="手机号", top_k=100)
    detail = await service.get_experience(org_id=org_id, experience_id=experience.id)
    templates = await service.list_custom_templates(org_id=org_id)
    stats = service.get_stats(org_id)

    rendered = str({"results": results, "detail": detail, "templates": templates, "stats": stats})
    assert "13812345678" not in rendered
    assert "11010119900101123X" not in rendered
    assert "zhang.san@example.com" not in rendered
    assert "138****5678" in rendered
    assert "110101********123X" in rendered
    assert "z***@example.com" in rendered

    assert await service.search_experiences(org_id="org-b", query="手机号") == []
    assert await service.list_custom_templates(org_id="org-b") == []


@pytest.mark.asyncio
async def test_knowledge_management_categories_require_auth(client, auth_client):
    anonymous = await client.get("/api/v1/knowledge-mgmt/categories")
    assert anonymous.status_code == 401

    authenticated = await auth_client.get("/api/v1/knowledge-mgmt/categories")
    assert authenticated.status_code == 200
    assert "contract_dispute" in authenticated.json()["data"]["categories"]


@pytest.mark.asyncio
async def test_knowledge_management_write_requires_write_permission(auth_client):
    response = await auth_client.post(
        "/api/v1/knowledge-mgmt/experiences",
        json={
            "title": "劳动合同解除经验",
            "category": "labor_dispute",
            "summary": "这是一条用于权限校验的律所经验。",
            "key_points": ["普通 member 不能写入律所知识库"],
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_knowledge_management_api_redacts_admin_added_experience(admin_auth_client):
    created = await admin_auth_client.post(
        "/api/v1/knowledge-mgmt/experiences",
        json={
            "title": "客户联系经验",
            "category": "contract_dispute",
            "summary": SENSITIVE_TEXT,
            "key_points": [SENSITIVE_TEXT],
            "lessons_learned": SENSITIVE_TEXT,
            "tags": ["联系人13812345678"],
        },
    )
    assert created.status_code == 200

    listed = await admin_auth_client.get(
        "/api/v1/knowledge-mgmt/experiences", params={"query": "联系人"}
    )
    assert listed.status_code == 200

    rendered = str({"created": created.json(), "listed": listed.json()})
    assert "13812345678" not in rendered
    assert "11010119900101123X" not in rendered
    assert "zhang.san@example.com" not in rendered
    assert "138****5678" in rendered
    assert "110101********123X" in rendered


@pytest.mark.asyncio
async def test_knowledge_management_user_without_org_fails_closed(client, db_session):
    user = User(
        id=str(uuid4()),
        email=f"no-org-{uuid4().hex[:8]}@example.com",
        name="无组织用户",
        hashed_password="hashed_password",
        role="lawyer",
        org_id=None,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    token = create_access_token(user_id=user.id)
    response = await client.get(
        "/api/v1/knowledge-mgmt/experiences",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
