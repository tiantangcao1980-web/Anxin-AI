"""
agent_tasks 路由 —— P2 异步任务 MVP

挂载点（在 ``api/routes/__init__.py`` 用 ``prefix="/agent-tasks"`` 注册）::

    GET    /api/v1/agent-tasks                       列表（query: status, limit, offset）
    POST   /api/v1/agent-tasks                       创建
    GET    /api/v1/agent-tasks/{id}                  详情
    POST   /api/v1/agent-tasks/{id}/cancel           取消
    POST   /api/v1/agent-tasks/{id}/approve          审批通过
    POST   /api/v1/agent-tasks/{id}/reject           审批驳回
    GET    /api/v1/agent-tasks/{id}/events           SSE 事件流（断线重连用 Last-Event-ID）
    GET    /api/v1/agent-tasks/{id}/events/poll      轮询事件流（RN 友好，query: after_ts=stream_id）
    GET    /api/v1/agent-tasks/{id}/result           结果详情

权限：登录即可，跨用户读写返回 403（按 user_id 严格隔离）。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.schemas.agent_task import (
    AgentTaskApproveBody,
    AgentTaskCreate,
    AgentTaskEventOut,
    AgentTaskListOut,
    AgentTaskOut,
    AgentTaskRejectBody,
    AgentTaskResultOut,
)
from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.models.user import User
from src.services.task_orchestrator.events import consume_events, replay_events
from src.services.task_orchestrator.models import Task, TaskStatus
from src.services.task_orchestrator.service import TaskOrchestratorService
from src.services.task_orchestrator.state_machine import InvalidTransitionError

router = APIRouter()


# ---------------------------------------------------------------------------
# helper
# ---------------------------------------------------------------------------


def _ensure_owner(task: Task, user: User) -> None:
    """跨用户访问拦截。super_admin / admin 放行（运营 / 客服查看）。"""
    if user.role in {"super_admin", "admin"}:
        return
    if str(task.user_id) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该任务",
        )


def _get_service(db: AsyncSession) -> TaskOrchestratorService:
    return TaskOrchestratorService(db)


# ---------------------------------------------------------------------------
# 创建 / 列表 / 详情
# ---------------------------------------------------------------------------


@router.post("", response_model=AgentTaskOut, status_code=status.HTTP_201_CREATED)
async def create_agent_task(
    body: AgentTaskCreate,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> AgentTaskOut:
    """派发新任务（落库 + 入 Celery 队列）。"""
    service = _get_service(db)
    task = await service.create_task(
        user_id=str(user.id),
        agent_persona=body.agent_persona,
        payload=body.payload,
        priority=body.priority,
        parent_task_id=body.parent_task_id,
    )
    return AgentTaskOut.model_validate(task)


@router.get("", response_model=AgentTaskListOut)
async def list_agent_tasks(
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> AgentTaskListOut:
    """列出当前用户的任务（按 created_at 倒序）。"""
    service = _get_service(db)
    items = await service.list_tasks_for_user(
        str(user.id),
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return AgentTaskListOut(
        items=[AgentTaskOut.model_validate(t) for t in items],
        limit=limit,
        offset=offset,
    )


@router.get("/{task_id}", response_model=AgentTaskOut)
async def get_agent_task(
    task_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> AgentTaskOut:
    service = _get_service(db)
    task = await service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_owner(task, user)
    return AgentTaskOut.model_validate(task)


# ---------------------------------------------------------------------------
# 操作端点
# ---------------------------------------------------------------------------


@router.post("/{task_id}/cancel", response_model=AgentTaskOut)
async def cancel_agent_task(
    task_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> AgentTaskOut:
    service = _get_service(db)
    task = await service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_owner(task, user)
    try:
        task = await service.cancel(task_id)
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return AgentTaskOut.model_validate(task)


@router.post("/{task_id}/approve", response_model=AgentTaskOut)
async def approve_agent_task(
    task_id: str,
    body: AgentTaskApproveBody | None = None,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> AgentTaskOut:
    """审批通过。仅允许 NEEDS_APPROVAL 任务。"""
    service = _get_service(db)
    task = await service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_owner(task, user)
    try:
        task = await service.approve(task_id, approver_id=str(user.id))
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return AgentTaskOut.model_validate(task)


@router.post("/{task_id}/reject", response_model=AgentTaskOut)
async def reject_agent_task(
    task_id: str,
    body: AgentTaskRejectBody,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> AgentTaskOut:
    """审批驳回（NEEDS_APPROVAL → CANCELLED）。"""
    service = _get_service(db)
    task = await service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_owner(task, user)
    try:
        task = await service.reject(
            task_id,
            approver_id=str(user.id),
            reason=body.reason,
        )
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return AgentTaskOut.model_validate(task)


# ---------------------------------------------------------------------------
# SSE 事件流 + 结果详情
# ---------------------------------------------------------------------------


def _format_sse(event_id: str, event_name: str, data: str) -> str:
    """按 SSE 协议格式化一条事件帧。"""
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_name}")
    # 多行 data 需要每行前缀 "data: "
    for ln in data.splitlines() or [""]:
        lines.append(f"data: {ln}")
    lines.append("")  # 事件以空行结束
    lines.append("")
    return "\n".join(lines)


@router.get("/{task_id}/events")
async def stream_agent_task_events(
    request: Request,
    task_id: str,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """SSE 事件流。

    - 支持 ``Last-Event-ID`` 请求头：服务端用它做 Redis Streams 续传起点；
    - 收到任务终态事件（completed/failed/cancelled）后流自动结束；
    - 心跳：上游 ``consume_events`` 在阻塞超时时 yield 一个 ``_heartbeat=True`` 的 progress 事件。
    """
    service = _get_service(db)
    task = await service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_owner(task, user)

    start_cursor = last_event_id or "0-0"

    async def event_generator() -> AsyncIterator[bytes]:
        # 1. 先回放历史（如果指定了 last_event_id）
        if start_cursor != "$":
            for ev in await replay_events(task_id, last_event_id=start_cursor):
                if await request.is_disconnected():
                    return
                yield _format_sse(
                    ev.stream_id or "",
                    ev.event_type.value,
                    json.dumps(ev.to_dict(), ensure_ascii=False),
                ).encode("utf-8")

        # 2. 然后阻塞读新事件直到终态
        async for ev in consume_events(task_id, last_event_id="$"):
            if await request.is_disconnected():
                return
            yield _format_sse(
                ev.stream_id or "",
                ev.event_type.value,
                json.dumps(ev.to_dict(), ensure_ascii=False),
            ).encode("utf-8")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 关闭 Nginx 缓冲
            "Connection": "keep-alive",
        },
    )


@router.get("/{task_id}/events/poll", response_model=list[AgentTaskEventOut])
async def poll_agent_task_events(
    task_id: str,
    after_ts: str | None = Query(
        default=None,
        description="续传游标：上次返回数组里最后一条事件的 stream_id（缺省从头回放）",
    ),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> list[AgentTaskEventOut]:
    """轮询式事件拉取（RN 友好，替代 SSE）。

    RN 无原生 EventSource，移动端用轮询此端点替代 ``/events`` SSE：
    - 复用 ``replay_events`` 做非阻塞增量拉取，返回 JSON 数组（按时间顺序）；
    - ``after_ts`` 是上一批最后一条事件的 ``stream_id``（Redis Streams entry id），
      缺省时 ``"0-0"`` 表示从头回放；
    - 鉴权与 ``/events`` 一致（登录 + owner 校验）。

    不影响既有 SSE ``/events`` 端点（Web 端在用）。
    """
    service = _get_service(db)
    task = await service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_owner(task, user)

    cursor = after_ts or "0-0"
    events = await replay_events(task_id, last_event_id=cursor)
    return [AgentTaskEventOut.model_validate(ev.to_dict()) for ev in events]


@router.get("/{task_id}/result", response_model=AgentTaskResultOut)
async def get_agent_task_result(
    task_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> AgentTaskResultOut:
    """查询任务最终结果（DONE / FAILED / CANCELLED 才有意义）。"""
    service = _get_service(db)
    task = await service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_owner(task, user)
    return AgentTaskResultOut(
        task_id=task.id,
        status=task.status,
        result=task.result,
        error=task.error,
        finished_at=task.finished_at,
    )
