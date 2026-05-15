"""
任务管理路由
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.core.responses import UnifiedResponse
from src.core.schemas import CamelModel
from src.models.task import Task
from src.models.user import User
from src.services.task_service import TaskService

router = APIRouter()

ADMIN_TASK_ROLES = {"admin", "super_admin", "org_admin", "partner"}


class TaskCreate(CamelModel):
    title: str
    description: str | None = None
    status: str = "todo"
    priority: str = "medium"
    due_date: date | None = None
    assignee: str | None = None
    case_id: str | None = None
    tags: list[str] | None = None


class TaskUpdate(CamelModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: date | None = None
    assignee: str | None = None
    case_id: str | None = None
    tags: list[str] | None = None


class TaskResponse(CamelModel):
    id: str
    title: str
    description: str | None = None
    status: str
    priority: str
    due_date: str | None = None
    assignee: str | None = None
    case_id: str | None = None
    case_title: str | None = None
    tags: list[str] = []
    created_at: str | None = None


def task_to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=str(task.due_date) if task.due_date else None,
        assignee=getattr(getattr(task, "assignee", None), "name", None),
        case_id=task.case_id,
        case_title=getattr(getattr(task, "case", None), "title", None),
        tags=task.tags or [],
        created_at=task.created_at.isoformat() if task.created_at else None,
    )


def _is_task_admin(user: User) -> bool:
    return getattr(user, "role", None) in ADMIN_TASK_ROLES


@router.get("/")
async def list_tasks(
    status: str | None = Query(None),
    priority: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    service = TaskService(db)
    tasks, total = await service.list_tasks(
        org_id=user.org_id,
        status=status,
        priority=priority,
        current_user_id=user.id,
        is_admin=_is_task_admin(user),
        page=page,
        page_size=page_size,
    )
    return UnifiedResponse.success(
        data={
            "items": [task_to_response(t) for t in tasks],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("/")
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    service = TaskService(db)
    task = await service.create_task(
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        due_date=data.due_date,
        tags=data.tags or [],
        case_id=data.case_id,
        created_by=user.id,
        org_id=user.org_id,
    )
    return UnifiedResponse.success(data=task_to_response(task))


@router.put("/{task_id}")
async def update_task(
    task_id: str,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    service = TaskService(db)
    update_data: dict[str, Any] = {}
    if data.title is not None:
        update_data["title"] = data.title
    if data.description is not None:
        update_data["description"] = data.description
    if data.status is not None:
        update_data["status"] = data.status
    if data.priority is not None:
        update_data["priority"] = data.priority
    if data.due_date is not None:
        update_data["due_date"] = data.due_date
    if data.tags is not None:
        update_data["tags"] = data.tags
    if data.case_id is not None:
        update_data["case_id"] = data.case_id

    task = await service.update_task(
        task_id,
        org_id=user.org_id,
        current_user_id=user.id,
        is_admin=_is_task_admin(user),
        **update_data,
    )
    if not task:
        return UnifiedResponse.error(code=404, message="任务不存在")
    return UnifiedResponse.success(data=task_to_response(task))


@router.patch("/{task_id}/status")
async def update_task_status(
    task_id: str,
    status: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    service = TaskService(db)
    task = await service.update_task(
        task_id,
        org_id=user.org_id,
        current_user_id=user.id,
        is_admin=_is_task_admin(user),
        status=status,
    )
    if not task:
        return UnifiedResponse.error(code=404, message="任务不存在")
    return UnifiedResponse.success(data=task_to_response(task))


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    service = TaskService(db)
    success = await service.delete_task(
        task_id,
        org_id=user.org_id,
        current_user_id=user.id,
        is_admin=_is_task_admin(user),
    )
    if not success:
        return UnifiedResponse.error(code=404, message="任务不存在")
    return UnifiedResponse.success(message="删除成功")


# ===== 看板操作 =====


class StatusTransitionRequest(BaseModel):
    """状态转换"""

    status: str


class BatchUpdateRequest(BaseModel):
    """批量更新"""

    updates: list[dict[str, Any]]  # [{"task_id": "xxx", "status": "in_progress", "sort_order": 0}]


@router.put("/{task_id}/transition")
async def transition_task_status(
    task_id: str,
    req: StatusTransitionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """状态转换（带校验）"""
    service = TaskService(db)
    try:
        task = await service.transition_status(
            task_id,
            req.status,
            org_id=user.org_id,
            current_user_id=user.id,
            is_admin=_is_task_admin(user),
        )
        if not task:
            return UnifiedResponse.error(code=404, message="任务不存在")
        await db.commit()
        return UnifiedResponse.success(data=task_to_response(task))
    except ValueError as e:
        return UnifiedResponse.error(code=400, message=str(e))


@router.post("/batch-update")
async def batch_update_tasks(
    req: BatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """批量更新任务状态（看板拖拽）"""
    service = TaskService(db)
    result = await service.batch_update_status(
        req.updates,
        org_id=user.org_id,
        current_user_id=user.id,
        is_admin=_is_task_admin(user),
    )
    await db.commit()
    return UnifiedResponse.success(data=result)


@router.get("/kanban/stats")
async def get_kanban_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取看板统计"""
    service = TaskService(db)
    stats = await service.get_kanban_stats(org_id=user.org_id)
    return UnifiedResponse.success(data=stats)
