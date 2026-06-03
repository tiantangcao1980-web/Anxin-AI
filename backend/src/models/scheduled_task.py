# -*- coding: utf-8 -*-
"""
ScheduledTask 模型 —— D-1 定时任务管理后端

契约以 mobile/src/lib/api/__mocks__/capabilities.mock.ts 的 ScheduledTask 为准：
    { id, name, kind, cron, cron_human, status, last_run_at, next_run_at,
      last_run_ok, agent_persona }

MVP 范围说明：
    本表只负责定时任务的「管理 API」（CRUD + toggle）真实落库。
    **实际执行**（cron 真正触发、agent persona 真正跑起来）同 IM 协议握手一样
    标为后续 P-later —— 当前不存在调度器消费本表、也不写 last_run_*。
    last_run_at / last_run_ok 仅作为执行回填占位列，由未来的 scheduler 写入。
    next_run_at 在 创建 / toggle(active) 时由服务层从 cron 计算（无 croniter
    依赖时退化为简易内置解析，见 services/scheduled_task_service.py 注释）。
"""

from datetime import datetime

# 全库约定：JSON 列用通用 JSON（Postgres 落 JSONB，SQLite 落 JSON），禁 PG 专属 JSONB
from sqlalchemy import JSON as JSONB
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import GUID, Base


class ScheduledTask(Base):
    """定时任务（管理元数据）。

    status：active | paused | failed
    kind：ScheduleKind，如 contract_expiry_alert / case_status_daily /
          sentiment_weekly / compliance_monthly（字符串存储，不做 DB 枚举约束，
          便于前端扩展 kind 而无需迁移）。
    """

    __tablename__ = "scheduled_tasks"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    kind: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="ScheduleKind：contract_expiry_alert|case_status_daily|"
        "sentiment_weekly|compliance_monthly|...",
    )

    cron: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="标准 5 段 cron 表达式，如 '0 9 * * *'",
    )
    cron_human: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="",
        comment="人类可读串（后端按 cron 生成，前端也有映射兜底）",
    )

    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="active",
        index=True,
        comment="active|paused|failed",
    )

    agent_persona: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="",
        comment="触发时使用的 agent persona，如 legal / research / tax_finance",
    )

    # --- 执行回填（P-later：由未来 scheduler 写入，当前恒为占位值） ---
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="上次实际执行时间；调度器未实现前恒为 NULL",
    )
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="下次预计执行时间；创建 / toggle(active) 时由 cron 计算",
    )
    last_run_ok: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="上次执行是否成功；调度器未实现前恒为 NULL",
    )

    # 自由扩展（暂存 persona 入参、提醒阈值等），保持向后兼容
    config: Mapped[dict[str, "object"]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # --- 多租户隔离 ---
    org_id: Mapped[str | None] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_by: Mapped[str | None] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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
        Index("ix_scheduled_tasks_org_status", "org_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<ScheduledTask id={self.id} name={self.name!r} "
            f"kind={self.kind} status={self.status}>"
        )
