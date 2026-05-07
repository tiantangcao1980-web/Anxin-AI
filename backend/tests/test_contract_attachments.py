from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.core.config import settings
from src.core.security import create_access_token
from src.models.audit import AuditAction, AuditLog
from src.models.contract import Contract, ContractStatus
from src.models.user import Organization, User
from src.services.contract_service import ContractService
from src.services.object_storage_service import LocalObjectStorageService


@pytest_asyncio.fixture
async def attachment_contract(db_session, test_user):
    contract = Contract(
        id=str(uuid4()),
        title="附件生命周期合同",
        contract_number=f"CONTRACT-ATTACH-{uuid4().hex[:8]}",
        contract_type="service",
        status=ContractStatus.DRAFT,
        org_id=test_user.org_id,
        original_text="合同正文",
    )
    db_session.add(contract)
    await db_session.flush()
    return contract


@pytest_asyncio.fixture
async def outsider_client(db_session):
    from src.api.main import app
    from src.core.database import get_db

    org = Organization(id=str(uuid4()), name="合同附件外部组织")
    user = User(
        id=str(uuid4()),
        email=f"attachment-outsider-{uuid4().hex[:8]}@example.com",
        name="外部用户",
        hashed_password="hashed_password",
        org_id=org.id,
        is_active=True,
    )
    db_session.add_all([org, user])
    await db_session.flush()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(user_id=user.id)
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_contract_attachment_service_lifecycle(db_session, tmp_path: Path, attachment_contract):
    storage = LocalObjectStorageService(tmp_path)
    service = ContractService(db_session, object_storage=storage)

    attachment = await service.upload_attachment(
        attachment_contract.id,
        filename="../补充协议.txt",
        content="补充协议内容".encode(),
        content_type="text/plain",
        org_id=attachment_contract.org_id,
        actor_id=str(uuid4()),
    )

    assert attachment.original_filename == "补充协议.txt"
    assert attachment.storage_backend == "local"
    assert attachment.file_size == len("补充协议内容".encode())
    assert await storage.get(attachment.object_key) == "补充协议内容".encode()

    listed = await service.list_attachments(attachment_contract.id, org_id=attachment_contract.org_id)
    assert [item.id for item in listed] == [attachment.id]

    loaded, content = await service.get_attachment_content(
        attachment_contract.id,
        attachment.id,
        org_id=attachment_contract.org_id,
    )
    assert loaded.id == attachment.id
    assert content == "补充协议内容".encode()
    url_attachment, download_url = await service.get_attachment_download_url(
        attachment_contract.id,
        attachment.id,
        org_id=attachment_contract.org_id,
    )
    assert url_attachment.id == attachment.id
    assert download_url == f"local://{attachment.object_key}"

    deleted = await service.delete_attachment(
        attachment_contract.id,
        attachment.id,
        org_id=attachment_contract.org_id,
    )
    assert deleted.id == attachment.id
    assert await storage.exists(attachment.object_key) is False
    assert await service.list_attachments(attachment_contract.id, org_id=attachment_contract.org_id) == []


