from uuid import uuid4

import pytest

from src.models.contract import Contract, ContractRisk, ContractStatus, RiskLevel
from src.services.contract_lifecycle_service import IllegalStateTransition
from src.services.contract_service import ContractService


async def _contract_with_versions(db_session, test_organization, test_user):
    service = ContractService(db_session)
    contract = await service.create_contract(
        title="版本合同",
        contract_type="service",
        org_id=test_organization.id,
    )
    contract.original_text = "第一条 付款期限为30天。\n\n第二条 违约金为合同金额5%。"
    risk = ContractRisk(
        contract_id=contract.id,
        risk_type="payment",
        risk_level=RiskLevel.HIGH,
        title="付款周期过长",
        description="付款周期超过建议值",
        original_text="付款期限为30天",
        suggested_text="付款期限为10天",
        suggestion="缩短回款周期",
    )
    db_session.add(risk)
    await db_session.flush()

    await service.apply_suggestions(
        contract.id,
        [risk.id],
        actor_id=test_user.id,
        org_id=test_organization.id,
    )
    await db_session.refresh(contract)
    return service, contract


@pytest.mark.asyncio
async def test_apply_suggestions_creates_contract_versions_and_structured_diff(
    db_session,
    test_organization,
    test_user,
):
    service, contract = await _contract_with_versions(db_session, test_organization, test_user)

    versions = await service.get_contract_versions(contract.id, org_id=test_organization.id)
    diff = await service.get_version_diff(contract.id, 1, 2, org_id=test_organization.id)

    assert [version.version for version in versions] == [2, 1]
    assert contract.version == 2
    assert versions[0].source == "suggestion"
    assert diff["summary"]["replacements"] == 1
    assert diff["changes"][0]["old_text"] == "第一条 付款期限为30天。"
    assert diff["changes"][0]["new_text"] == "第一条 付款期限为10天。"


@pytest.mark.asyncio
async def test_rollback_to_version_uses_lifecycle_and_creates_new_snapshot(
    db_session,
    test_organization,
    test_user,
):
    service, contract = await _contract_with_versions(db_session, test_organization, test_user)
    contract.status = ContractStatus.PENDING_REVIEW
    await db_session.flush()

    rolled_back = await service.rollback_to_version(
        contract.id,
        1,
        actor_id=test_user.id,
        reason="restore original",
        org_id=test_organization.id,
    )
    versions = await service.get_contract_versions(contract.id, org_id=test_organization.id)

    assert rolled_back.status == ContractStatus.DRAFT
    assert rolled_back.version == 3
    assert rolled_back.modified_text == "第一条 付款期限为30天。\n\n第二条 违约金为合同金额5%。"
    assert versions[0].source == "rollback"
    assert versions[0].description == "rollback to version 1"


@pytest.mark.asyncio
async def test_rollback_rejects_terminal_contract_status(
    db_session,
    test_organization,
    test_user,
):
    service, contract = await _contract_with_versions(db_session, test_organization, test_user)
    contract.status = ContractStatus.TERMINATED
    current_text = contract.modified_text
    await db_session.flush()

    with pytest.raises(IllegalStateTransition):
        await service.rollback_to_version(
            contract.id,
            1,
            actor_id=test_user.id,
            reason="illegal revive",
            org_id=test_organization.id,
        )

    await db_session.refresh(contract)
    assert contract.status == ContractStatus.TERMINATED
    assert contract.modified_text == current_text


@pytest.mark.asyncio
async def test_contract_version_api_lists_diffs_and_rolls_back(
    auth_client,
    db_session,
    test_organization,
    test_user,
):
    service, contract = await _contract_with_versions(db_session, test_organization, test_user)
    contract.status = ContractStatus.PENDING_REVIEW
    await db_session.flush()

    versions_response = await auth_client.get(f"/api/v1/contracts/{contract.id}/versions")
    diff_response = await auth_client.get(
        f"/api/v1/contracts/{contract.id}/versions/diff",
        params={"from_version": 1, "to_version": 2},
    )
    rollback_response = await auth_client.post(
        f"/api/v1/contracts/{contract.id}/versions/1/rollback",
        json={"reason": "restore original"},
    )

    assert versions_response.status_code == 200
    assert [item["version"] for item in versions_response.json()["data"]["versions"]] == [2, 1]
    assert diff_response.status_code == 200
    assert diff_response.json()["data"]["summary"]["replacements"] == 1
    assert rollback_response.status_code == 200
    assert rollback_response.json()["data"]["status"] == ContractStatus.DRAFT.value
    assert rollback_response.json()["data"]["version"] == 3
    assert (
        rollback_response.json()["data"]["text"]
        == "第一条 付款期限为30天。\n\n第二条 违约金为合同金额5%。"
    )


@pytest.mark.asyncio
async def test_contract_version_api_blocks_cross_org_access(
    auth_client,
    db_session,
):
    other_contract = Contract(
        id=str(uuid4()),
        title="其他组织合同",
        contract_number=f"OTHER-{uuid4().hex[:8]}",
        contract_type="service",
        status=ContractStatus.DRAFT,
        org_id=str(uuid4()),
        original_text="其他组织正文",
    )
    db_session.add(other_contract)
    await db_session.flush()

    response = await auth_client.get(f"/api/v1/contracts/{other_contract.id}/versions")

    assert response.status_code == 200
    assert response.json()["code"] == 404
