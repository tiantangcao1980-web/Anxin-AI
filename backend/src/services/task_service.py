"""
任务管理服务
"""

from datetime import UTC
from typing import Any

from sqlalchemy import Select, false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.task import Task


class TaskService:
    STATUS_ALIASES = {
        "pending": "todo",
        "completed": "done",
    }

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _can_access_task(self, task: Task, current_user_id: str | None, is_admin: bool) -> bool:
        if is_admin:
            return True
        if not current_user_id:
            return False
        return task.created_by == current_user_id or task.assignee_id == current_user_id

    def _apply_owner_scope(
        self,
        query: Select[tuple[Task]],
        current_user_id: str | None,
        is_admin: bool,
    ) -> Select[tuple[Task]]:
        if is_admin:
            return query
        if not current_user_id:
            return query.where(false())
        return query.where(
            or_(
                Task.created_by == current_user_id,
                Task.assignee_id == current_user_id,
            )
        )

    async def list_tasks(
        self,
        org_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        assignee_id: str | None = None,
        current_user_id: str | None = None,
        is_admin: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Task], int]:
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
        query = self._apply_owner_scope(query, current_user_id, is_admin)

        # 统计总数
        from sqlalchemy import func
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 分页
        query = query.order_by(Task.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_task(
        self,
        task_id: str,
        org_id: str | None = None,
        current_user_id: str | None = None,
        is_admin: bool = False,
    ) -> Task | None:
        query = (
            select(Task)
            .options(selectinload(Task.assignee), selectinload(Task.case))
            .where(Task.id == task_id)
        )
        if org_id:
            query = query.where(Task.org_id == org_id)

        result = await self.db.execute(query)
        task = result.scalar_one_or_none()
        if not task or not self._can_access_task(task, current_user_id, is_admin):
            return None
        return task

    async def create_task(self, **kwargs: Any) -> Task:
        task = Task(**kwargs)
        self.db.add(task)
        await self.db.flush()
        return task

    async def update_task(
        self,
        task_id: str,
        org_id: str | None = None,
        current_user_id: str | None = None,
        is_admin: bool = False,
        **kwargs: Any,
    ) -> Task | None:
        query = select(Task).where(Task.id == task_id)
        if org_id:
            query = query.where(Task.org_id == org_id)
        result = await self.db.execute(query)
        task = result.scalar_one_or_none()
        if not task or not self._can_access_task(task, current_user_id, is_admin):
            return None
        for k, v in kwargs.items():
            if hasattr(task, k) and v is not None:
                setattr(task, k, v)
        await self.db.flush()
        return task

    async def delete_task(
        self,
        task_id: str,
        org_id: str | None = None,
        current_user_id: str | None = None,
        is_admin: bool = False,
    ) -> bool:
        query = select(Task).where(Task.id == task_id)
        if org_id:
            query = query.where(Task.org_id == org_id)
        result = await self.db.execute(query)
        task = result.scalar_one_or_none()
        if not task or not self._can_access_task(task, current_user_id, is_admin):
            return False
        await self.db.delete(task)
        await self.db.flush()
        return True

    # ===== 看板拖拽批量更新 =====

    VALID_STATUS_TRANSITIONS = {
        'todo': ['in_progress'],
        'in_progress': ['done', 'todo'],
        'done': ['todo'],
    }

    def _normalize_status(self, status: str | None) -> str:
        raw = status or "todo"
        return self.STATUS_ALIASES.get(raw, raw)

    async def transition_status(
        self,
        task_id: str,
        new_status: str,
        org_id: str | None = None,
        current_user_id: str | None = None,
        is_admin: bool = False,
    ) -> Task | None:
        """状态转换（带校验）"""
        task = await self.get_task(
            task_id,
            org_id=org_id,
            current_user_id=current_user_id,
            is_admin=is_admin,
        )
        if not task:
            return None

        current = self._normalize_status(task.status)
        target = self._normalize_status(new_status)
        allowed = self.VALID_STATUS_TRANSITIONS.get(current, [])
        if target not in allowed:
            raise ValueError(
                f"无效状态转换: {current} → {target}，允许的目标状态: {allowed}"
            )

        task.status = target

        # 自动设置完成时间
        if target == 'done' and hasattr(task, 'completed_at'):
            from datetime import datetime

            task.completed_at = datetime.now(UTC)

        await self.db.flush()
        return task

    async def batch_update_status(
        self,
        updates: list[dict[str, Any]],
        org_id: str | None = None,
        current_user_id: str | None = None,
        is_admin: bool = False,
    ) -> dict[str, Any]:
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
                task = await self.transition_status(
                    task_id,
                    new_status,
                    org_id,
                    current_user_id=current_user_id,
                    is_admin=is_admin,
                )
                if not task:
                    failed += 1
                    errors.append({"task_id": task_id, "error": "任务不存在"})
                    continue

                if sort_order is not None and hasattr(task, 'sort_order'):
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

    async def get_kanban_stats(self, org_id: str | None = None) -> dict[str, int]:
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

        stats: dict[str, int] = {}
        for status, count in rows:
            normalized = self._normalize_status(status)
            stats[normalized] = stats.get(normalized, 0) + int(count)

        return {
            "todo": stats.get("todo", 0),
            "in_progress": stats.get("in_progress", 0),
            "done": stats.get("done", 0),
            "total": sum(stats.values()),
        }
