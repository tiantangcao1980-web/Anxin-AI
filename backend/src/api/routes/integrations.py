from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from src.core.config import settings
from src.core.deps import UserRole, get_current_user_required, require_role
from src.models.user import User
from src.services.oa_integration_service import OAProviderConfigError, oa_service

router = APIRouter()


# ===== 集成 API 密钥校验 =====


async def verify_integration_key(
    x_integration_key: str = Header(..., alias="X-Integration-Key"),
) -> None:
    """校验集成 API 密钥（用于外部系统回调和 API 调用）"""
    expected_key = getattr(settings, "INTEGRATION_API_KEY", None)
    if not expected_key:
        # 未配置集成密钥时拒绝所有请求
        raise HTTPException(status_code=503, detail="集成服务未配置")
    if x_integration_key != expected_key:
        raise HTTPException(status_code=401, detail="无效的集成密钥")


class NotificationRequest(BaseModel):
    user_id: str | None = None
    title: str
    content: str
    provider: str | None = None  # feishu, dingtalk, wecom


class ApprovalRequest(BaseModel):
    title: str
    details: dict[str, Any]
    initiator_id: str | None = None
    provider: str | None = None


class SyncRequest(BaseModel):
    provider: str | None = None


@router.post("/notify", summary="发送OA通知")
async def send_oa_notification(
    req: NotificationRequest,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """
    向当前登录用户在 OA 平台的账户发送通知消息。

    为避免伪造目标用户，服务端不信任客户端传入的 user_id。
    """
    target_user_id = str(user.id)

    try:
        success = await oa_service.send_notification(
            target_user_id, req.title, req.content, req.provider
        )
    except OAProviderConfigError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send notification")
    return {"status": "success", "message": "Notification sent"}


@router.post("/approval/create", summary="发起OA审批")
async def create_oa_approval(
    req: ApprovalRequest,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """
    在OA系统中创建审批流程（如合同审批、用印申请）
    """
    try:
        instance_id = await oa_service.initiate_approval(
            req.title, req.details, str(user.id), req.provider
        )
    except OAProviderConfigError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {"status": "success", "instance_id": instance_id}


@router.post("/sync/users", summary="同步OA用户")
async def sync_oa_users(
    req: SyncRequest,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)),
) -> dict[str, Any]:
    """
    从OA系统同步用户和组织架构
    """
    try:
        result = await oa_service.sync_org_structure(req.provider)
    except OAProviderConfigError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return {"status": "success", "data": result}


@router.post("/webhook/{provider}", summary="OA回调接收")
async def oa_webhook(
    provider: str,
    payload: dict[str, Any],
    _: None = Depends(verify_integration_key),
) -> dict[str, str]:
    """
    接收OA系统的回调通知（如审批状态变更）
    需要通过 X-Integration-Key 头部验证密钥
    """
    return {"status": "received"}
