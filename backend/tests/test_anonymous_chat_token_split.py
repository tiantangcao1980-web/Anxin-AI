"""
匿名聊天双 token 拆分回归测试

来自任务：TASK-09 P0-2 / PROJECT_STATUS S7
方案文档：docs/audit/09-risk/PROPOSAL-anonymous-chat-token.md

历史：POST /rooms 任意客户端无身份校验可调，一次返回 user_token + lawyer_token，
      允许单方伪造双边身份。
修复：拆分为：
- POST /rooms              （用户发起，要登录 + consultation 所有者）
- POST /rooms/{id}/lawyer-join  （律师认领，要登录 + matched_lawyer）
- GET  /rooms/{id}/my-token     （各自重取）
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.security import create_access_token
from src.models.lawyer_matching import Consultation, ConsultationStatus, PrivacyLevel
from src.models.user import User


@pytest_asyncio.fixture
async def user_a(db_session):
    user = User(
        id=str(uuid4()),
        email=f"u-a-{uuid4().hex[:6]}@example.com",
        name="用户 A",
        hashed_password="x",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def lawyer_a(db_session):
    user = User(
        id=str(uuid4()),
        email=f"l-a-{uuid4().hex[:6]}@example.com",
        name="律师 A",
        hashed_password="x",
        is_active=True,
        role="lawyer",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def stranger(db_session):
    user = User(
        id=str(uuid4()),
        email=f"s-{uuid4().hex[:6]}@example.com",
        name="陌生人",
        hashed_password="x",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def consultation_a_l(db_session, user_a, lawyer_a):
    """用户 A 发起的咨询，已匹配律师 A"""
    cons = Consultation(
        id=str(uuid4()),
        user_id=user_a.id,
        original_description="我有一个合同纠纷",
        anonymous_summary="客户咨询合同纠纷",
        legal_domain="contract",
        urgency="normal",
        status=ConsultationStatus.MATCHED.value,
        privacy_level=PrivacyLevel.ANONYMOUS.value,
        matched_lawyer_id=lawyer_a.id,
    )
    db_session.add(cons)
    await db_session.flush()
    return cons


def _auth_headers(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user_id=user.id)}"}


@pytest_asyncio.fixture
async def client(db_session):
    from src.api.main import app
    from src.core.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


# ============== POST /rooms 拆分后行为 ==============


@pytest.mark.asyncio
async def test_create_room_requires_auth(client):
    """无登录调 POST /rooms → 401（修复前是任意客户端可调）"""
    resp = await client.post(
        "/api/v1/anonymous-chat/rooms",
        json={"consultation_id": str(uuid4())},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_room_response_excludes_lawyer_token(client, user_a, consultation_a_l):
    """成功创建 → 仅返回 user_token，不再含 lawyer_token 字段（S7 关键修复）"""
    resp = await client.post(
        "/api/v1/anonymous-chat/rooms",
        json={
            "consultation_id": consultation_a_l.id,
            "user_name": "Alice",
        },
        headers=_auth_headers(user_a),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "user_token" in body
    assert body["user_token"].startswith("u-")
    # 关键断言：响应中不再包含 lawyer_token，律师必须走 /lawyer-join 单独获取
    assert "lawyer_token" not in body


@pytest.mark.asyncio
async def test_create_room_for_others_consultation_blocked(client, stranger, consultation_a_l):
    """陌生人传他人的 consultation_id 创建房间 → 403"""
    resp = await client.post(
        "/api/v1/anonymous-chat/rooms",
        json={"consultation_id": consultation_a_l.id},
        headers=_auth_headers(stranger),
    )
    assert resp.status_code == 403


# ============== POST /rooms/{id}/lawyer-join ==============


@pytest.mark.asyncio
async def test_lawyer_join_requires_matched_lawyer(client, user_a, lawyer_a, stranger, consultation_a_l):
    """律师认领接口仅放行 consultation.matched_lawyer_id"""
    # 用户 A 先创建房间
    create_resp = await client.post(
        "/api/v1/anonymous-chat/rooms",
        json={"consultation_id": consultation_a_l.id},
        headers=_auth_headers(user_a),
    )
    room_id = create_resp.json()["room_id"]

    # 陌生人尝试认领 → 403
    bad = await client.post(
        f"/api/v1/anonymous-chat/rooms/{room_id}/lawyer-join",
        headers=_auth_headers(stranger),
    )
    assert bad.status_code == 403

    # matched 律师认领 → 200 + lawyer_token
    good = await client.post(
        f"/api/v1/anonymous-chat/rooms/{room_id}/lawyer-join",
        headers=_auth_headers(lawyer_a),
    )
    assert good.status_code == 200
    body = good.json()
    assert body["lawyer_token"].startswith("l-")


@pytest.mark.asyncio
async def test_lawyer_join_requires_auth(client, consultation_a_l):
    """无登录调 lawyer-join → 401"""
    resp = await client.post(
        f"/api/v1/anonymous-chat/rooms/{uuid4().hex[:8]}/lawyer-join",
    )
    assert resp.status_code == 401


# ============== GET /rooms/{id}/my-token ==============


@pytest.mark.asyncio
async def test_my_token_for_user(client, user_a, consultation_a_l):
    """用户重取 my-token 应得 role=user"""
    create_resp = await client.post(
        "/api/v1/anonymous-chat/rooms",
        json={"consultation_id": consultation_a_l.id},
        headers=_auth_headers(user_a),
    )
    room_id = create_resp.json()["room_id"]
    user_token = create_resp.json()["user_token"]

    resp = await client.get(
        f"/api/v1/anonymous-chat/rooms/{room_id}/my-token",
        headers=_auth_headers(user_a),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "user"
    assert body["token"] == user_token


@pytest.mark.asyncio
async def test_my_token_for_lawyer(client, user_a, lawyer_a, consultation_a_l):
    """律师重取 my-token 应得 role=lawyer"""
    create_resp = await client.post(
        "/api/v1/anonymous-chat/rooms",
        json={"consultation_id": consultation_a_l.id},
        headers=_auth_headers(user_a),
    )
    room_id = create_resp.json()["room_id"]

    resp = await client.get(
        f"/api/v1/anonymous-chat/rooms/{room_id}/my-token",
        headers=_auth_headers(lawyer_a),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "lawyer"
    assert body["token"].startswith("l-")


@pytest.mark.asyncio
async def test_my_token_third_party_blocked(client, user_a, stranger, consultation_a_l):
    """第三方调 my-token → 403"""
    create_resp = await client.post(
        "/api/v1/anonymous-chat/rooms",
        json={"consultation_id": consultation_a_l.id},
        headers=_auth_headers(user_a),
    )
    room_id = create_resp.json()["room_id"]

    resp = await client.get(
        f"/api/v1/anonymous-chat/rooms/{room_id}/my-token",
        headers=_auth_headers(stranger),
    )
    assert resp.status_code == 403
