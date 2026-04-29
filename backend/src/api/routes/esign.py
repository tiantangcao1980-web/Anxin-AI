# -*- coding: utf-8 -*-
"""
电子签章 API 路由

提供合同电子签署流程的创建、查询、签署链接获取和 Webhook 回调。
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from loguru import logger

from src.core.config import settings
from src.core.deps import get_current_user_required, get_current_user
from src.models.user import User
from src.services.esign_service import (
    get_esign_provider,
    SignerInfo,
    SignType,
    FlowStatus,
)
from src.services.webhook_security import WebhookSecurity

router = APIRouter()

# ========== 请求/响应模型 ==========


class SignerInput(BaseModel):
    """创建签署流程时的签署人输入"""
    name: str = Field(..., description="签署人姓名/企业名称")
    id_number: Optional[str] = Field(None, description="身份证号/统一社会信用代码")
    mobile: Optional[str] = Field(None, description="手机号码")
    email: Optional[str] = Field(None, description="邮箱")
    sign_type: str = Field(default="personal", description="签署类型: personal/company")
    sign_order: int = Field(default=0, description="签署顺序，0 表示不限顺序")


class CreateFlowRequest(BaseModel):
    """创建签署流程请求"""
    contract_id: str = Field(..., description="合同ID")
    title: str = Field(..., description="签署流程标题")
    signers: list[SignerInput] = Field(..., min_length=1, description="签署人列表")
    document_url: Optional[str] = Field(None, description="待签署文件URL")
    expire_hours: int = Field(default=72, ge=1, le=720, description="过期时间（小时）")


class FlowResponse(BaseModel):
    """签署流程响应"""
    flow_id: str
    contract_id: str
    status: str
    sign_urls: dict[str, str] = {}
    created_at: Optional[str] = None
    expires_at: Optional[str] = None


class FlowStatusResponse(BaseModel):
    """签署流程状态响应"""
    flow_id: str
    contract_id: str
    status: str
    signers: list[dict] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None


class SignUrlResponse(BaseModel):
    """签署链接响应"""
    flow_id: str
    signer_id: str
    sign_url: str


class WebhookPayload(BaseModel):
    """Webhook 回调载荷（通用格式，各提供商格式不同）"""
    flow_id: Optional[str] = None
    action: Optional[str] = None
    signer_id: Optional[str] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None
    # 预留字段，不同提供商可能有不同字段
    extra: Optional[dict] = None


# ========== API 端点 ==========


@router.post(
    "/flows",
    response_model=FlowResponse,
    summary="创建签署流程",
    description="为指定合同创建电子签署流程，生成各签署人的签署链接",
)
async def create_sign_flow(
    req: CreateFlowRequest,
    user: User = Depends(get_current_user_required),
):
    """创建签署流程"""
    provider = get_esign_provider()

    # 构造签署人列表
    signers = []
    for s in req.signers:
        signers.append(SignerInfo(
            name=s.name,
            id_number=s.id_number,
            mobile=s.mobile,
            email=s.email,
            sign_type=SignType(s.sign_type),
            sign_order=s.sign_order,
        ))

    try:
        result = await provider.create_sign_flow(
            contract_id=req.contract_id,
            title=req.title,
            signers=signers,
            document_url=req.document_url,
            expire_hours=req.expire_hours,
        )
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    logger.info(
        f"用户 {user.email} 创建签署流程: flow_id={result.flow_id}, "
        f"contract_id={req.contract_id}"
    )

    return FlowResponse(
        flow_id=result.flow_id,
        contract_id=result.contract_id,
        status=result.status.value,
        sign_urls=result.sign_urls,
        created_at=result.created_at.isoformat() if result.created_at else None,
        expires_at=result.expires_at.isoformat() if result.expires_at else None,
    )


@router.get(
    "/flows",
    summary="列出签署流程",
    description="列出当前用户相关的签署流程（Mock 模式下返回所有流程）",
)
async def list_flows(
    contract_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    user: User = Depends(get_current_user_required),
):
    """列出签署流程"""
    provider = get_esign_provider()

    # Mock 实现通过内部存储列出
    from src.services.esign_service import MockESignProvider
    if isinstance(provider, MockESignProvider):
        flows = []
        for flow_data in provider._flows.values():
            # 可选按 contract_id 过滤
            if contract_id and flow_data["contract_id"] != contract_id:
                continue
            if status_filter and flow_data["status"] != status_filter:
                continue
            flows.append({
                "flow_id": flow_data["flow_id"],
                "contract_id": flow_data["contract_id"],
                "title": flow_data.get("title", ""),
                "status": flow_data["status"],
                "created_at": flow_data["created_at"],
                "expires_at": flow_data.get("expires_at"),
                "signer_count": len(flow_data.get("signers_status", [])),
            })
        return {"flows": flows, "total": len(flows)}

    # 其他提供商暂未实现列表接口
    return {"flows": [], "total": 0}


@router.get(
    "/flows/{flow_id}",
    response_model=FlowStatusResponse,
    summary="查询签署流程状态",
    description="获取指定签署流程的详细状态，包括各签署人的签署进度",
)
async def get_flow_status(
    flow_id: str,
    user: User = Depends(get_current_user_required),
):
    """查询签署流程状态"""
    provider = get_esign_provider()

    try:
        result = await provider.get_flow_status(flow_id)
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    signers = []
    for s in result.signers_status:
        signers.append({
            "signer_id": s.signer_id,
            "name": s.name,
            "sign_type": s.sign_type.value,
            "status": s.status.value,
            "signed_at": s.signed_at.isoformat() if s.signed_at else None,
            "reject_reason": s.reject_reason,
        })

    return FlowStatusResponse(
        flow_id=result.flow_id,
        contract_id=result.contract_id,
        status=result.status.value,
        signers=signers,
        created_at=result.created_at.isoformat() if result.created_at else None,
        updated_at=result.updated_at.isoformat() if result.updated_at else None,
        completed_at=result.completed_at.isoformat() if result.completed_at else None,
    )


@router.get(
    "/flows/{flow_id}/sign-url/{signer_id}",
    response_model=SignUrlResponse,
    summary="获取签署链接",
    description="获取指定签署人的签署页面链接",
)
async def get_sign_url(
    flow_id: str,
    signer_id: str,
    user: User = Depends(get_current_user_required),
):
    """获取签署链接"""
    provider = get_esign_provider()

    try:
        url = await provider.get_sign_url(flow_id, signer_id)
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return SignUrlResponse(
        flow_id=flow_id,
        signer_id=signer_id,
        sign_url=url,
    )


@router.post(
    "/flows/{flow_id}/cancel",
    summary="取消签署流程",
    description="取消指定的签署流程",
)
async def cancel_flow(
    flow_id: str,
    reason: str = "",
    user: User = Depends(get_current_user_required),
):
    """取消签署流程"""
    provider = get_esign_provider()

    try:
        success = await provider.cancel_flow(flow_id, reason)
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法取消该签署流程（可能已完成或已取消）",
        )

    logger.info(f"用户 {user.email} 取消签署流程: flow_id={flow_id}, reason={reason}")
    return {"message": "签署流程已取消", "flow_id": flow_id}


@router.post(
    "/webhook",
    summary="签署状态回调",
    description="接收电子签章平台的签署状态 Webhook 回调（无需认证）",
)
async def esign_webhook(
    payload: WebhookPayload,
    request: Request,
):
    """
    Webhook 回调端点

    接收来自电子签章平台（e签宝/法大大）的签署状态变更通知。
    生产环境应验证回调签名。
    """
    logger.info(
        f"[ESign Webhook] 收到回调: flow_id={payload.flow_id}, "
        f"action={payload.action}, status={payload.status}"
    )
    signature = request.headers.get("X-ESign-Signature", "")
    timestamp = request.headers.get("X-Webhook-Timestamp")
    if not await WebhookSecurity.verify(
        scope="esign",
        body=await request.body(),
        signature=signature,
        secret=settings.ESIGN_WEBHOOK_SECRET,
        timestamp=timestamp,
    ):
        raise HTTPException(status_code=403, detail="签名验证失败")

    # TODO: 根据回调内容更新合同签署状态
    # 1. 查找对应的合同记录
    # 2. 更新签署状态
    # 3. 如果所有方签署完成，自动归档

    return {"code": 0, "message": "ok"}
