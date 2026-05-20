"""Official provider webhook verification helpers."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class OfficialWebhookVerificationError(ValueError):
    """Raised when an official channel webhook fails verification."""


def _header(headers: Mapping[str, str], name: str) -> str | None:
    value = headers.get(name)
    if value is not None:
        return value
    lowered = name.lower()
    for key, candidate in headers.items():
        if key.lower() == lowered:
            return candidate
    return None


def _pem_from_config(value: str | None, path: str | None) -> bytes:
    if path:
        return Path(path).read_bytes()
    if not value:
        raise OfficialWebhookVerificationError("missing public key configuration")
    normalized = value.replace("\\n", "\n")
    return normalized.encode("utf-8")


def _load_public_key(value: str | None, path: str | None) -> Any:
    raw = _pem_from_config(value, path)
    try:
        return serialization.load_pem_public_key(raw)
    except ValueError:
        try:
            return x509.load_pem_x509_certificate(raw).public_key()
        except Exception as exc:
            raise OfficialWebhookVerificationError("invalid public key configuration") from exc
    except OfficialWebhookVerificationError:
        raise
    except Exception as exc:
        raise OfficialWebhookVerificationError("invalid public key configuration") from exc


def _verify_rsa_sha256(public_key: Any, message: bytes, signature: str) -> None:
    try:
        signature_bytes = base64.b64decode(signature.replace(" ", "+"), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise OfficialWebhookVerificationError("invalid base64 signature") from exc

    try:
        public_key.verify(
            signature_bytes,
            message,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except InvalidSignature as exc:
        raise OfficialWebhookVerificationError("invalid RSA-SHA256 signature") from exc


def _require_fresh_timestamp(timestamp: str | None, *, max_age_seconds: int) -> str:
    if not timestamp:
        raise OfficialWebhookVerificationError("missing timestamp")
    try:
        ts_value = int(timestamp)
    except ValueError as exc:
        raise OfficialWebhookVerificationError("invalid timestamp") from exc
    if abs(int(time.time()) - ts_value) > max_age_seconds:
        raise OfficialWebhookVerificationError("stale timestamp")
    return timestamp


def _require_fresh_millis_timestamp(timestamp: str | None, *, max_age_seconds: int) -> str:
    if not timestamp:
        raise OfficialWebhookVerificationError("missing timestamp")
    try:
        ts_value = int(timestamp)
    except ValueError as exc:
        raise OfficialWebhookVerificationError("invalid timestamp") from exc
    if ts_value < 10_000_000_000:
        ts_value *= 1000
    if abs(int(time.time() * 1000) - ts_value) > max_age_seconds * 1000:
        raise OfficialWebhookVerificationError("stale timestamp")
    return timestamp


def _query_value_content(query_params: Mapping[str, Any]) -> bytes:
    parts = []
    for key in sorted(query_params):
        value = query_params[key]
        if value is None:
            parts.append("")
            continue
        parts.append(str(value))
    return "".join(parts).encode("utf-8")


def _compare_hmac_sha256_signature(signature: str, digest: bytes) -> bool:
    normalized = signature.strip()
    expected_hex = digest.hex()
    if hmac.compare_digest(normalized.lower(), expected_hex):
        return True
    expected_base64 = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(normalized.replace(" ", "+"), expected_base64)


def verify_wechat_pay_signature(
    *,
    headers: Mapping[str, str],
    body: bytes,
    public_key: str | None,
    public_key_path: str | None,
    expected_serial: str | None,
    max_age_seconds: int,
) -> None:
    """Verify a WeChat Pay v3 API response or notification signature."""

    timestamp = _require_fresh_timestamp(
        _header(headers, "Wechatpay-Timestamp"),
        max_age_seconds=max_age_seconds,
    )
    nonce = _header(headers, "Wechatpay-Nonce")
    signature = _header(headers, "Wechatpay-Signature")
    serial = _header(headers, "Wechatpay-Serial")
    if not nonce or not signature or not serial:
        raise OfficialWebhookVerificationError("missing WeChat Pay signature headers")
    if expected_serial and serial != expected_serial:
        raise OfficialWebhookVerificationError("unexpected WeChat Pay platform serial")

    message = f"{timestamp}\n{nonce}\n".encode() + body + b"\n"
    _verify_rsa_sha256(_load_public_key(public_key, public_key_path), message, signature)


def verify_wechat_pay_notification(
    *,
    headers: Mapping[str, str],
    body: bytes,
    public_key: str | None,
    public_key_path: str | None,
    expected_serial: str | None,
    max_age_seconds: int,
) -> dict[str, Any]:
    """Verify a WeChat Pay v3 notification and return its outer JSON payload."""

    verify_wechat_pay_signature(
        headers=headers,
        body=body,
        public_key=public_key,
        public_key_path=public_key_path,
        expected_serial=expected_serial,
        max_age_seconds=max_age_seconds,
    )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise OfficialWebhookVerificationError("invalid WeChat Pay notification JSON") from exc
    if not isinstance(payload, dict):
        raise OfficialWebhookVerificationError("invalid WeChat Pay notification payload")
    return payload


def decrypt_wechat_pay_resource(
    payload: Mapping[str, Any], *, api_v3_key: str | None
) -> dict[str, Any]:
    """Decrypt a WeChat Pay v3 AEAD_AES_256_GCM notification resource."""

    resource = payload.get("resource")
    if not isinstance(resource, Mapping):
        return dict(payload)
    if resource.get("algorithm") != "AEAD_AES_256_GCM":
        raise OfficialWebhookVerificationError("unsupported WeChat Pay resource algorithm")
    if not api_v3_key:
        raise OfficialWebhookVerificationError("missing WeChat Pay API v3 key")

    try:
        aes = AESGCM(api_v3_key.encode("utf-8"))
        associated_data = str(resource.get("associated_data") or "").encode("utf-8")
        plaintext = aes.decrypt(
            str(resource.get("nonce", "")).encode("utf-8"),
            base64.b64decode(str(resource.get("ciphertext", ""))),
            associated_data,
        )
        decrypted = json.loads(plaintext)
    except Exception as exc:
        raise OfficialWebhookVerificationError("failed to decrypt WeChat Pay resource") from exc
    if not isinstance(decrypted, dict):
        raise OfficialWebhookVerificationError("invalid decrypted WeChat Pay resource")
    return decrypted


def parse_wechat_pay_notification(
    *,
    headers: Mapping[str, str],
    body: bytes,
    public_key: str | None,
    public_key_path: str | None,
    expected_serial: str | None,
    api_v3_key: str | None,
    max_age_seconds: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return ``(business_payload, outer_payload)`` for a verified WeChat Pay notification."""

    outer_payload = verify_wechat_pay_notification(
        headers=headers,
        body=body,
        public_key=public_key,
        public_key_path=public_key_path,
        expected_serial=expected_serial,
        max_age_seconds=max_age_seconds,
    )
    business_payload = decrypt_wechat_pay_resource(outer_payload, api_v3_key=api_v3_key)
    return business_payload, outer_payload


