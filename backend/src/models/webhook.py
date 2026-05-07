"""Webhook processing records for durable idempotency."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class WebhookReceived(Base, TimestampMixin):
    """Persisted webhook processing state keyed by provider scope and event id."""

    __tablename__ = "webhook_received"
    __table_args__ = (
        UniqueConstraint("scope", "idempotency_key", name="uq_webhook_received_scope_key"),
        Index("ix_webhook_received_status", "status"),
        Index("ix_webhook_received_processed_at", "processed_at"),
        Index("ix_webhook_received_next_retry_at", "next_retry_at"),
    )

    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="processing")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
