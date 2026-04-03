# -*- coding: utf-8 -*-
"""
IM 即时通讯路由

REST API + WebSocket 端点，提供对话管理、消息收发、实时通信。
"""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from sqlalchemy import or_, select as sa_select

from src.core.database import get_db
from src.core.deps import get_current_user_required, Permission, require_permission
from src.core.responses import UnifiedResponse
from src.core.security import verify_token
from src.models.user import User
from src.services.im_service import IMService
from src.services.im_hub import im_manager

router = APIRouter(prefix="/im", tags=["即时通讯"])

# ===== 常量 =====
MAX_CONTENT_LENGTH = 5000  # 消息内容最大长度
ALLOWED_MESSAGE_TYPES = {"text", "image", "file", "system", "card"}  # 允许的消息类型白名单


# ===== 响应模型（用于文档目的） =====


class ConversationResponse(BaseModel):
    """对话响应模型"""
    id: str
    type: str
    title: Optional[str] = None
    avatar_url: Optional[str] = None
    last_message_preview: Optional[str] = None
    last_message_at: Optional[str] = None
    unread_count: int = 0


class MessageResponse(BaseModel):
    """消息响应模型"""
    id: str
    conversation_id: str
    sender_id: str
    content: str
    message_type: str = "text"
    reply_to_id: Optional[str] = None
    is_recalled: bool = False
    created_at: str


# ===== 请求模型 =====


class CreateConversationRequest(BaseModel):
    """创建对话请求"""
    type: str = Field(..., description="对话类型: private|group|case|contract")
    participant_ids: list[str] = Field(..., description="参与者用户 ID 列表")
    title: Optional[str] = Field(None, description="对话标题（群聊时使用）")
    case_id: Optional[str] = Field(None, description="关联案件 ID")
    contract_id: Optional[str] = Field(None, description="关联合同 ID")


# ===== REST API =====


@router.get("/users/search")
async def search_users_for_im(
    q: str = Query("", description="搜索关键词（姓名/邮箱）"),
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(require_permission(Permission.USE_CHAT)),
    db: AsyncSession = Depends(get_db),
):
    """搜索用户（用于创建对话时选择成员），排除当前用户"""
    query = sa_select(User).where(User.is_active == True, User.id != user.id)
    if user.role not in {"super_admin", "admin"} and getattr(user, "org_id", None):
        query = query.where(User.org_id == user.org_id)

    if q.strip():
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(User.name.ilike(pattern), User.email.ilike(pattern))
        )

    query = query.order_by(User.name).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return UnifiedResponse.success(data=[
        {
            "id": str(u.id),
            "name": u.name,
            "email": u.email,
            "avatar_url": u.avatar_url,
            "department": u.department,
            "role": u.role,
        }
        for u in users
    ])


