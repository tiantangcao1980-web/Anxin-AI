# -*- coding: utf-8 -*-
"""
SkillExecutor 数据模型 —— 进程内运行时对象，**不入库**。

如未来需要做执行审计落库，新建一张 ``skill_execution_logs`` 表 + ORM 即可，
保持本模块 dataclass 轻量。
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class SkillExecutionStatus(str, enum.Enum):
    """技能执行状态（与 ``task_orchestrator`` 风格保持一致）。"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class ExecutionContext:
    """技能执行上下文（注入到 prompt）。

    字段：
        user_id              : 调用者用户 ID
        persona              : user-facing persona（lawyer / hr / executive ...）
        app_authorizations   : 该用户已授权的 OAuth 应用 ID 列表（dingtalk/feishu/...）
        org_id               : 所属租户/组织 ID
        locale               : 语言（默认中文 ``zh-CN``）
        extra                : 业务自定义键值，会原样拼入 prompt
        request_id           : 用于跨服务追踪的 trace id（可选）
    """

    user_id: str
    persona: str = "default"
    app_authorizations: list[str] = field(default_factory=list)
    org_id: str | None = None
    locale: str = "zh-CN"
    extra: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None

    def to_prompt_block(self) -> str:
        """渲染成 markdown 片段，注入到 system prompt。"""
        lines = [
            "## 执行上下文",
            f"- user_id: {self.user_id}",
            f"- persona: {self.persona}",
            f"- locale: {self.locale}",
        ]
        if self.org_id:
            lines.append(f"- org_id: {self.org_id}")
        if self.app_authorizations:
            lines.append(
                "- app_authorizations: " + ", ".join(self.app_authorizations)
            )
        if self.extra:
            lines.append("- extra:")
            for k, v in self.extra.items():
                lines.append(f"    - {k}: {v}")
        return "\n".join(lines)


@dataclass(slots=True)
class SkillResult:
    """技能执行结果。"""

    skill_name: str
    status: SkillExecutionStatus
    output: str = ""
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0

    @property
    def ok(self) -> bool:
        return self.status == SkillExecutionStatus.SUCCESS

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "metadata": dict(self.metadata),
            "duration_ms": self.duration_ms,
        }


@dataclass(slots=True)
class SkillExecutionLog:
    """单次执行的审计日志（可由调用方持久化）。"""

    id: str = field(default_factory=lambda: uuid4().hex)
    skill_name: str = ""
    user_id: str = ""
    persona: str = "default"
    payload: dict[str, Any] = field(default_factory=dict)
    status: SkillExecutionStatus = SkillExecutionStatus.PENDING
    output: str = ""
    error: str | None = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None

    def mark_success(self, output: str) -> None:
        self.status = SkillExecutionStatus.SUCCESS
        self.output = output
        self.finished_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        self.status = SkillExecutionStatus.FAILED
        self.error = error
        self.finished_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "skill_name": self.skill_name,
            "user_id": self.user_id,
            "persona": self.persona,
            "payload": dict(self.payload),
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }
