"""
资产管理模型
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import GUID, Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.user import Organization, User


class Asset(Base, TimestampMixin):
    """企业资产表"""

    __tablename__ = "assets"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # real_estate, equity, vehicle, ip, equipment
    original_value: Mapped[float] = mapped_column(Float, default=0.0)
    current_value: Mapped[float] = mapped_column(Float, default=0.0)
    acquisition_date: Mapped[Date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(String(1000))

    # 归属
    org_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE")
    )
    created_by: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )

    # 关系
    organization: Mapped[Optional["Organization"]] = relationship("Organization")
    creator: Mapped[Optional["User"]] = relationship("User")
