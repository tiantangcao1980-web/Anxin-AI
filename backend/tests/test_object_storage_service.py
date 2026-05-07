from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.models.contract import Contract
from src.models.document import DocumentVersion
from src.services.contract_service import ContractService
from src.services.document_service import DocumentService
from src.services.object_storage_service import LocalObjectStorageService, ObjectStorageError


@pytest.mark.asyncio
async def test_local_object_storage_put_get_delete_roundtrip(tmp_path: Path):
    storage = LocalObjectStorageService(tmp_path)

    stored = await storage.put(
        "documents/org-1/example.txt",
        b"hello storage",
        content_type="text/plain",
    )

    assert stored.backend == "local"
    assert stored.object_key == "documents/org-1/example.txt"
    assert await storage.get(stored.object_key) == b"hello storage"
    assert await storage.exists(stored.object_key) is True

    await storage.delete(stored.object_key)

    assert await storage.exists(stored.object_key) is False


@pytest.mark.asyncio
async def test_local_object_storage_rejects_path_traversal(tmp_path: Path):
    storage = LocalObjectStorageService(tmp_path)

    with pytest.raises(ObjectStorageError):
        await storage.put("../secret.txt", b"nope")


@pytest.mark.asyncio
async def test_document_upload_writes_object_storage(db_session, tmp_path: Path, monkeypatch):
    async def fake_parse_contract_document(file_content: bytes, file_name: str):
        return {"text": file_content.decode("utf-8")}

    monkeypatch.setattr(
        "src.services.document_parser.parse_contract_document",
        fake_parse_contract_document,
    )
    storage = LocalObjectStorageService(tmp_path)
    service = DocumentService(db_session, object_storage=storage)
    org_id = str(uuid4())

    document = await service.upload_document(
        name="memo.txt",
        file_content=b"contract memo",
        mime_type="text/plain",
        org_id=org_id,
        created_by=None,
    )

    assert document.storage_backend == "local"
    assert document.object_key == document.file_path
    assert document.object_key.endswith(".txt")
    assert await storage.get(document.object_key) == b"contract memo"
    assert document.extracted_text == "contract memo"


@pytest.mark.asyncio
async def test_document_content_update_preserves_versions_in_storage(
    db_session,
    tmp_path: Path,
    monkeypatch,
):
    async def fake_parse_contract_document(file_content: bytes, file_name: str):
        return {"text": file_content.decode("utf-8")}

    monkeypatch.setattr(
        "src.services.document_parser.parse_contract_document",
        fake_parse_contract_document,
    )
    storage = LocalObjectStorageService(tmp_path)
    service = DocumentService(db_session, object_storage=storage)
    org_id = str(uuid4())
    document = await service.create_text_document(
        name="draft.md",
        content="old content",
        org_id=org_id,
    )
    old_key = document.object_key

    updated = await service.update_document_content(
        document.id,
        "new content",
        org_id=org_id,
        change_summary="update",
    )
    version_result = await db_session.execute(
        select(DocumentVersion).where(DocumentVersion.document_id == document.id)
    )
    versions = list(version_result.scalars().all())

    assert updated is not None
    assert updated.version == 2
    assert updated.object_key != old_key
    assert await storage.get(updated.object_key) == b"new content"
    assert await storage.get(old_key) == b"old content"
    assert len(versions) == 1
    assert versions[0].object_key == old_key
    assert versions[0].storage_backend == "local"


@pytest.mark.asyncio
async def test_document_delete_removes_current_and_version_objects(
    db_session,
    tmp_path: Path,
    monkeypatch,
):
    async def fake_parse_contract_document(file_content: bytes, file_name: str):
        return {"text": file_content.decode("utf-8")}

    monkeypatch.setattr(
        "src.services.document_parser.parse_contract_document",
        fake_parse_contract_document,
    )
    storage = LocalObjectStorageService(tmp_path)
    service = DocumentService(db_session, object_storage=storage)
    org_id = str(uuid4())
    document = await service.create_text_document(
        name="draft.md",
        content="old content",
        org_id=org_id,
    )
    old_key = document.object_key
    updated = await service.update_document_content(
        document.id,
        "new content",
        org_id=org_id,
    )
    new_key = updated.object_key

    assert await service.delete_document(document.id, org_id=org_id) is True

    assert await storage.exists(old_key) is False
    assert await storage.exists(new_key) is False


@pytest.mark.asyncio
async def test_contract_save_file_writes_object_storage(db_session, tmp_path: Path):
    storage = LocalObjectStorageService(tmp_path)
    org_id = str(uuid4())
    contract = Contract(
        title="服务合同",
        contract_number="CONTRACT-STORAGE-1",
        contract_type="service",
        original_text="合同正文",
        org_id=org_id,
    )
    db_session.add(contract)
    await db_session.flush()
    service = ContractService(db_session, object_storage=storage)

    object_key = await service.save_contract_file(
        contract.id,
        user_id="user-storage",
        org_id=org_id,
    )

    assert object_key == f"contracts/{org_id}/CONTRACT-STORAGE-1/{contract.id}.txt"
    assert await storage.get(object_key) == "合同正文".encode()
