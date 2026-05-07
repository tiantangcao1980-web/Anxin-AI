"""
律师评价模型
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import GUID, Base, TimestampMixin


class LawyerReview(Base, TimestampMixin):
    """律师评价"""

    __tablename__ = "lawyer_reviews"

    # 关联律师档案
    lawyer_profile_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("lawyer_profiles.id", ondelete="CASCADE"), nullable=False
    )
    # 评价人
    reviewer_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # 关联咨询（可选）
    consultation_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("consultations.id", ondelete="SET NULL"), nullable=True
    )
    # 关联委托（可选）
    delegation_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("delegations.id", ondelete="SET NULL"), nullable=True
    )

    # 评分 1-5 星
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    # 评价内容
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 标签，如 ["专业", "耐心", "高效"]
    tags: Mapped[list[str] | None] = mapped_column(JSON, default=list)
    # 是否匿名评价
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)

    # 律师回复
    reply_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 关系
    lawyer_profile = relationship("LawyerProfile", backref="reviews")
    reviewer = relationship("User", backref="lawyer_reviews")
    consultation = relationship("Consultation", backref="reviews")
    delegation = relationship("Delegation", backref="reviews")

    __table_args__ = (
        Index("ix_lawyer_reviews_profile_created", "lawyer_profile_id", "created_at"),
        Index("ix_lawyer_reviews_reviewer", "reviewer_id"),
    )
