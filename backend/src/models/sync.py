"""Durable client sync and remote-control models."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import GUID, Base, TimestampMixin


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
    client_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class RemoteControlPairing(Base, TimestampMixin):
    """Mobile-to-desktop pairing request that must be confirmed before commands."""

    __tablename__ = "remote_control_pairings"
    __table_args__ = (
        Index("ix_remote_control_pairings_org_status", "org_id", "status"),
        Index("ix_remote_control_pairings_user_desktop", "user_id", "desktop_device_id"),
        UniqueConstraint("org_id", "id", name="uq_remote_control_pairings_org_id"),
    )

    org_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    mobile_device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    desktop_device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    requested_scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    privacy_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="hybrid")
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="pending_desktop_confirmation"
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class RemoteControlCommand(Base, TimestampMixin):
    """Queued remote-control command; execution is handled by a desktop host later."""

    __tablename__ = "remote_control_commands"
    __table_args__ = (
        Index("ix_remote_control_commands_org_status", "org_id", "status"),
        Index("ix_remote_control_commands_pairing", "pairing_id"),
        Index("ix_remote_control_commands_desktop_status", "desktop_device_id", "status"),
    )

    org_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    pairing_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("remote_control_pairings.id", ondelete="RESTRICT"), nullable=False
    )
    desktop_device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    command_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    risk_level: Mapped[str] = mapped_column(String(40), nullable=False, default="l3")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="queued")
    route_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    route_consumer_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    route_scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    second_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_by_host: Mapped[str | None] = mapped_column(String(160), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class RemoteControlAuditEvent(Base):
    """Append-only audit event for remote-control pairing and command actions."""

    __tablename__ = "remote_control_audit_events"
    __table_args__ = (
        Index("ix_remote_control_audit_events_org_created", "org_id", "created_at"),
        Index("ix_remote_control_audit_events_action_status", "action", "status"),
    )

    org_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    pairing_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    command_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="success")
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