def build_alipay_sign_content(params: Mapping[str, Any]) -> bytes:
    """Build the RSA/RSA2 verification content for an Alipay async notification."""

    parts = []
    for key in sorted(params):
        if key in {"sign", "sign_type"}:
            continue
        value = params[key]
        if value is None:
            continue
        parts.append(f"{key}={value}")
    return "&".join(parts).encode("utf-8")


def extract_alipay_response_sign_content(raw_body: bytes, response_key: str) -> bytes:
    """Extract the exact JSON response object Alipay signs in OpenAPI responses."""

    try:
        raw_text = raw_body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OfficialWebhookVerificationError("invalid Alipay response encoding") from exc

    key_token = json.dumps(response_key, ensure_ascii=False)
    key_index = raw_text.find(key_token)
    if key_index < 0:
        raise OfficialWebhookVerificationError("missing Alipay response root")

    colon_index = raw_text.find(":", key_index + len(key_token))
    if colon_index < 0:
        raise OfficialWebhookVerificationError("invalid Alipay response root")

    start = colon_index + 1
    while start < len(raw_text) and raw_text[start].isspace():
        start += 1
    if start >= len(raw_text) or raw_text[start] not in "{[":
        raise OfficialWebhookVerificationError("invalid Alipay response content")

    opener = raw_text[start]
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(raw_text)):
        char = raw_text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return raw_text[start : index + 1].encode("utf-8")

    raise OfficialWebhookVerificationError("unterminated Alipay response content")


def verify_alipay_response_body(
    *,
    raw_body: bytes,
    response_key: str,
    public_key: str | None,
    public_key_path: str | None,
) -> None:
    """Verify an Alipay OpenAPI JSON response signed with RSA2."""

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise OfficialWebhookVerificationError("invalid Alipay response JSON") from exc
    if not isinstance(payload, Mapping):
        raise OfficialWebhookVerificationError("invalid Alipay response payload")
    signature = payload.get("sign")
    if not signature:
        raise OfficialWebhookVerificationError("missing Alipay response sign")

    _verify_rsa_sha256(
        _load_public_key(public_key, public_key_path),
        extract_alipay_response_sign_content(raw_body, response_key),
        str(signature),
    )


def verify_alipay_notification(
    *,
    params: Mapping[str, Any],
    public_key: str | None,
    public_key_path: str | None,
) -> None:
    """Verify an Alipay asynchronous notification signed with RSA2."""

    sign_type = str(params.get("sign_type", "RSA2")).upper()
    if sign_type != "RSA2":
        raise OfficialWebhookVerificationError("unsupported Alipay sign_type")
    signature = params.get("sign")
    if not signature:
        raise OfficialWebhookVerificationError("missing Alipay sign")
    _verify_rsa_sha256(
        _load_public_key(public_key, public_key_path),
        build_alipay_sign_content(params),
        str(signature),
    )


