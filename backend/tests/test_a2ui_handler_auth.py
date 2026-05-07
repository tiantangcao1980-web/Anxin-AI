"""
A2UI handler 鉴权防护 单元测试

来自任务：TASK-04 P0-2（Agent 4 调研报告）
- 历史：handle_a2ui_event 不接受 user_id，payload 里 lawyerId/serviceId 完全裸字符串
- 修复：
  1. WebSocketContext 加 user_id 字段（由 websocket_chat 首包鉴权后写入）
  2. handle_a2ui_event 在 ctx.user_id 缺失时拒绝 + 发送 error 给前端
  3. context 字典传给 a2ui_intent_handler 时附带 user_id / session_id

测试策略：单元测试 handler 的拒绝行为（不走完整 WS 链路，因 chat.py 内部直接用
async_session_maker 而非 Depends(get_db)，集成测试需要真实 postgres）。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.routes.chat_handlers.a2ui_handler import handle_a2ui_event
from src.api.routes.chat_handlers.context import WebSocketContext


def _build_mock_ctx(user_id: str | None) -> MagicMock:
    """构造一个 mock WebSocketContext，仅暴露测试需要的字段"""
    ctx = MagicMock(spec=WebSocketContext)
    ctx.user_id = user_id
    ctx.conversation_id = "conv-test"
    ctx.session_id = "sess-test"
    ctx.send = AsyncMock()
    ctx.save_message = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_a2ui_handler_rejects_when_user_id_missing():
    """ctx.user_id 缺失（None）时必须拒绝并发送 error"""
    ctx = _build_mock_ctx(user_id=None)
    data = {
        "action_id": "view_lawyer_detail",
        "component_id": "lawyer-card-1",
        "payload": {"lawyerId": "victim-uuid"},
        "form_data": {},
    }

    handled = await handle_a2ui_event(ctx, data)

    assert handled is True  # caller continue
    ctx.send.assert_called_once()
    args, kwargs = ctx.send.call_args
    assert args[0] == "error"
    assert args[1]["code"] == "unauthenticated"


@pytest.mark.asyncio
async def test_a2ui_handler_passes_user_id_to_intent_handler():
    """ctx.user_id 存在时，要把 user_id 灌入 intent_handler 的 context 参数"""
    ctx = _build_mock_ctx(user_id="real-user-id")
    data = {
        "action_id": "view_case_detail",
        "component_id": "case-card-1",
        "payload": {"caseId": "abc-123"},
        "form_data": {},
    }

    with patch(
        "src.services.a2ui_intent_handler.handle_a2ui_event",
        new=AsyncMock(return_value={"type": "a2ui_message", "ok": True}),
    ) as mock_intent:
        handled = await handle_a2ui_event(ctx, data)

    assert handled is True
    mock_intent.assert_called_once()
    call_kwargs = mock_intent.call_args.kwargs
    assert call_kwargs["context"]["user_id"] == "real-user-id"
    assert call_kwargs["context"]["conversation_id"] == "conv-test"
    assert call_kwargs["context"]["session_id"] == "sess-test"


@pytest.mark.asyncio
async def test_a2ui_handler_returns_false_when_no_intent_handler_match():
    """intent_handler 返回 None 时应回退（return False）让 caller 走对话流"""
    ctx = _build_mock_ctx(user_id="user-x")
    data = {"action_id": "unknown_action", "component_id": "", "payload": {}, "form_data": {}}

    with patch(
        "src.services.a2ui_intent_handler.handle_a2ui_event",
        new=AsyncMock(return_value=None),
    ):
        handled = await handle_a2ui_event(ctx, data)

    assert handled is False


@pytest.mark.asyncio
async def test_a2ui_handler_swallows_intent_handler_exception():
    """intent_handler 抛异常时应捕获 + 发送 error，不让 ws 崩"""
    ctx = _build_mock_ctx(user_id="user-x")
    data = {"action_id": "broken_action", "component_id": "", "payload": {}, "form_data": {}}

    with patch(
        "src.services.a2ui_intent_handler.handle_a2ui_event",
        new=AsyncMock(side_effect=RuntimeError("intent handler boom")),
    ):
        handled = await handle_a2ui_event(ctx, data)

    assert handled is True
    # 应发送 error
    error_calls = [c for c in ctx.send.call_args_list if c.args[0] == "error"]
    assert len(error_calls) == 1


def test_websocket_context_default_user_id_is_none():
    """WebSocketContext 默认 user_id=None（防御性兜底，防止意外构造时绕过鉴权）"""
    ctx = WebSocketContext(
        websocket=MagicMock(),
        session_id="s",
        conversation_id="c",
        workforce=MagicMock(),
    )
    assert ctx.user_id is None


def test_websocket_context_accepts_user_id():
    ctx = WebSocketContext(
        websocket=MagicMock(),
        session_id="s",
        conversation_id="c",
        workforce=MagicMock(),
        user_id="u-123",
    )
    assert ctx.user_id == "u-123"
