from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base import AgentResponse
from src.agents.coordinator import CoordinatorAgent

from .conftest import create_auth_headers


@pytest.mark.asyncio
async def test_aggregate_results_preserves_contract_review_structure():
    coordinator = object.__new__(CoordinatorAgent)

    investigation = AgentResponse(
        agent_name="合同调查Agent",
        content="已完成前置调查",
        metadata={
            "contract_type": "采购合同",
            "focus_areas": [{"area": "付款条款"}],
            "missing_elements": ["验收标准"],
        },
    )
    review = AgentResponse(
        agent_name="合同审查Agent",
        content="已完成风险识别",
        metadata={
            "summary": "合同存在付款节点缺失与违约责任失衡风险",
            "risk_level": "high",
            "risk_score": 0.82,
            "risks": [
                {
                    "type": "payment",
                    "title": "付款节点缺失",
                    "level": "high",
                    "description": "未明确分期付款条件",
                    "suggestion": "补充阶段性付款安排",
                }
            ],
            "suggestions": ["补充付款节点", "增加争议解决条款"],
            "key_terms": {"amount": "100万元"},
            "missing_clauses": ["争议解决"],
        },
    )
    verification = AgentResponse(
        agent_name="审查验证Agent",
        content="已完成质量验证",
        metadata={
            "quality_score": 0.91,
            "confidence_level": "high",
            "verification_results": [{"risk_index": 0, "legal_basis_correct": True}],
        },
    )

    result = await coordinator.aggregate_results([investigation, review, verification])

    assert result["summary"] == "合同存在付款节点缺失与违约责任失衡风险"
    assert result["risk_level"] == "high"
    assert result["risk_score"] == 0.82
    assert result["risks"][0]["title"] == "付款节点缺失"
    assert result["key_risks"][0]["title"] == "付款节点缺失"
    assert result["missing_clauses"] == ["争议解决"]
    assert result["investigation"]["contract_type"] == "采购合同"
    assert result["verification"]["confidence_level"] == "high"


@pytest.mark.asyncio
async def test_quick_review_uses_risks_when_key_risks_missing(client, test_user, monkeypatch):
    fake_workforce = MagicMock(
        process_task=AsyncMock(
            return_value={
                "final_result": {
                    "summary": "审查完成",
                    "risk_level": "high",
                    "risk_score": 0.77,
                    "risks": [
                        {
                            "type": "liability",
                            "title": "违约责任失衡",
                            "level": "high",
                            "description": "仅约束乙方责任",
                            "suggestion": "增加双方对等违约责任",
                        }
                    ],
                    "suggestions": ["增加对等违约责任"],
                    "key_terms": {"term": "一年"},
                }
            }
        )
    )

    monkeypatch.setattr(
        "src.api.routes.contracts.get_workforce",
        lambda: fake_workforce,
    )
    monkeypatch.setattr(
        "src.api.routes.contracts.contract_analyzer.analyze_contract_type",
        lambda text: "服务合同",
    )
    monkeypatch.setattr(
        "src.api.routes.contracts.contract_analyzer.extract_key_info",
        lambda text: {"high_risk_terms": []},
    )

    response = await client.post(
        "/api/v1/contracts/quick-review",
        headers=create_auth_headers(test_user),
        json={"text": "乙方承担全部违约责任，甲方不承担任何责任。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_level"] == "high"
    assert payload["risk_score"] == 0.77
    assert payload["key_risks"][0]["title"] == "违约责任失衡"
