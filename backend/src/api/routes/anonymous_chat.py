"""
匿名聊天室 WebSocket API

用户和律师在匹配后通过匿名聊天室沟通，双方同意后才揭示身份信息。

路由：
- POST   /api/v1/anonymous-chat/rooms              用户创建聊天室（要登录 + 必须是 consultation 所有者，仅返回 user_token）
- POST   /api/v1/anonymous-chat/rooms/{room_id}/lawyer-join  律师认领并获取 lawyer_token（要登录 + 必须是 consultation.matched_lawyer）
- GET    /api/v1/anonymous-chat/rooms/{room_id}/my-token     重新获取自己的 token（要登录 + 必须是 user_id 或 matched_lawyer_id）
- GET    /api/v1/anonymous-chat/rooms/{room_id}     获取聊天室信息
- POST   /api/v1/anonymous-chat/rooms/{room_id}/reveal  双方确认揭示身份
- WS     /api/v1/anonymous-chat/ws/{room_id}?token={temp_token}  WebSocket 聊天连接

V2 安全修复（PROJECT_STATUS S7）：
  历史：POST /rooms 任意客户端无身份校验可调，一次返回 user_token + lawyer_token，
        允许单方伪造双边身份。
  修复：拆分为"用户发起"+"律师认领"+"各自重取" 三个接口，每个都强制身份归属校验。
        前端单一调用方仅消费 user_token；lawyer_token 改为律师走 lawyer-join 单独获取。
"""

import asyncio
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required, rate_limit
from src.models.user import User

if TYPE_CHECKING:
    from src.models.lawyer_matching import Consultation

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
    consultation_id: str | None = None
    user_token: str
    lawyer_token: str
    user_name: str | None = None
    lawyer_name: str | None = None
    user_contact: str | None = None
    lawyer_contact: str | None = None
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

    consultation_id: str | None = Field(None, description="关联咨询 ID")
    user_name: str | None = Field(None, description="用户真实姓名（揭示后展示）")
    lawyer_name: str | None = Field(None, description="律师真实姓名（揭示后展示）")
    user_contact: str | None = Field(None, description="用户联系方式（揭示后展示）")
    lawyer_contact: str | None = Field(None, description="律师联系方式（揭示后展示）")


class CreateRoomResponse(BaseModel):
    """V2 安全修复：仅返回调用者（用户）自己的 token。律师走 lawyer-join 获取自己的 token。"""

    room_id: str
    user_token: str
    created_at: str
    message: str


class LawyerJoinResponse(BaseModel):
    """律师认领房间后返回 lawyer_token"""

    room_id: str
    lawyer_token: str
    message: str


class MyTokenResponse(BaseModel):
    """各方重新获取自己的 token（用于客户端丢失场景）"""

    room_id: str
    role: str  # "user" | "lawyer"
    token: str


class RoomInfoResponse(BaseModel):
    room_id: str
    consultation_id: str | None
    revealed: bool
    message_count: int
    created_at: str
    closed: bool
    # 揭示后才返回身份信息
    user_name: str | None = None
    lawyer_name: str | None = None
    user_contact: str | None = None
    lawyer_contact: str | None = None


# ===== 辅助函数 =====


def _get_room(room_id: str) -> ChatRoom:
    room = rooms.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="聊天室不存在")
    return room


def _get_role_by_token(room: ChatRoom, token: str) -> str | None:
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
        timestamp=datetime.now(UTC).isoformat(),
        type="system",
    )


async def _broadcast_to_room(room_id: str, message: dict[str, Any]) -> None:
    """向房间内所有连接广播消息"""
    conns = active_connections.get(room_id, {})
    disconnected: list[str] = []
    for role, ws in conns.items():
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(role)
    for role in disconnected:
        conns.pop(role, None)


# ===== REST API =====


async def _get_consultation_or_403(
    db: AsyncSession, consultation_id: str, user: User
) -> "Consultation":
    """读取 consultation 并校验调用者是否为参与方（user 或 matched_lawyer）"""
    from src.models.lawyer_matching import Consultation

    result = await db.execute(select(Consultation).where(Consultation.id == consultation_id))
    consultation = result.scalar_one_or_none()
    if not consultation:
        raise HTTPException(status_code=404, detail="咨询不存在")
    return consultation


@router.post("/rooms", response_model=CreateRoomResponse)
async def create_room(
    req: CreateRoomRequest,
    request: Request,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit(limit=10, window=300, endpoint="anon_chat_create", by_user=True)),
) -> CreateRoomResponse:
    """
    用户发起创建匿名聊天室。

    V2 安全修复：
    - 必须登录（去掉无身份的 by_user=False 限流）
    - 若传 consultation_id，则必须是 consultation 的所有者（user_id 匹配）
    - 仅返回 user_token；lawyer_token 由律师走 /rooms/{id}/lawyer-join 获取
    """
    # 校验 consultation 归属（如有）
    if req.consultation_id:
        consultation = await _get_consultation_or_403(db, req.consultation_id, user)
        if consultation.user_id != user.id:
            raise HTTPException(status_code=403, detail="无权为他人的咨询创建聊天室")

    room_id = str(uuid.uuid4())[:8]
    user_token = f"u-{uuid.uuid4().hex[:16]}"
    lawyer_token = f"l-{uuid.uuid4().hex[:16]}"

    room = ChatRoom(
        room_id=room_id,
        consultation_id=req.consultation_id,
        user_token=user_token,
        lawyer_token=lawyer_token,  # 内部存储，但不在响应中返回给用户
        user_name=req.user_name,
        lawyer_name=req.lawyer_name,
        user_contact=req.user_contact,
        lawyer_contact=req.lawyer_contact,
        created_at=datetime.now(UTC).isoformat(),
    )

    # 添加系统欢迎消息
    welcome = _create_system_message(
        "匿名咨询室已开启，双方身份信息已隐藏。您可以安全地沟通法律问题。"
    )
    room.messages.append(welcome)

    rooms[room_id] = room
    logger.info(
        f"匿名聊天室创建: room={room_id}, 创建人 user={user.id}, 关联咨询={req.consultation_id}"
    )

    return CreateRoomResponse(
        room_id=room_id,
        user_token=user_token,
        created_at=room.created_at,
        message="匿名聊天室已创建",
    )


