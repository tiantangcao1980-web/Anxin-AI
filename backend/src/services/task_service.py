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
        query = select(Task).options(
            selectinload(Task.assignee),
            selectinload(Task.case),
        )
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
        result = await self.db.execute(
            select(Task)
            .options(selectinload(Task.assignee), selectinload(Task.case))
            .where(Task.id == task_id)
        )
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

    # ===== 看板拖拽批量更新 =====

    VALID_STATUS_TRANSITIONS = {
        'pending': ['in_progress', 'cancelled'],
        'in_progress': ['completed', 'pending', 'blocked'],
        'blocked': ['in_progress', 'cancelled'],
        'completed': ['pending'],  # 允许重新打开
        'cancelled': ['pending'],
    }

    async def transition_status(
        self,
        task_id: str,
        new_status: str,
        org_id: Optional[str] = None,
    ) -> Optional[Task]:
        """状态转换（带校验）"""
        task = await self.get_task(task_id)
        if not task:
            return None

        current = task.status or 'pending'
        allowed = self.VALID_STATUS_TRANSITIONS.get(current, [])
        if new_status not in allowed:
            raise ValueError(
                f"无效状态转换: {current} → {new_status}，允许的目标状态: {allowed}"
            )

        task.status = new_status

        # 自动设置完成时间
        if new_status == 'completed' and hasattr(task, 'completed_at'):
            from datetime import datetime
            task.completed_at = datetime.utcnow()

        await self.db.flush()
        return task

    async def batch_update_status(
        self,
        updates: List[dict],
        org_id: Optional[str] = None,
    ) -> dict:
        """批量更新任务状态（看板拖拽）

        Args:
            updates: [{"task_id": "xxx", "status": "in_progress", "sort_order": 0}, ...]

        Returns:
            {"success": count, "failed": count, "errors": [...]}
        """
        success = 0
        failed = 0
        errors = []

        for item in updates:
            task_id = item.get("task_id")
            new_status = item.get("status")
            sort_order = item.get("sort_order")

            if not task_id or not new_status:
                failed += 1
                errors.append({"task_id": task_id, "error": "缺少必要参数"})
                continue

            try:
                task = await self.transition_status(task_id, new_status, org_id)
                if task and sort_order is not None and hasattr(task, 'sort_order'):
                    task.sort_order = sort_order
                success += 1
            except ValueError as e:
                failed += 1
                errors.append({"task_id": task_id, "error": str(e)})
            except Exception as e:
                failed += 1
                errors.append({"task_id": task_id, "error": f"更新失败: {e}"})

        await self.db.flush()
        return {"success": success, "failed": failed, "errors": errors}

    async def get_kanban_stats(self, org_id: Optional[str] = None) -> dict:
        """获取看板统计（各状态任务数量）"""
        from sqlalchemy import func

        query = select(
            Task.status,
            func.count(Task.id).label("count"),
        )
        if org_id:
            query = query.where(Task.org_id == org_id)
        query = query.group_by(Task.status)

        result = await self.db.execute(query)
        rows = result.all()

        stats = {row.status: row.count for row in rows}
        return {
            "pending": stats.get("pending", 0),
            "in_progress": stats.get("in_progress", 0),
            "blocked": stats.get("blocked", 0),
            "completed": stats.get("completed", 0),
            "cancelled": stats.get("cancelled", 0),
            "total": sum(stats.values()),
        }
