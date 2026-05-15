"""
飞书 IM 适配器单元测试（P3）

覆盖：
    1. test_signature_verification             — SHA-256 签名算法正确性
    2. test_url_verification_challenge_path    — challenge 走快速路径，跳过签名
    3. test_send_text_message_calls_api        — text 类型调用飞书 messages API
    4. test_send_interactive_card              — interactive 卡片正确序列化
    5. test_token_caching_hit_skip_refresh     — 命中 Redis 缓存时不刷新
    6. test_token_auto_refresh_before_expiry   — 缺失 / 过期时刷新并写回 Redis
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# 兼容性：项目根 conftest.py 使用 SQLite 内存库 + Base.metadata.create_all，
# 而 IMChannel.config 使用 PostgreSQL JSONB。导入 feishu_adapter 会注册
# im_gateway_* 表，create_all 时会因 JSONB 在 SQLite 下无法编译而报错。
#
# 本测试不需要这些表（全程使用 mock httpx + redis），因此在导入前注册一个
# SQLAlchemy "compiles" 钩子，把 JSONB 在 SQLite 方言下渲染成普通 JSON 即可。
# ---------------------------------------------------------------------------
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(JSONB, "sqlite")  # type: ignore[misc]
def _compile_jsonb_for_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


from src.services.im_gateway.feishu_adapter import FeishuAdapter  # noqa: E402
from src.services.im_gateway.feishu_card_templates import (  # noqa: E402
    task_completed_card,
)
from src.services.im_gateway.feishu_signature import (  # noqa: E402
    _compute_signature,
    verify_signature,
)


# ---------------------------------------------------------------------------
# 工具：构造一个测试用 adapter（注入 mock httpx + redis）
# ---------------------------------------------------------------------------
def _make_adapter(
    *,
    http_client: Any = None,
    redis_client: Any = None,
    encrypt_key: str = "test-encrypt-key-1234567890",
) -> FeishuAdapter:
    return FeishuAdapter(
        config={
            "app_id": "cli_test_app_id",
            "app_secret": "test_secret",
            "encrypt_key": encrypt_key,
            "verify_token": "test_verify_token",
        },
        http_client=http_client,
        redis_client=redis_client,
    )


def _mock_http_response(json_data: dict[str, Any], status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json = MagicMock(return_value=json_data)
    resp.raise_for_status = MagicMock()
    return resp


# ===========================================================================
# 1. 签名校验
# ===========================================================================
def test_signature_verification() -> None:
    """SHA-256 签名按 (timestamp+nonce+encrypt_key+body) 拼接，并常量时间比较。

    P16-C：``verify_signature`` 现在会校验 timestamp 新鲜度（默认 ±300s），
    所以这里固定 ``now=ts`` 让 timestamp 视作当前时间。
    """
    encrypt_key = "abcdef1234567890"
    timestamp = "1714125600"
    nonce = "rand-nonce"
    body = b'{"event":"hi","content":"\xe4\xb8\xad\xe6\x96\x87"}'  # 含中文 UTF-8

    expected = _compute_signature(timestamp, nonce, body, encrypt_key)

    # 手动按文档算法复算一遍
    raw = (timestamp + nonce + encrypt_key).encode("utf-8") + body
    manual = hashlib.sha256(raw).hexdigest()
    assert expected == manual, "签名计算应与手算 SHA-256 一致"

    fixed_now = float(timestamp)

    # 正确签名通过
    assert verify_signature(timestamp, nonce, body, expected, encrypt_key, now=fixed_now) is True

    # 错误签名拒绝
    assert (
        verify_signature(timestamp, nonce, body, "deadbeef" * 8, encrypt_key, now=fixed_now)
        is False
    )

    # body 篡改 → 拒绝
    tampered_body = body + b"x"
    assert (
        verify_signature(timestamp, nonce, tampered_body, expected, encrypt_key, now=fixed_now)
        is False
    )


# ===========================================================================
# 2. URL 验证（challenge 快速路径）
# ===========================================================================
@pytest.mark.asyncio
async def test_url_verification_challenge_path() -> None:
    """challenge 请求不应做签名校验，原样回填 challenge 值。"""
    adapter = _make_adapter()
    body = json.dumps(
        {"type": "url_verification", "challenge": "abc-xyz-123", "token": "test_verify_token"}
    ).encode("utf-8")

    # 注意：故意不传任何签名头 — 走快速路径不应抛 PermissionError
    result = await adapter.receive_webhook(body, headers={})

    assert result["kind"] == "url_verification"
    assert result["channel_type"] == "feishu"
    assert result["data"]["challenge"] == "abc-xyz-123"


# ===========================================================================
# 3. send_message — text
# ===========================================================================
@pytest.mark.asyncio
async def test_send_text_message_calls_api() -> None:
    """text 类型应调用 ``POST /im/v1/messages?receive_id_type=chat_id``，
    且 content 字段被包成 ``{"text": ...}`` 的 JSON 字符串。"""
    http = MagicMock()

    # post(token) → 返回 token；request(send) → 返回 message_id
    async def fake_post(url: str, json: dict[str, Any]) -> MagicMock:  # noqa: A002
        assert "tenant_access_token" in url
        return _mock_http_response({"code": 0, "tenant_access_token": "t-abc", "expire": 7200})

    async def fake_request(
        method: str,
        url: str,
        json: dict[str, Any] | None = None,  # noqa: A002
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> MagicMock:
        assert method == "POST"
        assert url.startswith("https://open.feishu.cn/open-apis/im/v1/messages")
        assert "receive_id_type=chat_id" in url
        assert headers and headers["Authorization"] == "Bearer t-abc"
        assert json["receive_id"] == "oc_test_chat"
        assert json["msg_type"] == "text"
        # content 必须是 JSON 字符串 {"text": "..."}
        parsed = __import__("json").loads(json["content"])
        assert parsed == {"text": "你好，安心助手"}
        return _mock_http_response({"code": 0, "data": {"message_id": "om_msg_001"}})

    http.post = AsyncMock(side_effect=fake_post)
    http.request = AsyncMock(side_effect=fake_request)

    # Redis 不可用 → 走兜底直接刷 token
    adapter = _make_adapter(http_client=http, redis_client=None)
    # 强制 _get_redis 返回 None，避免真连本地 redis
    adapter._get_redis = AsyncMock(return_value=None)  # type: ignore[method-assign]

    result = await adapter.send_message("oc_test_chat", "你好，安心助手")

    assert result["data"]["message_id"] == "om_msg_001"
    assert http.request.await_count == 1


# ===========================================================================
# 4. send_message — interactive card
# ===========================================================================
@pytest.mark.asyncio
async def test_send_interactive_card() -> None:
    """interactive 卡片应把 ``card`` dict 序列化成字符串放进 ``content``。"""
    http = MagicMock()

    async def fake_post(url: str, json: dict[str, Any]) -> MagicMock:  # noqa: A002
        return _mock_http_response({"code": 0, "tenant_access_token": "t-card", "expire": 7200})

    captured: dict[str, Any] = {}

    async def fake_request(
        method: str,
        url: str,
        json: dict[str, Any] | None = None,  # noqa: A002
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> MagicMock:
        captured["payload"] = json
        return _mock_http_response({"code": 0, "data": {"message_id": "om_card_1"}})

    http.post = AsyncMock(side_effect=fake_post)
    http.request = AsyncMock(side_effect=fake_request)

    adapter = _make_adapter(http_client=http)
    adapter._get_redis = AsyncMock(return_value=None)  # type: ignore[method-assign]

    card = task_completed_card(
        {
            "id": "task-001",
            "title": "合同审查",
            "summary": "已完成 12 条风险点识别",
            "finished_at": "2026-04-26 10:00",
            "detail_url": "https://anxin.example/v3/tasks/task-001",
        }
    )

    await adapter.send_message("oc_chat", content="", msg_type="interactive", card=card)

    payload = captured["payload"]
    assert payload["msg_type"] == "interactive"
    parsed = json.loads(payload["content"])
    # 卡片应保留 header.template = green + 至少一个 element
    assert parsed["header"]["template"] == "green"
    assert any(el["tag"] == "div" for el in parsed["elements"])


# ===========================================================================
# 5. token 缓存命中 → 不再请求飞书 token API
# ===========================================================================
@pytest.mark.asyncio
async def test_token_caching_hit_skip_refresh() -> None:
    """Redis 缓存命中时，不应再调用 ``/auth/v3/tenant_access_token/internal``。"""
    http = MagicMock()
    http.post = AsyncMock(side_effect=AssertionError("命中缓存时不应触发 token 请求"))

    redis = MagicMock()
    redis.get = AsyncMock(return_value="cached-token-xyz")
    redis.set = AsyncMock()
    redis.delete = AsyncMock()

    adapter = _make_adapter(http_client=http, redis_client=redis)

    token = await adapter._get_tenant_access_token()
    assert token == "cached-token-xyz"
    redis.get.assert_awaited()
    http.post.assert_not_awaited()


# ===========================================================================
# 6. token 缓存未命中 → 调用 API 并以 (expire - 300s) 写回 Redis
# ===========================================================================
@pytest.mark.asyncio
async def test_token_auto_refresh_before_expiry() -> None:
    """未命中缓存时，向飞书拉新 token，并以 expire-leeway 作为 TTL 写回。"""
    http = MagicMock()

    async def fake_post(url: str, json: dict[str, Any]) -> MagicMock:  # noqa: A002
        assert url.endswith("/auth/v3/tenant_access_token/internal")
        assert json == {"app_id": "cli_test_app_id", "app_secret": "test_secret"}
        return _mock_http_response(
            {"code": 0, "tenant_access_token": "fresh-token", "expire": 7200}
        )

    http.post = AsyncMock(side_effect=fake_post)

    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)  # 缓存未命中
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock()

    adapter = _make_adapter(http_client=http, redis_client=redis)
    token = await adapter._get_tenant_access_token()

    assert token == "fresh-token"
    http.post.assert_awaited_once()

    # 写回 Redis：TTL = 7200 - 300 = 6900
    redis.set.assert_awaited_once()
    _, kwargs = redis.set.call_args
    args = redis.set.call_args.args
    assert args[0] == "im:feishu:tenant_token:cli_test_app_id"
    assert args[1] == "fresh-token"
    assert kwargs["ex"] == 7200 - 300
