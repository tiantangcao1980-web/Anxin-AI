from io import BytesIO
from uuid import uuid4

import pytest

from src.models.contract import Contract, ContractStatus
from src.services.document_export import ContractExportService, ExportSizeLimitError

from .conftest import create_auth_headers


def test_docx_export_rejects_source_content_over_limit(monkeypatch):
    monkeypatch.setenv("CONTRACT_EXPORT_MAX_BYTES", "8")

    with pytest.raises(ExportSizeLimitError):
        ContractExportService.export_docx(title="测试合同", text="123456789")


def test_export_streams_bytes_in_chunks():
    chunks = list(ContractExportService.iter_bytes(BytesIO(b"abcdef"), chunk_size=2))

    assert chunks == [b"ab", b"cd", b"ef"]


@pytest.mark.asyncio
async def test_contract_download_rejects_oversized_contract(
    client,
    db_session,
    test_user,
    monkeypatch,
):
    monkeypatch.setenv("CONTRACT_EXPORT_MAX_BYTES", "8")
    contract = Contract(
        id=str(uuid4()),
        title="超限合同",
        contract_number="EXPORT-LIMIT-001",
        contract_type="purchase",
        status=ContractStatus.DRAFT,
        org_id=test_user.org_id,
        original_text="123456789",
    )
    db_session.add(contract)
    await db_session.flush()

    response = await client.get(
        f"/api/v1/contracts/{contract.id}/download?format=docx",
        headers=create_auth_headers(test_user),
    )

    assert response.status_code == 413
    assert "导出源内容超过导出大小限制" in response.text
