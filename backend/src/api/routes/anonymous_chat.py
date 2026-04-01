# -*- coding: utf-8 -*-
"""
匿名聊天室 WebSocket API

用户和律师在匹配后通过匿名聊天室沟通，双方同意后才揭示身份信息。

路由：
- POST   /api/v1/anonymous-chat/rooms              创建聊天室（返回 room_id + 双方临时 token）
- GET    /api/v1/anonymous-chat/rooms/{room_id}     获取聊天室信息
- POST   /api/v1/anonymous-chat/rooms/{room_id}/reveal  双方确认揭示身份
- WS     /api/v1/anonymous-chat/ws/{room_id}?token={temp_token}  WebSocket 聊天连接
"""

import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query, Request
from src.core.deps import rate_limit
from pydantic import BaseModel, Field
from loguru import logger

router = APIRouter(prefix="/anonymous-chat", tags=["匿名聊天"])


# ===== 内存存储（后续可迁移至 Redis） =====

class ChatMessage(BaseModel):
    id: str
    sender: str  # "user" | "lawyer"
    content: str
    timestamp: str
    type: str = "text"  # "text" | "system"


class ChatRoom(BaseModel):
    room_id: str
    consultation_id: Optional[str] = None
    user_token: str
    lawyer_token: str
    user_name: Optional[str] = None
    lawyer_name: Optional[str] = None
    user_contact: Optional[str] = None
    lawyer_contact: Optional[str] = None
    messages: list[ChatMessage] = []
    user_reveal: bool = False
    lawyer_reveal: bool = False
    revealed: bool = False
    created_at: str
    closed: bool = False


# 房间存储: room_id -> ChatRoom
rooms: dict[str, ChatRoom] = {}

# 活跃 WebSocket 连接: room_id -> {role: WebSocket}
active_connections: dict[str, dict[str, WebSocket]] = {}


# ===== 请求/响应模型 =====

class CreateRoomRequest(BaseModel):
    """创建匿名聊天室"""
    consultation_id: Optional[str] = Field(None, description="关联咨询 ID")
    user_name: Optional[str] = Field(None, description="用户真实姓名（揭示后展示）")
    lawyer_name: Optional[str] = Field(None, description="律师真实姓名（揭示后展示）")
    user_contact: Optional[str] = Field(None, description="用户联系方式（揭示后展示）")
    lawyer_contact: Optional[str] = Field(None, description="律师联系方式（揭示后展示）")


class CreateRoomResponse(BaseModel):
    room_id: str
    user_token: str
    lawyer_token: str
    created_at: str
    message: str


class RoomInfoResponse(BaseModel):
    room_id: str
    consultation_id: Optional[str]
    revealed: bool
    message_count: int
    created_at: str
    closed: bool
    # 揭示后才返回身份信息
    user_name: Optional[str] = None
    lawyer_name: Optional[str] = None
    user_contact: Optional[str] = None
    lawyer_contact: Optional[str] = None


# ===== 辅助函数 =====

def _get_room(room_id: str) -> ChatRoom:
    room = rooms.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="聊天室不存在")
    return room


def _get_role_by_token(room: ChatRoom, token: str) -> Optional[str]:
    if token == room.user_token:
        return "user"
    elif token == room.lawyer_token:
        return "lawyer"
    return None


def _create_system_message(content: str) -> ChatMessage:
    return ChatMessage(
        id=str(uuid.uuid4()),
        sender="system",
        content=content,
        timestamp=datetime.now(timezone.utc).isoformat(),
        type="system",
    )


async def _broadcast_to_room(room_id: str, message: dict):
    """向房间内所有连接广播消息"""
    conns = active_connections.get(room_id, {})
    disconnected = []
    for role, ws in conns.items():
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(role)
    for role in disconnected:
        conns.pop(role, None)


# ===== REST API =====

