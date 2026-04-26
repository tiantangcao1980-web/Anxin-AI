# -*- coding: utf-8 -*-
"""
任务事件定义

提供给 SSE / WebSocket 推送层使用的事件 DTO。
P2 阶段会接 Redis Pub/Sub 作为传输总线。
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class TaskEventType(str, enum.Enum):
    """任务事件类型。

    与状态机一一对应；``PROGRESS`` 用于 RUNNING 中的细粒度进度上报。
    """

    QUEUED = "task.queued"
    PROVISIONING = "task.provisioning"
    STARTED = "task.started"
    PROGRESS = "task.progress"
    REPORTING = "task.reporting"
    NEEDS_APPROVAL = "task.needs_approval"
    COMPLETED = "task.completed"
    FAILED = "task.failed"


@dataclass(slots=True)
class TaskEvent:
    """任务事件 DTO（不入库）。

    字段：
        task_id    : 任务 ID（UUID 字符串）
        event_type : 事件类型
        payload    : 事件载荷（进度百分比 / 中间消息 / result / error 等）
        timestamp  : 事件时间（默认当前 UTC）
    """

    task_id: str
    event_type: TaskEventType
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        """序列化为可 JSON 编码的字典（用于 SSE/WebSocket 推送）。"""
        return {
            "task_id": self.task_id,
            "event_type": self.event_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
        }