@router.get("/conversations")
async def get_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.USE_CHAT)),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的对话列表"""
    service = IMService(db)
    conversations = await service.get_conversations(user.id, limit=limit, offset=offset)
    return UnifiedResponse.success(data=conversations)


@router.post("/conversations")
async def create_conversation(
    req: CreateConversationRequest,
    user: User = Depends(require_permission(Permission.USE_CHAT)),
    db: AsyncSession = Depends(get_db),
):
    """创建新对话"""
    if req.type not in ("private", "group", "case", "contract"):
        return UnifiedResponse.error(code=400, message="无效的对话类型")

    if req.type == "private" and len(req.participant_ids) != 1:
        return UnifiedResponse.error(code=400, message="私聊对话只能有一个对方参与者")

    service = IMService(db)
    conversation = await service.create_conversation(
        type=req.type,
        creator_id=user.id,
        participant_ids=req.participant_ids,
        title=req.title,
        case_id=req.case_id,
        contract_id=req.contract_id,
    )

    # 返回完整对话信息
    conv_data = await service.get_conversation(conversation.id, user.id)
    return UnifiedResponse.success(data=conv_data, message="对话已创建")


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    before_id: Optional[str] = Query(None, description="游标：获取此消息之前的记录"),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(require_permission(Permission.USE_CHAT)),
    db: AsyncSession = Depends(get_db),
):
    """获取对话消息历史（游标分页）"""
    service = IMService(db)

    # 验证参与者
    if not await service.is_participant(conversation_id, user.id):
        return UnifiedResponse.error(code=403, message="您不是该对话的参与者")

    messages = await service.get_messages(
        conversation_id=conversation_id,
        user_id=user.id,
        before_id=before_id,
        limit=limit,
    )
    return UnifiedResponse.success(data=messages)


@router.put("/conversations/{conversation_id}/read")
async def mark_as_read(
    conversation_id: str,
    user: User = Depends(require_permission(Permission.USE_CHAT)),
    db: AsyncSession = Depends(get_db),
):
    """标记对话为已读"""
    service = IMService(db)

    if not await service.is_participant(conversation_id, user.id):
        return UnifiedResponse.error(code=403, message="您不是该对话的参与者")

    await service.mark_as_read(conversation_id, user.id)
    return UnifiedResponse.success(message="已标记为已读")


# ===== WebSocket 端点 =====


@router.websocket("/ws")
async def im_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="JWT Token"),
    db: AsyncSession = Depends(get_db),
):
    """
    IM WebSocket 连接

    消息协议（客户端 → 服务端）:
    - { type: "message", conversation_id, content, message_type?, reply_to_id? }
    - { type: "typing", conversation_id }
    - { type: "read_receipt", conversation_id }
    - { type: "recall", message_id }

    消息协议（服务端 → 客户端）:
    - { type: "message", message: {...} }
    - { type: "typing", conversation_id, user_id }
    - { type: "read_receipt", conversation_id, user_id }
    - { type: "recall", message_id, conversation_id }
    - { type: "notification", notification: {...} }
    - { type: "error", message: "..." }
    """
    # 验证 JWT
    user_id = verify_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="认证失败")
        return

    # 注册连接
    await im_manager.connect(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                await _handle_message(db, user_id, data, websocket)
            elif msg_type == "typing":
                await _handle_typing(db, user_id, data)
            elif msg_type == "read_receipt":
                await _handle_read_receipt(db, user_id, data)
            elif msg_type == "recall":
                await _handle_recall(db, user_id, data)
            else:
                await websocket.send_json(
                    {"type": "error", "message": f"未知消息类型: {msg_type}"}
                )

    except WebSocketDisconnect:
        logger.info(f"[IM WS] 用户 {user_id} 断开连接")
    except Exception as e:
        logger.error(f"[IM WS] 用户 {user_id} 异常: {e}")
    finally:
        await im_manager.disconnect(user_id, websocket)


# ===== WebSocket 消息处理 =====


async def _handle_message(
    db: AsyncSession, sender_id: str, data: dict, websocket: WebSocket
) -> None:
    """处理发送消息"""
    conversation_id = data.get("conversation_id")
    content = data.get("content", "").strip()
    message_type = data.get("message_type", "text")
    reply_to_id = data.get("reply_to_id")
    metadata_ = data.get("metadata_")

    if not conversation_id or not content:
        await websocket.send_json(
            {"type": "error", "message": "conversation_id 和 content 为必填项"}
        )
        return

    # 消息内容长度限制
    if len(content) > MAX_CONTENT_LENGTH:
        await websocket.send_json(
            {"type": "error", "message": f"消息内容超过最大长度限制（{MAX_CONTENT_LENGTH} 字符）"}
        )
        return

    # 消息类型白名单验证
    if message_type not in ALLOWED_MESSAGE_TYPES:
        await websocket.send_json(
            {"type": "error", "message": f"不支持的消息类型: {message_type}，允许: {', '.join(sorted(ALLOWED_MESSAGE_TYPES))}"}
        )
        return

    service = IMService(db)
    msg = await service.send_message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        content=content,
        message_type=message_type,
        reply_to_id=reply_to_id,
        metadata_=metadata_,
    )

    if not msg:
        await websocket.send_json(
            {"type": "error", "message": "发送失败，您可能不是该对话的参与者"}
        )
        return

    # 广播给对话所有参与者（包括发送者的其他设备）
    participant_ids = await service.get_participant_ids(conversation_id)
    await im_manager.broadcast_to_conversation(
        participant_ids=participant_ids,
        message={"type": "message", "message": msg},
    )

    # AI 旁听钩子：异步触发，不阻塞消息流
    if message_type == "text":
        from src.services.meeting_assistant_service import meeting_assistant
        asyncio.create_task(
            meeting_assistant.on_message(
                conversation_id=conversation_id,
                sender_id=sender_id,
                content=content,
            )
        )


async def _handle_typing(
    db: AsyncSession, user_id: str, data: dict
) -> None:
    """处理正在输入状态"""
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return

    service = IMService(db)
    participant_ids = await service.get_participant_ids(conversation_id)
    await im_manager.broadcast_to_conversation(
        participant_ids=participant_ids,
        message={
            "type": "typing",
            "conversation_id": conversation_id,
            "user_id": user_id,
        },
        exclude_user=user_id,
    )


async def _handle_read_receipt(
    db: AsyncSession, user_id: str, data: dict
) -> None:
    """处理已读回执"""
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return

    service = IMService(db)
    await service.mark_as_read(conversation_id, user_id)

    participant_ids = await service.get_participant_ids(conversation_id)
    await im_manager.broadcast_to_conversation(
        participant_ids=participant_ids,
        message={
            "type": "read_receipt",
            "conversation_id": conversation_id,
            "user_id": user_id,
        },
        exclude_user=user_id,
    )


async def _handle_recall(
    db: AsyncSession, user_id: str, data: dict
) -> None:
    """处理撤回消息"""
    message_id = data.get("message_id")
    if not message_id:
        return

    service = IMService(db)
    recalled = await service.recall_message(message_id, user_id)

    if recalled:
        conversation_id = recalled["conversation_id"]
        participant_ids = await service.get_participant_ids(conversation_id)
        await im_manager.broadcast_to_conversation(
            participant_ids=participant_ids,
            message={
                "type": "recall",
                "message_id": message_id,
                "conversation_id": conversation_id,
            },
        )
