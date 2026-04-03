from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.security import create_access_token
from src.models.meeting_record import MeetingRecord
from src.models.user import Organization, User


@pytest_asyncio.fixture
async def outsider_org(db_session):
    org = Organization(
        id=str(uuid4()),
        name="旁听外部组织",
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def outsider_user(db_session, outsider_org):
    user = User(
        id=str(uuid4()),
        email=f"meeting-outsider-{uuid4().hex[:8]}@example.com",
        name="旁听外部用户",
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
async def test_start_meeting_assistant_blocks_existing_record_owned_by_other_user(
    outsider_client,
    db_session,
    test_user,
):
    record = MeetingRecord(
        conversation_id="conv-shared-1",
        conversation_type="im",
        status="listening",
        started_by=test_user.id,
        insights=[],
        action_items=[],
    )
    db_session.add(record)
    await db_session.flush()

    response = await outsider_client.post(
        "/api/v1/assistant/start",
        json={
            "conversation_id": "conv-shared-1",
            "conversation_type": "im",
        },
    )

    assert response.status_code == 403
    assert "已有其他用户开启旁听" in response.json()["detail"]


@pytest.mark.asyncio
async def test_stop_meeting_assistant_blocks_record_owned_by_other_user(
    outsider_client,
    db_session,
    test_user,
):
    record = MeetingRecord(
        conversation_id="conv-shared-2",
        conversation_type="im",
        status="listening",
        started_by=test_user.id,
        insights=[],
        action_items=[],
    )
    db_session.add(record)
    await db_session.flush()

    response = await outsider_client.post(
        "/api/v1/assistant/stop",
        json={
            "conversation_id": "conv-shared-2",
        },
    )

    assert response.status_code == 403
    assert "无权停止该旁听记录" in response.json()["detail"]
