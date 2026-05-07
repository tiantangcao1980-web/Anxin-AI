import asyncio
from datetime import date
from types import SimpleNamespace

import pytest

from src.models.contract import ContractStatus
from src.services import webhook_handler
from src.services.esign_webhook_service import (
    ESignWebhookError,
    parse_esign_webhook_event,
)
from src.services.payment_service import PaymentStatusEnum
from src.services.payment_webhook_service import (
    PaymentWebhookError,
    parse_payment_webhook_event,
)


def test_parse_wechat_payment_event_from_decrypted_resource():
    event = parse_payment_webhook_event(
        provider="wechat_pay",
        payload={
            "id": "wx-notice-1",
            "event_type": "TRANSACTION.SUCCESS",
            "resource": {
                "plaintext": {
                    "out_trade_no": "order-1",
                    "trade_state": "SUCCESS",
                    "transaction_id": "wx-txn-1",
                }
            },
        },
    )

    assert event.provider == "wechat_pay"
    assert event.order_id == "order-1"
    assert event.status == PaymentStatusEnum.PAID
    assert event.provider_status == "transaction.success"
    assert event.transaction_id == "wx-txn-1"
    assert event.event_id == "wx-notice-1"
    assert event.event_type == "TRANSACTION.SUCCESS"


def test_parse_payment_event_rejects_missing_status():
    with pytest.raises(PaymentWebhookError, match="Unsupported payment webhook status"):
        parse_payment_webhook_event(
            provider="alipay",
            payload={"out_trade_no": "order-2"},
        )


def test_parse_esign_event_from_nested_data():
    event = parse_esign_webhook_event(
        {
            "eventId": "esign-event-1",
            "eventType": "SIGN_COMPLETED",
            "data": {
                "flowId": "flow-1",
                "signedAt": "2026-05-06T01:02:03Z",
            },
        }
    )

    assert event.contract_id is None
    assert event.flow_id == "flow-1"
    assert event.target_status == ContractStatus.SIGNED
    assert event.provider_status == "sign_completed"
    assert event.signed_date == date(2026, 5, 6)
    assert event.event_id == "esign-event-1"
    assert event.event_type == "SIGN_COMPLETED"


def test_parse_esign_event_preserves_in_progress_without_target_status():
    event = parse_esign_webhook_event(
        {
            "flowId": "flow-2",
            "status": "signing",
        }
    )

    assert event.flow_id == "flow-2"
    assert event.target_status is None
    assert event.provider_status == "signing"
    assert event.signed_date is None


def test_parse_esign_event_requires_contract_or_flow():
    with pytest.raises(ESignWebhookError, match="Missing contract_id or flow_id"):
        parse_esign_webhook_event({"status": "signed"})


@pytest.mark.asyncio
async def test_verified_webhook_serializes_concurrent_duplicate_business_writeback(monkeypatch):
    state = {"processed": False, "apply_calls": 0}
    record = SimpleNamespace(status="processing")

    class FakeDB:
        async def commit(self):
            return None

        async def rollback(self):
            return None

    async def fake_begin_webhook(*_args, **_kwargs):
        return record, state["processed"]

    async def fake_apply_webhook_business_event(*_args, **_kwargs):
        state["apply_calls"] += 1
        await asyncio.sleep(0.02)
        return {"contract_id": "contract-1", "updated": True}

    async def fake_mark_webhook_processed(_record):
        state["processed"] = True

    monkeypatch.setattr(webhook_handler, "begin_webhook", fake_begin_webhook)
    monkeypatch.setattr(
        webhook_handler,
        "apply_webhook_business_event",
        fake_apply_webhook_business_event,
    )
    monkeypatch.setattr(webhook_handler, "mark_webhook_processed", fake_mark_webhook_processed)

    first, second = await asyncio.gather(
        webhook_handler.handle_verified_webhook(
            FakeDB(),
            scope="esign",
            payload={"eventId": "esign-concurrent-1"},
            idempotency_key="esign-concurrent-1",
        ),
        webhook_handler.handle_verified_webhook(
            FakeDB(),
            scope="esign",
            payload={"eventId": "esign-concurrent-1"},
            idempotency_key="esign-concurrent-1",
        ),
    )

    assert state["apply_calls"] == 1
    assert {first.already_handled, second.already_handled} == {False, True}
