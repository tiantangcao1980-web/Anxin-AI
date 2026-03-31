# -*- coding: utf-8 -*-
"""
任务管理路由
"""

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required, require_permission, Permission
from src.core.responses import UnifiedResponse
from src.models.user import User
from src.services.task_service import TaskService

router = APIRouter()


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    dueDate: Optional[date] = None
    assignee: Optional[str] = None
    caseId: Optional[str] = None
    tags: Optional[List[str]] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    dueDate: Optional[date] = None
    assignee: Optional[str] = None
    caseId: Optional[str] = None
    tags: Optional[List[str]] = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    dueDate: Optional[str] = None
    assignee: Optional[str] = None
    caseId: Optional[str] = None
    caseTitle: Optional[str] = None
    tags: List[str] = []
    createdAt: Optional[str] = None


def task_to_response(task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        dueDate=str(task.due_date) if task.due_date else None,
        assignee=getattr(getattr(task, "assignee", None), "name", None),
        caseId=task.case_id,
        caseTitle=getattr(getattr(task, "case", None), "title", None),
        tags=task.tags or [],
        createdAt=task.created_at.isoformat() if task.created_at else None,
    )


@router.get("/")
async def list_tasks(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    service = TaskService(db)
    tasks, total = await service.list_tasks(
        org_id=user.org_id,
        status=status,
        priority=priority,
        page=page,
        page_size=page_size,
    )
    return UnifiedResponse.success(data={
        "items": [task_to_response(t) for t in tasks],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/")
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    service = TaskService(db)
    task = await service.create_task(
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        due_date=data.dueDate,
        tags=data.tags or [],
        case_id=data.caseId,
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
):
    service = TaskService(db)
    update_data = {}
    if data.title is not None:
        update_data["title"] = data.title
    if data.description is not None:
        update_data["description"] = data.description
    if data.status is not None:
        update_data["status"] = data.status
    if data.priority is not None:
        update_data["priority"] = data.priority
    if data.dueDate is not None:
        update_data["due_date"] = data.dueDate
    if data.tags is not None:
        update_data["tags"] = data.tags
    if data.caseId is not None:
        update_data["case_id"] = data.caseId

    task = await service.update_task(task_id, org_id=user.org_id, **update_data)
    if not task:
        return UnifiedResponse.error(code=404, message="任务不存在")
    return UnifiedResponse.success(data=task_to_response(task))


@router.patch("/{task_id}/status")
async def update_task_status(
    task_id: str,
    status: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    service = TaskService(db)
    task = await service.update_task(task_id, org_id=user.org_id, status=status)
    if not task:
        return UnifiedResponse.error(code=404, message="任务不存在")
    return UnifiedResponse.success(data=task_to_response(task))


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    service = TaskService(db)
    success = await service.delete_task(task_id, org_id=user.org_id)
    if not success:
        return UnifiedResponse.error(code=404, message="任务不存在")
    return UnifiedResponse.success(message="删除成功")


# ===== 看板操作 =====

class StatusTransitionRequest(BaseModel):
    """状态转换"""
    status: str


class BatchUpdateRequest(BaseModel):
    """批量更新"""
    updates: list  # [{"task_id": "xxx", "status": "in_progress", "sort_order": 0}]


@router.put("/{task_id}/transition")
async def transition_task_status(
    task_id: str,
    req: StatusTransitionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """状态转换（带校验）"""
    service = TaskService(db)
    try:
        task = await service.transition_status(task_id, req.status, org_id=user.org_id)
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
):
    """批量更新任务状态（看板拖拽）"""
    service = TaskService(db)
    result = await service.batch_update_status(req.updates, org_id=user.org_id)
    await db.commit()
    return UnifiedResponse.success(data=result)


@router.get("/kanban/stats")
async def get_kanban_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取看板统计"""
    service = TaskService(db)
    stats = await service.get_kanban_stats(org_id=user.org_id)
    return UnifiedResponse.success(data=stats)
