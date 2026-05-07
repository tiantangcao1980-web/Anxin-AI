import base64
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.core.config import settings
from src.models.payment import PaymentOrder
from src.services.official_webhook_security import (
    OfficialWebhookVerificationError,
    decrypt_wechat_pay_resource,
    verify_esignbao_notification,
)


def _rsa_key_pair() -> tuple[object, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_key, public_pem


def _rsa_sha256_sign(private_key, content: bytes) -> str:
    signature = private_key.sign(
        content,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("ascii")


@pytest.mark.asyncio
async def test_wechat_pay_official_webhook_verifies_rsa_signature(client, db_session, monkeypatch):
    private_key, public_pem = _rsa_key_pair()
    monkeypatch.setattr(settings, "WECHAT_PAY_OFFICIAL_WEBHOOK_ENABLED", True)
    monkeypatch.setattr(settings, "WECHAT_PAY_PLATFORM_PUBLIC_KEY", public_pem)
    monkeypatch.setattr(settings, "WECHAT_PAY_PLATFORM_PUBLIC_KEY_PATH", None)
    monkeypatch.setattr(settings, "WECHAT_PAY_PLATFORM_SERIAL", "PUB_KEY_ID_TEST")

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
            "id": f"EV-{uuid4().hex}",
            "out_trade_no": order.id,
            "trade_state": "SUCCESS",
            "transaction_id": "wx-official-txn",
        }
    ).encode("utf-8")
    timestamp = str(int(time.time()))
    nonce = uuid4().hex
    signature = _rsa_sha256_sign(private_key, f"{timestamp}\n{nonce}\n".encode() + body + b"\n")

    response = await client.post(
        "/api/v1/payments/webhook/wechat",
        content=body,
        headers={
            "Content-Type": "application/json",
            "Wechatpay-Timestamp": timestamp,
            "Wechatpay-Nonce": nonce,
            "Wechatpay-Serial": "PUB_KEY_ID_TEST",
            "Wechatpay-Signature": signature,
        },
    )

    assert response.status_code == 200
    await db_session.refresh(order)
    assert order.status == "paid"
    assert order.transaction_id == "wx-official-txn"
    assert order.paid_at is not None


def test_wechat_pay_resource_decryption_uses_api_v3_key():
    api_key = "0123456789abcdef0123456789abcdef"
    nonce = "0123456789ab"
    associated_data = "transaction"
    plaintext = b'{"out_trade_no":"order-1","trade_state":"SUCCESS"}'
    ciphertext = AESGCM(api_key.encode("utf-8")).encrypt(
        nonce.encode("utf-8"),
        plaintext,
        associated_data.encode("utf-8"),
    )
    payload = {
        "resource": {
            "algorithm": "AEAD_AES_256_GCM",
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
            "associated_data": associated_data,
            "nonce": nonce,
        }
    }

    assert decrypt_wechat_pay_resource(payload, api_v3_key=api_key) == {
        "out_trade_no": "order-1",
        "trade_state": "SUCCESS",
    }


def test_esignbao_official_webhook_rejects_bad_hmac_signature():
    body = b'{"flow_id":"flow-1","status":"completed"}'
    timestamp = str(int(time.time()))
    valid_signature = hmac.new(
        b"esignbao-secret",
        timestamp.encode("utf-8") + b"acct-1ord-1" + body,
        hashlib.sha256,
    ).hexdigest()
    bad_signature = valid_signature[:-1] + ("0" if valid_signature[-1] != "0" else "1")

    with pytest.raises(OfficialWebhookVerificationError, match="invalid eSignBao"):
        verify_esignbao_notification(
            headers={
                "X-Tsign-Open-App-Id": "app-1",
                "X-Tsign-Open-TIMESTAMP": timestamp,
                "X-Tsign-Open-SIGNATURE-ALGORITHM": "hmac-sha256",
                "X-Tsign-Open-SIGNATURE": bad_signature,
            },
            body=body,
            query_params={"orderNo": "ord-1", "accountId": "acct-1"},
            app_id="app-1",
            app_secret="esignbao-secret",
            max_age_seconds=300,
        )


@pytest.mark.asyncio
async def test_alipay_official_webhook_verifies_rsa2_signature(client, db_session, monkeypatch):
    private_key, public_pem = _rsa_key_pair()
    monkeypatch.setattr(settings, "ALIPAY_OFFICIAL_WEBHOOK_ENABLED", True)
    monkeypatch.setattr(settings, "ALIPAY_PUBLIC_KEY", public_pem)
    monkeypatch.setattr(settings, "ALIPAY_PUBLIC_KEY_PATH", None)

    order = PaymentOrder(
        id=str(uuid4()),
        user_id=str(uuid4()),
        order_type="consultation_fee",
        amount=199.0,
        status="pending",
        description="咨询费",
        payment_provider="alipay",
    )
    db_session.add(order)
    await db_session.flush()

    payload = {
        "app_id": "2026000000000000",
        "notify_id": f"notify-{uuid4().hex}",
        "notify_time": "2026-05-06 12:00:00",
        "notify_type": "trade_status_sync",
        "out_trade_no": order.id,
        "sign_type": "RSA2",
        "trade_no": "ali-official-txn",
        "trade_status": "TRADE_SUCCESS",
    }
    sign_content = "&".join(
        f"{key}={payload[key]}"
        for key in sorted(payload)
        if key not in {"sign", "sign_type"}
    ).encode("utf-8")
    payload["sign"] = _rsa_sha256_sign(private_key, sign_content)

    response = await client.post(
        "/api/v1/payments/webhook/alipay",
        content=urlencode(payload).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    assert response.text == "success"
    await db_session.refresh(order)
    assert order.status == "paid"
    assert order.transaction_id == "ali-official-txn"
