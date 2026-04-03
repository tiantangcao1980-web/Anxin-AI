from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.security import create_access_token
from src.models.contract import Contract, ContractRisk, ContractStatus, RiskLevel
from src.models.user import Organization, User


@pytest_asyncio.fixture
async def outsider_org(db_session):
    org = Organization(
        id=str(uuid4()),
        name="合同外部组织",
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def outsider_user(db_session, outsider_org):
    user = User(
        id=str(uuid4()),
        email=f"contract-outsider-{uuid4().hex[:8]}@example.com",
        name="合同外部用户",
        hashed_password="hashed_password",
        org_id=outsider_org.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def outsider_client(db_session, outsider_user):
    from src.api.main import app
    from src.core.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(user_id=outsider_user.id)
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def primary_contract(db_session, test_user):
    contract = Contract(
        title="内部采购合同",
        contract_number="CONTRACT-TEST-001",
        contract_type="purchase",
        status=ContractStatus.DRAFT,
        org_id=test_user.org_id,
        original_text="第一条 付款期限为30天。",
    )
    db_session.add(contract)
    await db_session.flush()
    return contract


@pytest.mark.asyncio
async def test_contract_detail_blocks_cross_org_access(outsider_client, primary_contract):
    response = await outsider_client.get(f"/api/v1/contracts/{primary_contract.id}")

    assert response.status_code == 200
    assert response.json()["code"] == 404


@pytest.mark.asyncio
async def test_contract_review_blocks_cross_org_access(outsider_client, primary_contract):
    response = await outsider_client.post(
        f"/api/v1/contracts/{primary_contract.id}/review",
        json={"contract_text": "请审查这份合同"},
    )

    assert response.status_code == 200
    assert response.json()["code"] == 404


@pytest.mark.asyncio
async def test_contract_apply_suggestions_blocks_cross_org_access(
    outsider_client,
    db_session,
    primary_contract,
):
    risk = ContractRisk(
        contract_id=primary_contract.id,
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

    response = await outsider_client.post(
        f"/api/v1/contracts/{primary_contract.id}/apply-suggestions",
        json={"accepted_risk_ids": [risk.id]},
    )

    assert response.status_code == 200
    assert response.json()["code"] == 404


@pytest.mark.asyncio
async def test_contract_risk_resolution_blocks_cross_org_access(
    outsider_client,
    db_session,
    primary_contract,
):
    risk = ContractRisk(
        contract_id=primary_contract.id,
        risk_type="payment",
        risk_level=RiskLevel.HIGH,
        title="付款周期过长",
        description="付款周期超过建议值",
        suggestion="缩短回款周期",
    )
    db_session.add(risk)
    await db_session.flush()

    response = await outsider_client.post(
        f"/api/v1/contracts/{primary_contract.id}/risks/{risk.id}/resolve",
    )

    await db_session.refresh(risk)

    assert response.status_code == 200
    assert response.json()["code"] == 404
    assert risk.is_resolved is False


@pytest.mark.asyncio
async def test_contract_risks_blocks_cross_org_access(
    outsider_client,
    db_session,
    primary_contract,
):
    risk = ContractRisk(
        contract_id=primary_contract.id,
        risk_type="payment",
        risk_level=RiskLevel.HIGH,
        title="付款周期过长",
        description="付款周期超过建议值",
        suggestion="缩短回款周期",
    )
    db_session.add(risk)
    await db_session.flush()

    response = await outsider_client.get(
        f"/api/v1/contracts/{primary_contract.id}/risks",
    )

    assert response.status_code == 200
    assert response.json()["code"] == 404


@pytest.mark.asyncio
async def test_contract_save_file_blocks_cross_org_access(outsider_client, primary_contract):
    response = await outsider_client.post(
        f"/api/v1/contracts/{primary_contract.id}/save-file",
    )

    assert response.status_code == 200
    assert response.json()["code"] == 404


@pytest.mark.asyncio
async def test_contract_download_blocks_cross_org_access(outsider_client, primary_contract):
    response = await outsider_client.get(
        f"/api/v1/contracts/{primary_contract.id}/download",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "合同不存在"
