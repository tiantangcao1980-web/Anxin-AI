"""
资产管理模型
"""

from typing import Optional
from sqlalchemy import String, Float, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, GUID

class Asset(Base, TimestampMixin):
    """企业资产表"""
    __tablename__ = "assets"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)  # real_estate, equity, vehicle, ip, equipment
    original_value: Mapped[float] = mapped_column(Float, default=0.0)
    current_value: Mapped[float] = mapped_column(Float, default=0.0)
    acquisition_date: Mapped[Optional[Date]] = mapped_column(Date)
    description: Mapped[Optional[str]] = mapped_column(String(1000))
    
    # 归属
    org_id: Mapped[Optional[str]] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL")
    )

    # 关系
    organization: Mapped[Optional["Organization"]] = relationship("Organization")
    creator: Mapped[Optional["User"]] = relationship("User")
