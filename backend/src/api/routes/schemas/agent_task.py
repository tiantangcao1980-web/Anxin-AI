"""agent_tasks 路由 Pydantic schemas（请求/响应 DTO）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.services.task_orchestrator.models import TaskStatus

# ---------------------------------------------------------------------------
# 请求体
# ---------------------------------------------------------------------------


class AgentTaskCreate(BaseModel):
    """创建任务请求体。"""

    agent_persona: str = Field(
        ...,
        max_length=64,
        description="agent 角色（free_legal / pro_legal / contract_review / ...）",
    )
    payload: dict[str, Any] | None = Field(
        default=None,
        description="任务参数 / 输入快照",
    )
    priority: int = Field(default=100, ge=0, le=1000, description="优先级（数字越小越先执行）")
    parent_task_id: str | None = Field(default=None, description="父任务 ID（链式调用）")


class AgentTaskRejectBody(BaseModel):
    """驳回请求体。"""

    reason: str = Field(..., max_length=500, description="驳回理由")


class AgentTaskApproveBody(BaseModel):
    """审批通过请求体（可选 reason，仅留痕）。"""

    reason: str | None = Field(default=None, max_length=500)


# ---------------------------------------------------------------------------
# 响应体
# ---------------------------------------------------------------------------


class AgentTaskOut(BaseModel):
    """任务详情响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    agent_persona: str
    status: TaskStatus
    priority: int
    payload: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    parent_task_id: str | None = None
    sandbox_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AgentTaskListOut(BaseModel):
    """任务列表响应。"""

    items: list[AgentTaskOut]
    limit: int
    offset: int


class AgentTaskResultOut(BaseModel):
    """任务结果详情响应。"""

    task_id: str
    status: TaskStatus
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    finished_at: datetime | None = None
