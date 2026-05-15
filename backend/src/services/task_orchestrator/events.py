"""
任务事件定义与 Redis Streams 持久化

提供给 SSE / WebSocket 推送层使用的事件 DTO，并基于 Redis Streams
做事件持久化（key: ``agent_task_events:{task_id}``）。

为什么用 Redis Streams 而不是 Pub/Sub：
- Streams 可持久化，断线重连用 Last-Event-ID 续传；
- Pub/Sub 是 fire-and-forget，前端断网即丢事件；
- 与 SSE 的 ``Last-Event-ID`` 语义天然吻合。
"""

from __future__ import annotations

import asyncio
import enum
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger

# ---------------------------------------------------------------------------
# 事件类型 / DTO
# ---------------------------------------------------------------------------


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
    APPROVED = "task.approved"
    REJECTED = "task.rejected"
    COMPLETED = "task.completed"
    FAILED = "task.failed"
    CANCELLED = "task.cancelled"


@dataclass(slots=True)
class TaskEvent:
    """任务事件 DTO（不入库）。

    字段：
        task_id    : 任务 ID（UUID 字符串）
        event_type : 事件类型
        payload    : 事件载荷（进度百分比 / 中间消息 / result / error 等）
        timestamp  : 事件时间（默认当前 UTC）
        stream_id  : Redis Streams 自动生成的 ID（消费时带回，未持久化时为 None）
    """

    task_id: str
    event_type: TaskEventType
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    stream_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """序列化为可 JSON 编码的字典（用于 SSE/WebSocket 推送）。"""
        return {
            "task_id": self.task_id,
            "event_type": self.event_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "stream_id": self.stream_id,
        }

    @classmethod
    def from_redis_entry(
        cls, entry_id: str, fields: dict[bytes | str, bytes | str], task_id: str
    ) -> TaskEvent:
        """从 Redis Streams 条目还原 ``TaskEvent``。

        Redis Streams 条目格式: ``(b"<id>", {b"data": b"<json>"})``
        """

        def _decode(v: Any) -> str:
            if isinstance(v, (bytes, bytearray)):
                return v.decode("utf-8")
            return str(v)

        normalised: dict[str, str] = {_decode(k): _decode(v) for k, v in fields.items()}
        raw = normalised.get("data", "{}")
        data = json.loads(raw)
        ts_str = data.get("timestamp")
        try:
            ts = datetime.fromisoformat(ts_str) if ts_str else datetime.now(UTC)
        except ValueError:
            ts = datetime.now(UTC)
        try:
            etype = TaskEventType(data.get("event_type", TaskEventType.PROGRESS.value))
        except ValueError:
            etype = TaskEventType.PROGRESS
        return cls(
            task_id=data.get("task_id", task_id),
            event_type=etype,
            payload=data.get("payload", {}) or {},
            timestamp=ts,
            stream_id=_decode(entry_id),
        )


# ---------------------------------------------------------------------------
# Redis Streams 事件总线
# ---------------------------------------------------------------------------


def stream_key(task_id: str) -> str:
    """单任务事件流 Redis key。"""
    return f"agent_task_events:{task_id}"


# Stream 默认裁剪长度（保留最近 N 条事件即可，避免无限增长）
DEFAULT_MAXLEN = 1000


def _get_redis_url() -> str:
    """从全局 settings 读 REDIS_URL。"""
    from src.core.config import settings

    return getattr(settings, "REDIS_URL", "redis://localhost:6379/0")


_redis_client: Any = None
_redis_lock = asyncio.Lock()


async def get_redis():
    """单例 Redis async client（由 events 模块自管理）。"""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    async with _redis_lock:
        if _redis_client is not None:
            return _redis_client
        try:
            import redis.asyncio as aioredis  # type: ignore

            _redis_client = aioredis.from_url(_get_redis_url(), decode_responses=False)
        except Exception as e:  # pragma: no cover - 容错
            logger.warning(f"Redis client 初始化失败，事件持久化将降级为 noop: {e}")
            _redis_client = _NoopRedis()
        return _redis_client