@pytest.mark.asyncio
async def test_contract_attachment_api_upload_list_download_delete(
    auth_client,
    db_session,
    test_user,
    attachment_contract,
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local", raising=False)
    monkeypatch.setattr(settings, "STORAGE_LOCAL_PATH", str(tmp_path), raising=False)

    upload = await auth_client.post(
        f"/api/v1/contracts/{attachment_contract.id}/attachments",
        files={"file": ("补充协议.txt", b"hello attachment", "text/plain")},
    )

    assert upload.status_code == 200
    payload = upload.json()
    assert payload["code"] == 200
    attachment = payload["data"]
    assert attachment["filename"] == "补充协议.txt"
    assert attachment["file_size"] == len(b"hello attachment")
    assert attachment["storage_backend"] == "local"
    assert (tmp_path / attachment["object_key"]).read_bytes() == b"hello attachment"

    list_response = await auth_client.get(f"/api/v1/contracts/{attachment_contract.id}/attachments")
    assert list_response.status_code == 200
    assert list_response.json()["data"]["attachments"][0]["id"] == attachment["id"]

    download = await auth_client.get(
        f"/api/v1/contracts/{attachment_contract.id}/attachments/{attachment['id']}/download"
    )
    assert download.status_code == 200
    assert download.content == b"hello attachment"
    assert "filename*=UTF-8''" in download.headers["content-disposition"]

    download_url = await auth_client.get(
        f"/api/v1/contracts/{attachment_contract.id}/attachments/{attachment['id']}/download-url"
    )
    assert download_url.status_code == 200
    assert download_url.json()["data"]["download_url"] == f"local://{attachment['object_key']}"
    assert download_url.json()["data"]["expires_seconds"] == 3600

    delete_response = await auth_client.delete(
        f"/api/v1/contracts/{attachment_contract.id}/attachments/{attachment['id']}"
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["deleted"] is True
    assert not (tmp_path / attachment["object_key"]).exists()

    empty_list = await auth_client.get(f"/api/v1/contracts/{attachment_contract.id}/attachments")
    assert empty_list.json()["data"]["attachments"] == []

    audit_result = await db_session.execute(
        select(AuditLog.action).where(AuditLog.resource_id == attachment_contract.id)
    )
    assert {
        AuditAction.CONTRACT_ATTACHMENT_UPLOAD.value,
        AuditAction.CONTRACT_ATTACHMENT_DOWNLOAD.value,
        AuditAction.CONTRACT_ATTACHMENT_DELETE.value,
    } <= set(audit_result.scalars().all())


@pytest.mark.asyncio
async def test_contract_attachment_api_blocks_cross_org_access(
    auth_client,
    outsider_client,
    db_session,
    attachment_contract,
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local", raising=False)
    monkeypatch.setattr(settings, "STORAGE_LOCAL_PATH", str(tmp_path), raising=False)

    upload = await auth_client.post(
        f"/api/v1/contracts/{attachment_contract.id}/attachments",
        files={"file": ("证据.txt", b"owner-only", "text/plain")},
    )
    attachment = upload.json()["data"]

    outsider_upload = await outsider_client.post(
        f"/api/v1/contracts/{attachment_contract.id}/attachments",
        files={"file": ("外部.txt", b"blocked", "text/plain")},
    )
    assert outsider_upload.status_code == 200
    assert outsider_upload.json()["code"] == 404

    outsider_list = await outsider_client.get(f"/api/v1/contracts/{attachment_contract.id}/attachments")
    assert outsider_list.status_code == 200
    assert outsider_list.json()["code"] == 404

    outsider_download = await outsider_client.get(
        f"/api/v1/contracts/{attachment_contract.id}/attachments/{attachment['id']}/download"
    )
    assert outsider_download.status_code == 404

    outsider_download_url = await outsider_client.get(
        f"/api/v1/contracts/{attachment_contract.id}/attachments/{attachment['id']}/download-url"
    )
    assert outsider_download_url.status_code == 200
    assert outsider_download_url.json()["code"] == 404

    outsider_delete = await outsider_client.delete(
        f"/api/v1/contracts/{attachment_contract.id}/attachments/{attachment['id']}"
    )
    assert outsider_delete.status_code == 200
    assert outsider_delete.json()["code"] == 404
    assert (tmp_path / attachment["object_key"]).read_bytes() == b"owner-only"


@pytest.mark.asyncio
async def test_contract_attachment_upload_uses_shared_file_validation(
    auth_client,
    attachment_contract,
):
    response = await auth_client.post(
        f"/api/v1/contracts/{attachment_contract.id}/attachments",
        files={"file": ("payload.exe", b"MZ", "application/x-msdownload")},
    )

    assert response.status_code == 400
    assert "不支持的文件类型" in response.text
