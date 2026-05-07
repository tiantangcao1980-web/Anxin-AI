"""
司法学院课程服务
"""


from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.course import Course, CourseProgress


class CourseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_courses(
        self,
        category: str | None = None,
        level: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Course], int]:
        query = select(Course)
        if category:
            query = query.where(Course.category == category)
        if level:
            query = query.where(Course.level == level)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(Course.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_course(self, course_id: str) -> Course | None:
        result = await self.db.execute(select(Course).where(Course.id == course_id))
        return result.scalar_one_or_none()

    async def create_course(self, **kwargs: Any) -> Course:
        course = Course(**kwargs)
        self.db.add(course)
        await self.db.flush()
        return course

    async def update_course(self, course_id: str, **kwargs: Any) -> Course | None:
        result = await self.db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
        if not course:
            return None
        for k, v in kwargs.items():
            if hasattr(course, k) and v is not None:
                setattr(course, k, v)
        await self.db.flush()
        return course

    async def delete_course(self, course_id: str) -> bool:
        result = await self.db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
        if not course:
            return False
        await self.db.delete(course)
        await self.db.flush()
        return True

    # 学习进度管理
    async def get_progress(self, user_id: str, course_id: str) -> CourseProgress | None:
        result = await self.db.execute(
            select(CourseProgress).where(
                CourseProgress.user_id == user_id,
                CourseProgress.course_id == course_id
            )
        )
        return result.scalar_one_or_none()

    async def update_progress(
        self,
        user_id: str,
        course_id: str,
        progress: int,
        completed_lessons: list[Any] | None = None,
    ) -> CourseProgress:
        existing = await self.get_progress(user_id, course_id)
        if existing:
            existing.progress = progress
            if completed_lessons is not None:
                existing.completed_lessons = completed_lessons
            await self.db.flush()
            return existing
        else:
            cp = CourseProgress(
                user_id=user_id,
                course_id=course_id,
                progress=progress,
                completed_lessons=completed_lessons or []
            )
            self.db.add(cp)
            await self.db.flush()
            return cp

    async def list_user_progress(self, user_id: str) -> list[CourseProgress]:
        result = await self.db.execute(
            select(CourseProgress).where(CourseProgress.user_id == user_id)
        )
        return list(result.scalars().all())
