from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.services.chat_service import ChatService
from src.services.template_context import build_template_context_message


def test_build_template_context_message_returns_system_instruction_for_builtin_template():
    content = build_template_context_message("nda")

    assert content is not None
    assert content.startswith("当前输出模板：")
    assert "保密协议" in content
    assert "结构、章节顺序与文书语气" in content


@pytest.mark.asyncio
async def test_prepare_chat_context_injects_template_instruction_into_context_history(db_session):
    service = ChatService(db_session)
    service._load_llm_config = AsyncMock(return_value=None)
    service.create_conversation = AsyncMock(return_value=SimpleNamespace(id="conv-template"))
    service.add_message = AsyncMock(return_value=SimpleNamespace(id="msg-template"))
    service.get_recent_history = AsyncMock(return_value=[{"role": "assistant", "content": "好的"}])

    with patch.object(service, "_decide_route", return_value=("general", None, None)):
        ctx = await service._prepare_chat_context(
            content="请起草法律意见书",
            conversation_id=None,
            user_id=None,
            case_id=None,
            agent_name=None,
            mode="document",
            knowledge_base_ids=None,
            template_id="legal-opinion",
        )

    service.add_message.assert_awaited_once()
    saved_content = service.add_message.await_args.kwargs["content"]
    assert saved_content == "请起草法律意见书"
    assert ctx.context_messages[0]["role"] == "system"
    assert "法律意见书" in ctx.context_messages[0]["content"]
    assert ctx.context_messages[1]["content"] == "好的"
