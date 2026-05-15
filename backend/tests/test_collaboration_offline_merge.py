import json
from uuid import uuid4

import pytest

from src.services.collaboration_service import (
    CollaborationService,
    DocumentOperation,
    _operation_to_dict,
)


@pytest.fixture
def collaboration_doc_id():
    return f"doc-{uuid4()}"


async def _apply(service, document_id, user_id, operation):
    result = await service.handle_operation(
        document_id=document_id,
        user_id=user_id,
        operation=operation,
    )
    assert result["success"] is True
    return result


def test_operation_broadcast_payload_is_json_serializable(collaboration_doc_id):
    payload = _operation_to_dict(
        DocumentOperation(
            id="op-1",
            document_id=collaboration_doc_id,
            user_id="user-a",
            operation_type="insert",
            position=0,
            content="hello",
        )
    )

    json.dumps(payload)
    assert isinstance(payload["timestamp"], str)


@pytest.mark.asyncio
async def test_offline_inserts_from_old_base_version_preserve_intent(
    db_session, collaboration_doc_id
):
    service = CollaborationService(db_session)
    service.manager.remove_session(collaboration_doc_id)
    service.manager.get_or_create_session(collaboration_doc_id, "甲乙")

    user_a_text = "甲方离线编辑" * 10
    user_b_text = "乙方离线编辑" * 10

    try:
        await _apply(
            service,
            collaboration_doc_id,
            "user-a",
            {"type": "insert", "position": 1, "content": user_a_text, "base_version": 0},
        )
        result = await _apply(
            service,
            collaboration_doc_id,
            "user-b",
            {"type": "insert", "position": 2, "content": user_b_text, "base_version": 0},
        )

        assert result["version"] == 2
        assert result["content"] == f"甲{user_a_text}乙{user_b_text}"
        assert result["content"].count(user_a_text) == 1
        assert result["content"].count(user_b_text) == 1
    finally:
        service.manager.remove_session(collaboration_doc_id)


@pytest.mark.asyncio
async def test_offline_insert_after_concurrent_delete_is_rebased(db_session, collaboration_doc_id):
    service = CollaborationService(db_session)
    service.manager.remove_session(collaboration_doc_id)
    service.manager.get_or_create_session(collaboration_doc_id, "abcdef")

    offline_text = "离线补充" * 20

    try:
        await _apply(
            service,
            collaboration_doc_id,
            "user-a",
            {"type": "delete", "position": 2, "length": 2, "base_version": 0},
        )
        result = await _apply(
            service,
            collaboration_doc_id,
            "user-b",
            {"type": "insert", "position": 4, "content": offline_text, "baseVersion": 0},
        )

        assert result["content"] == f"ab{offline_text}ef"
        assert result["content"].count(offline_text) == 1
    finally:
        service.manager.remove_session(collaboration_doc_id)


@pytest.mark.asyncio
async def test_live_operations_without_base_version_keep_current_position_semantics(
    db_session,
    collaboration_doc_id,
):
    service = CollaborationService(db_session)
    service.manager.remove_session(collaboration_doc_id)
    service.manager.get_or_create_session(collaboration_doc_id, "ab")

    try:
        await _apply(
            service,
            collaboration_doc_id,
            "user-a",
            {"type": "insert", "position": 1, "content": "X"},
        )
        result = await _apply(
            service,
            collaboration_doc_id,
            "user-b",
            {"type": "insert", "position": 2, "content": "Y"},
        )

        assert result["content"] == "aXYb"
    finally:
        service.manager.remove_session(collaboration_doc_id)
