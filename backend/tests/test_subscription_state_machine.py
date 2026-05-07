import hashlib
import hmac
import time
from datetime import date, timedelta
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.core.config import settings
from src.models.billing import BillingPlan, Subscription, SubscriptionEvent
from src.models.payment import PaymentOrder
from src.services.payment_webhook_service import apply_payment_webhook
from src.services.subscription_service import SubscriptionService


async def _events_for(db_session, subscription_id: str) -> list[SubscriptionEvent]:
    result = await db_session.execute(
        select(SubscriptionEvent)
        .where(SubscriptionEvent.subscription_id == subscription_id)
        .order_by(SubscriptionEvent.created_at.asc())
    )
    return list(result.scalars().all())


@pytest.mark.asyncio
async def test_create_subscription_starts_pending_and_records_event(
    db_session,
    test_user,
):
    plan = BillingPlan(
        name="专业版",
        code=f"pro-{uuid4().hex[:8]}",
        billing_mode="monthly",
        base_price=299.0,
    )
    db_session.add(plan)
    await db_session.flush()

    result = await SubscriptionService(db_session).create_subscription(
        user_id=test_user.id,
        plan_id=plan.id,
    )

    subscription = await db_session.get(Subscription, result["subscription"]["id"])
    order = await db_session.get(PaymentOrder, result["payment_order"]["id"])
    assert subscription.status == "pending"
    assert order.status == "pending"
    assert order.related_id == subscription.id
    assert subscription.last_payment_id == order.id

    events = await _events_for(db_session, subscription.id)
    assert [(event.from_status, event.to_status, event.event_type) for event in events] == [
        (None, "pending", "created")
    ]


@pytest.mark.asyncio
async def test_trial_to_paid_records_activation_event(db_session, test_user):
    plan = BillingPlan(
        name="试用转付费套餐",
        code=f"trial-upgrade-{uuid4().hex[:8]}",
        billing_mode="monthly",
        base_price=199.0,
    )
    db_session.add(plan)
    await db_session.flush()
    subscription = Subscription(
        user_id=test_user.id,
        plan_id=plan.id,
        status="trial",
        current_period_start=date.today(),
        current_period_end=date.today() + timedelta(days=3),
        auto_renew=False,
    )
    db_session.add(subscription)
    await db_session.flush()

    await SubscriptionService(db_session).activate_or_renew_from_payment(
        subscription,
        payment_id="pay-trial-upgrade",
    )
    await db_session.flush()

    assert subscription.status == "active"
    assert subscription.last_payment_id == "pay-trial-upgrade"
    assert subscription.current_period_end == date.today() + timedelta(days=30)
    events = await _events_for(db_session, subscription.id)
    assert [(event.from_status, event.to_status, event.event_type) for event in events] == [
        ("trial", "active", "activated")
    ]


@pytest.mark.asyncio
async def test_active_subscription_renewal_extends_period_once(db_session, test_user):
    plan = BillingPlan(
        name="续费套餐",
        code=f"renew-{uuid4().hex[:8]}",
        billing_mode="monthly",
        base_price=299.0,
    )
    db_session.add(plan)
    await db_session.flush()
    original_end = date.today() + timedelta(days=10)
    subscription = Subscription(
        user_id=test_user.id,
        plan_id=plan.id,
        status="active",
        current_period_start=date.today() - timedelta(days=20),
        current_period_end=original_end,
        last_payment_id="pay-old",
    )
    db_session.add(subscription)
    await db_session.flush()

    service = SubscriptionService(db_session)
    await service.activate_or_renew_from_payment(
        subscription,
        payment_id="pay-renewal",
    )
    await service.activate_or_renew_from_payment(
        subscription,
        payment_id="pay-renewal",
    )
    await db_session.flush()

    assert subscription.status == "active"
    assert subscription.last_payment_id == "pay-renewal"
    assert subscription.current_period_end == original_end + timedelta(days=30)
    events = await _events_for(db_session, subscription.id)
    assert [(event.from_status, event.to_status, event.event_type) for event in events] == [
        ("active", "active", "renewed"),
        ("active", "active", "payment_duplicate"),
    ]


