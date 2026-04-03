import hashlib
import hmac
import pytest
import pytest_asyncio
import time
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from src.core.config import settings
from src.services.crawler_service import CrawlerTask, crawler_service
from src.services.crawler_service import _is_allowed_runtime_url
from src.core.security import create_access_token
from src.models.user import Organization, User


@pytest_asyncio.fixture
async def outsider_org_user(db_session):
    org = Organization(id=str(uuid4()), name="外部LIC组织")
    db_session.add(org)
    await db_session.flush()

    user = User(
        id=str(uuid4()),
        email=f"lic-outsider-{uuid4().hex[:8]}@example.com",
        name="LIC 外部用户",
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
async def test_payment_webhook_rejects_invalid_signature(client, monkeypatch):
    monkeypatch.setattr(settings, "WECHAT_PAY_WEBHOOK_SECRET", "test-secret")

    response = await client.post(
        "/api/v1/payments/webhook/wechat",
        content=b'{"order":"1"}',
        headers={"X-Wechat-Signature": "bad-signature", "X-Webhook-Timestamp": str(int(time.time()))},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_esign_webhook_accepts_valid_signature(client, monkeypatch):
    monkeypatch.setattr(settings, "ESIGN_WEBHOOK_SECRET", "esign-secret")
    body = b'{"flow_id":"f1","action":"signed","status":"completed"}'
    timestamp = str(int(time.time()))
    signature = hmac.new(b"esign-secret", f"{timestamp}.".encode("utf-8") + body, hashlib.sha256).hexdigest()

    response = await client.post(
        "/api/v1/esign/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-ESign-Signature": signature,
            "X-Webhook-Timestamp": timestamp,
        },
    )

    assert response.status_code == 200
    assert response.json()["code"] == 0


@pytest.mark.asyncio
async def test_esign_webhook_rejects_replay(client, monkeypatch):
    monkeypatch.setattr(settings, "ESIGN_WEBHOOK_SECRET", "esign-secret")
    body = b'{"flow_id":"f2","action":"completed","status":"done"}'
    timestamp = str(int(time.time()))
    signature = hmac.new(b"esign-secret", f"{timestamp}.".encode("utf-8") + body, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-ESign-Signature": signature,
        "X-Webhook-Timestamp": timestamp,
    }

    first = await client.post("/api/v1/esign/webhook", content=body, headers=headers)
    second = await client.post("/api/v1/esign/webhook", content=body, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 403


@pytest.mark.asyncio
async def test_oa_approval_uses_current_user_as_initiator(auth_client, test_user):
    with patch("src.api.routes.integrations.oa_service.initiate_approval", new=AsyncMock(return_value="oa-1")) as mock_call:
        response = await auth_client.post(
            "/api/v1/integrations/oa/approval/create",
            json={
                "title": "审批测试",
                "details": {"a": 1},
                "initiator_id": "forged-user",
                "provider": "feishu",
            },
        )

    assert response.status_code == 200
    assert mock_call.await_args.args[2] == str(test_user.id)


@pytest.mark.asyncio
async def test_oa_notification_scopes_target_to_current_user(auth_client, test_user):
    with patch("src.api.routes.integrations.oa_service.send_notification", new=AsyncMock(return_value=True)) as mock_call:
        response = await auth_client.post(
            "/api/v1/integrations/oa/notify",
            json={
                "user_id": "forged-user",
                "title": "通知测试",
                "content": "hello",
                "provider": "feishu",
            },
        )

    assert response.status_code == 200
    assert mock_call.await_args.args[0] == str(test_user.id)


@pytest.mark.asyncio
async def test_oa_notification_ignores_admin_override_target(admin_auth_client, test_admin):
    with patch("src.api.routes.integrations.oa_service.send_notification", new=AsyncMock(return_value=True)) as mock_call:
        response = await admin_auth_client.post(
            "/api/v1/integrations/oa/notify",
            json={
                "user_id": "forged-admin-target",
                "title": "管理员通知测试",
                "content": "hello",
                "provider": "feishu",
            },
        )

    assert response.status_code == 200
    assert mock_call.await_args.args[0] == str(test_admin.id)


@pytest.mark.asyncio
async def test_lic_status_requires_task_owner(auth_client, outsider_auth_client, test_user):
    task = CrawlerTask(url="https://example.com", keyword="k", task_id="task-owner", owner_id=str(test_user.id))
    crawler_service.tasks[task.id] = task
    try:
        ok = await auth_client.get(f"/api/v1/lic/status/{task.id}")
        assert ok.status_code == 200

        forbidden = await outsider_auth_client.get(f"/api/v1/lic/status/{task.id}")
        assert forbidden.status_code == 200
        assert forbidden.json()["code"] == 403
    finally:
        crawler_service.tasks.pop(task.id, None)


@pytest.mark.asyncio
async def test_lic_crawl_respects_allowlist(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "LIC_ALLOWED_HOSTS", ["court.gov.cn"])

    blocked = await auth_client.post(
        "/api/v1/lic/crawl",
        json={"url": "https://example.com/legal", "keyword": "test", "task_id": "task-allowlist"},
    )

    assert blocked.status_code == 403


def test_lic_runtime_url_validator_blocks_redirect_targets(monkeypatch):
    monkeypatch.setattr(settings, "LIC_ALLOWED_HOSTS", ["court.gov.cn"])

    # Mock DNS 解析，避免依赖网络环境（VPN/代理可能返回私有 IP）
    import socket
    _real_getaddrinfo = socket.getaddrinfo

    def _fake_getaddrinfo(host, *args, **kwargs):
        # 白名单域名返回公网 IP，其他走真实解析
        if host and host.endswith("court.gov.cn"):
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.2.3.4", 443))]
        return _real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)

    assert _is_allowed_runtime_url("https://sub.court.gov.cn/page") is True
    assert _is_allowed_runtime_url("http://127.0.0.1/private") is False
    assert _is_allowed_runtime_url("https://example.com/redirected") is False


@pytest.mark.asyncio
async def test_mcp_tools_require_platform_admin(client, auth_client, admin_auth_client):
    anonymous = await client.get("/api/v1/mcp/tools")
    assert anonymous.status_code == 401

    forbidden = await auth_client.get("/api/v1/mcp/tools")
    assert forbidden.status_code == 403

    with patch("src.api.routes.mcp_routes.mcp_client_service.get_all_tools", new=AsyncMock(return_value=[{"name": "tool-a"}])):
        allowed = await admin_auth_client.get("/api/v1/mcp/tools")

    assert allowed.status_code == 200
    assert allowed.json() == [{"name": "tool-a"}]


@pytest.mark.asyncio
async def test_public_health_response_is_minimal(client):
    response = await client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"status"}
    assert payload["status"] in {"healthy", "degraded", "unhealthy"}
