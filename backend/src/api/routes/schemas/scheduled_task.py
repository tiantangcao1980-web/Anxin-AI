# -*- coding: utf-8 -*-
"""scheduled_tasks 路由 Pydantic schemas（请求 / 响应 DTO）。

契约对齐 mobile/src/lib/api/__mocks__/capabilities.mock.ts 的 ScheduledTask：
    { id, name, kind, cron, cron_human, status, last_run_at, next_run_at,
      last_run_ok, agent_persona }
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# 与前端 ScheduleStatus 对齐
ScheduleStatus = Literal["active", "paused", "failed"]


class ScheduledTaskOut(BaseModel):
    """单条定时任务 DTO（字段名 1:1 对齐前端契约）。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    kind: str
    cron: str
    cron_human: str
    status: str
    last_run_at: datetime | None = None
    next_run_at: datetime
    last_run_ok: bool | None = None
    agent_persona: str


class ScheduledTaskCreate(BaseModel):
    """POST 创建请求体。"""

    name: str = Field(..., min_length=1, max_length=255)
    kind: str = Field(..., min_length=1, max_length=64)
    cron: str = Field(..., min_length=1, max_length=128)
    agent_persona: str | None = Field(default=None, max_length=64)
    cron_human: str | None = Field(default=None, max_length=128)
    status: ScheduleStatus = "active"


class ToggleStatusBody(BaseModel):
    """PUT /{id}/toggle 请求体。"""

    status: ScheduleStatus