@pytest.mark.asyncio
async def test_refund_payment_webhook_expires_subscription(
    client,
    db_session,
    test_user,
    monkeypatch,
):
    monkeypatch.setattr(settings, "ALIPAY_WEBHOOK_SECRET", "alipay-secret")
    plan = BillingPlan(
        name="退款过期套餐",
        code=f"refund-expire-{uuid4().hex[:8]}",
        billing_mode="monthly",
        base_price=299.0,
    )
    db_session.add(plan)
    await db_session.flush()
    subscription = Subscription(
        user_id=test_user.id,
        plan_id=plan.id,
        status="active",
        current_period_start=date.today(),
        current_period_end=date.today() + timedelta(days=30),
        auto_renew=True,
    )
    db_session.add(subscription)
    await db_session.flush()
    order = PaymentOrder(
        id=str(uuid4()),
        user_id=test_user.id,
        order_type="subscription",
        amount=299.0,
        status="paid",
        description="订阅专业版",
        related_id=subscription.id,
        payment_provider="alipay",
    )
    db_session.add(order)
    await db_session.flush()

    body = urlencode(
        {
            "out_trade_no": order.id,
            "trade_status": "TRADE_REFUND",
            "trade_no": "ali-refund-txn-1",
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
    assert order.status == "refunded"
    assert order.refunded_at is not None
    assert subscription.status == "expired"
    assert subscription.auto_renew is False
    assert subscription.next_billing_date is None

    events = await _events_for(db_session, subscription.id)
    assert [(event.from_status, event.to_status, event.event_type) for event in events] == [
        ("active", "expired", "refunded")
    ]


@pytest.mark.asyncio
async def test_invalid_subscription_transition_returns_409(
    auth_client,
    db_session,
    test_user,
):
    plan = BillingPlan(
        name="终态套餐",
        code=f"expired-{uuid4().hex[:8]}",
        billing_mode="monthly",
        base_price=299.0,
    )
    db_session.add(plan)
    await db_session.flush()
    subscription = Subscription(
        user_id=test_user.id,
        plan_id=plan.id,
        status="expired",
        current_period_start=date.today() - timedelta(days=40),
        current_period_end=date.today() - timedelta(days=10),
    )
    db_session.add(subscription)
    await db_session.flush()

    response = await auth_client.post(
        f"/api/v1/billing/subscriptions/{subscription.id}/cancel",
        json={"reason": "终态重复取消", "immediate": True},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == 409
    assert "无法取消" in body["message"]


@pytest.mark.asyncio
async def test_dual_client_subscriptions_are_isolated(db_session, test_user):
    needer_plan = BillingPlan(
        name="需求方 Pro",
        code=f"needer-pro-{uuid4().hex[:8]}",
        billing_mode="monthly",
        base_price=199.0,
        client_type="needer",
        features={"modes": ["local", "hybrid"]},
    )
    provider_plan = BillingPlan(
        name="服务方 Lawyer Pro",
        code=f"provider-pro-{uuid4().hex[:8]}",
        billing_mode="monthly",
        base_price=399.0,
        client_type="provider",
        features={"modes": ["local", "hybrid", "cloud"]},
    )
    db_session.add_all([needer_plan, provider_plan])
    await db_session.flush()

    service = SubscriptionService(db_session)
    needer_result = await service.create_subscription(
        user_id=test_user.id,
        plan_id=needer_plan.id,
        client_type="needer",
    )
    provider_result = await service.create_subscription(
        user_id=test_user.id,
        plan_id=provider_plan.id,
        client_type="provider",
    )
    needer_sub = await db_session.get(Subscription, needer_result["subscription"]["id"])
    provider_sub = await db_session.get(Subscription, provider_result["subscription"]["id"])
    needer_order = await db_session.get(PaymentOrder, needer_result["payment_order"]["id"])
    provider_order = await db_session.get(PaymentOrder, provider_result["payment_order"]["id"])

    assert needer_sub.client_type == "needer"
    assert provider_sub.client_type == "provider"
    assert needer_sub.allowed_modes == ["local", "hybrid"]
    assert provider_sub.allowed_modes == ["local", "hybrid", "cloud"]

    await apply_payment_webhook(
        db_session,
        provider="mock",
        payload={
            "out_trade_no": provider_order.id,
            "status": "paid",
            "transaction_id": "provider-paid-1",
        },
    )
    await db_session.flush()
    await db_session.refresh(needer_sub)
    await db_session.refresh(provider_sub)
    await db_session.refresh(needer_order)
    await db_session.refresh(provider_order)

    assert provider_order.status == "paid"
    assert provider_sub.status == "active"
    assert needer_order.status == "pending"
    assert needer_sub.status == "pending"

    await apply_payment_webhook(
        db_session,
        provider="mock",
        payload={
            "out_trade_no": provider_order.id,
            "status": "refunded",
            "transaction_id": "provider-refund-1",
        },
    )
    await db_session.flush()
    await db_session.refresh(needer_sub)
    await db_session.refresh(provider_sub)

    assert provider_sub.status == "expired"
    assert needer_sub.status == "pending"

    needer_events = await _events_for(db_session, needer_sub.id)
    provider_events = await _events_for(db_session, provider_sub.id)
    assert [(event.to_status, event.event_type) for event in needer_events] == [
        ("pending", "created")
    ]
    assert [(event.to_status, event.event_type) for event in provider_events] == [
        ("pending", "created"),
        ("active", "activated"),
        ("expired", "refunded"),
    ]


@pytest.mark.asyncio
async def test_create_subscription_rejects_wrong_client_plan(db_session, test_user):
    provider_plan = BillingPlan(
        name="服务方套餐",
        code=f"provider-only-{uuid4().hex[:8]}",
        billing_mode="monthly",
        base_price=399.0,
        client_type="provider",
    )
    db_session.add(provider_plan)
    await db_session.flush()

    with pytest.raises(ValueError, match="不适用于"):
        await SubscriptionService(db_session).create_subscription(
            user_id=test_user.id,
            plan_id=provider_plan.id,
            client_type="needer",
        )
