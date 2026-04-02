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
from src.services.rtc_service import rtc_service

router = APIRouter()


class CreateRoomRequest(BaseModel):
    conversation_id: str
    call_type: str = "voice"  # voice | video


class CreateRoomResponse(BaseModel):
    room_name: str
    token: str
    livekit_url: str


@router.post("/rooms", response_model=UnifiedResponse)
async def create_room(
    req: CreateRoomRequest,
    user: User = Depends(get_current_user_required),
):
    """创建通话房间并返回加入 Token"""
    if not rtc_service.is_available():
        raise HTTPException(status_code=503, detail="音视频服务未配置")

    if req.call_type not in ("voice", "video"):
        raise HTTPException(status_code=400, detail="call_type 必须是 voice 或 video")

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
):
    """获取加入已有房间的 Token"""
    if not rtc_service.is_available():
        raise HTTPException(status_code=503, detail="音视频服务未配置")

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
):
    """结束通话（删除房间）"""
    if not rtc_service.is_available():
        raise HTTPException(status_code=503, detail="音视频服务未配置")

    success = await rtc_service.delete_room(room_name)
    if not success:
        raise HTTPException(status_code=500, detail="结束通话失败")

    return UnifiedResponse.success(message="通话已结束")


@router.get("/rooms", response_model=UnifiedResponse)
async def list_active_rooms(
    user: User = Depends(get_current_user_required),
):
    """列出活跃的通话房间"""
    if not rtc_service.is_available():
        return UnifiedResponse.success(data={"rooms": [], "available": False})

    rooms = await rtc_service.list_rooms()
    return UnifiedResponse.success(data={"rooms": rooms, "available": True})
