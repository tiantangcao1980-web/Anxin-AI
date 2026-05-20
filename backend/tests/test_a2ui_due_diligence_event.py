from unittest.mock import AsyncMock, patch

import pytest

from src.services.a2ui_intent_handler import handle_a2ui_event


@pytest.mark.asyncio
@patch("src.services.a2ui_intent_handler.get_company_info", new_callable=AsyncMock)
async def test_start_due_diligence_event_returns_structured_cards(mock_get_company_info):
    mock_get_company_info.return_value = {
        "basic_info": {
            "name": "杭州某某科技有限公司",
            "status": "正常",
            "legal_representative": "张明",
            "registered_capital": "1000万元",
        },
        "litigation": {"plaintiff_cases": 1, "defendant_cases": 2},
        "credit": {"credit_rating": "B"},
        "risk": {
            "overall_rating": "medium",
            "risk_points": ["作为被告案件较多，需关注历史纠纷"],
            "recommendations": ["建议核查近两年裁判文书与执行信息"],
        },
    }

    result = await handle_a2ui_event(
        action_id="start_due_diligence",
        component_id="form-1",
        form_data={
            "company_name": "杭州某某科技有限公司",
            "investigation_scope": ["basic", "litigation"],
            "purpose": "supplier",
        },
    )

    assert result is not None
    assert result["type"] == "a2ui_message"
    component_types = [component["type"] for component in result["components"]]
    assert "status-card" in component_types
    assert "detail-list" in component_types
    assert result["agent"] == "尽职调查 Agent"


@pytest.mark.asyncio
async def test_start_due_diligence_event_requires_company_name():
    result = await handle_a2ui_event(
        action_id="start_due_diligence",
        component_id="form-2",
        form_data={},
    )

    assert result is not None
    assert result["type"] == "a2ui_message"
    assert any(
        "请先填写需要调查的企业名称" in component["data"].get("content", "")
        or "请先填写需要调查的企业名称" in component["data"].get("description", "")
        for component in result["components"]
    )
