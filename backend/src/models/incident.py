# -*- coding: utf-8 -*-
"""
Incident 模型 — CREAO 自愈闭环 Slice 1

汇聚所有失败信号到统一表，供 Slice 2 做 triage / GitHub Issue 化。

来源 (source):
- output_validator   后端输出校验失败
- agent_forum        Agent 内部辩论分歧 / 失败
- low_rating         用户低分反馈
- api_5xx            服务器 5xx
- frontend_error     前端 JS 错误（前端主动上报）
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    Integer,
    Index,
    func,
)
# 使用 SQL 通用 JSON：Postgres 落 JSONB，SQLite 落 JSON，方便测试
from sqlalchemy import JSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, GUID


class Incident(Base):
    """失败信号统一记录"""

    __tablename__ = "incidents"

    # --- 来源与等级 ---
    source: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True,
        comment="信号来源：output_validator|agent_forum|low_rating|api_5xx|frontend_error",
    )
    severity: Mapped[str] = mapped_column(
        String(8), nullable=False, default="P2", index=True,
        comment="严重等级：P0|P1|P2|P3",
    )

    # --- 去重指纹 ---
    fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="sha256(source + 关键字段)，用于聚合同类事件",
    )

    # --- 内容 ---
    title: Mapped[str] = mapped_column(
        String(256), nullable=False,
        comment="人读摘要",
    )
    payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
        comment="已经过 PII 脱敏的明细 payload",
    )
    payload_classification: Mapped[str] = mapped_column(
        String(16), nullable=False, default="CONFIDENTIAL",
        comment="数据分级：PUBLIC|INTERNAL|CONFIDENTIAL|SECRET|TOP_SECRET",
    )

    # --- 上下文 ---
    user_id: Mapped[Optional[str]] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True,
    )
    trace_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True,
    )
    agent_name: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True,
    )
    route: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True,
    )

    # --- 状态机 ---
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="open", index=True,
        comment="open|triaged|linked|resolved|dismissed",
    )
    occurrence_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
    )

    # --- 时间窗口 ---
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.utcnow(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.utcnow(),
        index=True,
    )

    # --- Slice 2 字段（先占位） ---
    triage_summary: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Slice 2: AI triage 总结",
    )
    github_issue_url: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True,
        comment="Slice 2: 关联的 GitHub Issue URL",
    )

    # --- 审计时间戳 ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.utcnow(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.utcnow(),
    )

    __table_args__ = (
        # 同 fingerprint 在 open 状态只能有一条（PG 上是部分唯一索引；
        # SQLite 不支持 partial unique index 的 server-side 强约束，
        # 但应用层 Collector 已通过 5 分钟内查询去重保证语义。）
        Index(
            "uq_incidents_fingerprint_open",
            "fingerprint",
            unique=True,
            postgresql_where="status = 'open'",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Incident id={self.id} source={self.source} "
            f"severity={self.severity} status={self.status} "
            f"fingerprint={self.fingerprint[:8]}...>"
        )
