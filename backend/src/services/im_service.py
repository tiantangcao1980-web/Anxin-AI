"""
IM 即时通讯业务服务

提供对话管理、消息收发、已读标记、撤回等核心功能。
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from loguru import logger
from sqlalchemy import and_, desc, func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.im import IMConversation, IMMessage, IMParticipant


class IMService:
    """IM 即时通讯服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ==================== 对话管理 ====================

    async def create_conversation(
        self,
        type: str,
        creator_id: str,
        participant_ids: list[str],
        title: str | None = None,
        case_id: str | None = None,
        contract_id: str | None = None,
        metadata_: dict[str, Any] | None = None,
    ) -> IMConversation:
        """
        创建对话

        - private 类型：检查是否已存在两人私聊，存在则返回已有对话
        - group/case/contract 类型：直接创建新对话
        """
        # 确保创建者在参与者列表中
        if creator_id not in participant_ids:
            participant_ids = [creator_id] + participant_ids

        # private 类型：检查是否已存在
        if type == "private" and len(participant_ids) == 2:
            existing = await self._find_private_conversation(
                participant_ids[0], participant_ids[1]
            )
            if existing:
                return existing

        # 创建对话
        conversation = IMConversation(
            id=str(uuid.uuid4()),
            type=type,
            title=title,
            case_id=case_id,
            contract_id=contract_id,
            metadata_=metadata_,
        )
        self.db.add(conversation)
        await self.db.flush()

        # 创建参与者
        now = datetime.now(UTC)
        for uid in participant_ids:
            role = "owner" if uid == creator_id else "member"
            participant = IMParticipant(
                id=str(uuid.uuid4()),
                conversation_id=conversation.id,
                user_id=uid,
                role=role,
                joined_at=now,
            )
            self.db.add(participant)

        await self.db.commit()
        await self.db.refresh(conversation)
        logger.info(
            f"[IM] 对话已创建: id={conversation.id}, type={type}, "
            f"participants={participant_ids}"
        )
        return conversation

    async def _find_private_conversation(
        self, user_id_1: str, user_id_2: str
    ) -> IMConversation | None:
        """查找两人之间已存在的私聊对话"""
        # 子查询：找到两个用户都参与的、类型为 private 的对话
        subq1 = (
            select(IMParticipant.conversation_id)
            .where(IMParticipant.user_id == user_id_1)
            .subquery()
        )
        subq2 = (
            select(IMParticipant.conversation_id)
            .where(IMParticipant.user_id == user_id_2)
            .subquery()
        )

        result = await self.db.execute(
            select(IMConversation)
            .where(
                and_(
                    IMConversation.type == "private",
                    IMConversation.is_active == True,
                    IMConversation.id.in_(select(subq1.c.conversation_id)),
                    IMConversation.id.in_(select(subq2.c.conversation_id)),
                )
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_conversations(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        获取用户参与的所有对话列表

        按 last_message_at 降序排列，返回列表含 unread_count 和 last_message_preview。
        """
        # 查询用户参与的对话
        result = await self.db.execute(
            select(IMConversation, IMParticipant.unread_count)
            .join(
                IMParticipant,
                and_(
                    IMParticipant.conversation_id == IMConversation.id,
                    IMParticipant.user_id == user_id,
                ),
            )
            .where(IMConversation.is_active == True)
            .order_by(desc(IMConversation.last_message_at))
            .offset(offset)
            .limit(limit)
        )
        rows = result.all()

        conversations: list[dict[str, Any]] = []
        for conv, unread_count in rows:
            # 获取参与者列表
            p_result = await self.db.execute(
                select(IMParticipant).where(
                    IMParticipant.conversation_id == conv.id
                )
            )
            participants = p_result.scalars().all()

            conversations.append(
                {
                    "id": conv.id,
                    "type": conv.type,
                    "title": conv.title,
                    "avatar_url": conv.avatar_url,
                    "is_active": conv.is_active,
                    "last_message_at": (
                        conv.last_message_at.isoformat() if conv.last_message_at else None
                    ),
                    "last_message_preview": conv.last_message_preview,
                    "unread_count": unread_count or 0,
                    "case_id": conv.case_id,
                    "contract_id": conv.contract_id,
                    "participants": [
                        {
                            "user_id": p.user_id,
                            "role": p.role,
                            "nickname": p.nickname,
                        }
                        for p in participants
                    ],
                    "created_at": conv.created_at.isoformat(),
                }
            )

        return conversations

    async def get_conversation(
        self, conversation_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """获取单个对话详情（验证用户是参与者）"""
        result = await self.db.execute(
            select(IMConversation, IMParticipant.unread_count)
            .join(
                IMParticipant,
                and_(
                    IMParticipant.conversation_id == IMConversation.id,
                    IMParticipant.user_id == user_id,
                ),
            )
            .where(IMConversation.id == conversation_id)
        )
        row = result.first()
        if not row:
            return None

        conv, unread_count = row

        p_result = await self.db.execute(
            select(IMParticipant).where(
                IMParticipant.conversation_id == conv.id
            )
        )
        participants = p_result.scalars().all()

        return {
            "id": conv.id,
            "type": conv.type,
            "title": conv.title,
            "avatar_url": conv.avatar_url,
            "is_active": conv.is_active,
            "last_message_at": (
                conv.last_message_at.isoformat() if conv.last_message_at else None
            ),
            "last_message_preview": conv.last_message_preview,
            "unread_count": unread_count or 0,
            "case_id": conv.case_id,
            "contract_id": conv.contract_id,
            "participants": [
                {
                    "user_id": p.user_id,
                    "role": p.role,
                    "nickname": p.nickname,
                }
                for p in participants
            ],
            "created_at": conv.created_at.isoformat(),
        }

    async def get_participant_ids(self, conversation_id: str) -> list[str]:
        """获取对话所有参与者 ID"""
        result = await self.db.execute(
            select(IMParticipant.user_id).where(
                IMParticipant.conversation_id == conversation_id
            )
        )
        return [row[0] for row in result.all()]

    async def is_participant(self, conversation_id: str, user_id: str) -> bool:
        """检查用户是否为对话参与者"""
        result = await self.db.execute(
            select(IMParticipant.id).where(
                and_(
                    IMParticipant.conversation_id == conversation_id,
                    IMParticipant.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none() is not None

    # ==================== 消息管理 ====================

    async def get_messages(
        self,
        conversation_id: str,
        user_id: str,
        before_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        游标分页获取消息列表

        验证用户是参与者后，返回消息列表（按 created_at 升序）。
        """
        # 验证参与者
        if not await self.is_participant(conversation_id, user_id):
            return []

        query = select(IMMessage).where(
            IMMessage.conversation_id == conversation_id
        )

        # 游标分页
        if before_id:
            # 获取 before 消息的 created_at
            before_result = await self.db.execute(
                select(IMMessage.created_at).where(IMMessage.id == before_id)
            )
            before_time = before_result.scalar_one_or_none()
            if before_time:
                query = query.where(IMMessage.created_at < before_time)

        query = query.order_by(desc(IMMessage.created_at)).limit(limit)

        result = await self.db.execute(query)
        messages = result.scalars().all()

        # 按时间正序返回
        messages = list(reversed(messages))

        return [self._message_to_dict(msg) for msg in messages]

    async def get_offline_messages(
        self,
        user_id: str,
        last_ack_message_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        获取用户离线期间未确认的消息。

        如果客户端提供 last_ack_message_id，则返回该消息之后、用户参与的所有对话消息；
        否则按每个参与关系的 last_read_at / joined_at 返回未读增量。
        """
        limit = max(1, min(limit, 500))
        ack_conversation_id = None
        ack_sequence = None
        if last_ack_message_id:
            ack_result = await self.db.execute(
                select(IMMessage.conversation_id, IMMessage.sequence)
                .join(
                    IMParticipant,
                    and_(
                        IMParticipant.conversation_id == IMMessage.conversation_id,
                        IMParticipant.user_id == user_id,
                    ),
                )
                .where(IMMessage.id == last_ack_message_id)
            )
            ack_row = ack_result.first()
            if ack_row:
                ack_conversation_id, ack_sequence = ack_row

        query = (
            select(IMMessage)
            .join(
                IMParticipant,
                and_(
                    IMParticipant.conversation_id == IMMessage.conversation_id,
                    IMParticipant.user_id == user_id,
                ),
            )
            .where(IMMessage.sender_id != user_id)
        )
        if ack_conversation_id and ack_sequence is not None:
            query = query.where(
                or_(
                    and_(
                        IMMessage.conversation_id == ack_conversation_id,
                        IMMessage.sequence > ack_sequence,
                    ),
                    and_(
                        IMMessage.conversation_id != ack_conversation_id,
                        IMMessage.created_at >= IMParticipant.joined_at,
                        or_(
                            IMParticipant.last_read_at.is_(None),
                            IMMessage.created_at > IMParticipant.last_read_at,
                        ),
                    ),
                )
            )
        else:
            query = query.where(
                IMMessage.created_at >= IMParticipant.joined_at,
                or_(
                    IMParticipant.last_read_at.is_(None),
                    IMMessage.created_at > IMParticipant.last_read_at,
                ),
            )

        query = query.order_by(IMMessage.created_at.asc(), IMMessage.sequence.asc()).limit(limit)
        result = await self.db.execute(query)
        return [self._message_to_dict(msg) for msg in result.scalars().all()]

    async def send_message(
        self,
        conversation_id: str,
        sender_id: str,
        content: str,
        message_type: str = "text",
        reply_to_id: str | None = None,
        metadata_: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        发送消息

        创建消息记录，更新对话最后消息信息，增加其他参与者未读计数。
        """
        # 验证参与者
        if not await self.is_participant(conversation_id, sender_id):
            return None

        now = datetime.now(UTC)
        sequence_result = await self.db.execute(
            select(func.coalesce(func.max(IMMessage.sequence), 0)).where(
                IMMessage.conversation_id == conversation_id
            )
        )
        next_sequence = (sequence_result.scalar_one() or 0) + 1

        # 创建消息
        message = IMMessage(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            sequence=next_sequence,
            reply_to_id=reply_to_id,
            metadata_=metadata_,
            read_by=[sender_id],
        )
        self.db.add(message)

        # 生成预览文本
        preview = content[:100] if message_type == "text" else f"[{message_type}]"

        # 更新对话最后消息信息
        await self.db.execute(
            update(IMConversation)
            .where(IMConversation.id == conversation_id)
            .values(
                last_message_at=now,
                last_message_preview=preview,
                updated_at=now,
            )
        )

        # 其他参与者未读计数 +1
        await self.db.execute(
            update(IMParticipant)
            .where(
                and_(
                    IMParticipant.conversation_id == conversation_id,
                    IMParticipant.user_id != sender_id,
                )
            )
            .values(unread_count=IMParticipant.unread_count + 1)
        )

        await self.db.commit()
        await self.db.refresh(message)

        return self._message_to_dict(message)

    async def mark_as_read(self, conversation_id: str, user_id: str) -> bool:
        """标记对话为已读：重置未读数，更新 last_read_at"""
        now = datetime.now(UTC)
        result = await self.db.execute(
            update(IMParticipant)
            .where(
                and_(
                    IMParticipant.conversation_id == conversation_id,
                    IMParticipant.user_id == user_id,
                )
            )
            .values(unread_count=0, last_read_at=now)
        )
        await self.db.commit()
        return cast(CursorResult[Any], result).rowcount > 0

    async def ack_message(self, message_id: str, user_id: str) -> bool:
        """确认客户端已收到某条消息，并推进该会话的已读游标。"""
        result = await self.db.execute(
            select(IMMessage).where(IMMessage.id == message_id)
        )
        message = result.scalar_one_or_none()
        if not message:
            return False

        participant_result = await self.db.execute(
            select(IMParticipant).where(
                and_(
                    IMParticipant.conversation_id == message.conversation_id,
                    IMParticipant.user_id == user_id,
                )
            )
        )
        participant = participant_result.scalar_one_or_none()
        if not participant:
            return False

        read_by = set(message.read_by or [])
        read_by.add(user_id)
        message.read_by = sorted(read_by)
        participant.last_read_at = message.created_at

        remaining_result = await self.db.execute(
            select(func.count())
            .select_from(IMMessage)
            .where(
                and_(
                    IMMessage.conversation_id == message.conversation_id,
                    IMMessage.sender_id != user_id,
                    IMMessage.sequence > message.sequence,
                )
            )
        )
        participant.unread_count = remaining_result.scalar_one() or 0

        await self.db.commit()
        return True

    async def recall_message(
        self, message_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """
        撤回消息

        - 只能撤回自己发送的消息
        - 发送后 2 分钟内可撤回
        """
        result = await self.db.execute(
            select(IMMessage).where(IMMessage.id == message_id)
        )
        message = result.scalar_one_or_none()

        if not message:
            return None

        # 验证是发送者
        if message.sender_id != user_id:
            return None

        # 验证 2 分钟内
        now = datetime.now(UTC)
        if now - message.created_at.replace(tzinfo=UTC) > timedelta(minutes=2):
            return None

        # 执行撤回
        message.is_recalled = True
        message.content = "消息已撤回"
        message.updated_at = now

        await self.db.commit()
        await self.db.refresh(message)

        return self._message_to_dict(message)

    # ==================== 辅助方法 ====================

    @staticmethod
    def _message_to_dict(msg: IMMessage) -> dict[str, Any]:
        """将消息模型转换为字典"""
        return {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "sender_id": msg.sender_id,
            "content": msg.content,
            "message_type": msg.message_type,
            "sequence": msg.sequence,
            "reply_to_id": msg.reply_to_id,
            "metadata_": msg.metadata_,
            "is_recalled": msg.is_recalled,
            "read_by": msg.read_by or [],
            "created_at": msg.created_at.isoformat(),
        }
