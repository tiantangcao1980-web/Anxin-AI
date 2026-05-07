import base64
import json
import time
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from src.models.payment import PaymentOrder
from src.services.payment_service import (
    AlipayProvider,
    PaymentStatusEnum,
    WeChatPayProvider,
    reset_payment_providers,
)
from src.services.payment_webhook_service import apply_payment_webhook


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


def _wechat_response(payload: dict, private_key, serial: str = "PUB_KEY_ID_TEST"):
    body = json.dumps(payload).encode("utf-8")
    timestamp = str(int(time.time()))
    nonce = uuid4().hex
    signature = _rsa_sha256_sign(private_key, f"{timestamp}\n{nonce}\n".encode() + body + b"\n")
    return _FakeResponse(
        payload,
        raw_content=body,
        headers={
            "Wechatpay-Timestamp": timestamp,
            "Wechatpay-Nonce": nonce,
            "Wechatpay-Serial": serial,
            "Wechatpay-Signature": signature,
        },
    )


def _alipay_response(response_key: str, result: dict, private_key):
    content = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sign = _rsa_sha256_sign(private_key, content)
    raw_body = (
        b'{"'
        + response_key.encode("utf-8")
        + b'":'
        + content
        + b',"sign":'
        + json.dumps(sign).encode("utf-8")
        + b"}"
    )
    return _FakeResponse(json.loads(raw_body), raw_content=raw_body)


def _merchant_private_key_pem() -> str:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200, raw_content: bytes | None = None, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.content = raw_content if raw_content is not None else (json.dumps(payload).encode("utf-8") if payload else b"")
        self.text = self.content.decode("utf-8")
        self.headers = headers or {}

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def reset_providers():
    reset_payment_providers()
    yield
    reset_payment_providers()


