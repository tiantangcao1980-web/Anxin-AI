"""
im_pairing 路由 —— P3-B IM 配对授权 24h 窗口

挂载点（在 ``api/routes/__init__.py`` 用 ``prefix="/im/pairing"`` 注册）::

    POST   /api/v1/im/pairing/request                  创建配对请求（来自 webhook 内部调）
    GET    /api/v1/im/pairing/pending                  管理员看待审核
    POST   /api/v1/im/pairing/{id}/approve             审批通过
    POST   /api/v1/im/pairing/{id}/reject              驳回 { reason }
    GET    /api/v1/im/pairing/authorized               已授权列表

权限：
    - ``/request`` 需登录（webhook 内部网关也以系统账号 token 调用）
    - ``/pending`` / ``/{id}/approve`` / ``/{id}/reject`` 需管理员
      （super_admin / admin / org_admin），复用 ``get_admin_user``
    - ``/authorized`` 需登录即可（管理员看全量；普通用户也能看到自己已绑定的，
      未来可基于 internal_user_id 进一步过滤，本期返回全量给前端 UI）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.schemas.im_pairing import (
    IMBindingListOut,
    IMBindingOut,
    PairingApproveBody,
    PairingRejectBody,
    PairingRequestCreate,
    PairingRequestListOut,
    PairingRequestOut,
)
from src.core.database import get_db
from src.core.deps import get_admin_user, get_current_user_required
from src.models.user import User
from src.services.im_gateway.pairing.service import (
    PairingExpiredError,
    PairingNotFoundError,
    PairingNotPendingError,
    PairingService,
)

router = APIRouter()


def _get_service(db: AsyncSession) -> PairingService:
    return PairingService(db)


# ---------------------------------------------------------------------------
# 创建（内部 webhook 触发）
# ---------------------------------------------------------------------------


@router.post(
    "/request",
    response_model=PairingRequestOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_pairing_request(
    body: PairingRequestCreate,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> PairingRequestOut:
    """创建一条 24h 配对请求（IM webhook 在收到 @bot 后内部调用）。"""
    service = _get_service(db)
    request = await service.create_pairing_request(
        channel_id=body.channel_id,
        external_user_id=body.external_user_id,
        external_user_name=body.external_user_name,
    )
    return PairingRequestOut.model_validate(request)


# ---------------------------------------------------------------------------
# 列表查询
# ---------------------------------------------------------------------------


@router.get("/pending", response_model=PairingRequestListOut)
async def list_pending_pairing_requests(
    channel_id: str | None = Query(default=None, description="按通道过滤"),
    limit: int = Query(default=50, ge=1, le=200),
    _admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> PairingRequestListOut:
    """管理员看待审核的 PENDING（未过期）请求。"""
    service = _get_service(db)
    items = await service.list_pending(channel_id=channel_id, limit=limit)
    return PairingRequestListOut(
        items=[PairingRequestOut.model_validate(r) for r in items],
        limit=limit,
        channel_id=channel_id,
    )


@router.get("/authorized", response_model=IMBindingListOut)
async def list_authorized_bindings(
    channel_id: str | None = Query(default=None, description="按通道过滤"),
    limit: int = Query(default=50, ge=1, le=200),
    _user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> IMBindingListOut:
    """已生效的 IM 绑定列表。"""
    service = _get_service(db)
    items = await service.list_authorized(channel_id=channel_id, limit=limit)
    return IMBindingListOut(
        items=[IMBindingOut.model_validate(b) for b in items],
        limit=limit,
        channel_id=channel_id,
    )


# ---------------------------------------------------------------------------
# 审批 / 驳回
# ---------------------------------------------------------------------------


@router.post("/{request_id}/approve", response_model=IMBindingOut)
async def approve_pairing_request(
    request_id: str,
    body: PairingApproveBody | None = None,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> IMBindingOut:
    """审批通过：写入 ``IMBinding`` + 飞书卡片回执。"""
    service = _get_service(db)
    try:
        binding = await service.approve(request_id, approver_id=str(admin.id))
    except PairingNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PairingNotPendingError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except PairingExpiredError as e:
        raise HTTPException(status_code=410, detail=str(e)) from e
    return IMBindingOut.model_validate(binding)


@router.post("/{request_id}/reject", response_model=PairingRequestOut)
async def reject_pairing_request(
    request_id: str,
    body: PairingRejectBody,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> PairingRequestOut:
    """驳回审批（必须填写 ``reason``）。"""
    service = _get_service(db)
    try:
        request = await service.reject(
            request_id,
            approver_id=str(admin.id),
            reason=body.reason,
        )
    except PairingNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PairingNotPendingError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return PairingRequestOut.model_validate(request)
