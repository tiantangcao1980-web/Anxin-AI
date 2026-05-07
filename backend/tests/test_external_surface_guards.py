import hashlib
import hmac
import json
import time
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, patch
from urllib.parse import urlencode
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.core.config import settings
from src.core.security import create_access_token
from src.models.audit import AuditLog
from src.models.billing import BillingPlan, Subscription
from src.models.contract import Contract, ContractStatus
from src.models.mcp_config import McpServerConfig
from src.models.payment import PaymentOrder
from src.models.user import Organization, User
from src.models.webhook import WebhookReceived
from src.services.crawler_service import CrawlerTask, _is_allowed_runtime_url, crawler_service
from src.services.webhook_idempotency_service import build_webhook_idempotency_key
from src.services.webhook_retry_service import retry_due_failed_webhooks


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
async def test_wechat_payment_webhook_updates_order_status(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "WECHAT_PAY_WEBHOOK_SECRET", "wechat-secret")
    order = PaymentOrder(
        id=str(uuid4()),
        user_id=str(uuid4()),
        order_type="consultation_fee",
        amount=199.0,
        status="pending",
        description="咨询费",
        payment_provider="wechat_pay",
    )
    db_session.add(order)
    await db_session.flush()
    body = json.dumps(
        {
            "out_trade_no": order.id,
            "trade_state": "SUCCESS",
            "transaction_id": "wx-txn-1",
        }
    ).encode("utf-8")
    timestamp = str(int(time.time()))
    signature = hmac.new(
        b"wechat-secret",
        f"{timestamp}.".encode() + body,
        hashlib.sha256,
    ).hexdigest()

    response = await client.post(
        "/api/v1/payments/webhook/wechat",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Wechat-Signature": signature,
            "X-Webhook-Timestamp": timestamp,
        },
    )

    assert response.status_code == 200
    await db_session.refresh(order)
    assert order.status == "paid"
    assert order.transaction_id == "wx-txn-1"
    assert order.paid_at is not None
    idempotency_key = build_webhook_idempotency_key("wechat_pay", payload=json.loads(body), body=body)
    records = (
        await db_session.execute(
            select(WebhookReceived).where(
                WebhookReceived.scope == "wechat_pay",
                WebhookReceived.idempotency_key == idempotency_key,
            )
        )
    ).scalars().all()
    assert len(records) == 1
    assert records[0].scope == "wechat_pay"
    assert records[0].status == "processed"


@pytest.mark.asyncio
async def test_wechat_payment_webhook_duplicate_body_is_idempotent(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "WECHAT_PAY_WEBHOOK_SECRET", "wechat-secret")
    order = PaymentOrder(
        id=str(uuid4()),
        user_id=str(uuid4()),
        order_type="consultation_fee",
        amount=199.0,
        status="pending",
        description="咨询费",
        payment_provider="wechat_pay",
    )
    db_session.add(order)
    await db_session.flush()
    body = json.dumps(
        {
            "out_trade_no": order.id,
            "trade_state": "SUCCESS",
            "transaction_id": "wx-txn-duplicate",
        }
    ).encode("utf-8")

    async def post_with_timestamp(ts: str):
        signature = hmac.new(
            b"wechat-secret",
            f"{ts}.".encode() + body,
            hashlib.sha256,
        ).hexdigest()
        return await client.post(
            "/api/v1/payments/webhook/wechat",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Wechat-Signature": signature,
                "X-Webhook-Timestamp": ts,
            },
        )

    timestamp = int(time.time())
    first = await post_with_timestamp(str(timestamp))
    assert first.status_code == 200

    order.transaction_id = "manual-after-first"
    await db_session.flush()
    second = await post_with_timestamp(str(timestamp + 1))

    assert second.status_code == 200
    await db_session.refresh(order)
    assert order.transaction_id == "manual-after-first"
    idempotency_key = build_webhook_idempotency_key("wechat_pay", payload=json.loads(body), body=body)
    records = (
        await db_session.execute(
            select(WebhookReceived).where(
                WebhookReceived.scope == "wechat_pay",
                WebhookReceived.idempotency_key == idempotency_key,
            )
        )
    ).scalars().all()
    assert len(records) == 1
    assert records[0].status == "processed"
    assert records[0].retry_count == 0