class _NoopRedis:
    """Redis 不可用时的 no-op 占位（保证 service / worker 不报错）。"""

    async def xadd(self, *args: Any, **kwargs: Any) -> bytes:  # noqa: D401
        return b"0-0"

    async def xrange(self, *args: Any, **kwargs: Any) -> list:  # noqa: D401
        return []

    async def xread(self, *args: Any, **kwargs: Any) -> list:  # noqa: D401
        await asyncio.sleep(0.05)
        return []

    async def aclose(self) -> None:  # noqa: D401
        return None


async def publish_event(event: TaskEvent, *, maxlen: int = DEFAULT_MAXLEN) -> str:
    """把事件 ``XADD`` 到 ``agent_task_events:{task_id}``。

    参数：
        event:   要发布的事件
        maxlen:  Stream 近似裁剪长度（``XADD ... MAXLEN ~ N``）

    返回：
        Redis 自动分配的 entry id（如 ``"1714138390000-0"``）。
    """
    client = await get_redis()
    key = stream_key(event.task_id)
    payload = json.dumps(
        {
            "task_id": event.task_id,
            "event_type": event.event_type.value,
            "payload": event.payload,
            "timestamp": event.timestamp.isoformat(),
        },
        ensure_ascii=False,
    )
    try:
        entry_id = await client.xadd(
            key,
            {"data": payload},
            maxlen=maxlen,
            approximate=True,
        )
        if isinstance(entry_id, (bytes, bytearray)):
            entry_id = entry_id.decode("utf-8")
        event.stream_id = entry_id
        return entry_id
    except Exception as e:  # pragma: no cover - Redis 故障容错
        logger.warning(f"Redis XADD 失败，事件丢弃: task={event.task_id} err={e}")
        return ""


async def replay_events(task_id: str, *, last_event_id: str = "0-0") -> list[TaskEvent]:
    """从 ``last_event_id`` 之后回放所有历史事件（不阻塞）。

    用于 SSE 客户端断线重连时拉齐错过的事件。
    """
    client = await get_redis()
    key = stream_key(task_id)
    try:
        entries = await client.xrange(key, min="(" + last_event_id, max="+")
    except Exception as e:  # pragma: no cover
        logger.warning(f"Redis XRANGE 失败: task={task_id} err={e}")
        return []
    return [TaskEvent.from_redis_entry(entry_id, fields, task_id) for entry_id, fields in entries]


async def consume_events(
    task_id: str,
    *,
    last_event_id: str = "$",
    block_ms: int = 15000,
    stop_on_terminal: bool = True,
) -> AsyncIterator[TaskEvent]:
    """异步迭代器：阻塞读取某任务的事件流。

    - ``last_event_id="$"``：仅从订阅之后的新事件开始读；
    - ``last_event_id="0-0"``：从头开始读；
    - 终态事件（COMPLETED / FAILED / CANCELLED）触发后自动结束（除非 stop_on_terminal=False）；
    - block 期间 client 在 Redis 端阻塞，超时空响应继续下一轮。

    用法示例（SSE 端点）::

        async for ev in consume_events(task_id, last_event_id=last_id):
            yield f"id: {ev.stream_id}\\nevent: {ev.event_type.value}\\ndata: {json.dumps(ev.to_dict())}\\n\\n"
    """
    client = await get_redis()
    key = stream_key(task_id)
    cursor: str = last_event_id
    terminal = {
        TaskEventType.COMPLETED,
        TaskEventType.FAILED,
        TaskEventType.CANCELLED,
    }
    while True:
        try:
            resp = await client.xread({key: cursor}, count=50, block=block_ms)
        except Exception as e:  # pragma: no cover
            logger.warning(f"Redis XREAD 失败: task={task_id} err={e}")
            await asyncio.sleep(1.0)
            continue

        if not resp:
            # 阻塞超时 — 心跳一次让上层有机会 keepalive，不结束
            yield TaskEvent(
                task_id=task_id,
                event_type=TaskEventType.PROGRESS,
                payload={"_heartbeat": True},
            )
            continue

        for _stream, entries in resp:
            for entry_id, fields in entries:
                ev = TaskEvent.from_redis_entry(entry_id, fields, task_id)
                cursor = ev.stream_id or cursor
                yield ev
                if stop_on_terminal and ev.event_type in terminal:
                    return


async def close_redis() -> None:
    """关闭 Redis client（供测试 / shutdown 调用）。"""
    global _redis_client
    if _redis_client is None:
        return
    try:
        await _redis_client.aclose()
    except Exception:  # pragma: no cover
        pass
    _redis_client = None
