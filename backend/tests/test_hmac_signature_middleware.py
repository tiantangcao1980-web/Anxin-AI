import base64
import hashlib
import hmac
from typing import Any

from src.middleware.hmac_signature import HMACSignatureMiddleware


async def _noop_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    return None


def test_hmac_signature_verifier_accepts_canonical_payload() -> None:
    middleware = HMACSignatureMiddleware(_noop_app)
    key = "test-signing-key"
    timestamp = "1700000000"
    nonce = "0123456789abcdef"
    method = "POST"
    path = "/api/v1/contracts"
    body = b'{"name":"contract"}'
    body_hash = hashlib.sha256(body).hexdigest()
    payload = f"{timestamp}\n{nonce}\n{method}\n{path}\n{body_hash}"
    digest = hmac.new(key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    signature = base64.b64encode(digest).decode("utf-8")

    assert middleware._verify_signature(key, timestamp, nonce, method, path, body, signature)
    assert not middleware._verify_signature(key, timestamp, nonce, method, path, body, "bad")
