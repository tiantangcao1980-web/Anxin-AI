import logging
from typing import Any, cast

from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.notification import (
    Notification,
    NotificationChannel,
    NotificationEventType,
    NotificationPreference,
)

logger = logging.getLogger(__name__)

# ============================================================
# 通知模板
# ============================================================
NOTIFICATION_TEMPLATES: dict[str, dict[str, str]] = {
    "approval_pending": {
        "title": "新审批待处理",
        "message": "您有一条新的审批待处理：{title}",
        "event_type": NotificationEventType.APPROVAL,
        "type": "urgent",
    },
    "approval_approved": {
        "title": "审批已通过",
        "message": "您的审批申请已通过：{title}",
        "event_type": NotificationEventType.APPROVAL,
        "type": "success",
    },
    "approval_rejected": {
        "title": "审批已驳回",
        "message": "您的审批申请已驳回：{title}",
        "event_type": NotificationEventType.APPROVAL,
        "type": "warning",
    },
    "case_assigned": {
        "title": "新案件分配",
        "message": "您被分配了一个新案件：{title}",
        "event_type": NotificationEventType.CASE,
        "type": "info",
    },
    "contract_review": {
        "title": "合同审查完成",
        "message": "合同审查已完成，风险等级：{risk_level}",
        "event_type": NotificationEventType.CONTRACT,
        "type": "info",
    },
    "lawyer_match": {
        "title": "律师匹配结果",
        "message": "有新的律师匹配结果，共{count}位律师",
        "event_type": NotificationEventType.LAWYER,
        "type": "info",
    },
    "system_update": {
        "title": "系统通知",
        "message": "{message}",
        "event_type": NotificationEventType.SYSTEM,
        "type": "info",
    },
}


