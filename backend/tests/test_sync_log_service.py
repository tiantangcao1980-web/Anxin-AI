from uuid import uuid4

import pytest
from sqlalchemy import select

from src.models.sync import SyncLog
from src.models.user import User
from src.services.sync_service import SyncService


def _record(entity_id: str, title: str, version: int = 1) -> dict:
    return {
        "entity_type": "document",
        "entity_id": entity_id,
        "action": "update",
        "data": {"title": title},
        "timestamp": "2026-05-06T10:00:00Z",
        "version": version,
    }


def _sync_record(
    entity_type: str,
    entity_id: str,
    data: dict,
    *,
    action: str = "upsert",
    version: int = 1,
    timestamp: str = "2026-05-06T10:00:00Z",
) -> dict:
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "data": data,
        "timestamp": timestamp,
        "version": version,
    }


@pytest.mark.asyncio
async def test_sync_push_persists_log_and_pull_returns_incremental(db_session, test_user):
    service = SyncService(db_session)

    result = await service.push(
        user_id=test_user.id,
        device_id="desktop-a",
        records=[_record("doc-1", "第一份"), _record("doc-2", "第二份")],
        last_sync_version=0,
    )

    assert result["accepted"] == 2
    assert result["rejected"] == 0
    assert result["server_version"] == 2

    stored = (
        (
            await db_session.execute(
                select(SyncLog)
                .where(SyncLog.user_id == test_user.id)
                .order_by(SyncLog.version.asc())
            )
        )
        .scalars()
        .all()
    )
    assert [(row.entity_id, row.version, row.device_id) for row in stored] == [
        ("doc-1", 1, "desktop-a"),
        ("doc-2", 2, "desktop-a"),
    ]

    pull_all = await service.pull(test_user.id, since_version=0)
    assert [record["entity_id"] for record in pull_all["records"]] == ["doc-1", "doc-2"]

    pull_incremental = await service.pull(test_user.id, since_version=1)
    assert [record["entity_id"] for record in pull_incremental["records"]] == ["doc-2"]


@pytest.mark.asyncio
async def test_cross_device_conversation_continuation_has_no_lost_or_duplicate_rows(
    db_session,
    test_user,
):
    service = SyncService(db_session)

    desktop_push = await service.push(
        user_id=test_user.id,
        device_id="desktop-a",
        last_sync_version=0,
        records=[
            _sync_record(
                "conversation",
                "conv-cross-1",
                {"id": "conv-cross-1", "title": "跨端会话", "mode": "hybrid"},
                action="create",
            ),
            _sync_record(
                "message",
                "msg-desktop-1",
                {
                    "id": "msg-desktop-1",
                    "conversation_id": "conv-cross-1",
                    "role": "user",
                    "content": "桌面端先发起",
                },
                action="create",
                version=2,
            ),
        ],
    )

    assert desktop_push["accepted"] == 2
    assert desktop_push["server_version"] == 2

    web_resume = await service.pull(
        test_user.id,
        since_version=0,
        entity_types=["conversation", "message"],
    )
    mobile_resume = await service.pull(
        test_user.id,
        since_version=0,
        entity_types=["conversation", "message"],
    )

    for resume_payload in (web_resume, mobile_resume):
        records = resume_payload["records"]
        assert [record["entity_id"] for record in records] == [
            "conv-cross-1",
            "msg-desktop-1",
        ]
        assert len({record["entity_id"] for record in records}) == len(records)
        assert {record["device_id"] for record in records} == {"desktop-a"}

    mobile_push = await service.push(
        user_id=test_user.id,
        device_id="uni-mobile-a",
        last_sync_version=desktop_push["server_version"],
        records=[
            _sync_record(
                "message",
                "msg-mobile-1",
                {
                    "id": "msg-mobile-1",
                    "conversation_id": "conv-cross-1",
                    "role": "user",
                    "content": "移动端继续回复",
                },
                action="create",
                version=1,
                timestamp="2026-05-06T10:01:00Z",
            )
        ],
    )

    assert mobile_push["accepted"] == 1
    assert mobile_push["server_version"] == 3

    desktop_resume = await service.pull(
        test_user.id,
        since_version=desktop_push["server_version"],
        entity_types=["message"],
    )
    assert [record["entity_id"] for record in desktop_resume["records"]] == ["msg-mobile-1"]
    assert desktop_resume["records"][0]["device_id"] == "uni-mobile-a"
    assert desktop_resume["records"][0]["data"]["conversation_id"] == "conv-cross-1"


@pytest.mark.asyncio
async def test_sync_pull_is_user_scoped(db_session, test_user, test_organization):
    other_user = User(
        id=str(uuid4()),
        email=f"sync-other-{uuid4().hex[:8]}@example.com",
        name="同步隔离用户",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.flush()

    service = SyncService(db_session)
    await service.push(test_user.id, "desktop-a", [_record("doc-a", "A 用户")], 0)
    await service.push(other_user.id, "desktop-b", [_record("doc-b", "B 用户")], 0)

    user_records = await service.pull(test_user.id, since_version=0)
    other_records = await service.pull(other_user.id, since_version=0)

    assert [record["entity_id"] for record in user_records["records"]] == ["doc-a"]
    assert [record["entity_id"] for record in other_records["records"]] == ["doc-b"]


@pytest.mark.asyncio
async def test_sync_push_reports_conflict_for_stale_entity_version(db_session, test_user):
    service = SyncService(db_session)
    await service.push(test_user.id, "desktop-a", [_record("doc-1", "云端版本")], 0)

    result = await service.push(
        user_id=test_user.id,
        device_id="desktop-b",
        records=[_record("doc-1", "过期本地版本", version=2)],
        last_sync_version=0,
    )

    assert result["accepted"] == 0
    assert result["rejected"] == 1
    assert result["conflicts"][0]["entity_id"] == "doc-1"
    assert result["conflicts"][0]["remote_data"] == {"title": "云端版本"}
    assert isinstance(result["conflicts"][0]["remote_timestamp"], str)


@pytest.mark.asyncio
async def test_sync_artifacts_are_session_scoped(db_session, test_user):
    service = SyncService(db_session)
    await service.push_artifacts(
        user_id=test_user.id,
        device_id="desktop-a",
        session_id="session-1",
        artifacts={
            "summary": {"text": "摘要"},
            "citations": [{"title": "法规"}],
        },
    )
    await service.push_artifacts(
        user_id=test_user.id,
        device_id="desktop-a",
        session_id="session-2",
        artifacts={"summary": {"text": "另一个摘要"}},
    )

    result = await service.pull_artifacts(test_user.id, "session-1")

    assert result["count"] == 2
    assert result["artifacts"]["summary"] == {"text": "摘要"}
    assert result["artifacts"]["citations"] == [{"title": "法规"}]
