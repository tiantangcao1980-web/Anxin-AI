import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock
from uuid import uuid4

from src.core.security import create_access_token
from src.models.im import IMConversation, IMParticipant
from src.models.user import Organization, User


@pytest_asyncio.fixture
async def same_org_peer(db_session, test_organization):
    user = User(
        id=str(uuid4()),
        email=f"peer-{uuid4().hex[:8]}@example.com",
        name="同组织同事",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
        role="member",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def rtc_conversation(db_session, test_user, same_org_peer):
    conversation = IMConversation(
        id=str(uuid4()),
        type="private",
        title="RTC Test",
        is_active=True,
    )
    db_session.add(conversation)
    await db_session.flush()

    for uid in (test_user.id, same_org_peer.id):
        participant = IMParticipant(
            id=str(uuid4()),
            conversation_id=conversation.id,
            user_id=uid,
            role="member",
        )
        db_session.add(participant)

    await db_session.flush()
    return conversation


@pytest_asyncio.fixture
async def outsider_org_user(db_session):
    org = Organization(id=str(uuid4()), name="外部组织-RTC")
    db_session.add(org)
    await db_session.flush()

    user = User(
        id=str(uuid4()),
        email=f"rtc-outsider-{uuid4().hex[:8]}@example.com",
        name="外部RTC用户",
        hashed_password="hashed_password",
        org_id=org.id,
        is_active=True,
        role="member",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def outsider_auth_client(db_session, outsider_org_user):
    from src.api.main import app
    from src.core.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(user_id=outsider_org_user.id)
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_im_user_search_scoped_to_org(auth_client, db_session, same_org_peer, outsider_org_user):
    response = await auth_client.get("/api/v1/im/users/search?q=%40example.com")

    assert response.status_code == 200
    body = response.json()
    items = body["data"]
    ids = {item["id"] for item in items}
    assert str(same_org_peer.id) in ids
    assert str(outsider_org_user.id) not in ids


@pytest.mark.asyncio
async def test_rtc_room_requires_participant(auth_client, outsider_auth_client, rtc_conversation, monkeypatch):
    monkeypatch.setattr("src.api.routes.rtc.rtc_service.is_available", lambda: True)
    monkeypatch.setattr("src.api.routes.rtc.rtc_service.create_room", AsyncMock(return_value={"name": "ok"}))
    monkeypatch.setattr("src.api.routes.rtc.rtc_service.generate_token", lambda **_: "rtc-token")
    monkeypatch.setattr("src.api.routes.rtc.rtc_service.delete_room", AsyncMock(return_value=True))
    monkeypatch.setattr("src.api.routes.rtc.rtc_service.list_rooms", AsyncMock(return_value=[
        {"name": f"call_{rtc_conversation.id}_12345", "sid": "sid-1", "num_participants": 2},
    ]))

    allowed = await auth_client.post(
        "/api/v1/rtc/rooms",
        json={"conversation_id": rtc_conversation.id, "call_type": "voice"},
    )
    assert allowed.status_code == 200
    room_name = allowed.json()["data"]["room_name"]

    forbidden_create = await outsider_auth_client.post(
        "/api/v1/rtc/rooms",
        json={"conversation_id": rtc_conversation.id, "call_type": "voice"},
    )
    assert forbidden_create.status_code == 403

    forbidden_token = await outsider_auth_client.get(f"/api/v1/rtc/rooms/{room_name}/token")
    assert forbidden_token.status_code == 403

    forbidden_delete = await outsider_auth_client.delete(f"/api/v1/rtc/rooms/{room_name}")
    assert forbidden_delete.status_code == 403

    list_response = await outsider_auth_client.get("/api/v1/rtc/rooms")
    assert list_response.status_code == 200
    assert list_response.json()["data"]["rooms"] == []
