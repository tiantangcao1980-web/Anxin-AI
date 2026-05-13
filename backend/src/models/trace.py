# -*- coding: utf-8 -*-
"""
Trace 持久化模型（T1 设计 / 待 H1 接入主路径）

- traces:        一次完整请求
- trace_spans:   子操作（agent / tool / LLM 调用）
- trace_clusters:失败聚类（T2 + O2 消费）

设计文档：docs/audit/harness/01-trace-persistence-design.md
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import JSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, GUID, ValueEnum


class ClientType(str, Enum):
    WEB = "web"
    DESKTOP = "desktop"
    MOBILE = "mobile"
    MINIAPP = "miniapp"
    SERVER = "server"


class TraceStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class RuntimeMode(str, Enum):
    LOCAL = "local"
    HYBRID = "hybrid"
    CLOUD = "cloud"


class SpanStatus(str, Enum):
    STARTED = "started"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class ClusterSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ClusterStatus(str, Enum):
    OPEN = "open"
    TRIAGING = "triaging"
    FIXED = "fixed"
    SUPPRESSED = "suppressed"


class Trace(Base):
    __tablename__ = "traces"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True)
    client_trace_id: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    client_type: Mapped[ClientType] = mapped_column(
        ValueEnum(ClientType), default=ClientType.SERVER, index=True
    )
    user_id: Mapped[Optional[str]] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    org_id: Mapped[Optional[str]] = mapped_column(GUID(), index=True)
    conversation_id: Mapped[Optional[str]] = mapped_column(GUID(), index=True)

    route: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    agent_used: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    mode: Mapped[Optional[RuntimeMode]] = mapped_column(ValueEnum(RuntimeMode), index=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    elapsed_ms: Mapped[Optional[float]] = mapped_column(Float)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))
    span_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0, index=True)

    cluster_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    status: Mapped[TraceStatus] = mapped_column(
        ValueEnum(TraceStatus), default=TraceStatus.SUCCESS, index=True
    )

    summary: Mapped[Optional[dict]] = mapped_column(JSONB)

    spans: Mapped[list["TraceSpan"]] = relationship(
        "TraceSpan", back_populates="trace", cascade="all, delete-orphan"
    )


class TraceSpan(Base):
    __tablename__ = "trace_spans"

    id: Mapped[str] = mapped_column(GUID(), primary_key=True)
    trace_id: Mapped[str] = mapped_column(GUID(), ForeignKey("traces.id"), index=True)
    parent_span_id: Mapped[Optional[str]] = mapped_column(GUID())

    operation: Mapped[str] = mapped_column(String(128), index=True)
    agent_name: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    tool_name: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    latency_ms: Mapped[Optional[float]] = mapped_column(Float)

    status: Mapped[SpanStatus] = mapped_column(
        ValueEnum(SpanStatus), default=SpanStatus.STARTED, index=True
    )
    error_type: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    error_msg: Mapped[Optional[str]] = mapped_column(Text)  # 已脱敏

    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    extra: Mapped[Optional[dict]] = mapped_column(JSONB)  # metadata 关键字保留，改名 extra

    trace: Mapped[Trace] = relationship("Trace", back_populates="spans")


class TraceCluster(Base):
    __tablename__ = "trace_clusters"

    cluster_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    signature: Mapped[dict] = mapped_column(JSONB)

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    occurrence_count: Mapped[int] = mapped_column(Integer, default=0)
    affected_users: Mapped[int] = mapped_column(Integer, default=0)

    severity: Mapped[ClusterSeverity] = mapped_column(
        ValueEnum(ClusterSeverity), default=ClusterSeverity.LOW, index=True
    )
    assigned_to: Mapped[Optional[str]] = mapped_column(String(64))
    status: Mapped[ClusterStatus] = mapped_column(
        ValueEnum(ClusterStatus), default=ClusterStatus.OPEN, index=True
    )
    linked_pr_url: Mapped[Optional[str]] = mapped_column(Text)
