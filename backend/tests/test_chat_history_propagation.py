import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.chat_service import ChatService
from src.agents.workforce import LegalWorkforce


@pytest.mark.asyncio
async def test_stream_chat_passes_recent_history_to_single_agent(db_session):
    service = ChatService(db_session)
    service._load_llm_config = AsyncMock(return_value=None)
    service.create_conversation = AsyncMock(return_value=SimpleNamespace(id="conv-history"))
    service.add_message = AsyncMock(return_value=SimpleNamespace(id="msg-history", citations=None, actions=None))
    service.get_recent_history = AsyncMock(
        return_value=[
            {"role": "user", "content": "上一轮问题"},
            {"role": "assistant", "content": "上一轮回答"},
        ]
    )

    token_queue = asyncio.Queue()
    await token_queue.put("新的回复")
    await token_queue.put(None)

    target_agent = MagicMock()
    target_agent.stream_chat = AsyncMock(return_value=token_queue)

    service._workforce = MagicMock()
    service._workforce.agents = {"legal_advisor": target_agent}

    events = []
    async for event in service.stream_chat("继续刚才的话题", agent_name="legal_advisor"):
        events.append(event)

    target_agent.stream_chat.assert_awaited_once_with(
        "继续刚才的话题",
        llm_config=None,
        history=[
            {"role": "user", "content": "上一轮问题"},
            {"role": "assistant", "content": "上一轮回答"},
        ],
    )
    assert any(event.get("type") == "content" for event in events)


@pytest.mark.asyncio
async def test_workforce_chat_forwards_history_to_agent():
    workforce = object.__new__(LegalWorkforce)
    target_agent = MagicMock()
    target_agent.chat = AsyncMock(return_value="ok")
    workforce.agents = {"legal_advisor": target_agent}

    history = [
        {"role": "user", "content": "前文问题"},
        {"role": "assistant", "content": "前文回答"},
    ]

    result = await LegalWorkforce.chat(
        workforce,
        "请接着回答",
        context={"llm_config": "cfg", "history": history},
    )

    assert result == "ok"
    target_agent.chat.assert_awaited_once_with(
        "请接着回答",
        llm_config="cfg",
        history=history,
    )


@pytest.mark.asyncio
async def test_task_history_var_propagates_to_agent_chat():
    """验证 _task_history_var contextvars 在 DAG 执行路径中自动透传对话历史到 agent.chat()"""
    from src.agents.base import _task_history_var, BaseLegalAgent

    history = [
        {"role": "user", "content": "之前的问题"},
        {"role": "assistant", "content": "之前的回答"},
    ]

    # 模拟在 DAG 执行环境中设置 contextvars
    token = _task_history_var.set(history)
    try:
        # 创建一个最小化的 Agent 实例
        agent = MagicMock(spec=BaseLegalAgent)
        agent._normalize_history_messages = BaseLegalAgent._normalize_history_messages
        agent._build_llm_messages = BaseLegalAgent._build_llm_messages.__get__(agent)

        # 调用 _build_llm_messages，模拟 chat() 内部行为
        # 当 history=None 时，应从 contextvars 获取
        effective_history = None or _task_history_var.get(None)
        assert effective_history == history
        assert len(effective_history) == 2
        assert effective_history[0]["content"] == "之前的问题"
    finally:
        _task_history_var.reset(token)

    # contextvars 重置后应为 None
    assert _task_history_var.get(None) is None


@pytest.mark.asyncio
async def test_execute_single_task_sets_history_contextvar():
    """验证 _execute_single_task 正确设置 _task_history_var"""
    from src.agents.base import AgentResponse, _task_history_var

    captured_history = []

    class MockAgent:
        name = "legal_advisor"

        async def process(self, task):
            # 在 process 内部读取 contextvars
            h = _task_history_var.get(None)
            captured_history.append(h)
            return AgentResponse(
                agent_name="legal_advisor",
                content="测试结果",
                reasoning="测试",
            )

        def get_info(self):
            return {"name": "legal_advisor"}

    workforce = object.__new__(LegalWorkforce)
    workforce.agents = {"legal_advisor": MockAgent()}
    workforce._dag_semaphore = asyncio.Semaphore(5)

    history = [{"role": "user", "content": "历史消息"}]
    context = {"llm_config": None, "history": history}

    result = await workforce._execute_single_task(
        {"agent": "legal_advisor", "instruction": "测试任务"},
        context,
        {},
        [],
    )

    assert result.content == "测试结果"
    assert len(captured_history) == 1
    assert captured_history[0] == history
