"""
电子签章 API 路由

提供合同电子签署流程的创建、查询、签署链接获取和 Webhook 回调。
"""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.models.contract import Contract, ContractStatus
from src.models.user import User
from src.services.audit_service import AuditService
from src.services.esign_service import (
    ESignProvider,
    ESignProviderAPIError,
    ESignProviderConfigError,
    MockESignProvider,
    SignerInfo,
    SignType,
    get_esign_provider,
)
from src.services.official_webhook_security import (
    OfficialWebhookVerificationError,
    verify_esignbao_notification,
    verify_fadada_notification,
)
from src.services.webhook_handler import WebhookBusinessError, handle_verified_webhook
from src.services.webhook_security import WebhookSecurity

router = APIRouter()


def _require_user_org_id(user: User) -> str:
    org_id = str(user.org_id) if user.org_id else ""
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户未加入组织，不能执行电子签章操作",
        )
    return org_id


async def _get_contract_for_user(
    db: AsyncSession,
    user: User,
    *,
    contract_id: str | None = None,
    flow_id: str | None = None,
) -> Contract:
    org_id = _require_user_org_id(user)
    conditions = [Contract.org_id == org_id]
    if contract_id is not None:
        conditions.append(Contract.id == contract_id)
    if flow_id is not None:
        conditions.append(Contract.esign_flow_id == flow_id)
    result = await db.execute(select(Contract).where(*conditions))
    contract = result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="合同或签署流程不存在",
        )
    return contract


def _get_provider_or_503() -> ESignProvider:
    try:
        return get_esign_provider()
    except ESignProviderConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e


def _esign_contract_audit_value(contract: Contract) -> dict[str, object | None]:
    return {
        "contract_id": contract.id,
        "status": contract.status.value if isinstance(contract.status, ContractStatus) else str(contract.status),
        "flow_id": contract.esign_flow_id,
        "provider": contract.esign_provider,
        "org_id": str(contract.org_id) if contract.org_id else None,
    }


async def _parse_webhook_payload(request: Request, body: bytes) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type or request.headers.get("X-FASC-App-Id"):
        form = await request.form()
        biz_content = form.get("bizContent")
        if isinstance(biz_content, str) and biz_content:
            payload = json.loads(biz_content)
            if not isinstance(payload, dict):
                raise ValueError("bizContent must be a JSON object")
            payload["eventType"] = request.headers.get("X-FASC-Event") or payload.get("eventType")
            return payload
    if not body:
        return {}
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("webhook body must be a JSON object")
    return payload

# ========== 请求/响应模型 ==========


class SignerInput(BaseModel):
    """创建签署流程时的签署人输入"""
    name: str = Field(..., description="签署人姓名/企业名称")
    id_number: str | None = Field(None, description="身份证号/统一社会信用代码")
    mobile: str | None = Field(None, description="手机号码")
    email: str | None = Field(None, description="邮箱")
    sign_type: str = Field(default="personal", description="签署类型: personal/company")
    sign_order: int = Field(default=0, description="签署顺序，0 表示不限顺序")


class CreateFlowRequest(BaseModel):
    """创建签署流程请求"""
    contract_id: str = Field(..., description="合同ID")
    title: str = Field(..., description="签署流程标题")
    signers: list[SignerInput] = Field(..., min_length=1, description="签署人列表")
    document_url: str | None = Field(None, description="待签署文件URL")
    expire_hours: int = Field(default=72, ge=1, le=720, description="过期时间（小时）")


class FlowResponse(BaseModel):
    """签署流程响应"""
    flow_id: str
    contract_id: str
    status: str
    sign_urls: dict[str, str] = {}
    created_at: str | None = None
    expires_at: str | None = None


class FlowStatusResponse(BaseModel):
    """签署流程状态响应"""
    flow_id: str
    contract_id: str
    status: str
    signers: list[dict[str, str | None]] = []
    created_at: str | None = None
    updated_at: str | None = None
    completed_at: str | None = None


class SignUrlResponse(BaseModel):
    """签署链接响应"""
    flow_id: str
    signer_id: str
    sign_url: str


class WebhookPayload(BaseModel):
    """Webhook 回调载荷（通用格式，各提供商格式不同）"""
    model_config = ConfigDict(populate_by_name=True)

    flow_id: str | None = None
    contract_id: str | None = None
    action: str | None = None
    signer_id: str | None = None
    status: str | None = None
    timestamp: str | None = None
    event_id: str | None = Field(default=None, alias="eventId")
    event_type: str | None = Field(default=None, alias="eventType")
    notify_id: str | None = Field(default=None, alias="notifyId")
    # 预留字段，不同提供商可能有不同字段
    extra: dict[str, Any] | None = None


# ========== API 端点 ==========


