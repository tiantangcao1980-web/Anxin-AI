"""
律师精英模型
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import GUID, Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.user import User


class Expert(Base, TimestampMixin):
    """律师精英表"""
    __tablename__ = "experts"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str | None] = mapped_column(String(100))  # 高级合伙人, 合伙人, 资深律师
    specialty: Mapped[list[str] | None] = mapped_column(JSON, default=list)  # ['civil', 'corporate']
    years_of_experience: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    cases_handled: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text)
    achievements: Mapped[list[str] | None] = mapped_column(JSON, default=list)

    # 关联到用户（可选，精英可以是外部律师）
    user_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )
    org_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE")
    )

    # 关系
    user: Mapped[Optional["User"]] = relationship("User")
