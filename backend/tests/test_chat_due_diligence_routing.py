from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.chat_service import ChatService


@pytest.mark.asyncio
@patch("src.services.chat_service.get_company_info", new_callable=AsyncMock)
async def test_chat_service_routes_company_investigation_to_due_diligence(
    mock_get_company_info,
    db_session,
):
    service = ChatService(db_session)
    service._load_llm_config = AsyncMock(return_value=None)
    service._workforce = MagicMock()
    service.create_conversation = AsyncMock(return_value=SimpleNamespace(id="conv-1"))
    service.add_message = AsyncMock(
        return_value=SimpleNamespace(id="msg-1", citations=None, actions=None)
    )
    service.get_messages = AsyncMock(return_value=[])

    mock_get_company_info.return_value = {
        "basic_info": {
            "name": "腾讯控股有限公司",
            "status": "正常",
            "legal_representative": "马化腾",
            "registered_capital": "待核验",
            "established_date": "1998-11-11",
            "data_source": "公开工商数据",
        },
        "litigation": {"plaintiff_cases": 2, "defendant_cases": 1},
        "credit": {"credit_rating": "A"},
        "risk": {
            "overall_rating": "low",
            "operation_risk": 20,
            "litigation_risk": 25,
            "credit_risk": 15,
            "compliance_risk": 30,
            "relation_risk": 20,
            "risk_points": ["存在平台治理相关合规风险"],
            "recommendations": ["建议核查近期监管处罚与整改情况"],
        },
    }

    result = await service.chat("帮我调查一下腾讯公司的背景、诉讼记录和股权结构")

    assert result["agent"] == "尽职调查Agent"
    assert "尽调摘要" in result["content"]
    assert "腾讯控股有限公司" in result["content"]
    mock_get_company_info.assert_awaited_once()
    assert not service._workforce.process_task.called


@pytest.mark.asyncio
async def test_chat_service_due_diligence_without_company_name_asks_for_clarification(
    db_session,
):
    service = ChatService(db_session)
    service._load_llm_config = AsyncMock(return_value=None)
    service._workforce = MagicMock()
    service.create_conversation = AsyncMock(return_value=SimpleNamespace(id="conv-2"))
    service.add_message = AsyncMock(
        return_value=SimpleNamespace(id="msg-2", citations=None, actions=None)
    )
    service.get_messages = AsyncMock(return_value=[])

    result = await service.chat("帮我调查一家公司是否可靠，重点看诉讼和工商")

    assert result["agent"] == "尽职调查Agent"
    assert "请至少补充目标企业的完整名称" in result["content"]
    assert not service._workforce.process_task.called


@pytest.mark.asyncio
async def test_chat_service_supplier_reliability_phrase_asks_for_company_name(
    db_session,
):
    service = ChatService(db_session)
    service._load_llm_config = AsyncMock(return_value=None)
    service._workforce = MagicMock()
    service.create_conversation = AsyncMock(return_value=SimpleNamespace(id="conv-3"))
    service.add_message = AsyncMock(
        return_value=SimpleNamespace(id="msg-3", citations=None, actions=None)
    )
    service.get_messages = AsyncMock(return_value=[])

    result = await service.chat("帮我看看这个供应商靠不靠谱，重点查信用和诉讼")

    assert result["agent"] == "尽职调查Agent"
    assert "完整名称" in result["content"]
    assert not service._workforce.process_task.called


def test_chat_service_routes_investigation_adjacent_intents_to_agents():
    service = ChatService.__new__(ChatService)

    assert service._decide_route(
        "搜索腾讯公司的负面新闻和媒体报道",
        agent_name=None,
    ) == ("specific_agent", "legal_researcher", None)
    assert service._decide_route(
        "监测腾讯公司适用的数据合规新规",
        agent_name=None,
    ) == ("specific_agent", "regulatory_monitor", None)
    assert service._decide_route(
        "查一下腾讯公司的工商信息和诉讼记录",
        agent_name=None,
    ) == ("due_diligence", "尽职调查Agent", "腾讯公司")


@pytest.mark.asyncio
@patch("src.services.chat_service.get_company_info", new_callable=AsyncMock)
async def test_stream_chat_routes_company_investigation_to_due_diligence(
    mock_get_company_info,
    db_session,
):
    service = ChatService(db_session)
    service._load_llm_config = AsyncMock(return_value=None)
    service._workforce = MagicMock()
    service.create_conversation = AsyncMock(return_value=SimpleNamespace(id="conv-stream"))
    service.add_message = AsyncMock(
        side_effect=[
            SimpleNamespace(id="user-msg", citations=None, actions=None),
            SimpleNamespace(id="assistant-msg", citations=None, actions=None),
        ]
    )

    mock_get_company_info.return_value = {
        "basic_info": {
            "name": "杭州某某科技有限公司",
            "status": "正常",
            "legal_representative": "张明",
            "registered_capital": "1000万元",
            "established_date": "2020-01-01",
            "data_source": "公开工商数据",
        },
        "litigation": {"plaintiff_cases": 1, "defendant_cases": 2},
        "credit": {"credit_rating": "B"},
        "risk": {
            "overall_rating": "medium",
            "operation_risk": 35,
            "litigation_risk": 45,
            "credit_risk": 30,
            "compliance_risk": 25,
            "relation_risk": 20,
            "risk_points": ["作为被告案件较多，需关注历史纠纷"],
            "recommendations": ["建议核查近两年裁判文书与执行信息"],
        },
    }

    events = []
    async for event in service.stream_chat("请查一下杭州某某科技有限公司的诉讼记录和工商情况"):
        events.append(event)

    assert any(event.get("agent") == "尽职调查Agent" for event in events)
    assert any(
        "尽调摘要" in event.get("text", "") for event in events if event.get("type") == "content"
    )
    assert events[-1]["type"] == "done"
    assert events[-1]["agent"] == "尽职调查Agent"
    assert not service._workforce.process_task.called