class NotificationService:
    """通知服务 - 支持多渠道分发和用户偏好"""

    # ============================================================
    # 基础 CRUD
    # ============================================================

    @staticmethod
    async def create_notification(
        session: AsyncSession,
        user_id: str,
        type: str,
        title: str,
        message: str,
        related_link: str | None = None,
        event_type: str | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            related_link=related_link,
            is_read=False,
            event_type=event_type,
        )
        session.add(notification)
        await session.commit()
        await session.refresh(notification)
        return notification

    @staticmethod
    async def get_user_notifications(
        session: AsyncSession,
        user_id: str,
        limit: int = 50,
        unread_only: bool = False,
        event_type: str | None = None,
    ) -> list[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            query = query.where(Notification.is_read == False)

        if event_type:
            query = query.where(Notification.event_type == event_type)

        query = query.order_by(Notification.created_at.desc()).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_unread_count(
        session: AsyncSession,
        user_id: str,
    ) -> int:
        """获取用户未读通知总数"""
        query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.is_read == False
        )
        result = await session.execute(query)
        return result.scalar() or 0

    @staticmethod
    async def mark_as_read(
        session: AsyncSession, notification_id: str, user_id: str
    ) -> Notification | None:
        query = (
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True)
            .returning(Notification)
        )
        result = await session.execute(query)
        await session.commit()
        return result.scalar_one_or_none()

    @staticmethod
    async def mark_all_as_read(session: AsyncSession, user_id: str) -> int:
        query = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True)
        )
        result = await session.execute(query)
        await session.commit()
        return cast(CursorResult[Any], result).rowcount

    @staticmethod
    async def delete_notification(
        session: AsyncSession, notification_id: str, user_id: str
    ) -> bool:
        query = delete(Notification).where(
            Notification.id == notification_id, Notification.user_id == user_id
        )
        result = await session.execute(query)
        await session.commit()
        return cast(CursorResult[Any], result).rowcount > 0

    # ============================================================
    # 通知偏好管理
    # ============================================================

    @staticmethod
    async def get_user_preferences(
        session: AsyncSession, user_id: str
    ) -> list[NotificationPreference]:
        """获取用户的通知偏好列表"""
        query = (
            select(NotificationPreference)
            .where(NotificationPreference.user_id == user_id)
            .order_by(NotificationPreference.event_type, NotificationPreference.channel)
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def upsert_preferences(
        session: AsyncSession, user_id: str, preferences: list[dict[str, Any]]
    ) -> list[NotificationPreference]:
        """批量更新/插入用户通知偏好

        preferences 格式：[{"channel": "email", "event_type": "approval", "enabled": true}, ...]
        """
        results = []
        for pref in preferences:
            channel = pref["channel"]
            event_type = pref["event_type"]
            enabled = pref.get("enabled", True)

            # 查找已有记录
            query = select(NotificationPreference).where(
                NotificationPreference.user_id == user_id,
                NotificationPreference.channel == channel,
                NotificationPreference.event_type == event_type,
            )
            result = await session.execute(query)
            existing = result.scalar_one_or_none()

            if existing:
                existing.enabled = enabled
                results.append(existing)
            else:
                new_pref = NotificationPreference(
                    user_id=user_id,
                    channel=channel,
                    event_type=event_type,
                    enabled=enabled,
                )
                session.add(new_pref)
                results.append(new_pref)

        await session.commit()
        # 刷新所有对象以获取数据库生成的字段
        for r in results:
            await session.refresh(r)
        return results

    @staticmethod
    async def is_channel_enabled(
        session: AsyncSession,
        user_id: str,
        channel: str,
        event_type: str,
    ) -> bool:
        """检查用户是否启用了特定渠道+事件类型的通知

        如果没有对应的偏好记录，站内信默认开启，其他渠道默认关闭。
        """
        query = select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.channel == channel,
            NotificationPreference.event_type == event_type,
        )
        result = await session.execute(query)
        pref = result.scalar_one_or_none()

        if pref is not None:
            return pref.enabled

        # 默认策略：站内信开启，其他渠道关闭
        return channel == NotificationChannel.SITE

    # ============================================================
    # 多渠道分发
    # ============================================================

    @staticmethod
    async def dispatch_notification(
        session: AsyncSession,
        user_id: str,
        template_key: str,
        params: dict[str, Any] | None = None,
        related_link: str | None = None,
    ) -> Notification | None:
        """根据模板和用户偏好，向所有启用的渠道分发通知

        站内信创建后会通过 WebSocket 实时推送给在线用户。
        返回站内信 Notification 对象（如果创建了的话），否则返回 None。
        """
        template = NOTIFICATION_TEMPLATES.get(template_key)
        if not template:
            logger.warning("未知的通知模板: %s", template_key)
            return None

        params = params or {}
        title = template["title"]
        message = template["message"].format(**params)
        event_type = template["event_type"]
        notif_type = template["type"]

        site_notification: Notification | None = None

        for channel in NotificationChannel:
            enabled = await NotificationService.is_channel_enabled(
                session, user_id, channel.value, event_type
            )
            if not enabled:
                continue

            if channel == NotificationChannel.SITE:
                site_notification = await NotificationService.create_notification(
                    session,
                    user_id=user_id,
                    type=notif_type,
                    title=title,
                    message=message,
                    related_link=related_link,
                    event_type=event_type,
                )
                # 通过 WebSocket 实时推送给在线用户
                try:
                    from src.services.im_hub import im_manager

                    await im_manager.push_notification(
                        user_id,
                        {
                            "id": str(site_notification.id),
                            "type": site_notification.type,
                            "title": site_notification.title,
                            "message": site_notification.message,
                            "is_read": False,
                            "related_link": site_notification.related_link,
                            "event_type": site_notification.event_type,
                            "created_at": (
                                site_notification.created_at.isoformat()
                                if site_notification.created_at
                                else None
                            ),
                        },
                    )
                except Exception as e:
                    logger.warning("WebSocket 推送通知失败: %s", e)

            elif channel == NotificationChannel.EMAIL:
                await NotificationService._send_email(user_id, title, message)
            elif channel == NotificationChannel.WECHAT:
                await NotificationService._send_wechat(user_id, title, message)
            elif channel == NotificationChannel.SMS:
                await NotificationService._send_sms(user_id, title, message)

        return site_notification

    # ============================================================
    # 渠道发送占位方法（后续集成实际服务）
    # ============================================================

    @staticmethod
    async def _send_email(user_id: str, title: str, message: str) -> None:
        """发送邮件通知（占位 - 仅记录日志）"""
        logger.info("[邮件通知] user=%s title=%s message=%s", user_id, title, message)

    @staticmethod
    async def _send_wechat(user_id: str, title: str, message: str) -> None:
        """发送微信通知（占位 - 仅记录日志）"""
        logger.info("[微信通知] user=%s title=%s message=%s", user_id, title, message)

    @staticmethod
    async def _send_sms(user_id: str, title: str, message: str) -> None:
        """发送短信通知（占位 - 仅记录日志）"""
        logger.info("[短信通知] user=%s title=%s message=%s", user_id, title, message)
