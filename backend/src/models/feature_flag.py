# -*- coding: utf-8 -*-

from typing import Optional
from datetime import datetime

from sqlalchemy import String, Boolean, Integer, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class FeatureFlag(Base, TimestampMixin):
    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    rollout_percentage: Mapped[int] = mapped_column(Integer, default=10000)  # 万分比，10000=100%
    target_roles: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    target_org_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
