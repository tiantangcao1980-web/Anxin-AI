from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from src.services.oa_integration_service import oa_service, OAProviderType

router = APIRouter()

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
async def send_oa_notification(req: NotificationRequest):
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
async def create_oa_approval(req: ApprovalRequest):
    """
    在OA系统中创建审批流程（如合同审批、用印申请）
    """
    instance_id = await oa_service.initiate_approval(
        req.title, req.details, req.initiator_id, req.provider
    )
    return {"status": "success", "instance_id": instance_id}

@router.post("/sync/users", summary="同步OA用户")
async def sync_oa_users(req: SyncRequest):
    """
    从OA系统同步用户和组织架构
    """
    result = await oa_service.sync_org_structure(req.provider)
    return {"status": "success", "data": result}

@router.post("/webhook/{provider}", summary="OA回调接收")
async def oa_webhook(provider: str, payload: Dict[str, Any]):
    """
    接收OA系统的回调通知（如审批状态变更）
    """
    # 这里可以根据 provider 分发处理逻辑
    # 例如更新本地数据库中的合同审批状态
    return {"status": "received"}