@router.post("/rooms", response_model=CreateRoomResponse)
async def create_room(
    req: CreateRoomRequest,
    request: Request,
    _: None = Depends(rate_limit(limit=10, window=300, endpoint="anon_chat_create", by_user=False)),
):
    """创建匿名聊天室，返回房间 ID 和双方临时 token"""
    room_id = str(uuid.uuid4())[:8]
    user_token = f"u-{uuid.uuid4().hex[:16]}"
    lawyer_token = f"l-{uuid.uuid4().hex[:16]}"

    room = ChatRoom(
        room_id=room_id,
        consultation_id=req.consultation_id,
        user_token=user_token,
        lawyer_token=lawyer_token,
        user_name=req.user_name,
        lawyer_name=req.lawyer_name,
        user_contact=req.user_contact,
        lawyer_contact=req.lawyer_contact,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    # 添加系统欢迎消息
    welcome = _create_system_message("匿名咨询室已开启，双方身份信息已隐藏。您可以安全地沟通法律问题。")
    room.messages.append(welcome)

    rooms[room_id] = room
    logger.info(f"匿名聊天室创建: {room_id}, 关联咨询: {req.consultation_id}")

    return CreateRoomResponse(
        room_id=room_id,
        user_token=user_token,
        lawyer_token=lawyer_token,
        created_at=room.created_at,
        message="匿名聊天室已创建",
    )


@router.get("/rooms/{room_id}", response_model=RoomInfoResponse)
async def get_room_info(room_id: str, token: str = Query(..., description="临时 token")):
    """获取聊天室信息（需要提供有效 token）"""
    room = _get_room(room_id)
    role = _get_role_by_token(room, token)
    if not role:
        raise HTTPException(status_code=403, detail="无效的 token")

    resp = RoomInfoResponse(
        room_id=room.room_id,
        consultation_id=room.consultation_id,
        revealed=room.revealed,
        message_count=len(room.messages),
        created_at=room.created_at,
        closed=room.closed,
    )

    # 揭示后返回身份信息
    if room.revealed:
        resp.user_name = room.user_name
        resp.lawyer_name = room.lawyer_name
        resp.user_contact = room.user_contact
        resp.lawyer_contact = room.lawyer_contact

    return resp


@router.post("/rooms/{room_id}/reveal")
async def reveal_identity(room_id: str, token: str = Query(..., description="临时 token")):
    """确认揭示身份 — 双方都确认后身份信息解除匿名"""
    room = _get_room(room_id)
    role = _get_role_by_token(room, token)
    if not role:
        raise HTTPException(status_code=403, detail="无效的 token")

    if room.revealed:
        return {"message": "身份已揭示", "revealed": True}

    if role == "user":
        room.user_reveal = True
    else:
        room.lawyer_reveal = True

    # 检查是否双方都确认
    if room.user_reveal and room.lawyer_reveal:
        room.revealed = True
        # 发送系统消息
        sys_msg = _create_system_message("双方已确认合作意向，身份信息已解除匿名")
        room.messages.append(sys_msg)

        # 广播揭示消息
        await _broadcast_to_room(room_id, {
            "type": "reveal",
            "message": sys_msg.model_dump(),
            "user_name": room.user_name,
            "lawyer_name": room.lawyer_name,
            "user_contact": room.user_contact,
            "lawyer_contact": room.lawyer_contact,
        })

        logger.info(f"聊天室 {room_id} 双方身份已揭示")
        return {
            "message": "双方已确认，身份信息已揭示",
            "revealed": True,
            "user_name": room.user_name,
            "lawyer_name": room.lawyer_name,
            "user_contact": room.user_contact,
            "lawyer_contact": room.lawyer_contact,
        }

    # 只有一方确认
    waiting_for = "律师" if role == "user" else "用户"
    notify_msg = _create_system_message(f"{'用户' if role == 'user' else '律师'}已同意揭示身份，等待{waiting_for}确认")
    room.messages.append(notify_msg)
    await _broadcast_to_room(room_id, {
        "type": "system",
        "message": notify_msg.model_dump(),
    })

    return {"message": f"已确认，等待{waiting_for}同意", "revealed": False}


# ===== WebSocket 端点 =====

@router.websocket("/ws/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: str, token: str = Query(...)):
    """匿名聊天 WebSocket 连接"""
    # 验证房间和 token
    room = rooms.get(room_id)
    if not room:
        await websocket.close(code=4004, reason="聊天室不存在")
        return

    role = _get_role_by_token(room, token)
    if not role:
        await websocket.close(code=4003, reason="无效的 token")
        return

    if room.closed:
        await websocket.close(code=4001, reason="聊天室已关闭")
        return

    await websocket.accept()

    # 注册连接
    if room_id not in active_connections:
        active_connections[room_id] = {}
    active_connections[room_id][role] = websocket

    role_label = "用户" if role == "user" else "律师"
    logger.info(f"WebSocket 连接: {role_label} 进入聊天室 {room_id}")

    # 发送历史消息
    await websocket.send_json({
        "type": "history",
        "messages": [m.model_dump() for m in room.messages],
        "role": role,
        "revealed": room.revealed,
    })

    # 通知对方上线
    join_msg = _create_system_message(f"{role_label}已加入聊天")
    room.messages.append(join_msg)
    await _broadcast_to_room(room_id, {
        "type": "system",
        "message": join_msg.model_dump(),
    })

    MAX_MESSAGE_LENGTH = 4096  # 单条消息最大长度
    MAX_MESSAGES_PER_MINUTE = 30  # 每分钟最大消息数
    _msg_timestamps: list = []

    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content", "").strip()
            if not content:
                continue

            # 消息长度限制
            if len(content) > MAX_MESSAGE_LENGTH:
                await websocket.send_json({
                    "type": "error",
                    "message": f"消息长度不能超过 {MAX_MESSAGE_LENGTH} 字符",
                })
                continue

            # 简易频率限制
            now = datetime.now(timezone.utc)
            _msg_timestamps.append(now)
            _msg_timestamps[:] = [t for t in _msg_timestamps if (now - t).total_seconds() < 60]
            if len(_msg_timestamps) > MAX_MESSAGES_PER_MINUTE:
                await websocket.send_json({
                    "type": "error",
                    "message": "发送过于频繁，请稍后再试",
                })
                continue

            # XSS 过滤：转义 HTML 特殊字符
            import html as html_mod
            content = html_mod.escape(content)

            # 创建消息
            msg = ChatMessage(
                id=str(uuid.uuid4()),
                sender=role,
                content=content,
                timestamp=now.isoformat(),
                type="text",
            )
            room.messages.append(msg)

            # 广播给房间内所有人
            await _broadcast_to_room(room_id, {
                "type": "message",
                "message": msg.model_dump(),
            })

            # AI 旁听钩子
            from src.services.meeting_assistant_service import meeting_assistant
            asyncio.create_task(
                meeting_assistant.on_message(
                    conversation_id=room_id,
                    sender_id=role,
                    content=content,
                    sender_name=role,
                )
            )

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开: {role_label} 离开聊天室 {room_id}")
        # 移除连接
        conns = active_connections.get(room_id, {})
        conns.pop(role, None)
        if not conns:
            active_connections.pop(room_id, None)

        # 通知对方离线
        leave_msg = _create_system_message(f"{role_label}已离开聊天")
        room.messages.append(leave_msg)
        await _broadcast_to_room(room_id, {
            "type": "system",
            "message": leave_msg.model_dump(),
        })
    except Exception as e:
        logger.error(f"WebSocket 错误: {room_id} - {e}")
        conns = active_connections.get(room_id, {})
        conns.pop(role, None)
