# -*- coding: utf-8 -*-
"""
IncidentCollector — CREAO 自愈闭环 Slice 1

统一接入点：所有失败信号（output_validator / agent_forum / low_rating /
api_5xx / frontend_error）都通过 collect() 落库。

职责：
1. PII 脱敏：所有 payload 字符串过 PIIService.scrub()，丢弃 recovery_map
2. 指纹生成：sha256(source + 选定字段) — 同类事件聚合
3. 5 分钟滑动窗口去重：同 fingerprint+open 状态 → occurrence_count++
4. 落库返回 Incident 实例
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.incident import Incident
from src.schemas.incident import IncidentSeverity, IncidentSource
from src.services.pii_service import PIIService


# 同 fingerprint 在 N 分钟内只 ++count，不新建
DEDUPE_WINDOW = timedelta(minutes=5)


class IncidentCollector:
    """失败信号收集器。"""

    def __init__(self, db: AsyncSession, pii: PIIService) -> None:
        self.db = db
        self.pii = pii

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _scrub_value(self, value: Any) -> Any:
        """递归清洗 payload 中的字符串字段。"""
        if isinstance(value, str):
            scrubbed, _recovery = self.pii.scrub(value)  # 丢弃 recovery_map
            return scrubbed
        if isinstance(value, dict):
            return {k: self._scrub_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._scrub_value(v) for v in value]
        if isinstance(value, tuple):
            return tuple(self._scrub_value(v) for v in value)
        return value

    @staticmethod
    def _make_fingerprint(
        source: IncidentSource,
        title: str,
        payload: dict[str, Any],
        fingerprint_keys: Optional[list[str]],
    ) -> str:
        """
        指纹算法：sha256(source + "|" + 序列化(选定 payload 子集 或 title 前 200))
        截断到 64 字符（hex 长度）。
        """
        if fingerprint_keys:
            subset = {k: payload.get(k) for k in fingerprint_keys}
            material = json.dumps(subset, sort_keys=True, ensure_ascii=False, default=str)
        else:
            material = title[:200]
        raw = f"{source.value}|{material}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:64]

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def collect(
        self,
        *,
        source: IncidentSource,
        title: str,
        payload: dict[str, Any],
        severity: IncidentSeverity = IncidentSeverity.P2,
        payload_classification: str = "CONFIDENTIAL",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        route: Optional[str] = None,
        fingerprint_keys: Optional[list[str]] = None,
    ) -> Incident:
        """
        汇报一个失败信号。同 fingerprint 在 5 分钟内重复 → 仅 ++ count。

        Returns:
            Incident 实例（新建或被复用的旧记录，已 commit）
        """
        # 1) PII 脱敏
        scrubbed_payload: dict[str, Any] = self._scrub_value(payload) or {}
        # 同时把 title 也脱敏一下，避免在 title 里泄露
        scrubbed_title, _ = self.pii.scrub(title)

        # 2) 指纹（基于脱敏后的内容做指纹，避免不同手机号被视为不同事件）
        fingerprint = self._make_fingerprint(
            source, scrubbed_title, scrubbed_payload, fingerprint_keys
        )

        # 3) 5 分钟内去重：找同 fingerprint + open 的 last_seen_at >= now-5min
        now = datetime.now(timezone.utc)
        window_start = now - DEDUPE_WINDOW

        stmt = (
            select(Incident)
            .where(
                Incident.fingerprint == fingerprint,
                Incident.status == "open",
                Incident.last_seen_at >= window_start,
            )
            .order_by(Incident.last_seen_at.desc())
            .limit(1)
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()

        if existing is not None:
            existing.occurrence_count = (existing.occurrence_count or 0) + 1
            existing.last_seen_at = now
            # 严重级别取最高（P0 < P1 < P2 < P3 字典序，但 P0 才是最严重）
            if self._severity_rank(severity) < self._severity_rank(
                IncidentSeverity(existing.severity)
            ):
                existing.severity = severity.value
            await self.db.flush()
            await self.db.commit()
            return existing

        # 4) 新建记录
        incident = Incident(
            id=str(uuid.uuid4()),
            source=source.value,
            severity=severity.value,
            fingerprint=fingerprint,
            title=scrubbed_title[:256],
            payload=scrubbed_payload,
            payload_classification=payload_classification,
            user_id=user_id,
            session_id=session_id,
            trace_id=trace_id,
            agent_name=agent_name,
            route=route,
            status="open",
            occurrence_count=1,
            first_seen_at=now,
            last_seen_at=now,
        )
        self.db.add(incident)
        await self.db.flush()
        await self.db.commit()
        return incident

    @staticmethod
    def _severity_rank(sev: IncidentSeverity) -> int:
        """P0=0(最严重) ... P3=3(最轻)。数字越小越严重。"""
        return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(sev.value, 99)