@pytest.mark.asyncio
async def test_wechat_pay_provider_posts_native_order(monkeypatch):
    from src.core.config import settings
    from src.services import payment_service

    captured = {}
    platform_private_key, platform_public_key = _rsa_key_pair()

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def request(self, method, url, content=None, headers=None):
            captured.update({"method": method, "url": url, "content": content, "headers": headers})
            return _wechat_response({"code_url": "weixin://wxpay/bizpayurl?pr=test"}, platform_private_key)

    monkeypatch.setattr(payment_service.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(settings, "PAYMENT_NOTIFY_BASE_URL", "https://api.example.com")
    monkeypatch.setattr(settings, "WECHAT_PAY_APP_ID", "wx-app")
    monkeypatch.setattr(settings, "WECHAT_PAY_MCH_ID", "1900000001")
    monkeypatch.setattr(settings, "WECHAT_PAY_MERCHANT_SERIAL_NO", "SERIAL123")
    monkeypatch.setattr(settings, "WECHAT_PAY_MERCHANT_PRIVATE_KEY", _merchant_private_key_pem())
    monkeypatch.setattr(settings, "WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH", None)
    monkeypatch.setattr(settings, "WECHAT_PAY_PLATFORM_SERIAL", "PUB_KEY_ID_TEST")
    monkeypatch.setattr(settings, "WECHAT_PAY_PLATFORM_PUBLIC_KEY", platform_public_key)
    monkeypatch.setattr(settings, "WECHAT_PAY_PLATFORM_PUBLIC_KEY_PATH", None)
    monkeypatch.setattr(settings, "WECHAT_PAY_API_BASE_URL", "https://api.mch.weixin.qq.com")

    order_id = str(uuid4())
    result = await WeChatPayProvider().create_order(
        order_id=order_id,
        amount=199.12,
        description="咨询服务",
        notify_url="/api/v1/payments/webhook/wechat",
    )

    payload = json.loads(captured["content"])
    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.mch.weixin.qq.com/v3/pay/transactions/native"
    assert captured["headers"]["Authorization"].startswith("WECHATPAY2-SHA256-RSA2048 ")
    assert captured["headers"]["Wechatpay-Serial"] == "PUB_KEY_ID_TEST"
    assert payload["appid"] == "wx-app"
    assert payload["mchid"] == "1900000001"
    assert payload["out_trade_no"] == order_id.replace("-", "")
    assert len(payload["out_trade_no"]) == 32
    assert payload["amount"] == {"total": 19912, "currency": "CNY"}
    assert payload["notify_url"] == "https://api.example.com/api/v1/payments/webhook/wechat"
    assert result.provider.value == "wechat_pay"
    assert result.qr_code == "weixin://wxpay/bizpayurl?pr=test"


@pytest.mark.asyncio
async def test_wechat_pay_provider_refund_sends_original_total(monkeypatch):
    from src.core.config import settings
    from src.services import payment_service

    captured = {}
    platform_private_key, platform_public_key = _rsa_key_pair()

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def request(self, method, url, content=None, headers=None):
            captured.update({"method": method, "url": url, "content": content, "headers": headers})
            return _wechat_response({"refund_id": "wx-refund-1", "status": "PROCESSING"}, platform_private_key)

    monkeypatch.setattr(payment_service.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(settings, "WECHAT_PAY_APP_ID", "wx-app")
    monkeypatch.setattr(settings, "WECHAT_PAY_MCH_ID", "1900000001")
    monkeypatch.setattr(settings, "WECHAT_PAY_MERCHANT_SERIAL_NO", "SERIAL123")
    monkeypatch.setattr(settings, "WECHAT_PAY_MERCHANT_PRIVATE_KEY", _merchant_private_key_pem())
    monkeypatch.setattr(settings, "WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH", None)
    monkeypatch.setattr(settings, "WECHAT_PAY_PLATFORM_SERIAL", "PUB_KEY_ID_TEST")
    monkeypatch.setattr(settings, "WECHAT_PAY_PLATFORM_PUBLIC_KEY", platform_public_key)
    monkeypatch.setattr(settings, "WECHAT_PAY_PLATFORM_PUBLIC_KEY_PATH", None)
    monkeypatch.setattr(settings, "WECHAT_PAY_API_BASE_URL", "https://api.mch.weixin.qq.com")

    result = await WeChatPayProvider().refund(
        order_id=str(uuid4()),
        amount=99.0,
        reason="部分退款",
        total_amount=199.0,
    )

    payload = json.loads(captured["content"])
    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.mch.weixin.qq.com/v3/refund/domestic/refunds"
    assert payload["amount"] == {"refund": 9900, "total": 19900, "currency": "CNY"}
    assert result.status == "pending"


@pytest.mark.asyncio
async def test_alipay_provider_builds_signed_page_pay_url(monkeypatch):
    from src.core.config import settings

    monkeypatch.setattr(settings, "PAYMENT_NOTIFY_BASE_URL", "https://api.example.com")
    monkeypatch.setattr(settings, "ALIPAY_APP_ID", "2026000000000000")
    monkeypatch.setattr(settings, "ALIPAY_PRIVATE_KEY", _merchant_private_key_pem())
    monkeypatch.setattr(settings, "ALIPAY_PRIVATE_KEY_PATH", None)
    monkeypatch.setattr(settings, "ALIPAY_GATEWAY_URL", "https://openapi.alipay.com/gateway.do")

    order_id = str(uuid4())
    result = await AlipayProvider().create_order(
        order_id=order_id,
        amount=299.0,
        description="订阅专业版",
        notify_url="/api/v1/payments/webhook/alipay",
    )

    parsed = urlparse(result.payment_url or "")
    params = {key: values[0] for key, values in parse_qs(parsed.query).items()}
    biz_content = json.loads(params["biz_content"])
    assert parsed.scheme == "https"
    assert params["method"] == "alipay.trade.page.pay"
    assert params["app_id"] == "2026000000000000"
    assert params["sign_type"] == "RSA2"
    assert params["notify_url"] == "https://api.example.com/api/v1/payments/webhook/alipay"
    assert "sign" in params
    assert biz_content["out_trade_no"] == order_id.replace("-", "")
    assert biz_content["total_amount"] == "299.00"
    assert biz_content["product_code"] == "FAST_INSTANT_TRADE_PAY"
    assert result.provider.value == "alipay"


@pytest.mark.asyncio
async def test_alipay_provider_verifies_query_response_signature(monkeypatch):
    from src.core.config import settings
    from src.services import payment_service

    alipay_private_key, alipay_public_key = _rsa_key_pair()

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, data=None):
            return _alipay_response(
                "alipay_trade_query_response",
                {
                    "code": "10000",
                    "msg": "Success",
                    "out_trade_no": data["biz_content"],
                    "trade_no": "ali-trade-1",
                    "trade_status": "TRADE_SUCCESS",
                },
                alipay_private_key,
            )

    monkeypatch.setattr(payment_service.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(settings, "ALIPAY_APP_ID", "2026000000000000")
    monkeypatch.setattr(settings, "ALIPAY_PRIVATE_KEY", _merchant_private_key_pem())
    monkeypatch.setattr(settings, "ALIPAY_PRIVATE_KEY_PATH", None)
    monkeypatch.setattr(settings, "ALIPAY_PUBLIC_KEY", alipay_public_key)
    monkeypatch.setattr(settings, "ALIPAY_PUBLIC_KEY_PATH", None)
    monkeypatch.setattr(settings, "ALIPAY_GATEWAY_URL", "https://openapi.alipay.com/gateway.do")

    result = await AlipayProvider().query_order(str(uuid4()))

    assert result.status == PaymentStatusEnum.PAID
    assert result.transaction_id == "ali-trade-1"


@pytest.mark.asyncio
async def test_payment_webhook_finds_uuid_order_by_provider_order_id(db_session):
    order_id = str(uuid4())
    order = PaymentOrder(
        id=order_id,
        user_id=str(uuid4()),
        order_type="consultation_fee",
        amount=199.0,
        status="pending",
        description="咨询费",
        payment_provider="wechat_pay",
    )
    db_session.add(order)
    await db_session.flush()

    updated = await apply_payment_webhook(
        db_session,
        provider="wechat_pay",
        payload={
            "out_trade_no": UUID(order_id).hex,
            "trade_state": "SUCCESS",
            "transaction_id": "wx-provider-order-id",
        },
    )

    assert updated.id == order.id
    assert updated.status == PaymentStatusEnum.PAID.value
    assert updated.transaction_id == "wx-provider-order-id"
