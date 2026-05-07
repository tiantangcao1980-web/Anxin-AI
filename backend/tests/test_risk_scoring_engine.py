"""风险评分解释性与确定性回归测试。"""

import pytest

from src.services.risk_scoring_engine import risk_scoring_engine


def _sample_inputs():
    return {
        "basic_info": {
            "status": "经营异常",
            "established_date": "2025-01-01",
        },
        "litigation": {
            "execution_cases": 4,
            "dishonest_records": 1,
            "wenshu_case_count": 8,
            "data_source_execution": "中国执行信息公开网",
            "data_source_dishonest": "全国法院失信被执行人名单",
            "data_source_wenshu": "中国裁判文书网",
        },
        "credit": {
            "administrative_penalties": 3,
            "tax_violations": 1,
            "environmental_penalties": 1,
            "data_source_credit_china": "信用中国",
        },
        "llm_risk": {
            "operation_risk": 80,
            "litigation_risk": 70,
            "credit_risk": 60,
            "compliance_risk": 50,
            "relation_risk": 45,
        },
    }


def test_risk_scoring_is_deterministic_and_explainable():
    inputs = _sample_inputs()

    first = risk_scoring_engine.compute_risk_scores(**inputs)
    second = risk_scoring_engine.compute_risk_scores(**inputs)

    assert first == second
    assert first["score"] == first["overall_score"]
    assert first["overall_rating"] in {"low", "medium", "high"}
    assert isinstance(first["explain"], str)
    assert "综合风险" in first["explain"]

    factors = first["factors"]
    assert [factor["key"] for factor in factors] == [
        "operation_risk",
        "litigation_risk",
        "credit_risk",
        "compliance_risk",
        "relation_risk",
    ]
    assert all(0 <= factor["score"] <= 100 for factor in factors)
    assert all(factor["weight"] == pytest.approx(0.2) for factor in factors)
    assert all("贡献" in factor["explain"] for factor in factors)
    assert sum(factor["contribution"] for factor in factors) == pytest.approx(
        first["overall_score"],
        abs=0.2,
    )


def test_risk_scoring_keeps_dimension_contract_for_existing_callers():
    result = risk_scoring_engine.compute_risk_scores(
        basic_info={"status": "正常", "established_date": "2001-01-01"},
        litigation={},
        credit={},
        llm_risk={},
    )

    assert set(result["dimensions"]) == {
        "operation_risk",
        "litigation_risk",
        "credit_risk",
        "compliance_risk",
        "relation_risk",
    }
    assert result["risk_points"]
    assert result["recommendations"]
