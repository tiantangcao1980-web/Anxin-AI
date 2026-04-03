"""Minimal secure sync service with per-user/device isolation."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class SyncConflictItem:
    entity_type: str
    entity_id: str
    local_data: dict
    remote_data: dict
    local_timestamp: str
    remote_timestamp: str

    def to_dict(self) -> dict:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "local_data": self.local_data,
            "remote_data": self.remote_data,
            "local_timestamp": self.local_timestamp,
            "remote_timestamp": self.remote_timestamp,
        }


class SyncService:
    """In-memory sync store used as a safe starter implementation."""

    def __init__(self) -> None:
        self._records_by_user: dict[str, list[dict]] = defaultdict(list)
        self._conflicts_by_user: dict[str, list[SyncConflictItem]] = defaultdict(list)
        self._server_version_by_user: dict[str, int] = defaultdict(int)
        self._last_sync_by_device: dict[tuple[str, str], str] = {}
        self._lock = asyncio.Lock()

    async def push(self, user_id: str, device_id: str, records: list[dict], last_sync_version: int) -> dict:
        accepted = 0
        rejected = 0
        conflicts: list[dict] = []

        async with self._lock:
            existing_records = self._records_by_user[user_id]

            for record in records:
                latest_remote = next(
                    (
                        item for item in reversed(existing_records)
                        if item["entity_type"] == record["entity_type"]
                        and item["entity_id"] == record["entity_id"]
                    ),
                    None,
                )

                if latest_remote and latest_remote["server_version"] > last_sync_version:
                    conflict = SyncConflictItem(
                        entity_type=record["entity_type"],
                        entity_id=record["entity_id"],
                        local_data=record["data"],
                        remote_data=latest_remote["data"],
                        local_timestamp=record["timestamp"],
                        remote_timestamp=latest_remote["timestamp"],
                    )
                    self._conflicts_by_user[user_id].append(conflict)
                    conflicts.append(conflict.to_dict())
                    rejected += 1
                    continue

                self._server_version_by_user[user_id] += 1
                stored = {
                    **record,
                    "server_version": self._server_version_by_user[user_id],
                    "device_id": device_id,
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                }
                existing_records.append(stored)
                accepted += 1

            self._last_sync_by_device[(user_id, device_id)] = datetime.now(timezone.utc).isoformat()

            return {
                "accepted": accepted,
                "rejected": rejected,
                "conflicts": conflicts,
                "server_version": self._server_version_by_user[user_id],
            }

    async def pull(
        self,
        user_id: str,
        since_version: int,
        entity_types: Optional[list[str]] = None,
        limit: int = 100,
    ) -> dict:
        async with self._lock:
            records = [
                item for item in self._records_by_user[user_id]
                if item["server_version"] > since_version
            ]
            if entity_types:
                records = [item for item in records if item["entity_type"] in entity_types]

            records = sorted(records, key=lambda item: item["server_version"])
            sliced = records[:limit]
            has_more = len(records) > limit

            return {
                "records": sliced,
                "server_version": self._server_version_by_user[user_id],
                "has_more": has_more,
            }

    async def status(self, user_id: str, device_id: Optional[str] = None) -> dict:
        async with self._lock:
            records = self._records_by_user[user_id]
            storage_used_bytes = sum(len(json.dumps(item, ensure_ascii=False)) for item in records)
            last_sync_time = self._last_sync_by_device.get((user_id, device_id), None) if device_id else None
            return {
                "server_version": self._server_version_by_user[user_id],
                "last_sync_time": last_sync_time,
                "pending_conflicts": len(self._conflicts_by_user[user_id]),
                "storage_used_bytes": storage_used_bytes,
                "storage_limit_bytes": 10 * 1024 * 1024 * 1024,
            }

    async def resolve(self, user_id: str, entity_type: str, entity_id: str, resolution: str, merged_data: Optional[dict]) -> dict:
        async with self._lock:
            remaining = []
            resolved = False
            for conflict in self._conflicts_by_user[user_id]:
                if conflict.entity_type == entity_type and conflict.entity_id == entity_id:
                    resolved = True
                    if resolution == "merge" and merged_data is not None:
                        self._server_version_by_user[user_id] += 1
                        self._records_by_user[user_id].append({
                            "entity_type": entity_type,
                            "entity_id": entity_id,
                            "action": "update",
                            "data": merged_data,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "version": self._server_version_by_user[user_id],
                            "server_version": self._server_version_by_user[user_id],
                            "device_id": "server-merge",
                            "synced_at": datetime.now(timezone.utc).isoformat(),
                        })
                    continue
                remaining.append(conflict)
            self._conflicts_by_user[user_id] = remaining

            return {
                "success": resolved,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "resolution": resolution,
            }

    async def full_sync(self, user_id: str, device_id: str) -> dict:
        async with self._lock:
            self._last_sync_by_device[(user_id, device_id)] = datetime.now(timezone.utc).isoformat()
            return {
                "success": True,
                "message": "全量同步已触发",
                "entity_counts": {
                    "messages": sum(1 for item in self._records_by_user[user_id] if item["entity_type"] == "message"),
                    "documents": sum(1 for item in self._records_by_user[user_id] if item["entity_type"] == "document"),
                    "cases": sum(1 for item in self._records_by_user[user_id] if item["entity_type"] == "case"),
                    "contracts": sum(1 for item in self._records_by_user[user_id] if item["entity_type"] == "contract"),
                    "settings": sum(1 for item in self._records_by_user[user_id] if item["entity_type"] == "setting"),
                },
            }


    # ========== Harness Artifact 同步 ==========

    async def push_artifacts(
        self,
        user_id: str,
        device_id: str,
        session_id: str,
        artifacts: dict[str, any],
    ) -> dict:
        """
        从客户端推送 Harness artifact（任务摘要、引用、风险标记等）到云端。

        桌面端完成一个任务后，将中间结论推送到云端，
        这样用户在 Web/移动端打开同一会话时可以看到结论。
        """
        async with self._lock:
            for art_type, art_data in artifacts.items():
                self._server_version_by_user[user_id] += 1
                record = {
                    "entity_type": f"harness_artifact_{art_type}",
                    "entity_id": f"{session_id}:{art_type}",
                    "action": "upsert",
                    "data": art_data,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "server_version": self._server_version_by_user[user_id],
                    "device_id": device_id,
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                }
                # 替换同 session 同类型的旧 artifact
                self._records_by_user[user_id] = [
                    r for r in self._records_by_user[user_id]
                    if not (r.get("entity_id") == record["entity_id"])
                ] + [record]

            self._last_sync_by_device[(user_id, device_id)] = datetime.now(timezone.utc).isoformat()

            return {
                "accepted": len(artifacts),
                "session_id": session_id,
                "server_version": self._server_version_by_user[user_id],
            }

    async def pull_artifacts(
        self,
        user_id: str,
        session_id: str,
        artifact_types: Optional[list[str]] = None,
    ) -> dict:
        """
        拉取指定会话的 Harness artifact。

        用户从桌面端切换到 Web 端时，拉取桌面端产生的中间结论。
        """
        async with self._lock:
            artifacts = {}
            for record in self._records_by_user[user_id]:
                if not record.get("entity_type", "").startswith("harness_artifact_"):
                    continue
                if record.get("session_id") != session_id:
                    continue
                art_type = record["entity_type"].replace("harness_artifact_", "")
                if artifact_types and art_type not in artifact_types:
                    continue
                artifacts[art_type] = record["data"]

            return {
                "session_id": session_id,
                "artifacts": artifacts,
                "count": len(artifacts),
            }


sync_service = SyncService()