@router.post("/rooms/{room_id}/lawyer-join", response_model=LawyerJoinResponse)
async def lawyer_join_room(
    room_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> LawyerJoinResponse:
    """
    律师认领并获取 lawyer_token。

    V2 安全修复：必须登录 + 必须是关联 consultation 的 matched_lawyer_id。
    无 consultation_id 的临时房间暂不支持律师认领。
    """
    room = _get_room(room_id)

    if not room.consultation_id:
        raise HTTPException(status_code=400, detail="房间未关联咨询，无法认领律师身份")

    consultation = await _get_consultation_or_403(db, room.consultation_id, user)
    if consultation.matched_lawyer_id != user.id:
        raise HTTPException(status_code=403, detail="您不是此咨询匹配的律师")

    logger.info(f"律师认领聊天室: room={room_id}, lawyer user={user.id}")
    return LawyerJoinResponse(
        room_id=room.room_id,
        lawyer_token=room.lawyer_token,
        message="已认领律师身份",
    )


@router.get("/rooms/{room_id}/my-token", response_model=MyTokenResponse)
async def get_my_token(
    room_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> MyTokenResponse:
    """
    重新获取自己的 token（客户端丢失场景）。

    根据登录用户与 consultation 的关系判定：
    - user_id 匹配 → 返回 user_token
    - matched_lawyer_id 匹配 → 返回 lawyer_token
    - 其他 → 403
    """
    room = _get_room(room_id)

    if not room.consultation_id:
        raise HTTPException(status_code=400, detail="房间未关联咨询，无法重取 token")

    consultation = await _get_consultation_or_403(db, room.consultation_id, user)
    if consultation.user_id == user.id:
        return MyTokenResponse(room_id=room.room_id, role="user", token=room.user_token)
    if consultation.matched_lawyer_id == user.id:
        return MyTokenResponse(room_id=room.room_id, role="lawyer", token=room.lawyer_token)
    raise HTTPException(status_code=403, detail="您不是该聊天室的参与方")


@router.get("/rooms/{room_id}", response_model=RoomInfoResponse)
async def get_room_info(
    room_id: str, token: str = Query(..., description="临时 token")
) -> RoomInfoResponse:
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
async def reveal_identity(
    room_id: str, token: str = Query(..., description="临时 token")
) -> dict[str, Any]:
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
        await _broadcast_to_room(
            room_id,
            {
                "type": "reveal",
                "message": sys_msg.model_dump(),
                "user_name": room.user_name,
                "lawyer_name": room.lawyer_name,
                "user_contact": room.user_contact,
                "lawyer_contact": room.lawyer_contact,
            },
        )

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
    notify_msg = _create_system_message(
        f"{'用户' if role == 'user' else '律师'}已同意揭示身份，等待{waiting_for}确认"
    )
    room.messages.append(notify_msg)
    await _broadcast_to_room(
        room_id,
        {
            "type": "system",
            "message": notify_msg.model_dump(),
        },
    )

    return {"message": f"已确认，等待{waiting_for}同意", "revealed": False}


# ===== WebSocket 端点 =====


@router.websocket("/ws/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: str, token: str = Query(...)) -> None:
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
    await websocket.send_json(
        {
            "type": "history",
            "messages": [m.model_dump() for m in room.messages],
            "role": role,
            "revealed": room.revealed,
        }
    )

    # 通知对方上线
    join_msg = _create_system_message(f"{role_label}已加入聊天")
    room.messages.append(join_msg)
    await _broadcast_to_room(
        room_id,
        {
            "type": "system",
            "message": join_msg.model_dump(),
        },
    )

    max_message_length = 4096  # 单条消息最大长度
    max_messages_per_minute = 30  # 每分钟最大消息数
    _msg_timestamps: list[datetime] = []

    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content", "").strip()
            if not content:
                continue

            # 消息长度限制
            if len(content) > max_message_length:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"消息长度不能超过 {max_message_length} 字符",
                    }
                )
                continue

            # 简易频率限制
            now = datetime.now(UTC)
            _msg_timestamps.append(now)
            _msg_timestamps[:] = [t for t in _msg_timestamps if (now - t).total_seconds() < 60]
            if len(_msg_timestamps) > max_messages_per_minute:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "发送过于频繁，请稍后再试",
                    }
                )
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
            await _broadcast_to_room(
                room_id,
                {
                    "type": "message",
                    "message": msg.model_dump(),
                },
            )

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
        await _broadcast_to_room(
            room_id,
            {
                "type": "system",
                "message": leave_msg.model_dump(),
            },
        )
    except Exception as e:
        logger.error(f"WebSocket 错误: {room_id} - {e}")
        conns = active_connections.get(room_id, {})
        conns.pop(role, None)
