import pytest

from src.api.routes.compliance import (
    ComplianceAnswer,
    ComplianceCheckRequest,
    evaluate_compliance,
    get_checklist,
    list_industries,
)
from src.models.user import User


@pytest.mark.asyncio
async def test_list_industries_exposes_template_counts() -> None:
    result = await list_industries()

    technology = next(item for item in result["industries"] if item["id"] == "technology")
    assert technology == {
        "id": "technology",
        "name": "科技/互联网",
        "category_count": 4,
        "item_count": 14,
    }


@pytest.mark.asyncio
async def test_get_checklist_rejects_unknown_industry() -> None:
    result = await get_checklist("unknown")

    assert result == {
        "error": "不支持的行业",
        "supported": ["technology", "manufacturing", "retail"],
    }


@pytest.mark.asyncio
async def test_evaluate_compliance_returns_full_report_for_authenticated_user() -> None:
    user = User(
        id=1,
        email="compliance@example.com",
        hashed_password="not-used",
        name="合规测试用户",
    )
    request = ComplianceCheckRequest(
        industry="retail",
        company_size="small",
        answers=[
            ComplianceAnswer(item_id="ret_consumer_01", answer=False),
            ComplianceAnswer(item_id="ret_consumer_02", answer=True),
            ComplianceAnswer(item_id="ret_consumer_03", answer=True),
            ComplianceAnswer(item_id="ret_data_01", answer=True),
            ComplianceAnswer(item_id="ret_data_02", answer=True),
            ComplianceAnswer(item_id="ret_labor_01", answer=True),
            ComplianceAnswer(item_id="ret_labor_02", answer=True),
        ],
    )

    result = await evaluate_compliance(request, user=user)

    assert result["score"] == 86
    assert result["grade"] == "B"
    assert result["full_report"] is True
    assert result["risk_summary"] == {"high": 1, "medium": 0, "low": 0}
    assert result["non_compliant_details"] == [
        {
            "id": "ret_consumer_01",
            "question": "商品/服务描述是否真实准确？",
            "risk_level": "high",
            "law_ref": "《消费者权益保护法》第20条",
        }
    ]
    assert result["recommendations"] == [
        "【HIGH】商品/服务描述是否真实准确？ — 参考法规：《消费者权益保护法》第20条"
    ]
