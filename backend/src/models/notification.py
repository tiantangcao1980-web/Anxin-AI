
import enum
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey, Text, UniqueConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, GUID

if TYPE_CHECKING:
    from src.models.user import User


class NotificationChannel(str, enum.Enum):
    """通知渠道"""
    SITE = "site"
    EMAIL = "email"
    WECHAT = "wechat"
    SMS = "sms"


class NotificationEventType(str, enum.Enum):
    """通知事件类型"""
    APPROVAL = "approval"
    CHAT = "chat"
    CASE = "case"
    SYSTEM = "system"
    CONTRACT = "contract"
    LAWYER = "lawyer"


class Notification(Base, TimestampMixin):
    """系统通知"""

    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    type: Mapped[str] = mapped_column(String(50), nullable=False) # urgent, warning, info, success
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    related_link: Mapped[Optional[str]] = mapped_column(String(500))

    # 事件类型，用于匹配通知偏好
    event_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 关联
    user: Mapped["User"] = relationship("User", backref="notifications")


class NotificationPreference(Base, TimestampMixin):
    """用户通知偏好设置"""

    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "channel", "event_type", name="uq_user_channel_event"),
    )

    user_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )  # site, email, wechat, sms

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )  # approval, chat, case, system, contract, lawyer

    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 关联
    user: Mapped["User"] = relationship("User", backref="notification_preferences")
