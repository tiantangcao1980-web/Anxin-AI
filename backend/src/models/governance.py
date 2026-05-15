# -*- coding: utf-8 -*-
"""
Governance ORM —— 治理体系持久化表

三张表：
- ``confirm_tickets``     PEP-4：等待人工 confirm 的外发 / 写动作
- ``audit_events``        审计事件 DB 镜像（JSONL 仍是法证真相源）
- ``shadow_runs``         Skill REVIEW → PUBLISHED 前的 24h shadow 运行记录
"""
from __future__ import annotations

import enum as _enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import GUID, Base


class ConfirmTicketStatus(str, _enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"
    cancelled = "cancelled"


class ConfirmTicket(Base):
    """PEP-4 — 等待人工 confirm 的外发 / 写动作。

    创建场景：governance.authz.decide() 返回 REQUIRE_CONFIRM 时，业务侧调用
    `confirm_inbox.create_ticket(...)` 把动作落表；ticket 被批准前不会真正外发。
    """

    __tablename__ = "confirm_tickets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    """形如 ``tk_<hex32>``。"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC), nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    requester_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    requester_role: Mapped[str] = mapped_column(String(64), nullable=False)

    persona: Mapped[str | None] = mapped_column(String(64), index=True)
    skill_id: Mapped[str | None] = mapped_column(String(160), index=True)
    cookbook_name: Mapped[str | None] = mapped_column(String(120), index=True)

    action: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    """完整 scope，如 ``connector.feishu.send`` / ``data.contract.write``。"""

    # 资源 / 上下文（含决策时的 jurisdiction / classification / amount 等）
    resource: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    # PDP 决策回放快照
    decision_reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    policy_snapshot_id: Mapped[str | None] = mapped_column(String(48))

    # 要执行的"挂起动作"：connector + payload（不含解密后的 PII）
    pending_action: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    # 草稿存放路径（如外发邮件草稿、合同 docx 路径）
    draft_path: Mapped[str | None] = mapped_column(String(500))

    status: Mapped[str] = mapped_column(
        String(20), index=True, nullable=False, default=ConfirmTicketStatus.pending.value,
    )

    # 审批
    approver_id: Mapped[str | None] = mapped_column(String(64), index=True)
    approver_role: Mapped[str | None] = mapped_column(String(64))
    decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_note: Mapped[str | None] = mapped_column(Text)

    # 双签（高金额 / privileged 场景）
    cosigner_id: Mapped[str | None] = mapped_column(String(64))
    cosigner_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 关联审计 event_id（创建 ticket 与 approve / reject 各写一条）
    create_audit_event_id: Mapped[str | None] = mapped_column(String(64), index=True)
    decision_audit_event_id: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        Index("ix_confirm_tickets_tenant_status", "tenant_id", "status"),
        Index("ix_confirm_tickets_persona_status", "persona", "status"),
    )


class AuditEventDB(Base):
    """审计事件 DB 镜像（JSONL 仍是真相源；DB 是查询性能层）。"""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    actor_id: Mapped[str | None] = mapped_column(String(64), index=True)
    actor_role: Mapped[str | None] = mapped_column(String(64))
    tenant_id: Mapped[str | None] = mapped_column(String(36), index=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True)

    action: Mapped[str | None] = mapped_column(String(160), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(500))

    decision: Mapped[str | None] = mapped_column(String(32), index=True)
    outcome: Mapped[str | None] = mapped_column(String(32), index=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    policy_snapshot_id: Mapped[str | None] = mapped_column(String(48), index=True)
    fingerprint: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_audit_events_actor_ts", "actor_id", "ts"),
        Index("ix_audit_events_action_ts", "action", "ts"),
        Index("ix_audit_events_decision_outcome", "decision", "outcome"),
    )


class ShadowRunStatus(str, _enum.Enum):
    running = "running"
    passed = "passed"
    failed = "failed"
    cancelled = "cancelled"


class ShadowRun(Base):
    """REVIEW → PUBLISHED 前的 24h shadow 录制。

    输入：真实用户 skill 调用
    动作：并行跑 REVIEW 版 + 当前 PUBLISHED 版；对比输出与 tool 调用
    判定：错误率 ≤ 5% 且 0 安全违规 → PASSED
    """

    __tablename__ = "shadow_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    skill_id: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    review_version: Mapped[str] = mapped_column(String(40), nullable=False)
    baseline_version: Mapped[str | None] = mapped_column(String(40))

    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), index=True, nullable=False, default=ShadowRunStatus.running.value,
    )

    total_invocations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    review_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    baseline_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    divergences: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    security_violations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 阈值（取自 policy.skill-lifecycle.thresholds 拷贝快照）
    max_error_rate: Mapped[float] = mapped_column(default=0.05, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text)
    samples: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    """采样 N 条 input / review_output / baseline_output / divergence_type。"""

    __table_args__ = (
        Index("ix_shadow_runs_skill_status", "skill_id", "status"),
    )