@pytest.mark.asyncio
async def test_webhook_handler_records_payment_business_failure(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "WECHAT_PAY_WEBHOOK_SECRET", "wechat-secret")
    body = json.dumps({"trade_state": "SUCCESS"}).encode("utf-8")
    timestamp = str(int(time.time()))
    signature = hmac.new(
        b"wechat-secret",
        f"{timestamp}.".encode() + body,
        hashlib.sha256,
    ).hexdigest()

    response = await client.post(
        "/api/v1/payments/webhook/wechat",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Wechat-Signature": signature,
            "X-Webhook-Timestamp": timestamp,
        },
    )

    assert response.status_code == 400
    assert "Missing order id" in response.json()["detail"]
    idempotency_key = build_webhook_idempotency_key("wechat_pay", payload=json.loads(body), body=body)
    records = (
        await db_session.execute(
            select(WebhookReceived).where(
                WebhookReceived.scope == "wechat_pay",
                WebhookReceived.idempotency_key == idempotency_key,
            )
        )
    ).scalars().all()
    assert len(records) == 1
    assert records[0].status == "failed"
    assert records[0].retry_count == 1
    assert records[0].next_retry_at is not None
    assert "Missing order id" in records[0].error
    await db_session.delete(records[0])
    await db_session.flush()


@pytest.mark.asyncio
async def test_alipay_payment_webhook_updates_subscription(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "ALIPAY_WEBHOOK_SECRET", "alipay-secret")
    user_id = str(uuid4())
    plan = BillingPlan(
        name="专业版",
        code=f"pro-{uuid4().hex[:8]}",
        billing_mode="monthly",
        base_price=299.0,
    )
    db_session.add(plan)
    await db_session.flush()
    subscription = Subscription(
        user_id=user_id,
        plan_id=plan.id,
        status="trial",
        current_period_start=date.today(),
        current_period_end=date.today() + timedelta(days=30),
    )
    db_session.add(subscription)
    await db_session.flush()
    order = PaymentOrder(
        id=str(uuid4()),
        user_id=user_id,
        order_type="subscription",
        amount=299.0,
        status="pending",
        description="订阅专业版",
        related_id=subscription.id,
        payment_provider="alipay",
    )
    db_session.add(order)
    await db_session.flush()
    body = urlencode(
        {
            "out_trade_no": order.id,
            "trade_status": "TRADE_SUCCESS",
            "trade_no": "ali-txn-1",
        }
    ).encode("utf-8")
    timestamp = str(int(time.time()))
    signature = hmac.new(
        b"alipay-secret",
        f"{timestamp}.".encode() + body,
        hashlib.sha256,
    ).hexdigest()

    response = await client.post(
        "/api/v1/payments/webhook/alipay",
        content=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Alipay-Signature": signature,
            "X-Webhook-Timestamp": timestamp,
        },
    )

    assert response.status_code == 200
    await db_session.refresh(order)
    await db_session.refresh(subscription)
    assert order.status == "paid"
    assert order.transaction_id == "ali-txn-1"
    assert subscription.status == "active"
    assert subscription.last_payment_id == order.id


