# -*- coding: utf-8 -*-
"""
L3 HeadlessXTier 接入测试。

覆盖：
- 未配置 → fetch 返回 None（让 service 跳过）
- 成功 → 返回 FetchResponse 含 bot_score / html
- 401 → 抛 HeadlessXAuthError 让上层处理
- 重试耗尽 → 返回 None（让 service 走 fallback 到 L2）
- 4xx 客户端错误 → 返回 success=False 的 FetchResponse 便于审计
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.services.fetch.headlessx_client import (
    HeadlessXAuthError,
    HeadlessXClient,
    HeadlessXClientError,
    HeadlessXServerError,
    HeadlessXTimeoutError,
    RenderResult,
)
from src.services.fetch.tiers.base import FetchRequest, TierName
from src.services.fetch.tiers.l3_headlessx import HeadlessXTier


# ============ 未配置 ============

@pytest.mark.asyncio
async def test_tier_disabled_when_no_base_url():
    tier = HeadlessXTier(base_url="", api_key="")
    assert tier.is_enabled is False
    result = await tier.fetch(FetchRequest(url="https://x.com"))
    assert result is None


# ============ 成功路径 ============

@pytest.mark.asyncio
async def test_tier_success_returns_fetch_response():
    fake_client = AsyncMock(spec=HeadlessXClient)
    fake_client.render.return_value = RenderResult(
        url="https://x.com",
        final_url="https://x.com/landed",
        status_code=200,
        html="<html>L3</html>",
        bot_score=0.15,
        duration_ms=987,
    )

    tier = HeadlessXTier(client=fake_client)
    response = await tier.fetch(
        FetchRequest(
            url="https://x.com",
            wait_for_selector=".main",
            wait_ms=100,
            screenshot=True,
        )
    )

    assert response is not None
    assert response.tier == TierName.L3_HEADLESSX
    assert response.success is True
    assert response.html == "<html>L3</html>"
    assert response.final_url == "https://x.com/landed"
    assert response.bot_score == 0.15
    assert response.duration_ms == 987

    # 校验参数透传
    fake_client.render.assert_awaited_once()
    kwargs = fake_client.render.call_args.kwargs
    assert kwargs["url"] == "https://x.com"
    assert kwargs["wait_for_selector"] == ".main"
    assert kwargs["wait_ms"] == 100
    assert kwargs["screenshot"] is True


# ============ 401 → 直接抛 ============

@pytest.mark.asyncio
async def test_tier_auth_error_propagates():
    fake_client = AsyncMock(spec=HeadlessXClient)
    fake_client.render.side_effect = HeadlessXAuthError("bad key", status_code=401)

    tier = HeadlessXTier(client=fake_client)
    with pytest.raises(HeadlessXAuthError):
        await tier.fetch(FetchRequest(url="https://x.com"))


# ============ 超时 / 5xx 重试耗尽 → None（fallback）============

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc",
    [
        HeadlessXTimeoutError("timeout", status_code=504),
        HeadlessXServerError("upstream down", status_code=503),
    ],
)
async def test_tier_returns_none_on_recoverable_exhaustion(exc):
    fake_client = AsyncMock(spec=HeadlessXClient)
    fake_client.render.side_effect = exc

    tier = HeadlessXTier(client=fake_client)
    result = await tier.fetch(FetchRequest(url="https://x.com"))
    assert result is None  # 让 service 回退到 L2


# ============ 4xx 客户端错误 → success=False ============

@pytest.mark.asyncio
async def test_tier_4xx_returns_failed_response_for_audit():
    fake_client = AsyncMock(spec=HeadlessXClient)
    fake_client.render.side_effect = HeadlessXClientError(
        "bad url", status_code=400
    )

    tier = HeadlessXTier(client=fake_client)
    result = await tier.fetch(FetchRequest(url="not-a-url"))

    assert result is not None
    assert result.success is False
    assert result.status_code == 400
    assert result.error is not None
    assert result.tier == TierName.L3_HEADLESSX


# ============ bot_score 透传 ============

@pytest.mark.asyncio
async def test_tier_passes_bot_score_to_response():
    """bot_score 必须如实透传，让 service 决定是否再换 proxy 重试。"""
    fake_client = AsyncMock(spec=HeadlessXClient)
    fake_client.render.return_value = RenderResult(
        url="https://blocked.com",
        final_url="https://blocked.com",
        status_code=200,
        html="<html>captcha</html>",
        bot_score=0.92,
    )

    tier = HeadlessXTier(client=fake_client)
    response = await tier.fetch(FetchRequest(url="https://blocked.com"))

    assert response is not None
    assert response.bot_score == 0.92
    # status 200 + bot_score 高 → success 仍 True，但 service 应自行判断


# ============ close 释放资源 ============

@pytest.mark.asyncio
async def test_tier_close_does_not_close_injected_client():
    """注入的 client 由调用方负责关闭，tier 不应主动关。"""
    fake_client = AsyncMock(spec=HeadlessXClient)
    tier = HeadlessXTier(client=fake_client)
    await tier.close()
    fake_client.aclose.assert_not_awaited()
