"""Durable client sync log models."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class SyncLog(Base, TimestampMixin):
    """Append-only sync change log scoped by user and source device."""

    __tablename__ = "sync_log"
    __table_args__ = (
        UniqueConstraint("user_id", "version", name="uq_sync_log_user_version"),
        Index("ix_sync_log_user_version", "user_id", "version"),
        Index("ix_sync_log_user_entity", "user_id", "entity_type", "entity_id"),
        Index("ix_sync_log_user_device", "user_id", "device_id"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    client_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    client_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

