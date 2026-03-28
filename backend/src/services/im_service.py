# -*- coding: utf-8 -*-
"""
IM 即时通讯业务服务

提供对话管理、消息收发、已读标记、撤回等核心功能。
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

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
        title: Optional[str] = None,
        case_id: Optional[str] = None,
        contract_id: Optional[str] = None,
        metadata_: Optional[dict] = None,
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
        now = datetime.now(timezone.utc)
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
    ) -> Optional[IMConversation]:
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
    ) -> list[dict]:
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

        conversations = []
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
    ) -> Optional[dict]:
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
        before_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
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

    async def send_message(
        self,
        conversation_id: str,
        sender_id: str,
        content: str,
        message_type: str = "text",
        reply_to_id: Optional[str] = None,
        metadata_: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        发送消息

        创建消息记录，更新对话最后消息信息，增加其他参与者未读计数。
        """
        # 验证参与者
        if not await self.is_participant(conversation_id, sender_id):
            return None

        now = datetime.now(timezone.utc)

        # 创建消息
        message = IMMessage(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
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
        now = datetime.now(timezone.utc)
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
        return result.rowcount > 0

    async def recall_message(
        self, message_id: str, user_id: str
    ) -> Optional[dict]:
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
        now = datetime.now(timezone.utc)
        if now - message.created_at.replace(tzinfo=timezone.utc) > timedelta(minutes=2):
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
    def _message_to_dict(msg: IMMessage) -> dict:
        """将消息模型转换为字典"""
        return {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "sender_id": msg.sender_id,
            "content": msg.content,
            "message_type": msg.message_type,
            "reply_to_id": msg.reply_to_id,
            "metadata_": msg.metadata_,
            "is_recalled": msg.is_recalled,
            "read_by": msg.read_by or [],
            "created_at": msg.created_at.isoformat(),
        }