@router.post(
    "/flows",
    response_model=FlowResponse,
    summary="创建签署流程",
    description="为指定合同创建电子签署流程，生成各签署人的签署链接",
)
async def create_sign_flow(
    req: CreateFlowRequest,
    request: Request,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> FlowResponse:
    """创建签署流程"""
    contract = await _get_contract_for_user(db, user, contract_id=req.contract_id)
    if contract.status != ContractStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="合同必须审批通过后才能发起电签",
        )

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

    provider = _get_provider_or_503()
    try:
        result = await provider.create_sign_flow(
            contract_id=req.contract_id,
            title=req.title,
            signers=signers,
            document_url=req.document_url,
            expire_hours=req.expire_hours,
        )
    except ESignProviderConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except ESignProviderAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    logger.info(
        f"用户 {user.email} 创建签署流程: flow_id={result.flow_id}, "
        f"contract_id={req.contract_id}"
    )
    old_value = _esign_contract_audit_value(contract)
    contract.esign_flow_id = result.flow_id
    contract.esign_provider = provider.__class__.__name__
    await db.commit()
    await db.refresh(contract)
    await AuditService(db).log_from_request(
        request,
        action="esign.flow.create",
        resource_type="contract",
        resource_id=contract.id,
        user=user,
        old_value=old_value,
        new_value={
            **_esign_contract_audit_value(contract),
            "signers_count": len(req.signers),
            "has_document_url": bool(req.document_url),
            "flow_status": result.status.value,
        },
        extra_data={"source": "esign", "provider": provider.__class__.__name__},
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
    contract_id: str | None = None,
    status_filter: str | None = None,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """列出签署流程"""
    org_id = _require_user_org_id(user)
    provider = _get_provider_or_503()
    contract_query = select(Contract).where(Contract.org_id == org_id, Contract.esign_flow_id.is_not(None))
    if contract_id:
        contract_query = contract_query.where(Contract.id == contract_id)
    contract_result = await db.execute(contract_query)
    allowed_flows = {contract.esign_flow_id for contract in contract_result.scalars().all() if contract.esign_flow_id}

    if isinstance(provider, MockESignProvider):
        flows: list[dict[str, Any]] = []
        for flow_data in provider._flows.values():
            if flow_data["flow_id"] not in allowed_flows:
                continue
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
    db: AsyncSession = Depends(get_db),
) -> FlowStatusResponse:
    """查询签署流程状态"""
    await _get_contract_for_user(db, user, flow_id=flow_id)
    provider = _get_provider_or_503()

    try:
        result = await provider.get_flow_status(flow_id)
    except ESignProviderConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except ESignProviderAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    signers: list[dict[str, str | None]] = []
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
    request: Request,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> SignUrlResponse:
    """获取签署链接"""
    contract = await _get_contract_for_user(db, user, flow_id=flow_id)
    provider = _get_provider_or_503()

    try:
        url = await provider.get_sign_url(flow_id, signer_id)
    except ESignProviderConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except ESignProviderAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    await AuditService(db).log_from_request(
        request,
        action="esign.flow.sign_url",
        resource_type="contract",
        resource_id=contract.id,
        user=user,
        new_value={**_esign_contract_audit_value(contract), "signer_id": signer_id},
        extra_data={"source": "esign", "provider": provider.__class__.__name__},
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
    request: Request,
    reason: str = "",
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """取消签署流程"""
    contract = await _get_contract_for_user(db, user, flow_id=flow_id)
    provider = _get_provider_or_503()

    try:
        success = await provider.cancel_flow(flow_id, reason)
    except ESignProviderConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except ESignProviderAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法取消该签署流程（可能已完成或已取消）",
        )

    logger.info(f"用户 {user.email} 取消签署流程: flow_id={flow_id}, reason={reason}")
    await AuditService(db).log_from_request(
        request,
        action="esign.flow.cancel",
        resource_type="contract",
        resource_id=contract.id,
        user=user,
        new_value={**_esign_contract_audit_value(contract), "cancelled": True},
        extra_data={
            "source": "esign",
            "provider": provider.__class__.__name__,
            "reason_present": bool(reason),
        },
    )
    return {"message": "签署流程已取消", "flow_id": flow_id}


@router.post(
    "/webhook",
    summary="签署状态回调",
    description="接收电子签章平台的签署状态 Webhook 回调（无需认证）",
)
async def esign_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Webhook 回调端点

    接收来自电子签章平台（e签宝/法大大）的签署状态变更通知。
    生产环境应验证回调签名。
    """
    signature = request.headers.get("X-ESign-Signature", "")
    timestamp = request.headers.get("X-Webhook-Timestamp")
    body = await request.body()
    try:
        webhook_payload = await _parse_webhook_payload(request, body)
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"无效 webhook payload: {exc}") from exc

    logger.info(
        f"[ESign Webhook] 收到回调: flow_id={webhook_payload.get('flow_id') or webhook_payload.get('flowId')}, "
        f"action={webhook_payload.get('action')}, status={webhook_payload.get('status')}"
    )
    if settings.ESIGN_OFFICIAL_WEBHOOK_ENABLED:
        try:
            if request.headers.get("X-FASC-App-Id"):
                webhook_payload = verify_fadada_notification(
                    headers=request.headers,
                    body=body,
                    app_id=settings.FADADA_APP_ID,
                    app_secret=settings.FADADA_APP_SECRET,
                    max_age_seconds=settings.WEBHOOK_SIGNATURE_MAX_AGE_SECONDS,
                )
            else:
                verify_esignbao_notification(
                    headers=request.headers,
                    body=body,
                    query_params=dict(request.query_params),
                    app_id=settings.ESIGN_BAO_APP_ID,
                    app_secret=settings.ESIGN_BAO_APP_SECRET,
                    max_age_seconds=settings.WEBHOOK_SIGNATURE_MAX_AGE_SECONDS,
                )
        except OfficialWebhookVerificationError as exc:
            raise HTTPException(status_code=403, detail=f"电签官方验签失败: {exc}") from exc
    elif not await WebhookSecurity.verify(
        scope="esign",
        body=body,
        signature=signature,
        secret=settings.ESIGN_WEBHOOK_SECRET,
        timestamp=timestamp,
    ):
        raise HTTPException(status_code=403, detail="签名验证失败")
    try:
        handle_result = await handle_verified_webhook(
            db,
            scope="esign",
            payload=webhook_payload,
            body=body,
        )
    except WebhookBusinessError as exc:
        logger.warning(f"[ESign Webhook] 回写失败: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[ESign Webhook] 回写异常")
        raise HTTPException(status_code=500, detail="签署状态回写失败") from exc

    response: dict[str, Any] = {"code": 0, "message": "ok"}
    if handle_result.result is not None:
        response["data"] = handle_result.result
    return response
