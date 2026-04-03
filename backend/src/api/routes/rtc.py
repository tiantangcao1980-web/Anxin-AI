# -*- coding: utf-8 -*-
"""音视频通话 (RTC) API 路由"""

import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.core.responses import UnifiedResponse
from src.models.user import User
from src.services.im_service import IMService
from src.services.rtc_service import rtc_service

router = APIRouter()


class CreateRoomRequest(BaseModel):
    conversation_id: str
    call_type: str = "voice"  # voice | video


class CreateRoomResponse(BaseModel):
    room_name: str
    token: str
    livekit_url: str


def _extract_conversation_id(room_name: str) -> Optional[str]:
    prefix = "call_"
    if not room_name.startswith(prefix):
        return None
    try:
        conversation_id, _ = room_name[len(prefix):].rsplit("_", 1)
    except ValueError:
        return None
    return conversation_id or None


async def _ensure_rtc_access(db: AsyncSession, user: User, conversation_id: str) -> None:
    if user.role in {"super_admin", "admin"}:
        return
    service = IMService(db)
    if not await service.is_participant(conversation_id, str(user.id)):
        raise HTTPException(status_code=403, detail="您不是该会话的参与者")


@router.post("/rooms", response_model=UnifiedResponse)
async def create_room(
    req: CreateRoomRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """创建通话房间并返回加入 Token"""
    if not rtc_service.is_available():
        raise HTTPException(status_code=503, detail="音视频服务未配置")

    if req.call_type not in ("voice", "video"):
        raise HTTPException(status_code=400, detail="call_type 必须是 voice 或 video")

    await _ensure_rtc_access(db, user, req.conversation_id)

    # 生成房间名：call_{conversation_id}_{timestamp}
    room_name = f"call_{req.conversation_id}_{int(time.time())}"

    # 创建房间
    room = await rtc_service.create_room(room_name)
    if not room:
        raise HTTPException(status_code=500, detail="创建通话房间失败")

    # 生成 Token
    token = rtc_service.generate_token(
        room_name=room_name,
        user_id=str(user.id),
        user_name=user.name,
    )
    if not token:
        raise HTTPException(status_code=500, detail="生成通话 Token 失败")

    from src.core.config import settings
    return UnifiedResponse.success(
        data={
            "room_name": room_name,
            "token": token,
            "livekit_url": settings.LIVEKIT_URL,
            "call_type": req.call_type,
            "conversation_id": req.conversation_id,
        }
    )


@router.get("/rooms/{room_name}/token", response_model=UnifiedResponse)
async def get_room_token(
    room_name: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """获取加入已有房间的 Token"""
    if not rtc_service.is_available():
        raise HTTPException(status_code=503, detail="音视频服务未配置")

    conversation_id = _extract_conversation_id(room_name)
    if not conversation_id:
        raise HTTPException(status_code=400, detail="无效的房间名")
    await _ensure_rtc_access(db, user, conversation_id)

    token = rtc_service.generate_token(
        room_name=room_name,
        user_id=str(user.id),
        user_name=user.name,
    )
    if not token:
        raise HTTPException(status_code=500, detail="生成 Token 失败")

    from src.core.config import settings
    return UnifiedResponse.success(
        data={
            "room_name": room_name,
            "token": token,
            "livekit_url": settings.LIVEKIT_URL,
        }
    )


@router.delete("/rooms/{room_name}", response_model=UnifiedResponse)
async def end_call(
    room_name: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """结束通话（删除房间）"""
    if not rtc_service.is_available():
        raise HTTPException(status_code=503, detail="音视频服务未配置")

    conversation_id = _extract_conversation_id(room_name)
    if not conversation_id:
        raise HTTPException(status_code=400, detail="无效的房间名")
    await _ensure_rtc_access(db, user, conversation_id)

    success = await rtc_service.delete_room(room_name)
    if not success:
        raise HTTPException(status_code=500, detail="结束通话失败")

    return UnifiedResponse.success(message="通话已结束")


@router.get("/rooms", response_model=UnifiedResponse)
async def list_active_rooms(
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """列出活跃的通话房间"""
    if not rtc_service.is_available():
        return UnifiedResponse.success(data={"rooms": [], "available": False})

    rooms = await rtc_service.list_rooms()
    if user.role in {"super_admin", "admin"}:
        return UnifiedResponse.success(data={"rooms": rooms, "available": True})

    service = IMService(db)
    visible_rooms = []
    for room in rooms:
        conversation_id = _extract_conversation_id(room.get("name", ""))
        if not conversation_id:
            continue
        if await service.is_participant(conversation_id, str(user.id)):
            visible_rooms.append(room)
    return UnifiedResponse.success(data={"rooms": visible_rooms, "available": True})
