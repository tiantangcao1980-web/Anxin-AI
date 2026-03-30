
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import get_current_user_required, get_db
from src.models.user import User
from src.services.notification_service import NotificationService

router = APIRouter()

# ============================================================
# Schemas - 通知
# ============================================================

class NotificationSchema(BaseModel):
    id: str
    type: str
    title: str
    message: str
    is_read: bool
    related_link: Optional[str] = None
    event_type: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class NotificationResponse(BaseModel):
    data: List[NotificationSchema]
    total: int

# ============================================================
# Schemas - 通知偏好
# ============================================================

class PreferenceItem(BaseModel):
    channel: str       # site, email, wechat, sms
    event_type: str    # approval, chat, case, system, contract, lawyer
    enabled: bool

    model_config = ConfigDict(from_attributes=True)

class PreferenceSchema(BaseModel):
    id: str
    channel: str
    event_type: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PreferencesUpdateRequest(BaseModel):
    preferences: List[PreferenceItem]

class PreferencesResponse(BaseModel):
    data: List[PreferenceSchema]

# ============================================================
# Routes - 通知
# ============================================================

@router.get("/", response_model=NotificationResponse)
async def get_notifications(
    limit: int = 50,
    unread_only: bool = False,
    event_type: Optional[str] = None,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户的通知列表，支持按事件类型筛选"""
    notifications = await NotificationService.get_user_notifications(
        db,
        current_user.id,
        limit=limit,
        unread_only=unread_only,
        event_type=event_type,
    )

    return NotificationResponse(
        data=notifications,
        total=len(notifications)
    )


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户未读通知总数（轻量接口）"""
    count = await NotificationService.get_unread_count(db, current_user.id)
    return {"count": count}

@router.post("/{notification_id}/read", response_model=NotificationSchema)
async def mark_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """
    标记通知为已读
    """
    notification = await NotificationService.mark_as_read(db, notification_id, current_user.id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    return notification

@router.post("/read-all", response_model=dict)
async def mark_all_as_read(
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """
    标记所有通知为已读
    """
    count = await NotificationService.mark_all_as_read(db, current_user.id)
    return {"message": "success", "count": count}

@router.delete("/{notification_id}", response_model=dict)
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """
    删除通知
    """
    success = await NotificationService.delete_notification(db, notification_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    return {"message": "success"}

# ============================================================
# Routes - 通知偏好
# ============================================================

@router.get("/preferences", response_model=PreferencesResponse)
async def get_preferences(
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的通知偏好设置
    """
    preferences = await NotificationService.get_user_preferences(db, current_user.id)
    return PreferencesResponse(data=preferences)


@router.put("/preferences", response_model=PreferencesResponse)
async def update_preferences(
    body: PreferencesUpdateRequest,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """
    批量更新用户通知偏好设置

    请求体示例：
    {
        "preferences": [
            {"channel": "email", "event_type": "approval", "enabled": true},
            {"channel": "wechat", "event_type": "case", "enabled": false}
        ]
    }
    """
    prefs = [p.model_dump() for p in body.preferences]
    updated = await NotificationService.upsert_preferences(db, current_user.id, prefs)
    return PreferencesResponse(data=updated)
