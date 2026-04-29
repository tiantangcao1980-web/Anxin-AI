# -*- coding: utf-8 -*-
"""
P16-C webhook fail-closed 测试

覆盖：
    1. test_feishu_no_encrypt_key_rejected_by_default
    2. test_feishu_no_encrypt_key_allowed_when_explicit_off
    3. test_feishu_timestamp_too_old_rejected
    4. test_feishu_signature_replay_attack_blocked
    5. test_webhook_replay_cache_redis_setnx
    6. test_webhook_redis_unavailable_fail_closed
    7. test_webhook_signature_mismatch_rejected
    8. test_webhook_no_secret_in_production_rejected
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from unittest.mock import AsyncMock

import pytest

# 兼容 SQLite 内存库 + JSONB（与 test_feishu_adapter 相同）
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(JSONB, "sqlite")  # type: ignore[misc]
def _compile_jsonb_for_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


from src.services import webhook_security as ws_mod  # noqa: E402
from src.services.im_gateway.feishu_signature import (  # noqa: E402
    FeishuSignatureError,
    FeishuTimestampError,
    _compute_signature,
    verify_signature,
)
from src.services.webhook_security import WebhookSecurity  # noqa: E402


# ===========================================================================
# 1. 飞书签名 fail-closed —— 空 encrypt_key 默认拒绝
# ===========================================================================
def test_feishu_no_encrypt_key_rejected_by_default(monkeypatch) -> None:
    """encrypt_key 为空 + FEISHU_VERIFY_SIGNATURE=True（默认）→ 抛 FeishuSignatureError。"""
    from src.core.config import settings as _settings

    monkeypatch.setattr(_settings, "FEISHU_VERIFY_SIGNATURE", True, raising=False)

    with pytest.raises(FeishuSignatureError) as exc_info:
        verify_signature(
            timestamp=str(int(time.time())),
            nonce="n1",
            body=b"{}",
            signature="x" * 64,
            encrypt_key="",
        )
    assert "FEISHU_ENCRYPT_KEY" in str(exc_info.value)


# ===========================================================================
# 2. 显式关闭后允许放行
# ===========================================================================
def test_feishu_no_encrypt_key_allowed_when_explicit_off(monkeypatch) -> None:
    """FEISHU_VERIFY_SIGNATURE=False 时，空 encrypt_key 才放行（联调用）。"""
    from src.core.config import settings as _settings

    monkeypatch.setattr(_settings, "FEISHU_VERIFY_SIGNATURE", False, raising=False)

    assert (
        verify_signature(
            timestamp=str(int(time.time())),
            nonce="n1",
            body=b"{}",
            signature="any",
            encrypt_key="",
        )
        is True
    )


# ===========================================================================
# 3. 时戳过旧拒绝（防 replay）
# ===========================================================================
def test_feishu_timestamp_too_old_rejected() -> None:
    """timestamp 超过 ±300s 窗口 → 抛 FeishuTimestampError。"""
    encrypt_key = "key123456"
    nonce = "n"
    body = b"{}"
    # 1 小时前的 timestamp
    old_ts = int(time.time()) - 3601
    sig = _compute_signature(str(old_ts), nonce, body, encrypt_key)

    with pytest.raises(FeishuTimestampError):
        verify_signature(
            timestamp=str(old_ts),
            nonce=nonce,
            body=body,
            signature=sig,
            encrypt_key=encrypt_key,
        )


def test_feishu_timestamp_missing_rejected() -> None:
    """空 timestamp 直接 fail-closed。"""
    with pytest.raises(FeishuTimestampError):
        verify_signature(
            timestamp="",
            nonce="n",
            body=b"{}",
            signature="x" * 64,
            encrypt_key="key",
        )


def test_feishu_timestamp_invalid_format_rejected() -> None:
    """非数字 timestamp → 抛 FeishuTimestampError。"""
    with pytest.raises(FeishuTimestampError):
        verify_signature(
            timestamp="not-a-number",
            nonce="n",
            body=b"{}",
            signature="x" * 64,
            encrypt_key="key",
        )


# ===========================================================================
# 4. 签名匹配但 timestamp 在窗口内：通过
# ===========================================================================
def test_feishu_signature_within_window_passes() -> None:
    encrypt_key = "key-ok"
    ts = str(int(time.time()))
    nonce = "n"
    body = b'{"ev":"x"}'
    sig = _compute_signature(ts, nonce, body, encrypt_key)
    assert (
        verify_signature(
            timestamp=ts, nonce=nonce, body=body, signature=sig, encrypt_key=encrypt_key
        )
        is True
    )


# ===========================================================================
# 5. WebhookSecurity Redis SETNX —— 第二次相同签名拒绝
# ===========================================================================
class _FakeAsyncRedis:
    """最小 Redis mock：支持 set(key, val, ex=, nx=) + ping()。"""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def ping(self) -> bool:
        return True

    async def set(
        self,
        key: str,
        val: str,
        *,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool | None:
        if nx and key in self.store:
            return None
        self.store[key] = val
        return True


def _make_signed_payload(secret: str, scope_unused: str = "") -> tuple[bytes, str, str]:
    """构造一对 (body, signature, timestamp)，让 WebhookSecurity.verify 能通过。"""
    body = b'{"event":"order.paid"}'
    ts = str(int(time.time()))
    payload = f"{ts}.".encode("utf-8") + body
    sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return body, sig, ts


@pytest.mark.asyncio
async def test_webhook_replay_cache_redis_setnx(monkeypatch) -> None:
    """第一次 verify 通过 → SETNX 写入；第二次同签名重放 → 拒绝。"""
    from src.core.config import settings as _settings

    monkeypatch.setattr(_settings, "WEBHOOK_SIGNATURE_MAX_AGE_SECONDS", 300, raising=False)

    fake = _FakeAsyncRedis()
    ws_mod._set_redis_client_for_test(fake)

    secret = "shh-it-is-a-secret"
    body, sig, ts = _make_signed_payload(secret)

    ok1 = await WebhookSecurity.verify(
        scope="test_pay", body=body, signature=sig, secret=secret, timestamp=ts
    )
    assert ok1 is True, "首次合法签名应通过"

    ok2 = await WebhookSecurity.verify(
        scope="test_pay", body=body, signature=sig, secret=secret, timestamp=ts
    )
    assert ok2 is False, "重放同一签名应被 SETNX 拒绝"

    # 验证 key 命名遵循约定
    assert any(
        k.startswith("webhook:replay:test_pay:") for k in fake.store
    ), f"replay key 命名应为 webhook:replay:{{scope}}:{{hash}}, 实际: {list(fake.store)}"

    ws_mod._set_redis_client_for_test(None)


# ===========================================================================
# 6. Redis 不可用 → fail-closed 拒绝
# ===========================================================================
class _BrokenRedis:
    async def ping(self) -> bool:  # noqa: D401
        raise ConnectionError("Redis down")

    async def set(self, *a: Any, **kw: Any) -> bool:
        raise ConnectionError("Redis down")


@pytest.mark.asyncio
async def test_webhook_redis_unavailable_fail_closed(monkeypatch) -> None:
    """Redis 不可用 → 即使 HMAC 校验通过也必须 fail-closed 拒绝。"""
    from src.core.config import settings as _settings

    monkeypatch.setattr(_settings, "WEBHOOK_SIGNATURE_MAX_AGE_SECONDS", 300, raising=False)

    # 注入"已存在但所有调用都失败"的 client（绕过 lazy 初始化）
    ws_mod._set_redis_client_for_test(_BrokenRedis())

    secret = "another-secret"
    body, sig, ts = _make_signed_payload(secret)

    result = await WebhookSecurity.verify(
        scope="broken_redis",
        body=body,
        signature=sig,
        secret=secret,
        timestamp=ts,
    )
    assert result is False, "Redis 不可用必须 fail-closed"

    ws_mod._set_redis_client_for_test(None)


# ===========================================================================
# 7. 签名不匹配 → 拒绝（基础 sanity）
# ===========================================================================
@pytest.mark.asyncio
async def test_webhook_signature_mismatch_rejected(monkeypatch) -> None:
    fake = _FakeAsyncRedis()
    ws_mod._set_redis_client_for_test(fake)

    body = b'{"x":1}'
    ts = str(int(time.time()))
    bad_sig = "deadbeef" * 8

    result = await WebhookSecurity.verify(
        scope="x",
        body=body,
        signature=bad_sig,
        secret="real-secret",
        timestamp=ts,
    )
    assert result is False
    assert not fake.store, "签名不匹配时不应写入 replay cache"

    ws_mod._set_redis_client_for_test(None)


# ===========================================================================
# 8. 飞书 webhook 签名 replay 攻击（adapter 层）
# ===========================================================================
@pytest.mark.asyncio
async def test_feishu_signature_replay_attack_blocked() -> None:
    """模拟 replay：攻击者用过旧 timestamp + 正确签名 → adapter 必拒。"""
    from src.services.im_gateway.feishu_adapter import FeishuAdapter

    adapter = FeishuAdapter(
        config={
            "app_id": "cli_x",
            "app_secret": "s",
            "encrypt_key": "encrypt-key-xxx",
        }
    )

    encrypt_key = "encrypt-key-xxx"
    body = b'{"schema":"2.0","header":{"event_type":"im.message"},"event":{}}'
    # 1 小时前
    old_ts = str(int(time.time()) - 3601)
    sig = _compute_signature(old_ts, "n", body, encrypt_key)

    with pytest.raises(PermissionError) as exc_info:
        await adapter.receive_webhook(
            body,
            headers={
                "X-Lark-Request-Timestamp": old_ts,
                "X-Lark-Request-Nonce": "n",
                "X-Lark-Signature": sig,
            },
        )
    assert "timestamp" in str(exc_info.value).lower()
