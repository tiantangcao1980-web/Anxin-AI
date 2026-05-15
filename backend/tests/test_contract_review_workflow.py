import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.contract import ContractRisk, ContractStatus, RiskLevel
from src.services.contract_review_lock import ContractReviewAlreadyRunning
from src.services.contract_service import (
    ContractReviewTimeoutError,
    ContractService,
)

from .conftest import create_auth_headers


@pytest.mark.asyncio
async def test_review_contract_persists_risks_and_summary(
    db_session,
    test_organization,
    test_user,
):
    service = ContractService(db_session)
    service._workforce = MagicMock(
        process_task=AsyncMock(
            return_value={
                "final_result": {
                    "summary": "合同存在较高付款与违约责任风险",
                    "risks": [
                        {
                            "type": "payment",
                            "title": "付款条件过于模糊",
                            "level": "high",
                            "description": "未明确付款节点，可能导致履约争议",
                            "legal_basis": "《民法典》第五百零九条",
                            "suggestion": "补充分期付款节点",
                            "suggested_text": "乙方应在验收后 5 日内支付首期款。",
                        },
                        {
                            "type": "liability",
                            "title": "违约责任失衡",
                            "level": "medium",
                            "description": "仅约束乙方违约责任",
                            "suggestion": "增加双方对等违约责任",
                        },
                    ],
                    "suggestions": ["补充付款节点", "增加争议解决条款"],
                    "key_terms": {"parties": "甲方、乙方", "term": "一年"},
                    "missing_clauses": ["争议解决"],
                }
            }
        )
    )

    contract = await service.create_contract(
        title="采购协议",
        contract_type="purchase",
        org_id=test_organization.id,
    )

    result = await service.review_contract(
        contract_id=contract.id,
        contract_text="甲方采购设备，乙方负责交付。",
        reviewed_by=test_user.id,
    )

    await db_session.refresh(contract)
    risks = await service.get_risks(contract.id)

    assert result["risk_level"] == "medium"
    assert result["summary"] == "合同存在较高付款与违约责任风险"
    assert result["missing_clauses"] == ["争议解决"]
    assert contract.status == ContractStatus.PENDING_REVIEW
    assert contract.reviewed_by == test_user.id
    assert contract.risk_level == RiskLevel.MEDIUM
    assert contract.review_summary == "合同存在较高付款与违约责任风险"
    assert len(risks) == 2
    assert (
        "《民法典》第五百零九条" in risks[0].description
        or "《民法典》第五百零九条" in risks[1].description
    )


@pytest.mark.asyncio
async def test_review_contract_rejects_concurrent_review(
    db_session,
    test_organization,
    test_user,
):
    started = asyncio.Event()
    finish = asyncio.Event()

    async def slow_review(*_args, **_kwargs):
        started.set()
        await finish.wait()
        return {"final_result": {"summary": "并发审查完成", "risks": []}}

    service_a = ContractService(db_session)
    service_a._workforce = MagicMock(process_task=AsyncMock(side_effect=slow_review))
    service_b = ContractService(db_session)
    service_b._workforce = MagicMock(
        process_task=AsyncMock(return_value={"final_result": {"summary": "不应执行"}})
    )

    contract = await service_a.create_contract(
        title="并发审查合同",
        contract_type="service",
        org_id=test_organization.id,
    )

    review_task = asyncio.create_task(
        service_a.review_contract(
            contract_id=contract.id,
            contract_text="第一条 服务内容。",
            reviewed_by=test_user.id,
        )
    )
    await started.wait()

    with pytest.raises(ContractReviewAlreadyRunning):
        await service_b.review_contract(
            contract_id=contract.id,
            contract_text="第一条 服务内容。",
            reviewed_by=test_user.id,
        )

    finish.set()
    await review_task
    service_b._workforce.process_task.assert_not_awaited()


