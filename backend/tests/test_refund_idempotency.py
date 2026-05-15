import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.billing import Refund
from src.models.payment import PaymentOrder
from src.services.payment_service import RefundResult
from src.services.refund_service import RefundService


class CountingRefundProvider:
    def __init__(self):
        self.calls = 0
        self.lock = asyncio.Lock()

    async def refund(self, order_id, amount, reason, total_amount=None):
        async with self.lock:
            self.calls += 1
            call_number = self.calls
        return RefundResult(
            refund_id=f"refund-{call_number}",
            status="success",
            amount=amount,
        )


@pytest.mark.asyncio
async def test_payment_refund_idempotency_key_returns_existing_result(
    auth_client,
    db_session,
    test_user,
    monkeypatch,
):
    provider = CountingRefundProvider()
    monkeypatch.setattr(
        "src.services.refund_service.get_payment_provider",
        lambda _provider: provider,
    )
    order = PaymentOrder(
        id=str(uuid4()),
        user_id=test_user.id,
        order_type="consultation_fee",
        amount=199.0,
        status="paid",
        description="咨询费",
        payment_provider="mock",
    )
    db_session.add(order)
    await db_session.flush()

    body = {"amount": 99.0, "reason": "重复提交退款"}
    headers = {"Idempotency-Key": "refund-key-1"}
    first = await auth_client.post(
        f"/api/v1/payments/orders/{order.id}/refund",
        json=body,
        headers=headers,
    )
    second = await auth_client.post(
        f"/api/v1/payments/orders/{order.id}/refund",
        json=body,
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == "refunded"
    assert second.json()["status"] == "refunded"
    assert provider.calls == 1

    refunds = (
        (await db_session.execute(select(Refund).where(Refund.idempotency_key == "refund-key-1")))
        .scalars()
        .all()
    )
    assert len(refunds) == 1
    assert refunds[0].order_id == order.id
    assert refunds[0].amount == 99.0
    assert refunds[0].status == "processed"
    assert refunds[0].processor_transaction_id == "refund-1"


@pytest.mark.asyncio
async def test_payment_refund_rejects_reused_idempotency_key_for_other_order(
    auth_client,
    db_session,
    test_user,
    monkeypatch,
):
    provider = CountingRefundProvider()
    monkeypatch.setattr(
        "src.services.refund_service.get_payment_provider",
        lambda _provider: provider,
    )
    orders = []
    for index in range(2):
        order = PaymentOrder(
            id=str(uuid4()),
            user_id=test_user.id,
            order_type="consultation_fee",
            amount=199.0,
            status="paid",
            description=f"咨询费 {index}",
            payment_provider="mock",
        )
        db_session.add(order)
        orders.append(order)
    await db_session.flush()

    first = await auth_client.post(
        f"/api/v1/payments/orders/{orders[0].id}/refund",
        json={"amount": 99.0, "reason": "退款"},
        headers={"Idempotency-Key": "refund-conflict-key"},
    )
    second = await auth_client.post(
        f"/api/v1/payments/orders/{orders[1].id}/refund",
        json={"amount": 99.0, "reason": "退款"},
        headers={"Idempotency-Key": "refund-conflict-key"},
    )

    assert first.status_code == 200
    assert second.status_code == 400
    assert "幂等键" in second.json()["detail"]
    assert provider.calls == 1

    refunds = (
        (
            await db_session.execute(
                select(Refund).where(Refund.idempotency_key == "refund-conflict-key")
            )
        )
        .scalars()
        .all()
    )
    assert len(refunds) == 1


@pytest.mark.asyncio
async def test_billing_refund_request_idempotency_key_reuses_pending_refund(
    auth_client,
    db_session,
    test_user,
):
    order = PaymentOrder(
        id=str(uuid4()),
        user_id=test_user.id,
        order_type="consultation_fee",
        amount=199.0,
        status="paid",
        description="咨询费",
        payment_provider="mock",
    )
    db_session.add(order)
    await db_session.flush()

    body = {
        "order_id": order.id,
        "amount": 99.0,
        "reason": "提交退款申请",
        "idempotency_key": "refund-request-key-1",
    }
    first = await auth_client.post("/api/v1/billing/refunds", json=body)
    second = await auth_client.post("/api/v1/billing/refunds", json=body)

    assert first.status_code == 200
    assert second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["code"] == 200
    assert second_payload["code"] == 200
    assert first_payload["data"]["id"] == second_payload["data"]["id"]

    refunds = (
        (
            await db_session.execute(
                select(Refund).where(Refund.idempotency_key == "refund-request-key-1")
            )
        )
        .scalars()
        .all()
    )
    assert len(refunds) == 1
    assert refunds[0].status == "pending"


@pytest.mark.asyncio
async def test_refund_idempotency_key_concurrent_requests_create_one_refund(
    db_session,
    test_user,
    monkeypatch,
):
    provider = CountingRefundProvider()
    monkeypatch.setattr(
        "src.services.refund_service.get_payment_provider",
        lambda _provider: provider,
    )
    order = PaymentOrder(
        id=str(uuid4()),
        user_id=test_user.id,
        order_type="consultation_fee",
        amount=199.0,
        status="paid",
        description="咨询费",
        payment_provider="mock",
    )
    db_session.add(order)
    await db_session.commit()

    session_factory = async_sessionmaker(
        db_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async def request_refund_once():
        async with session_factory() as session:
            return await RefundService(session).refund(
                user_id=test_user.id,
                order_id=order.id,
                amount=99.0,
                reason="并发退款",
                idempotency_key="refund-concurrent-key",
            )

    results = await asyncio.gather(*(request_refund_once() for _ in range(100)))

    assert len({result["id"] for result in results}) == 1
    assert provider.calls == 1
    async with session_factory() as session:
        refunds = (
            (
                await session.execute(
                    select(Refund).where(Refund.idempotency_key == "refund-concurrent-key")
                )
            )
            .scalars()
            .all()
        )
        assert len(refunds) == 1
        assert refunds[0].status == "processed"
