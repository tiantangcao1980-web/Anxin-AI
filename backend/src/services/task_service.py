# -*- coding: utf-8 -*-
"""
任务管理服务
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import date

from src.models.task import Task


class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_tasks(
        self,
        org_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[Task], int]:
        query = select(Task)
        if org_id:
            query = query.where(Task.org_id == org_id)
        if status:
            query = query.where(Task.status == status)
        if priority:
            query = query.where(Task.priority == priority)
        if assignee_id:
            query = query.where(Task.assignee_id == assignee_id)

        # 统计总数
        from sqlalchemy import func
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 分页
        query = query.order_by(Task.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_task(self, task_id: str) -> Optional[Task]:
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    async def create_task(self, **kwargs) -> Task:
        task = Task(**kwargs)
        self.db.add(task)
        await self.db.flush()
        return task

    async def update_task(self, task_id: str, org_id: Optional[str] = None, **kwargs) -> Optional[Task]:
        query = select(Task).where(Task.id == task_id)
        if org_id:
            query = query.where(Task.org_id == org_id)
        result = await self.db.execute(query)
        task = result.scalar_one_or_none()
        if not task:
            return None
        for k, v in kwargs.items():
            if hasattr(task, k) and v is not None:
                setattr(task, k, v)
        await self.db.flush()
        return task

    async def delete_task(self, task_id: str, org_id: Optional[str] = None) -> bool:
        query = select(Task).where(Task.id == task_id)
        if org_id:
            query = query.where(Task.org_id == org_id)
        result = await self.db.execute(query)
        task = result.scalar_one_or_none()
        if not task:
            return False
        await self.db.delete(task)
        await self.db.flush()
        return True