def verify_esignbao_notification(
    *,
    headers: Mapping[str, str],
    body: bytes,
    query_params: Mapping[str, Any],
    app_id: str | None,
    app_secret: str | None,
    max_age_seconds: int,
) -> None:
    """Verify an e签宝 callback signed with X-Tsign-Open-* HMAC-SHA256 headers."""

    timestamp = _require_fresh_timestamp(
        _header(headers, "X-Tsign-Open-TIMESTAMP"),
        max_age_seconds=max_age_seconds,
    )
    signature = _header(headers, "X-Tsign-Open-SIGNATURE")
    algorithm = (_header(headers, "X-Tsign-Open-SIGNATURE-ALGORITHM") or "").lower()
    received_app_id = _header(headers, "X-Tsign-Open-App-Id")
    if not signature:
        raise OfficialWebhookVerificationError("missing eSignBao signature")
    if algorithm and algorithm != "hmac-sha256":
        raise OfficialWebhookVerificationError("unsupported eSignBao signature algorithm")
    if not app_secret:
        raise OfficialWebhookVerificationError("missing eSignBao app secret")
    if app_id and received_app_id != app_id:
        raise OfficialWebhookVerificationError("unexpected eSignBao app id")

    message = timestamp.encode("utf-8") + _query_value_content(query_params) + body
    digest = hmac.new(app_secret.encode("utf-8"), message, hashlib.sha256).digest()
    if not _compare_hmac_sha256_signature(signature, digest):
        raise OfficialWebhookVerificationError("invalid eSignBao HMAC-SHA256 signature")


def _fadada_sort_content(params: Mapping[str, Any]) -> str:
    parts = []
    for key in sorted(params):
        value = params[key]
        if value is None or value == "":
            continue
        parts.append(f"{key}={value}")
    return "&".join(parts)


def _fadada_signature(params: Mapping[str, Any], *, timestamp: str, app_secret: str) -> str:
    sign_text = hashlib.sha256(_fadada_sort_content(params).encode("utf-8")).hexdigest().lower()
    temporary_key = hmac.new(
        app_secret.encode("utf-8"), timestamp.encode("utf-8"), hashlib.sha256
    ).digest()
    return hmac.new(temporary_key, sign_text.encode("utf-8"), hashlib.sha256).hexdigest().lower()


def parse_fadada_form_body(body: bytes) -> dict[str, str]:
    """Parse a FASC form notification body and keep the first value for each key."""

    try:
        parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    except UnicodeDecodeError as exc:
        raise OfficialWebhookVerificationError("invalid Fadada notification encoding") from exc
    return {key: values[0] if values else "" for key, values in parsed.items()}


def verify_fadada_notification(
    *,
    headers: Mapping[str, str],
    body: bytes,
    app_id: str | None,
    app_secret: str | None,
    max_age_seconds: int,
) -> dict[str, Any]:
    """Verify a Fadada FASC callback signed with X-FASC-* HMAC-SHA256 headers."""

    received_app_id = _header(headers, "X-FASC-App-Id")
    sign_type = (_header(headers, "X-FASC-Sign-Type") or "").upper()
    signature = _header(headers, "X-FASC-Sign")
    timestamp = _require_fresh_millis_timestamp(
        _header(headers, "X-FASC-Timestamp"),
        max_age_seconds=max_age_seconds,
    )
    nonce = _header(headers, "X-FASC-Nonce")
    event = _header(headers, "X-FASC-Event")
    if app_id and received_app_id != app_id:
        raise OfficialWebhookVerificationError("unexpected Fadada app id")
    if sign_type != "HMAC-SHA256":
        raise OfficialWebhookVerificationError("unsupported Fadada signature algorithm")
    if not signature or not nonce or not event:
        raise OfficialWebhookVerificationError("missing Fadada signature headers")
    if not app_secret:
        raise OfficialWebhookVerificationError("missing Fadada app secret")

    form = parse_fadada_form_body(body)
    biz_content = form.get("bizContent")
    if not biz_content:
        raise OfficialWebhookVerificationError("missing Fadada bizContent")
    params = {
        "X-FASC-App-Id": received_app_id or "",
        "X-FASC-Sign-Type": "HMAC-SHA256",
        "X-FASC-Timestamp": timestamp,
        "X-FASC-Nonce": nonce,
        "X-FASC-Event": event,
        "bizContent": biz_content,
    }
    expected = _fadada_signature(params, timestamp=timestamp, app_secret=app_secret)
    if not hmac.compare_digest(signature.lower(), expected):
        raise OfficialWebhookVerificationError("invalid Fadada HMAC-SHA256 signature")
    try:
        payload = json.loads(biz_content)
    except json.JSONDecodeError as exc:
        raise OfficialWebhookVerificationError("invalid Fadada bizContent JSON") from exc
    if not isinstance(payload, dict):
        raise OfficialWebhookVerificationError("invalid Fadada bizContent payload")
    payload.setdefault("eventType", event)
    return payload
