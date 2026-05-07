"""
司法学院课程模型
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import GUID, Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.user import User


class Course(Base, TimestampMixin):
    """课程表"""
    __tablename__ = "courses"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    instructor: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(50), default="regulation")  # regulation, case_study, practice, exam
    duration: Mapped[str | None] = mapped_column(String(50))
    lessons: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(20), default="入门")  # 入门, 进阶, 高级
    tags: Mapped[list[str] | None] = mapped_column(JSON, default=list)

    org_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE")
    )
    created_by: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )

    creator: Mapped[Optional["User"]] = relationship("User")


class CourseProgress(Base, TimestampMixin):
    """课程学习进度表"""
    __tablename__ = "course_progress"

    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    completed_lessons: Mapped[list[str] | None] = mapped_column(JSON, default=list)

    user: Mapped["User"] = relationship("User")
    course: Mapped["Course"] = relationship("Course")
