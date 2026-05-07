"""Durable client sync service with per-user/device isolation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sync import SyncLog


@dataclass
class SyncConflictItem:
    entity_type: str
    entity_id: str
    local_data: dict[str, Any]
    remote_data: dict[str, Any]
    local_timestamp: str
    remote_timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "local_data": self.local_data,
            "remote_data": self.remote_data,
            "local_timestamp": self.local_timestamp,
            "remote_timestamp": self.remote_timestamp,
        }


class SyncService:
    """Append-only sync log used by desktop/mobile clients."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def push(
        self,
        user_id: str,
        device_id: str,
        records: list[dict[str, Any]],
        last_sync_version: int,
    ) -> dict[str, Any]:
        accepted = 0
        rejected = 0
        conflicts: list[dict[str, Any]] = []
        next_version = await self._current_version(user_id)

        for record in records:
            latest_remote = await self._latest_for_entity(
                user_id=user_id,
                entity_type=record["entity_type"],
                entity_id=record["entity_id"],
            )
            if latest_remote and latest_remote.version > last_sync_version:
                conflict = SyncConflictItem(
                    entity_type=record["entity_type"],
                    entity_id=record["entity_id"],
                    local_data=record.get("data") or {},
                    remote_data=latest_remote.payload or {},
                    local_timestamp=record.get("timestamp") or "",
                    remote_timestamp=_iso(latest_remote.client_timestamp or latest_remote.created_at) or "",
                )
                conflicts.append(conflict.to_dict())
                rejected += 1
                continue

            next_version += 1
            self.db.add(
                SyncLog(
                    user_id=user_id,
                    device_id=device_id,
                    entity_type=record["entity_type"],
                    entity_id=record["entity_id"],
                    action=record["action"],
                    payload=record.get("data") or {},
                    version=next_version,
                    client_version=int(record.get("version") or 0),
                    client_timestamp=_parse_timestamp(record.get("timestamp")),
                )
            )
            accepted += 1

        await self.db.flush()
        return {
            "accepted": accepted,
            "rejected": rejected,
            "conflicts": conflicts,
            "server_version": await self._current_version(user_id),
        }

    async def pull(
        self,
        user_id: str,
        since_version: int,
        entity_types: list[str] | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        query = (
            select(SyncLog)
            .where(SyncLog.user_id == user_id, SyncLog.version > since_version)
            .order_by(SyncLog.version.asc())
            .limit(limit + 1)
        )
        if entity_types:
            query = query.where(SyncLog.entity_type.in_(entity_types))

        result = await self.db.execute(query)
        logs = list(result.scalars().all())
        has_more = len(logs) > limit
        sliced = logs[:limit]
        return {
            "records": [_to_record(log) for log in sliced],
            "server_version": await self._current_version(user_id),
            "has_more": has_more,
        }

    async def status(self, user_id: str, device_id: str | None = None) -> dict[str, Any]:
        query = select(SyncLog).where(SyncLog.user_id == user_id)
        if device_id:
            query = query.where(SyncLog.device_id == device_id)
        query = query.order_by(SyncLog.created_at.desc()).limit(1)
        latest = (await self.db.execute(query)).scalar_one_or_none()

        records = (
            await self.db.execute(select(SyncLog).where(SyncLog.user_id == user_id))
        ).scalars().all()
        storage_used_bytes = sum(
            len(json.dumps(_to_record(record), ensure_ascii=False))
            for record in records
        )
        return {
            "server_version": await self._current_version(user_id),
            "last_sync_time": _iso(latest.created_at) if latest else None,
            "pending_conflicts": 0,
            "storage_used_bytes": storage_used_bytes,
            "storage_limit_bytes": 10 * 1024 * 1024 * 1024,
        }

    async def resolve(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        resolution: str,
        merged_data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if resolution == "merge" and merged_data is not None:
            self.db.add(
                SyncLog(
                    user_id=user_id,
                    device_id="server-merge",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    action="update",
                    payload=merged_data,
                    version=await self._next_version(user_id),
                    client_version=0,
                    client_timestamp=datetime.now(UTC),
                )
            )
            await self.db.flush()
            success = True
        else:
            success = resolution in {"keep_local", "keep_remote"}

        return {
            "success": success,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "resolution": resolution,
        }

    async def full_sync(self, user_id: str, device_id: str) -> dict[str, Any]:
        counts = {}
        for entity_type in ("message", "document", "case", "contract", "setting"):
            counts[f"{entity_type}s"] = await self._count_entity(user_id, entity_type)
        return {
            "success": True,
            "message": "全量同步已触发",
            "device_id": device_id,
            "entity_counts": counts,
        }

    async def push_artifacts(
        self,
        user_id: str,
        device_id: str,
        session_id: str,
        artifacts: dict[str, Any],
    ) -> dict[str, Any]:
        next_version = await self._current_version(user_id)
        for artifact_type, artifact_data in artifacts.items():
            next_version += 1
            self.db.add(
                SyncLog(
                    user_id=user_id,
                    device_id=device_id,
                    entity_type=f"harness_artifact_{artifact_type}",
                    entity_id=f"{session_id}:{artifact_type}",
                    action="upsert",
                    payload={
                        "session_id": session_id,
                        "artifact_type": artifact_type,
                        "data": artifact_data,
                    },
                    version=next_version,
                    client_version=0,
                    client_timestamp=datetime.now(UTC),
                )
            )
        await self.db.flush()
        return {
            "accepted": len(artifacts),
            "session_id": session_id,
            "server_version": await self._current_version(user_id),
        }

    async def pull_artifacts(
        self,
        user_id: str,
        session_id: str,
        artifact_types: list[str] | None = None,
    ) -> dict[str, Any]:
        result = await self.db.execute(
            select(SyncLog)
            .where(
                SyncLog.user_id == user_id,
                SyncLog.entity_type.like("harness_artifact_%"),
            )
            .order_by(SyncLog.version.asc())
        )
        artifacts: dict[str, Any] = {}
        for record in result.scalars().all():
            payload = record.payload or {}
            if payload.get("session_id") != session_id:
                continue
            artifact_type = payload.get("artifact_type") or record.entity_type.replace(
                "harness_artifact_",
                "",
            )
            if artifact_types and artifact_type not in artifact_types:
                continue
            artifacts[artifact_type] = payload.get("data")

        return {
            "session_id": session_id,
            "artifacts": artifacts,
            "count": len(artifacts),
        }

    async def _latest_for_entity(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
    ) -> SyncLog | None:
        return (
            await self.db.execute(
                select(SyncLog)
                .where(
                    SyncLog.user_id == user_id,
                    SyncLog.entity_type == entity_type,
                    SyncLog.entity_id == entity_id,
                )
                .order_by(SyncLog.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def _current_version(self, user_id: str) -> int:
        result = await self.db.execute(
            select(func.max(SyncLog.version)).where(SyncLog.user_id == user_id)
        )
        return int(result.scalar() or 0)

    async def _next_version(self, user_id: str) -> int:
        return await self._current_version(user_id) + 1

    async def _count_entity(self, user_id: str, entity_type: str) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(SyncLog)
            .where(SyncLog.user_id == user_id, SyncLog.entity_type == entity_type)
        )
        return int(result.scalar() or 0)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _to_record(log: SyncLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "action": log.action,
        "data": log.payload or {},
        "timestamp": _iso(log.client_timestamp or log.created_at),
        "version": log.client_version,
        "server_version": log.version,
        "device_id": log.device_id,
        "synced_at": _iso(log.created_at),
    }
