from uuid import uuid4

import pytest
from sqlalchemy import select

from src.models.audit import AuditLog
from src.models.contract import Contract, ContractStatus
from src.models.payment import PaymentOrder
from src.services.esign_service import reset_esign_provider
from src.services.payment_service import RefundResult, reset_payment_providers


class _SuccessfulRefundProvider:
    async def refund(
        self,
        order_id: str,
        amount: float,
        reason: str,
        total_amount: float | None = None,
    ) -> RefundResult:
        return RefundResult(refund_id=f"refund-{order_id}", status="success", amount=amount)


@pytest.fixture(autouse=True)
def reset_provider_caches():
    reset_payment_providers()
    reset_esign_provider()
    yield
    reset_payment_providers()
    reset_esign_provider()


@pytest.mark.asyncio
async def test_payment_create_close_and_refund_write_audit_logs(
    auth_client,
    db_session,
    test_user,
    monkeypatch,
):
    monkeypatch.setattr(
        "src.services.refund_service.get_payment_provider",
        lambda _provider: _SuccessfulRefundProvider(),
    )

    create = await auth_client.post(
        "/api/v1/payments/orders",
        json={
            "type": "consultation_fee",
            "amount": 99.0,
            "description": "商业审计下单",
            "provider": "mock",
        },
        headers={"X-Request-ID": "payment-create-audit"},
    )
    assert create.status_code == 200
    created_order_id = create.json()["id"]

    close = await auth_client.post(
        f"/api/v1/payments/orders/{created_order_id}/close",
        headers={"X-Request-ID": "payment-close-audit"},
    )
    assert close.status_code == 200

    paid_order = PaymentOrder(
        id=str(uuid4()),
        user_id=test_user.id,
        order_type="consultation_fee",
        amount=199.0,
        status="paid",
        description="商业审计退款",
        payment_provider="mock",
    )
    db_session.add(paid_order)
    await db_session.flush()

    refund = await auth_client.post(
        f"/api/v1/payments/orders/{paid_order.id}/refund",
        json={"amount": 88.0, "reason": "审计退款"},
        headers={
            "Idempotency-Key": "commercial-audit-refund",
            "X-Request-ID": "payment-refund-audit",
        },
    )
    assert refund.status_code == 200

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.action.in_(
                [
                    "payment.order.create",
                    "payment.order.close",
                    "payment.order.refund",
                ]
            )
        )
    )
    logs = {log.action: log for log in result.scalars().all()}

    assert set(logs) == {
        "payment.order.create",
        "payment.order.close",
        "payment.order.refund",
    }
    assert logs["payment.order.create"].user_id == test_user.id
    assert logs["payment.order.create"].resource_id == created_order_id
    assert logs["payment.order.create"].new_value["provider"] == "mock"
    assert logs["payment.order.close"].old_value["status"] == "pending"
    assert logs["payment.order.close"].new_value["status"] == "closed"
    assert logs["payment.order.refund"].resource_id == paid_order.id
    assert logs["payment.order.refund"].old_value["status"] == "paid"
    assert logs["payment.order.refund"].new_value["refund_amount"] == 88.0
    assert logs["payment.order.refund"].extra_data["idempotency_key_present"] is True


@pytest.mark.asyncio
async def test_esign_create_sign_url_and_cancel_write_audit_logs(
    auth_client,
    db_session,
    test_user,
):
    contract = Contract(
        id=str(uuid4()),
        title="商业审计电签合同",
        contract_number=f"ESIGN-AUDIT-{uuid4().hex[:8]}",
        contract_type="service",
        status=ContractStatus.APPROVED,
        org_id=test_user.org_id,
    )
    db_session.add(contract)
    await db_session.flush()

    create = await auth_client.post(
        "/api/v1/esign/flows",
        json={
            "contract_id": contract.id,
            "title": "商业审计电签合同",
            "signers": [{"name": "张三"}],
            "document_url": "https://docs.example.invalid/contract.pdf",
        },
        headers={"X-Request-ID": "esign-create-audit"},
    )
    assert create.status_code == 200
    flow_payload = create.json()
    signer_id = next(iter(flow_payload["sign_urls"]))

    sign_url = await auth_client.get(
        f"/api/v1/esign/flows/{flow_payload['flow_id']}/sign-url/{signer_id}",
        headers={"X-Request-ID": "esign-sign-url-audit"},
    )
    assert sign_url.status_code == 200

    cancel = await auth_client.post(
        f"/api/v1/esign/flows/{flow_payload['flow_id']}/cancel?reason=用户取消",
        headers={"X-Request-ID": "esign-cancel-audit"},
    )
    assert cancel.status_code == 200

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.action.in_(
                [
                    "esign.flow.create",
                    "esign.flow.sign_url",
                    "esign.flow.cancel",
                ]
            )
        )
    )
    logs = {log.action: log for log in result.scalars().all()}

    assert set(logs) == {
        "esign.flow.create",
        "esign.flow.sign_url",
        "esign.flow.cancel",
    }
    assert logs["esign.flow.create"].resource_id == contract.id
    assert logs["esign.flow.create"].new_value["signers_count"] == 1
    assert logs["esign.flow.create"].new_value["has_document_url"] is True
    assert logs["esign.flow.sign_url"].new_value["signer_id"] == signer_id
    assert "sign_url" not in logs["esign.flow.sign_url"].new_value
    assert "mock-esign.example.com" not in str(logs["esign.flow.sign_url"].new_value)
    assert logs["esign.flow.cancel"].new_value["cancelled"] is True
    assert logs["esign.flow.cancel"].extra_data["reason_present"] is True