@pytest.mark.asyncio
async def test_review_contract_timeout_marks_failed_and_allows_retry(
    db_session,
    test_organization,
    test_user,
    monkeypatch,
):
    monkeypatch.setattr(
        "src.services.contract_service.settings.CONTRACT_REVIEW_TIMEOUT_SECONDS", 0.01
    )

    async def slow_review(*_args, **_kwargs):
        await asyncio.sleep(1)
        return {"final_result": {"summary": "不应返回"}}

    service = ContractService(db_session)
    service._workforce = MagicMock(process_task=AsyncMock(side_effect=slow_review))
    contract = await service.create_contract(
        title="超时审查合同",
        contract_type="service",
        org_id=test_organization.id,
    )

    with pytest.raises(ContractReviewTimeoutError):
        await service.review_contract(
            contract_id=contract.id,
            contract_text="第一条 交付内容。",
            reviewed_by=test_user.id,
        )

    await db_session.refresh(contract)
    assert contract.status == ContractStatus.REVIEW_FAILED
    assert contract.review_result["status"] == "failed"
    assert contract.review_result["reason"] == "contract_review_timeout"

    service._workforce = MagicMock(
        process_task=AsyncMock(return_value={"final_result": {"summary": "重试成功", "risks": []}})
    )
    result = await service.review_contract(
        contract_id=contract.id,
        contract_text="第一条 交付内容。",
        reviewed_by=test_user.id,
    )

    await db_session.refresh(contract)
    assert result["summary"] == "重试成功"
    assert contract.status == ContractStatus.PENDING_REVIEW


@pytest.mark.asyncio
async def test_apply_suggestions_rewrites_multiple_clauses_and_marks_risks_resolved(
    db_session,
    test_organization,
):
    service = ContractService(db_session)
    contract = await service.create_contract(
        title="销售合同",
        contract_type="sale",
        org_id=test_organization.id,
    )
    contract.original_text = "第一条 付款期限为30天。第二条 违约金为合同金额5%。"

    payment_risk = ContractRisk(
        contract_id=contract.id,
        risk_type="payment",
        risk_level=RiskLevel.HIGH,
        title="付款周期过长",
        description="付款周期超过建议值",
        original_text="付款期限为30天",
        suggested_text="付款期限为10天",
        suggestion="缩短回款周期",
    )
    penalty_risk = ContractRisk(
        contract_id=contract.id,
        risk_type="liability",
        risk_level=RiskLevel.MEDIUM,
        title="违约金不足",
        description="违约金偏低",
        original_text="违约金为合同金额5%",
        suggested_text="违约金为合同金额20%",
        suggestion="提高违约金比例",
    )
    db_session.add_all([payment_risk, penalty_risk])
    await db_session.flush()

    modified_text = await service.apply_suggestions(
        contract.id,
        [payment_risk.id, penalty_risk.id],
    )

    await db_session.refresh(contract)
    await db_session.refresh(payment_risk)
    await db_session.refresh(penalty_risk)

    assert modified_text == "第一条 付款期限为10天。第二条 违约金为合同金额20%。"
    assert contract.modified_text == modified_text
    assert payment_risk.is_resolved is True
    assert penalty_risk.is_resolved is True
    assert payment_risk.resolution_note == "用户已接受修改建议"
    assert penalty_risk.resolution_note == "用户已接受修改建议"


@pytest.mark.asyncio
async def test_quick_review_appends_detected_high_risk_terms(client, test_user, monkeypatch):
    fake_workforce = MagicMock(
        process_task=AsyncMock(
            return_value={
                "final_result": {
                    "summary": "已完成快速审查",
                    "risk_level": "medium",
                    "risk_score": 0.42,
                    "key_risks": [
                        {
                            "type": "termination",
                            "title": "解除条件不清晰",
                            "level": "medium",
                            "description": "解除触发条件未写明",
                        }
                    ],
                    "suggestions": ["补充解除条件"],
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
        lambda text: "采购合同",
    )
    monkeypatch.setattr(
        "src.api.routes.contracts.contract_analyzer.extract_key_info",
        lambda text: {"high_risk_terms": ["全权免责"]},
    )

    response = await client.post(
        "/api/v1/contracts/quick-review",
        headers=create_auth_headers(test_user),
        json={"text": "若发生争议，乙方承担全部责任且甲方全权免责。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_level"] == "medium"
    assert payload["risk_score"] == 0.42
    assert any(risk["title"] == "检测到高风险关键词" for risk in payload["key_risks"])
