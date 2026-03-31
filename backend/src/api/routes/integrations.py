from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from src.core.config import settings
from src.core.deps import get_current_user_required
from src.services.oa_integration_service import oa_service, OAProviderType
from src.models.user import User

router = APIRouter()


# ===== 集成 API 密钥校验 =====

async def verify_integration_key(
    x_integration_key: str = Header(..., alias="X-Integration-Key"),
):
    """校验集成 API 密钥（用于外部系统回调和 API 调用）"""
    expected_key = getattr(settings, "INTEGRATION_API_KEY", None)
    if not expected_key:
        # 未配置集成密钥时拒绝所有请求
        raise HTTPException(status_code=503, detail="集成服务未配置")
    if x_integration_key != expected_key:
        raise HTTPException(status_code=401, detail="无效的集成密钥")


class NotificationRequest(BaseModel):
    user_id: str
    title: str
    content: str
    provider: Optional[str] = None # feishu, dingtalk, wecom

class ApprovalRequest(BaseModel):
    title: str
    details: Dict[str, Any]
    initiator_id: str
    provider: Optional[str] = None

class SyncRequest(BaseModel):
    provider: Optional[str] = None

@router.post("/notify", summary="发送OA通知")
async def send_oa_notification(
    req: NotificationRequest,
    user: User = Depends(get_current_user_required),
):
    """
    向指定的OA平台发送通知消息
    """
    success = await oa_service.send_notification(
        req.user_id, req.title, req.content, req.provider
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send notification")
    return {"status": "success", "message": "Notification sent"}

@router.post("/approval/create", summary="发起OA审批")
async def create_oa_approval(
    req: ApprovalRequest,
    user: User = Depends(get_current_user_required),
):
    """
    在OA系统中创建审批流程（如合同审批、用印申请）
    """
    instance_id = await oa_service.initiate_approval(
        req.title, req.details, req.initiator_id, req.provider
    )
    return {"status": "success", "instance_id": instance_id}

@router.post("/sync/users", summary="同步OA用户")
async def sync_oa_users(
    req: SyncRequest,
    user: User = Depends(get_current_user_required),
):
    """
    从OA系统同步用户和组织架构
    """
    result = await oa_service.sync_org_structure(req.provider)
    return {"status": "success", "data": result}

@router.post("/webhook/{provider}", summary="OA回调接收")
async def oa_webhook(
    provider: str,
    payload: Dict[str, Any],
    _: None = Depends(verify_integration_key),
):
    """
    接收OA系统的回调通知（如审批状态变更）
    需要通过 X-Integration-Key 头部验证密钥
    """
    return {"status": "received"}
