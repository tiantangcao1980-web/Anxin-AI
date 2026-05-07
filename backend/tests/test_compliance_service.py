import pytest

from src.services.compliance_service import ComplianceService


@pytest.mark.asyncio
async def test_generate_report_falls_back_to_rule_based_suggestions() -> None:
    service = ComplianceService()

    report = await service.generate_report(
        {
            "industry": "technology",
            "industry_name": "科技/互联网",
            "score": 72,
            "grade": "C",
            "grade_label": "需改进",
            "risk_summary": {"high": 1, "medium": 0, "low": 0},
            "non_compliant_details": [
                {
                    "id": "tech_data_01",
                    "question": "是否制定了个人信息保护政策？",
                    "risk_level": "high",
                    "law_ref": "《个人信息保护法》第13条",
                }
            ],
            "recommendations": ["完善个人信息保护制度"],
        },
        company_name="安心科技",
    )

    assert report["company_name"] == "安心科技"
    assert report["score"] == 72
    assert "安心科技" in report["html"]
    assert report["ai_suggestions"] == [
        {
            "item_id": "tech_data_01",
            "suggestion": "建议按照《个人信息保护法》第13条要求，尽快完善相关制度并留存书面记录",
        }
    ]


@pytest.mark.asyncio
async def test_compare_evaluations_reports_score_and_risk_delta() -> None:
    service = ComplianceService()

    result = await service.compare_evaluations(
        current={"score": 88, "risk_summary": {"high": 1, "medium": 2, "low": 0}},
        previous={"score": 80, "risk_summary": {"high": 3, "medium": 1, "low": 0}},
    )

    assert result["score_delta"] == 8
    assert result["trend"] == "improved"
    assert result["risk_changes"] == {"high": -2, "medium": 1, "low": 0}
