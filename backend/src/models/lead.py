"""
案源管理模型
"""

from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import JSON, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import GUID, Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.user import User


class Lead(Base, TimestampMixin):
    """案源线索表"""

    __tablename__ = "leads"

    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_info: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str | None] = mapped_column(String(100))  # 转介绍, 线上咨询, 主动拓展, 电话咨询
    case_type: Mapped[str | None] = mapped_column(String(100))
    estimated_amount: Mapped[float] = mapped_column(Float, default=0.0)
    stage: Mapped[str] = mapped_column(
        String(20), default="new"
    )  # new, contacted, qualified, proposal, won, lost
    follow_ups: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, default=list)

    # 关联
    assignee_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
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
