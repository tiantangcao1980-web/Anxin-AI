from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.security import create_access_token
from src.models.knowledge import KnowledgeBase, KnowledgeType
from src.models.user import Organization, User
from src.services.case_service import CaseService


@pytest_asyncio.fixture
async def outsider_org(db_session):
    org = Organization(
        id=str(uuid4()),
        name="外部组织",
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def outsider_user(db_session, outsider_org):
    user = User(
        id=str(uuid4()),
        email=f"outsider-{uuid4().hex[:8]}@example.com",
        name="外部用户",
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
async def test_document_api_blocks_cross_org_access(outsider_client, test_document):
    response = await outsider_client.get(f"/api/v1/documents/{test_document.id}")

    assert response.status_code == 200
    assert response.json()["code"] == 404


@pytest.mark.asyncio
async def test_knowledge_api_blocks_cross_org_kb_access(db_session, outsider_client, test_user):
    kb = KnowledgeBase(
        id=str(uuid4()),
        name="内部知识库",
        knowledge_type=KnowledgeType.OTHER,
        description="only for primary org",
        org_id=test_user.org_id,
        created_by=test_user.id,
        is_public=False,
        vector_collection=f"kb_{uuid4().hex[:8]}",
    )
    db_session.add(kb)
    await db_session.flush()

    response = await outsider_client.get(f"/api/v1/knowledge/bases/{kb.id}")

    assert response.status_code == 200
    assert response.json()["code"] == 404


@pytest.mark.asyncio
async def test_case_service_blocks_cross_org_document_link(
    db_session,
    test_case,
    test_user,
    outsider_org,
):
    from src.models.document import Document, DocumentType

    foreign_doc = Document(
        id=str(uuid4()),
        name="外部文档.pdf",
        doc_type=DocumentType.CONTRACT,
        file_path="/uploads/foreign.pdf",
        file_size=2048,
        org_id=outsider_org.id,
        created_by=str(uuid4()),
    )
    db_session.add(foreign_doc)
    await db_session.flush()

    service = CaseService(db_session)
    success = await service.link_document(
        case_id=test_case.id,
        document_id=foreign_doc.id,
        org_id=test_user.org_id,
        created_by=test_user.id,
    )

    assert success is False


@pytest.mark.asyncio
async def test_collaboration_session_requires_membership(
    db_session,
    outsider_client,
    test_session,
):
    response = await outsider_client.get(f"/api/v1/collaboration/sessions/{test_session.id}")

    assert response.status_code == 200
    assert response.json()["code"] == 403


@pytest.mark.asyncio
async def test_collaboration_document_comments_require_membership(
    db_session,
    outsider_client,
    test_session,
    test_document,
):
    response = await outsider_client.get(
        f"/api/v1/collaboration/document/{test_document.id}/comments"
    )

    assert response.status_code == 403
