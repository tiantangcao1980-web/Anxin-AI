from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.notification import NotificationChannel, NotificationEventType
from src.models.user import User
from src.services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_notification_service_read_and_delete_lifecycle(
    db_session: AsyncSession,
) -> None:
    user = User(
        email=f"{uuid4()}@example.com",
        hashed_password="hashed",
        name="Notification User",
    )
    db_session.add(user)
    await db_session.flush()

    notification = await NotificationService.create_notification(
        db_session,
        user_id=user.id,
        type="info",
        title="Case updated",
        message="A case was updated.",
        event_type=NotificationEventType.CASE,
    )

    unread_count = await NotificationService.get_unread_count(db_session, user.id)
    assert unread_count == 1

    notifications = await NotificationService.get_user_notifications(db_session, user.id)
    assert [item.id for item in notifications] == [notification.id]

    marked = await NotificationService.mark_as_read(
        db_session,
        notification.id,
        user.id,
    )
    assert marked is not None
    assert marked.is_read is True

    assert await NotificationService.mark_all_as_read(db_session, user.id) == 0
    assert await NotificationService.delete_notification(db_session, notification.id, user.id)
    assert await NotificationService.get_user_notifications(db_session, user.id) == []


@pytest.mark.asyncio
async def test_notification_service_preferences_default_and_upsert(
    db_session: AsyncSession,
) -> None:
    user = User(
        email=f"{uuid4()}@example.com",
        hashed_password="hashed",
        name="Preference User",
    )
    db_session.add(user)
    await db_session.flush()

    assert await NotificationService.is_channel_enabled(
        db_session,
        user.id,
        NotificationChannel.SITE,
        NotificationEventType.APPROVAL,
    )
    assert not await NotificationService.is_channel_enabled(
        db_session,
        user.id,
        NotificationChannel.EMAIL,
        NotificationEventType.APPROVAL,
    )

    updated = await NotificationService.upsert_preferences(
        db_session,
        user.id,
        [
            {
                "channel": NotificationChannel.EMAIL,
                "event_type": NotificationEventType.APPROVAL,
                "enabled": True,
            }
        ],
    )

    assert len(updated) == 1
    assert updated[0].enabled is True
    assert await NotificationService.is_channel_enabled(
        db_session,
        user.id,
        NotificationChannel.EMAIL,
        NotificationEventType.APPROVAL,
    )
