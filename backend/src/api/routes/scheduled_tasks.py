# -*- coding: utf-8 -*-
"""
scheduled_tasks 路由 —— D-1 定时任务管理后端

挂载点（在 ``api/routes/__init__.py`` 以 ``prefix="/scheduled-tasks"`` 注册）::

    GET    /api/v1/scheduled-tasks            -> ScheduledTask[]
    POST   /api/v1/scheduled-tasks            -> ScheduledTask（创建）
    PUT    /api/v1/scheduled-tasks/{id}/toggle  body {status} -> ScheduledTask
    DELETE /api/v1/scheduled-tasks/{id}       -> 204

权限：均需登录；数据按 user.org_id 隔离（多租户）。

MVP 范围：仅「管理 API」真实落库。cron 实际触发 / agent persona 真正运行 =
P-later（同 IM 协议握手），当前无调度器消费本表，详见
``services/scheduled_task_service.py`` 与 ``models/scheduled_task.py`` 注释。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.schemas.scheduled_task import (
    ScheduledTaskCreate,
    ScheduledTaskOut,
    ToggleStatusBody,
)
from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.models.user import User
from src.services.scheduled_task_service import (
    ScheduledTaskNotFoundError,
    ScheduledTaskService,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# GET / — 当前 org 的定时任务列表
# ---------------------------------------------------------------------------


@router.get("", response_model=list[ScheduledTaskOut])
async def list_scheduled_tasks(
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> list[ScheduledTaskOut]:
    """当前用户所属 org 的全部定时任务。"""
    service = ScheduledTaskService(db)
    tasks = await service.list_for_org(user.org_id)
    return [ScheduledTaskOut.model_validate(t) for t in tasks]


# ---------------------------------------------------------------------------
# POST / — 创建
# ---------------------------------------------------------------------------


@router.post("", response_model=ScheduledTaskOut, status_code=status.HTTP_201_CREATED)
async def create_scheduled_task(
    body: ScheduledTaskCreate,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> ScheduledTaskOut:
    """创建定时任务（next_run_at 由 cron 计算，见 service）。"""
    service = ScheduledTaskService(db)
    task = await service.create(
        org_id=user.org_id,
        created_by=str(user.id),
        name=body.name,
        kind=body.kind,
        cron=body.cron,
        agent_persona=body.agent_persona,
        cron_human=body.cron_human,
        status=body.status,
    )
    return ScheduledTaskOut.model_validate(task)


# ---------------------------------------------------------------------------
# PUT /{id}/toggle — 切换状态
# ---------------------------------------------------------------------------


@router.put("/{task_id}/toggle", response_model=ScheduledTaskOut)
async def toggle_scheduled_task(
    task_id: str,
    body: ToggleStatusBody,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> ScheduledTaskOut:
    """切换 active|paused|failed；切到 active 时重算 next_run_at。"""
    service = ScheduledTaskService(db)
    try:
        task = await service.toggle(task_id, user.org_id, body.status)
    except ScheduledTaskNotFoundError as e:
        raise HTTPException(status_code=404, detail="定时任务不存在") from e
    return ScheduledTaskOut.model_validate(task)


# ---------------------------------------------------------------------------
# DELETE /{id} — 删除
# ---------------------------------------------------------------------------


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheduled_task(
    task_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> None:
    """删除定时任务（仅限本 org）。"""
    service = ScheduledTaskService(db)
    try:
        await service.delete(task_id, user.org_id)
    except ScheduledTaskNotFoundError as e:
        raise HTTPException(status_code=404, detail="定时任务不存在") from e
