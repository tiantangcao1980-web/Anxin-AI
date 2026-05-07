from uuid import uuid4

import pytest

from src.models.contract import Contract, ContractStatus
from src.services.contract_lifecycle_service import (
    LEGAL_TRANSITIONS,
    ContractLifecycleStateMachine,
    IllegalStateTransition,
    can_transition_contract,
)
from src.services.contract_service import ContractService


def _contract_with_status(status: ContractStatus) -> Contract:
    return Contract(
        id=str(uuid4()),
        title="状态机测试合同",
        contract_number=f"STATE-{uuid4().hex[:8]}",
        contract_type="service",
        status=status,
    )


def test_transition_matrix_covers_all_contract_statuses():
    assert set(LEGAL_TRANSITIONS) == set(ContractStatus)


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (ContractStatus.DRAFT, ContractStatus.UNDER_REVIEW),
        (ContractStatus.UNDER_REVIEW, ContractStatus.REVIEW_FAILED),
        (ContractStatus.REVIEW_FAILED, ContractStatus.UNDER_REVIEW),
        (ContractStatus.UNDER_REVIEW, ContractStatus.PENDING_REVIEW),
        (ContractStatus.PENDING_REVIEW, ContractStatus.APPROVED),
        (ContractStatus.APPROVED, ContractStatus.SIGNED),
        (ContractStatus.SIGNED, ContractStatus.ACTIVE),
        (ContractStatus.ACTIVE, ContractStatus.EXPIRED),
    ],
)
def test_legal_contract_status_transitions(source, target):
    contract = _contract_with_status(source)

    ContractLifecycleStateMachine.transition(
        contract,
        target,
        actor_id="tester",
        reason="unit-test",
    )

    assert contract.status == target
    assert can_transition_contract(source, target) is True


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (ContractStatus.DRAFT, ContractStatus.SIGNED),
        (ContractStatus.APPROVED, ContractStatus.UNDER_REVIEW),
        (ContractStatus.SIGNED, ContractStatus.DRAFT),
        (ContractStatus.ACTIVE, ContractStatus.PENDING_REVIEW),
        (ContractStatus.EXPIRED, ContractStatus.ACTIVE),
        (ContractStatus.TERMINATED, ContractStatus.APPROVED),
    ],
)
def test_illegal_contract_status_transitions_are_rejected(source, target):
    contract = _contract_with_status(source)

    with pytest.raises(IllegalStateTransition):
        ContractLifecycleStateMachine.transition(contract, target)

    assert contract.status == source
    assert can_transition_contract(source, target) is False


@pytest.mark.asyncio
async def test_service_transition_preserves_status_on_illegal_transition(
    db_session,
    test_organization,
):
    service = ContractService(db_session)
    contract = await service.create_contract(
        title="不可回退合同",
        contract_type="service",
        org_id=test_organization.id,
    )
    contract.status = ContractStatus.SIGNED
    await db_session.flush()

    with pytest.raises(IllegalStateTransition):
        await service.transition_status(
            contract.id,
            ContractStatus.DRAFT,
            actor_id="tester",
            reason="illegal rollback",
            org_id=test_organization.id,
        )

    await db_session.refresh(contract)
    assert contract.status == ContractStatus.SIGNED


@pytest.mark.asyncio
async def test_transition_api_accepts_legal_transition(auth_client, db_session, test_user):
    contract = Contract(
        id=str(uuid4()),
        title="API 状态转换合同",
        contract_number=f"API-STATE-{uuid4().hex[:8]}",
        contract_type="service",
        status=ContractStatus.DRAFT,
        org_id=test_user.org_id,
    )
    db_session.add(contract)
    await db_session.flush()

    response = await auth_client.post(
        f"/api/v1/contracts/{contract.id}/transition",
        json={"status": "pending_review", "reason": "submit for review"},
    )

    assert response.status_code == 200
    assert response.json()["code"] == 200
    assert response.json()["data"]["status"] == ContractStatus.PENDING_REVIEW.value
    await db_session.refresh(contract)
    assert contract.status == ContractStatus.PENDING_REVIEW


@pytest.mark.asyncio
async def test_transition_api_rejects_illegal_transition(auth_client, db_session, test_user):
    contract = Contract(
        id=str(uuid4()),
        title="API 非法转换合同",
        contract_number=f"API-ILLEGAL-{uuid4().hex[:8]}",
        contract_type="service",
        status=ContractStatus.TERMINATED,
        org_id=test_user.org_id,
    )
    db_session.add(contract)
    await db_session.flush()

    response = await auth_client.post(
        f"/api/v1/contracts/{contract.id}/transition",
        json={"status": "approved", "reason": "revive terminated contract"},
    )

    assert response.status_code == 409
    await db_session.refresh(contract)
    assert contract.status == ContractStatus.TERMINATED


@pytest.mark.asyncio
async def test_transition_api_rejects_unknown_status(auth_client, db_session, test_user):
    contract = Contract(
        id=str(uuid4()),
        title="API 未知状态合同",
        contract_number=f"API-UNKNOWN-{uuid4().hex[:8]}",
        contract_type="service",
        status=ContractStatus.DRAFT,
        org_id=test_user.org_id,
    )
    db_session.add(contract)
    await db_session.flush()

    response = await auth_client.post(
        f"/api/v1/contracts/{contract.id}/transition",
        json={"status": "archived", "reason": "unsupported"},
    )

    assert response.status_code == 422
    await db_session.refresh(contract)
    assert contract.status == ContractStatus.DRAFT


@pytest.mark.asyncio
async def test_esign_flow_rejects_contract_before_approval(
    auth_client,
    db_session,
    test_user,
):
    contract = Contract(
        id=str(uuid4()),
        title="未审批电签合同",
        contract_number=f"API-ESIGN-{uuid4().hex[:8]}",
        contract_type="service",
        status=ContractStatus.DRAFT,
        org_id=test_user.org_id,
    )
    db_session.add(contract)
    await db_session.flush()

    response = await auth_client.post(
        "/api/v1/esign/flows",
        json={
            "contract_id": contract.id,
            "title": "未审批电签合同",
            "signers": [{"name": "张三"}],
        },
    )

    assert response.status_code == 409
    await db_session.refresh(contract)
    assert contract.status == ContractStatus.DRAFT
