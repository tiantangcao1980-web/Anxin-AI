from uuid import uuid4

import pytest

from src.core.validators import FileValidator
from src.models.knowledge import KnowledgeBase, KnowledgeType

from .conftest import create_auth_headers


@pytest.mark.asyncio
async def test_upload_document_rejects_disallowed_extension(client, test_user):
    response = await client.post(
        "/api/v1/documents/",
        headers=create_auth_headers(test_user),
        files={"file": ("payload.exe", b"MZ", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "不支持的文件类型" in response.text


@pytest.mark.asyncio
async def test_upload_document_rejects_disallowed_mime(client, test_user):
    response = await client.post(
        "/api/v1/documents/",
        headers=create_auth_headers(test_user),
        files={"file": ("memo.txt", b"hello", "application/x-msdownload")},
    )

    assert response.status_code == 400
    assert "不支持的 MIME 类型" in response.text


@pytest.mark.asyncio
async def test_upload_document_rejects_oversized_file(client, test_user, monkeypatch):
    monkeypatch.setattr(FileValidator, "MAX_SIZE", 8)

    response = await client.post(
        "/api/v1/documents/",
        headers=create_auth_headers(test_user),
        files={"file": ("memo.txt", b"larger than eight bytes", "text/plain")},
    )

    assert response.status_code == 413
    assert "文件过大" in response.text


@pytest.mark.asyncio
async def test_upload_document_rejects_spoofed_pdf_content(client, test_user):
    response = await client.post(
        "/api/v1/documents/",
        headers=create_auth_headers(test_user),
        files={"file": ("contract.pdf", b"not actually a pdf", "application/pdf")},
    )

    assert response.status_code == 400
    assert "文件内容与扩展名不匹配" in response.text


@pytest.mark.asyncio
async def test_knowledge_upload_rejects_disallowed_mime(client, db_session, test_user):
    kb = KnowledgeBase(
        id=str(uuid4()),
        name="上传校验知识库",
        knowledge_type=KnowledgeType.OTHER,
        org_id=test_user.org_id,
        created_by=test_user.id,
        is_public=False,
        vector_collection=f"kb_{uuid4().hex[:8]}",
    )
    db_session.add(kb)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/knowledge/bases/{kb.id}/upload",
        headers=create_auth_headers(test_user),
        files={"file": ("memo.txt", b"hello", "application/x-msdownload")},
    )

    assert response.status_code == 400
    assert "不支持的 MIME 类型" in response.text


@pytest.mark.asyncio
async def test_knowledge_batch_upload_rejects_invalid_file(client, db_session, test_user):
    kb = KnowledgeBase(
        id=str(uuid4()),
        name="批量上传校验知识库",
        knowledge_type=KnowledgeType.OTHER,
        org_id=test_user.org_id,
        created_by=test_user.id,
        is_public=False,
        vector_collection=f"kb_{uuid4().hex[:8]}",
    )
    db_session.add(kb)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/knowledge/bases/{kb.id}/batch-upload",
        headers=create_auth_headers(test_user),
        files=[("files", ("payload.exe", b"MZ", "application/octet-stream"))],
    )

    assert response.status_code == 400
    assert "不支持的文件类型" in response.text


@pytest.mark.asyncio
async def test_contract_parse_rejects_disallowed_mime(client, test_user):
    response = await client.post(
        "/api/v1/contracts/parse",
        headers=create_auth_headers(test_user),
        files={"file": ("contract.txt", b"hello", "application/x-msdownload")},
    )

    assert response.status_code == 400
    assert "不支持的 MIME 类型" in response.text


@pytest.mark.asyncio
async def test_contract_upload_and_review_rejects_bad_extension(client, test_user):
    response = await client.post(
        "/api/v1/contracts/upload-and-review",
        headers=create_auth_headers(test_user),
        files={"file": ("payload.exe", b"MZ", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "不支持的文件类型" in response.text
