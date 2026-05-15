"""
司法学院课程路由
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.core.responses import UnifiedResponse
from src.core.schemas import CamelModel
from src.models.course import Course
from src.models.user import User
from src.services.course_service import CourseService

router = APIRouter()


class CourseCreate(CamelModel):
    title: str
    instructor: str | None = None
    category: str = "regulation"
    duration: str | None = None
    lessons: int = 0
    description: str | None = None
    level: str = "入门"
    tags: list[str] | None = None


class CourseUpdate(CamelModel):
    title: str | None = None
    instructor: str | None = None
    category: str | None = None
    duration: str | None = None
    lessons: int | None = None
    description: str | None = None
    level: str | None = None
    tags: list[str] | None = None


class ProgressUpdate(CamelModel):
    progress: int
    completed_lessons: list[int] | None = None


class CourseResponse(CamelModel):
    id: str
    title: str
    instructor: str | None = None
    category: str
    duration: str | None = None
    lessons: int = 0
    description: str | None = None
    level: str = "入门"
    tags: list[str] = []
    progress: int = 0


def course_to_response(course: Course, progress: int = 0) -> CourseResponse:
    return CourseResponse(
        id=course.id,
        title=course.title,
        instructor=course.instructor,
        category=course.category,
        duration=course.duration,
        lessons=course.lessons,
        description=course.description,
        level=course.level,
        tags=course.tags or [],
        progress=progress,
    )


@router.get("/")
async def list_courses(
    category: str | None = Query(None),
    level: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    service = CourseService(db)
    courses, total = await service.list_courses(
        category=category,
        level=level,
        page=page,
        page_size=page_size,
    )

    # 获取当前用户的学习进度
    progress_list = await service.list_user_progress(user.id)
    progress_map = {cp.course_id: cp.progress for cp in progress_list}

    return UnifiedResponse.success(
        data={
            "items": [course_to_response(c, progress_map.get(c.id, 0)) for c in courses],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("/")
async def create_course(
    data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    service = CourseService(db)
    course = await service.create_course(
        title=data.title,
        instructor=data.instructor,
        category=data.category,
        duration=data.duration,
        lessons=data.lessons,
        description=data.description,
        level=data.level,
        tags=data.tags or [],
        org_id=user.org_id,
        created_by=user.id,
    )
    return UnifiedResponse.success(data=course_to_response(course))


@router.get("/{course_id}")
async def get_course(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    service = CourseService(db)
    course = await service.get_course(course_id)
    if not course:
        return UnifiedResponse.error(code=404, message="课程不存在")
    progress = await service.get_progress(user.id, course_id)
    return UnifiedResponse.success(
        data=course_to_response(course, progress.progress if progress else 0)
    )


@router.put("/{course_id}")
async def update_course(
    course_id: str,
    data: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    service = CourseService(db)
    update_data = {}
    for field in [
        "title",
        "instructor",
        "category",
        "duration",
        "lessons",
        "description",
        "level",
        "tags",
    ]:
        val = getattr(data, field, None)
        if val is not None:
            update_data[field] = val

    course = await service.update_course(course_id, **update_data)
    if not course:
        return UnifiedResponse.error(code=404, message="课程不存在")
    return UnifiedResponse.success(data=course_to_response(course))


@router.put("/{course_id}/progress")
async def update_progress(
    course_id: str,
    data: ProgressUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    service = CourseService(db)
    cp = await service.update_progress(
        user_id=user.id,
        course_id=course_id,
        progress=data.progress,
        completed_lessons=data.completed_lessons,
    )
    return UnifiedResponse.success(
        data={
            "courseId": course_id,
            "progress": cp.progress,
            "completedLessons": cp.completed_lessons or [],
        }
    )


@router.delete("/{course_id}")
async def delete_course(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    service = CourseService(db)
    success = await service.delete_course(course_id)
    if not success:
        return UnifiedResponse.error(code=404, message="课程不存在")
    return UnifiedResponse.success(message="删除成功")
