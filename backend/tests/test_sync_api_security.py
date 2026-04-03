import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from uuid import uuid4

from src.core.security import create_access_token
from src.models.user import Organization, User


@pytest_asyncio.fixture
async def other_sync_user_client(db_session):
    org = Organization(id=str(uuid4()), name="同步隔离组织")
    db_session.add(org)
    await db_session.flush()

    user = User(
        id=str(uuid4()),
        email=f"sync-user-{uuid4().hex[:8]}@example.com",
        name="同步隔离用户",
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
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sync_push_and_pull_are_user_scoped(auth_client, other_sync_user_client):
    payload = {
        "records": [
            {
                "entity_type": "document",
                "entity_id": "doc-1",
                "action": "create",
                "data": {"title": "私有文档"},
                "timestamp": "2026-04-03T10:00:00Z",
                "version": 1,
            }
        ],
        "device_id": "device-a",
        "last_sync_version": 0,
    }

    push = await auth_client.post("/api/v1/sync/push", json=payload)
    assert push.status_code == 200
    assert push.json()["accepted"] == 1

    own_pull = await auth_client.get("/api/v1/sync/pull?since_version=0")
    assert own_pull.status_code == 200
    assert len(own_pull.json()["records"]) == 1

    other_pull = await other_sync_user_client.get("/api/v1/sync/pull?since_version=0")
    assert other_pull.status_code == 200
    assert other_pull.json()["records"] == []


@pytest.mark.asyncio
async def test_sync_status_and_full_sync_work(auth_client):
    status = await auth_client.get("/api/v1/sync/status?device_id=device-a")
    assert status.status_code == 200
    assert "server_version" in status.json()

    full_sync = await auth_client.post("/api/v1/sync/full-sync?device_id=device-a")
    assert full_sync.status_code == 200
    assert full_sync.json()["success"] is True
