from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.security import create_access_token
from src.models.user import Organization, User

from .conftest import create_auth_headers


@pytest_asyncio.fixture
async def outsider_org(db_session):
    org = Organization(
        id=str(uuid4()),
        name="文档外部组织",
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def outsider_user(db_session, outsider_org):
    user = User(
        id=str(uuid4()),
        email=f"document-outsider-{uuid4().hex[:8]}@example.com",
        name="文档外部用户",
        hashed_password="hashed_password",
        org_id=outsider_org.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def outsider_client(db_session, outsider_user):
    from src.api.main import app
    from src.core.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(user_id=outsider_user.id)
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_text_document_assigns_current_org(client, test_user):
    response = await client.post(
        "/api/v1/documents/text",
        headers=create_auth_headers(test_user),
        json={
            "name": "法务备忘录.md",
            "content": "# 法务备忘录\n\n请跟进合同条款。",
            "doc_type": "other",
            "tags": ["内部", "备忘录"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert payload["data"]["name"] == "法务备忘录.md"
    assert payload["data"]["extracted_text"] == "# 法务备忘录\n\n请跟进合同条款。"


@pytest.mark.asyncio
async def test_update_document_content_blocks_cross_org_access(outsider_client, test_document):
    response = await outsider_client.patch(
        f"/api/v1/documents/{test_document.id}/content",
        json={
            "content": "新的文档内容",
            "change_summary": "跨组织修改尝试",
        },
    )

    assert response.status_code == 200
    assert response.json()["code"] == 404


@pytest.mark.asyncio
async def test_update_document_metadata_blocks_cross_org_access(outsider_client, test_document):
    response = await outsider_client.put(
        f"/api/v1/documents/{test_document.id}",
        json={
            "name": "新的文档名.pdf",
            "description": "跨组织修改尝试",
        },
    )

    assert response.status_code == 200
    assert response.json()["code"] == 404


@pytest.mark.asyncio
async def test_delete_document_blocks_cross_org_access(outsider_client, test_document):
    response = await outsider_client.delete(
        f"/api/v1/documents/{test_document.id}",
    )

    assert response.status_code == 200
    assert response.json()["code"] == 404


@pytest.mark.asyncio
async def test_analyze_document_returns_summary(
    client,
    test_document,
    test_user,
    monkeypatch,
):
    mock_workforce = MagicMock()
    mock_workforce.process_task_governed = AsyncMock(
        return_value={
            "final_result": {
                "summary": "该文档主要涉及合同付款与违约条款。",
                "key_points": ["付款条件", "违约责任"],
                "entities": ["甲方", "乙方"],
                "dates": ["2026-04-03"],
                "amounts": ["100万元"],
                "risks": ["付款节点缺失"],
            }
        }
    )
    monkeypatch.setattr("src.agents.workforce.get_workforce", lambda: mock_workforce)

    response = await client.post(
        f"/api/v1/documents/{test_document.id}/analyze",
        headers=create_auth_headers(test_user),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert payload["data"]["document_id"] == test_document.id
    assert payload["data"]["summary"] == "该文档主要涉及合同付款与违约条款。"
    assert "付款条件" in payload["data"]["key_points"]


@pytest.mark.asyncio
async def test_analyze_document_blocks_cross_org_access(outsider_client, test_document):
    response = await outsider_client.post(
        f"/api/v1/documents/{test_document.id}/analyze",
    )

    assert response.status_code == 200
    assert response.json()["code"] == 404


@pytest.mark.asyncio
async def test_document_versions_block_cross_org_access(outsider_client, test_document):
    response = await outsider_client.get(
        f"/api/v1/documents/{test_document.id}/versions",
    )

    assert response.status_code == 200
    assert response.json()["code"] == 404