@pytest.mark.asyncio
async def test_esign_webhook_accepts_valid_signature(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "ESIGN_WEBHOOK_SECRET", "esign-secret")
    contract = Contract(
        id=str(uuid4()),
        title="电签测试合同",
        contract_number=f"ESIGN-{uuid4().hex[:8]}",
        contract_type="service",
        status=ContractStatus.APPROVED,
    )
    db_session.add(contract)
    await db_session.flush()
    body = json.dumps(
        {
            "flow_id": "f1",
            "contract_id": contract.id,
            "action": "signed",
            "status": "completed",
        }
    ).encode("utf-8")
    timestamp = str(int(time.time()))
    signature = hmac.new(b"esign-secret", f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()

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
    await db_session.refresh(contract)
    assert contract.status == ContractStatus.SIGNED
    assert contract.sign_date == date.today()
    idempotency_key = build_webhook_idempotency_key("esign", payload=json.loads(body), body=body)
    records = (
        await db_session.execute(
            select(WebhookReceived).where(
                WebhookReceived.scope == "esign",
                WebhookReceived.idempotency_key == idempotency_key,
            )
        )
    ).scalars().all()
    assert len(records) == 1
    assert records[0].scope == "esign"
    assert records[0].status == "processed"


@pytest.mark.asyncio
async def test_create_sign_flow_persists_provider_flow_mapping(auth_client, db_session, test_user):
    contract = Contract(
        id=str(uuid4()),
        title="待发起电签合同",
        contract_number=f"ESIGN-FLOW-{uuid4().hex[:8]}",
        contract_type="service",
        status=ContractStatus.APPROVED,
        org_id=test_user.org_id,
    )
    db_session.add(contract)
    await db_session.flush()

    response = await auth_client.post(
        "/api/v1/esign/flows",
        json={
            "contract_id": contract.id,
            "title": "待发起电签合同",
            "signers": [{"name": "张三"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    await db_session.refresh(contract)
    assert payload["flow_id"] == contract.esign_flow_id
    assert contract.esign_provider == "MockESignProvider"


@pytest.mark.asyncio
async def test_esign_flow_creation_requires_contract_org_scope(
    outsider_auth_client,
    db_session,
    test_user,
):
    contract = Contract(
        id=str(uuid4()),
        title="跨组织电签合同",
        contract_number=f"ESIGN-XORG-{uuid4().hex[:8]}",
        contract_type="service",
        status=ContractStatus.APPROVED,
        org_id=test_user.org_id,
    )
    db_session.add(contract)
    await db_session.flush()

    response = await outsider_auth_client.post(
        "/api/v1/esign/flows",
        json={
            "contract_id": contract.id,
            "title": "跨组织电签合同",
            "signers": [{"name": "张三"}],
        },
    )

    assert response.status_code == 404
    await db_session.refresh(contract)
    assert contract.esign_flow_id is None


@pytest.mark.asyncio
async def test_esign_flow_operations_require_flow_org_scope(
    outsider_auth_client,
    db_session,
    test_user,
):
    contract = Contract(
        id=str(uuid4()),
        title="跨组织签署流程",
        contract_number=f"ESIGN-FLOW-XORG-{uuid4().hex[:8]}",
        contract_type="service",
        status=ContractStatus.APPROVED,
        org_id=test_user.org_id,
        esign_flow_id="provider-flow-xorg",
        esign_provider="MockESignProvider",
    )
    db_session.add(contract)
    await db_session.flush()

    status_response = await outsider_auth_client.get("/api/v1/esign/flows/provider-flow-xorg")
    sign_url_response = await outsider_auth_client.get(
        "/api/v1/esign/flows/provider-flow-xorg/sign-url/signer-1"
    )
    cancel_response = await outsider_auth_client.post("/api/v1/esign/flows/provider-flow-xorg/cancel")

    assert status_response.status_code == 404
    assert sign_url_response.status_code == 404
    assert cancel_response.status_code == 404


@pytest.mark.asyncio
async def test_esign_webhook_resolves_contract_by_flow_id(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "ESIGN_WEBHOOK_SECRET", "esign-secret")
    contract = Contract(
        id=str(uuid4()),
        title="电签 flow 映射合同",
        contract_number=f"ESIGN-FLOW-{uuid4().hex[:8]}",
        contract_type="service",
        status=ContractStatus.APPROVED,
        esign_flow_id="provider-flow-1",
        esign_provider="MockESignProvider",
    )
    db_session.add(contract)
    await db_session.flush()
    body = json.dumps(
        {
            "flow_id": "provider-flow-1",
            "action": "signed",
            "status": "completed",
        }
    ).encode("utf-8")
    timestamp = str(int(time.time()))
    signature = hmac.new(b"esign-secret", f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()

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
    assert response.json()["data"]["contract_id"] == contract.id
    await db_session.refresh(contract)
    assert contract.status == ContractStatus.SIGNED
    assert contract.sign_date == date.today()


@pytest.mark.asyncio
async def test_esign_webhook_duplicate_body_is_idempotent(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "ESIGN_WEBHOOK_SECRET", "esign-secret")
    contract = Contract(
        id=str(uuid4()),
        title="电签幂等测试合同",
        contract_number=f"ESIGN-{uuid4().hex[:8]}",
        contract_type="service",
        status=ContractStatus.APPROVED,
    )
    db_session.add(contract)
    await db_session.flush()
    body = json.dumps(
        {
            "flow_id": "f-idempotent",
            "contract_id": contract.id,
            "action": "signed",
            "status": "completed",
        }
    ).encode("utf-8")

    async def post_with_timestamp(ts: str):
        signature = hmac.new(
            b"esign-secret",
            f"{ts}.".encode() + body,
            hashlib.sha256,
        ).hexdigest()
        return await client.post(
            "/api/v1/esign/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-ESign-Signature": signature,
                "X-Webhook-Timestamp": ts,
            },
        )

    timestamp = int(time.time())
    first = await post_with_timestamp(str(timestamp))
    assert first.status_code == 200

    contract.status = ContractStatus.APPROVED
    contract.sign_date = None
    await db_session.flush()
    second = await post_with_timestamp(str(timestamp + 1))

    assert second.status_code == 200
    await db_session.refresh(contract)
    assert contract.status == ContractStatus.APPROVED
    assert contract.sign_date is None
    idempotency_key = build_webhook_idempotency_key("esign", payload=json.loads(body), body=body)
    records = (
        await db_session.execute(
            select(WebhookReceived).where(
                WebhookReceived.scope == "esign",
                WebhookReceived.idempotency_key == idempotency_key,
            )
        )
    ).scalars().all()
    assert len(records) == 1
    assert records[0].status == "processed"
    assert records[0].retry_count == 0


@pytest.mark.asyncio
async def test_esign_webhook_event_id_is_idempotent_across_retry_bodies(
    client, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "ESIGN_WEBHOOK_SECRET", "esign-secret")
    event_id = f"esign-event-{uuid4().hex}"
    contract = Contract(
        id=str(uuid4()),
        title="电签官方事件ID幂等合同",
        contract_number=f"ESIGN-EVENT-{uuid4().hex[:8]}",
        contract_type="service",
        status=ContractStatus.APPROVED,
    )
    db_session.add(contract)
    await db_session.flush()

    async def post_payload(payload: dict, ts: str):
        body = json.dumps(payload).encode("utf-8")
        signature = hmac.new(
            b"esign-secret",
            f"{ts}.".encode() + body,
            hashlib.sha256,
        ).hexdigest()
        return await client.post(
            "/api/v1/esign/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-ESign-Signature": signature,
                "X-Webhook-Timestamp": ts,
            },
        )

    timestamp = int(time.time())
    first = await post_payload(
        {
            "eventId": event_id,
            "eventType": "SIGN_COMPLETED",
            "flow_id": "f-event-id",
            "contract_id": contract.id,
            "status": "completed",
            "timestamp": "first-delivery",
        },
        str(timestamp),
    )
    assert first.status_code == 200

    contract.status = ContractStatus.APPROVED
    contract.sign_date = None
    await db_session.flush()
    second = await post_payload(
        {
            "eventId": event_id,
            "eventType": "SIGN_COMPLETED",
            "flow_id": "f-event-id",
            "contract_id": contract.id,
            "status": "completed",
            "timestamp": "retry-delivery",
        },
        str(timestamp + 1),
    )

    assert second.status_code == 200
    await db_session.refresh(contract)
    assert contract.status == ContractStatus.APPROVED
    assert contract.sign_date is None
    records = (
        await db_session.execute(
            select(WebhookReceived).where(
                WebhookReceived.scope == "esign",
                WebhookReceived.idempotency_key == event_id,
            )
        )
    ).scalars().all()
    assert len(records) == 1
    assert records[0].status == "processed"
    assert records[0].retry_count == 0


@pytest.mark.asyncio
async def test_esignbao_official_webhook_verifies_tsign_headers(
    client, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "ESIGN_OFFICIAL_WEBHOOK_ENABLED", True)
    monkeypatch.setattr(settings, "ESIGN_BAO_APP_ID", "app-1")
    monkeypatch.setattr(settings, "ESIGN_BAO_APP_SECRET", "esignbao-secret")
    contract = Contract(
        id=str(uuid4()),
        title="e签宝官方验签合同",
        contract_number=f"ESIGN-BAO-{uuid4().hex[:8]}",
        contract_type="service",
        status=ContractStatus.APPROVED,
    )
    db_session.add(contract)
    await db_session.flush()

    body = json.dumps(
        {
            "eventId": f"esignbao-event-{uuid4().hex}",
            "eventType": "SIGN_FLOW_UPDATE",
            "flow_id": "esignbao-flow-1",
            "contract_id": contract.id,
            "action": "SIGN_FLOW_UPDATE",
            "status": "completed",
        }
    ).encode("utf-8")
    timestamp = str(int(time.time()))
    query_values = "acct-1ord-1"
    signature = hmac.new(
        b"esignbao-secret",
        timestamp.encode("utf-8") + query_values.encode("utf-8") + body,
        hashlib.sha256,
    ).hexdigest()

    response = await client.post(
        "/api/v1/esign/webhook?accountId=acct-1&orderNo=ord-1",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Tsign-Open-App-Id": "app-1",
            "X-Tsign-Open-TIMESTAMP": timestamp,
            "X-Tsign-Open-SIGNATURE-ALGORITHM": "hmac-sha256",
            "X-Tsign-Open-SIGNATURE": signature,
        },
    )

    assert response.status_code == 200
    await db_session.refresh(contract)
    assert contract.status == ContractStatus.SIGNED
    assert contract.sign_date == date.today()


@pytest.mark.asyncio
async def test_fadada_official_webhook_verifies_fasc_headers(
    client, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "ESIGN_OFFICIAL_WEBHOOK_ENABLED", True)
    monkeypatch.setattr(settings, "FADADA_APP_ID", "fadada-app-1")
    monkeypatch.setattr(settings, "FADADA_APP_SECRET", "fadada-secret")
    contract = Contract(
        id=str(uuid4()),
        title="法大大官方验签合同",
        contract_number=f"FADADA-{uuid4().hex[:8]}",
        contract_type="service",
        status=ContractStatus.APPROVED,
    )
    db_session.add(contract)
    await db_session.flush()

    biz_content = json.dumps(
        {
            "eventTime": str(int(time.time() * 1000)),
            "signTaskId": "fadada-task-1",
            "transReferenceId": contract.id,
            "signTaskStatus": "sign-task-signed",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    timestamp = str(int(time.time() * 1000))
    nonce = uuid4().hex
    event = "sign-task-signed"
    sign_params = {
        "X-FASC-App-Id": "fadada-app-1",
        "X-FASC-Sign-Type": "HMAC-SHA256",
        "X-FASC-Timestamp": timestamp,
        "X-FASC-Nonce": nonce,
        "X-FASC-Event": event,
        "bizContent": biz_content,
    }
    sort_content = "&".join(f"{key}={sign_params[key]}" for key in sorted(sign_params))
    sign_text = hashlib.sha256(sort_content.encode("utf-8")).hexdigest().lower()
    temporary_key = hmac.new(b"fadada-secret", timestamp.encode("utf-8"), hashlib.sha256).digest()
    signature = hmac.new(temporary_key, sign_text.encode("utf-8"), hashlib.sha256).hexdigest()
    body = urlencode({"bizContent": biz_content}).encode("utf-8")

    response = await client.post(
        "/api/v1/esign/webhook",
        content=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-FASC-App-Id": "fadada-app-1",
            "X-FASC-Sign-Type": "HMAC-SHA256",
            "X-FASC-Timestamp": timestamp,
            "X-FASC-Nonce": nonce,
            "X-FASC-Event": event,
            "X-FASC-Sign": signature,
        },
    )

    assert response.status_code == 200
    await db_session.refresh(contract)
    assert contract.status == ContractStatus.SIGNED
    assert contract.sign_date == date.today()


@pytest.mark.asyncio
async def test_esign_webhook_rejects_replay(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "ESIGN_WEBHOOK_SECRET", "esign-secret")
    contract = Contract(
        id=str(uuid4()),
        title="电签重放测试合同",
        contract_number=f"ESIGN-{uuid4().hex[:8]}",
        contract_type="service",
        status=ContractStatus.APPROVED,
    )
    db_session.add(contract)
    await db_session.flush()
    body = json.dumps(
        {
            "flow_id": "f2",
            "contract_id": contract.id,
            "action": "completed",
            "status": "pending",
        }
    ).encode("utf-8")
    timestamp = str(int(time.time()))
    signature = hmac.new(b"esign-secret", f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
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
async def test_oa_user_sync_requires_org_admin(auth_client, admin_auth_client):
    with patch("src.api.routes.integrations.oa_service.sync_org_structure", new=AsyncMock(return_value={"synced_count": 0})):
        forbidden = await auth_client.post("/api/v1/integrations/oa/sync/users", json={"provider": "feishu"})
        allowed = await admin_auth_client.post("/api/v1/integrations/oa/sync/users", json={"provider": "feishu"})

    assert forbidden.status_code == 403
    assert allowed.status_code == 200


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
async def test_mcp_server_management_requires_system_admin(client, admin_auth_client, db_session, test_organization):
    org_admin = User(
        id=str(uuid4()),
        email=f"mcp-org-admin-{uuid4().hex[:8]}@example.com",
        name="MCP 组织管理员",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
        role="org_admin",
    )
    db_session.add(org_admin)
    await db_session.flush()

    org_admin_response = await client.get(
        "/api/v1/mcp/servers",
        headers={"Authorization": f"Bearer {create_access_token(user_id=org_admin.id)}"},
    )
    platform_admin_response = await admin_auth_client.get("/api/v1/mcp/servers")

    assert org_admin_response.status_code == 403
    assert platform_admin_response.status_code == 200


@pytest.mark.asyncio
async def test_mcp_server_create_writes_masked_audit_log(admin_auth_client, db_session):
    response = await admin_auth_client.post(
        "/api/v1/mcp/servers",
        json={
            "name": "ci-mcp",
            "description": "test server",
            "type": "stdio",
            "command": "npx",
            "args": ["tool"],
            "env": {"API_TOKEN": "secret-value"},
            "is_enabled": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["env_keys"] == ["API_TOKEN"]

    audit_result = await db_session.execute(select(AuditLog).where(AuditLog.action == "mcp.server.create"))
    audit_log = audit_result.scalar_one()
    assert audit_log.resource_id == payload["id"]
    assert audit_log.extra_data == {"source": "mcp"}
    assert audit_log.new_value["env_keys"] == ["API_TOKEN"]
    assert "secret-value" not in json.dumps(audit_log.new_value, ensure_ascii=False)


@pytest.mark.asyncio
async def test_mcp_server_create_rejects_unapproved_sse_in_staging(admin_auth_client, db_session, monkeypatch):
    from src.services import mcp_client_service

    monkeypatch.setattr(mcp_client_service.settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(mcp_client_service.settings, "MCP_SSE_ALLOWED_SCHEMES", ["https"])
    monkeypatch.setattr(mcp_client_service.settings, "MCP_SSE_ALLOWED_HOSTS", [])

    response = await admin_auth_client.post(
        "/api/v1/mcp/servers",
        json={
            "name": "ci-mcp-blocked",
            "description": "blocked server",
            "type": "sse",
            "url": "https://mcp.example.com/sse",
            "is_enabled": False,
        },
    )

    assert response.status_code == 400
    assert "MCP_SSE_ALLOWED_HOSTS" in response.json()["detail"]
    result = await db_session.execute(
        select(McpServerConfig).where(McpServerConfig.name == "ci-mcp-blocked")
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_admin_webhooks_expose_idempotency_records(auth_client, admin_auth_client, db_session):
    record = WebhookReceived(
        scope="wechat_pay",
        idempotency_key=f"evt-{uuid4().hex}",
        payload={"out_trade_no": "order-1"},
        status="failed",
        error="Payment order not found",
        retry_count=1,
    )
    other = WebhookReceived(
        scope="esign",
        idempotency_key=f"evt-{uuid4().hex}",
        payload={"contract_id": "contract-1"},
        status="processed",
    )
    db_session.add_all([record, other])
    await db_session.flush()

    forbidden = await auth_client.get("/api/v1/admin/webhooks")
    assert forbidden.status_code == 403

    response = await admin_auth_client.get("/api/v1/admin/webhooks?scope=wechat_pay&status=failed")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    item_by_key = {item["idempotency_key"]: item for item in payload["items"]}
    assert record.idempotency_key in item_by_key
    assert item_by_key[record.idempotency_key]["status"] == "failed"
    assert item_by_key[record.idempotency_key]["error"] == "Payment order not found"
    assert payload["stats"]["failed"] >= 1


@pytest.mark.asyncio
async def test_admin_can_retry_failed_payment_webhook_record(auth_client, admin_auth_client, db_session):
    order = PaymentOrder(
        id=str(uuid4()),
        user_id=str(uuid4()),
        order_type="consultation_fee",
        amount=199.0,
        status="pending",
        description="咨询费",
        payment_provider="wechat_pay",
    )
    record = WebhookReceived(
        scope="wechat_pay",
        idempotency_key=f"evt-{uuid4().hex}",
        payload={
            "out_trade_no": order.id,
            "trade_state": "SUCCESS",
            "transaction_id": "wx-retry-1",
        },
        status="failed",
        error="Payment order not found",
        retry_count=1,
    )
    db_session.add_all([order, record])
    await db_session.flush()

    forbidden = await auth_client.post(f"/api/v1/admin/webhooks/{record.id}/retry")
    assert forbidden.status_code == 403

    response = await admin_auth_client.post(f"/api/v1/admin/webhooks/{record.id}/retry")
    assert response.status_code == 200
    payload = response.json()
    assert payload["record"]["status"] == "processed"
    assert payload["record"]["retry_count"] == 1
    assert payload["result"]["order_id"] == order.id

    await db_session.refresh(order)
    await db_session.refresh(record)
    assert order.status == "paid"
    assert order.transaction_id == "wx-retry-1"
    assert record.status == "processed"
    assert record.error is None


@pytest.mark.asyncio
async def test_admin_webhook_retry_keeps_failure_and_increments_retry_count(admin_auth_client, db_session):
    record = WebhookReceived(
        scope="wechat_pay",
        idempotency_key=f"evt-{uuid4().hex}",
        payload={"trade_state": "SUCCESS"},
        status="failed",
        error="previous failure",
        retry_count=1,
    )
    db_session.add(record)
    await db_session.flush()

    response = await admin_auth_client.post(f"/api/v1/admin/webhooks/{record.id}/retry")
    assert response.status_code == 400
    assert "Missing order id" in response.json()["detail"]

    await db_session.refresh(record)
    assert record.status == "failed"
    assert record.retry_count == 2
    assert record.last_retry_at is not None
    assert record.next_retry_at is not None
    assert "Missing order id" in record.error


@pytest.mark.asyncio
async def test_webhook_retry_worker_retries_due_failed_records(db_session):
    order = PaymentOrder(
        id=str(uuid4()),
        user_id=str(uuid4()),
        order_type="consultation_fee",
        amount=199.0,
        status="pending",
        description="咨询费",
        payment_provider="wechat_pay",
    )
    due = WebhookReceived(
        scope="wechat_pay",
        idempotency_key=f"evt-{uuid4().hex}",
        payload={
            "out_trade_no": order.id,
            "trade_state": "SUCCESS",
            "transaction_id": "wx-worker-1",
        },
        status="failed",
        retry_count=1,
        next_retry_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    not_due = WebhookReceived(
        scope="wechat_pay",
        idempotency_key=f"evt-{uuid4().hex}",
        payload={"trade_state": "SUCCESS"},
        status="failed",
        retry_count=1,
        next_retry_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db_session.add_all([order, due, not_due])
    await db_session.flush()

    summary = await retry_due_failed_webhooks(
        db_session,
        now=datetime.now(UTC),
        limit=10,
        max_attempts=5,
    )

    assert summary == {"attempted": 1, "succeeded": 1, "failed": 0}
    await db_session.refresh(order)
    await db_session.refresh(due)
    await db_session.refresh(not_due)
    assert order.status == "paid"
    assert order.transaction_id == "wx-worker-1"
    assert due.status == "processed"
    assert due.next_retry_at is None
    assert not_due.status == "failed"
    assert not_due.retry_count == 1


@pytest.mark.asyncio
async def test_webhook_retry_worker_respects_max_attempts(db_session):
    record = WebhookReceived(
        scope="wechat_pay",
        idempotency_key=f"evt-{uuid4().hex}",
        payload={"trade_state": "SUCCESS"},
        status="failed",
        retry_count=5,
        next_retry_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    db_session.add(record)
    await db_session.flush()

    summary = await retry_due_failed_webhooks(
        db_session,
        now=datetime.now(UTC),
        limit=10,
        max_attempts=5,
    )

    assert summary == {"attempted": 0, "succeeded": 0, "failed": 0}
    await db_session.refresh(record)
    assert record.status == "failed"
    assert record.retry_count == 5


@pytest.mark.asyncio
async def test_metrics_exports_webhook_status_counts(client, db_session):
    db_session.add_all(
        [
            WebhookReceived(
                scope="wechat_pay",
                idempotency_key=f"evt-{uuid4().hex}",
                payload={"out_trade_no": "order-1"},
                status="failed",
            ),
            WebhookReceived(
                scope="esign",
                idempotency_key=f"evt-{uuid4().hex}",
                payload={"contract_id": "contract-1"},
                status="processing",
            ),
        ]
    )
    await db_session.flush()

    response = await client.get("/api/v1/metrics")
    assert response.status_code == 200
    text = response.text
    assert "anxin_webhook_received_total" in text
    assert "anxin_webhook_failed_total" in text
    assert "anxin_webhook_processing" in text


@pytest.mark.asyncio
async def test_public_health_response_is_minimal(client):
    response = await client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"status"}
    assert payload["status"] in {"healthy", "degraded", "unhealthy"}
