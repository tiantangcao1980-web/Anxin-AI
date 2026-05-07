"""
任务管理模型
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import GUID, Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.case import Case
    from src.models.user import User


class Task(Base, TimestampMixin):
    """任务表"""
    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="todo")  # todo, in_progress, done
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # high, medium, low
    due_date: Mapped[Date | None] = mapped_column(Date)
    tags: Mapped[list[str] | None] = mapped_column(JSON, default=list)

    # 关联
    assignee_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )
    case_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("cases.id", ondelete="SET NULL")
    )
    created_by: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )
    org_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE")
    )

    # 关系
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assignee_id])
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])
    case: Mapped[Optional["Case"]] = relationship("Case")
