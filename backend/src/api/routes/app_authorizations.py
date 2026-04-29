# -*- coding: utf-8 -*-
"""
app_authorizations 路由 —— P4-A 通用应用授权框架

挂载点（在 ``api/routes/__init__.py`` 用 ``prefix="/app-authorizations"`` 注册）::

    GET    /api/v1/app-authorizations/providers
    GET    /api/v1/app-authorizations
    POST   /api/v1/app-authorizations/{provider_id}/start
    GET    /api/v1/app-authorizations/{provider_id}/callback?code=&state=
    POST   /api/v1/app-authorizations/{id}/refresh
    DELETE /api/v1/app-authorizations/{id}

权限：
    - ``/providers`` 公开（任何登录用户能看应用市场）
    - 其余 endpoint 需登录；写操作仅限授权所属用户本人
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.schemas.app_authorization import (
    AppAuthorizationListOut,
    AppAuthorizationOut,
    CallbackOut,
    ProviderListOut,
    ProviderMetadataOut,
    StartAuthorizeBody,
    StartAuthorizeOut,
)
from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.models.user import User
from src.services.app_authorization import (
    OAuthFlowError,
    OAuthFlowService,
    OAuthNotFoundError,
    OAuthProviderError,
    OAuthProviderRegistry,
    OAuthStateError,
)


router = APIRouter()


def _get_service(db: AsyncSession) -> OAuthFlowService:
    return OAuthFlowService(db)


def _serialize_authorization(auth) -> AppAuthorizationOut:
    """ORM 模型 → Pydantic（处理 enum.value）。"""
    return AppAuthorizationOut(
        id=str(auth.id),
        user_id=str(auth.user_id),
        provider_id=auth.provider_id,
        status=auth.status.value if hasattr(auth.status, "value") else str(auth.status),
        scopes=auth.scopes or [],
        connected_at=auth.connected_at,
        last_refresh_at=auth.last_refresh_at,
        error_message=auth.error_message,
        created_at=auth.created_at,
        updated_at=auth.updated_at,
    )


# ---------------------------------------------------------------------------
# GET /providers — 列出所有可用 provider（应用市场）
# ---------------------------------------------------------------------------


@router.get("/providers", response_model=ProviderListOut)
async def list_providers(
    category: str | None = Query(default=None, description="按类别过滤"),
    _user: User = Depends(get_current_user_required),
) -> ProviderListOut:
    """列出所有已注册的 OAuth provider 元数据。"""
    registry = OAuthProviderRegistry.default()
    if category:
        provider_classes = registry.list_by_category(category)
    else:
        provider_classes = registry.list_all()

    items = [
        ProviderMetadataOut(
            provider_id=cls.provider_id,
            display_name=cls.display_name,
            category=cls.category,
            icon_url=getattr(cls, "icon_url", None),
            default_scopes=list(getattr(cls, "default_scopes", []) or []),
        )
        for cls in provider_classes
    ]
    return ProviderListOut(items=items, total=len(items))


# ---------------------------------------------------------------------------
# GET / — 当前用户已连接的授权列表
# ---------------------------------------------------------------------------


@router.get("", response_model=AppAuthorizationListOut)
async def list_authorizations(
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> AppAuthorizationListOut:
    """当前用户已连接的所有授权（含 expired / error / revoked，由前端按 status 分组展示）。"""
    service = _get_service(db)
    auths = await service.list_for_user(str(user.id))
    items = [_serialize_authorization(a) for a in auths]
    return AppAuthorizationListOut(items=items, total=len(items))


# ---------------------------------------------------------------------------
# POST /{provider_id}/start — 生成 authorize_url
# ---------------------------------------------------------------------------


@router.post(
    "/{provider_id}/start",
    response_model=StartAuthorizeOut,
)
async def start_authorize(
    provider_id: str,
    body: StartAuthorizeBody | None = None,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> StartAuthorizeOut:
    """生成 OAuth 授权 URL（前端 window.open / Tauri 打开浏览器）。"""
    service = _get_service(db)
    body = body or StartAuthorizeBody()
    try:
        result = await service.start(
            provider_id=provider_id,
            user_id=str(user.id),
            redirect_uri=body.redirect_uri,
            scopes=body.scopes,
        )
    except OAuthProviderError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except OAuthFlowError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return StartAuthorizeOut(
        provider_id=provider_id,
        authorize_url=result["authorize_url"],
        state=result["state"],
    )


# ---------------------------------------------------------------------------
# GET /{provider_id}/callback — OAuth 回调
# ---------------------------------------------------------------------------


@router.get(
    "/{provider_id}/callback",
    response_model=CallbackOut,
)
async def oauth_callback(
    provider_id: str,
    code: str = Query(..., description="授权码"),
    state: str = Query(..., description="CSRF state"),
    db: AsyncSession = Depends(get_db),
) -> CallbackOut:
    """OAuth 回调入口（不要求登录态 —— state 已绑定 user_id）。

    P16-C 安全审计（2026-04-28）：
        - state 一次性校验：``OAuthFlowService.callback`` 内通过 Redis SETEX
          消费一次后失效，已防 CSRF + replay。
        - Shopify webhook：HMAC fail-closed (见 shopify provider)。
        - 飞书 OAuth callback：state 已带 user_id 绑定，签名校验由事件订阅
          走另条路径（受 ``feishu_signature.verify_signature`` fail-closed 保护）。
        - TODO（钉钉 / Notion）：当前 callback 仅依赖 state，provider 端未提
          供回调签名机制；如未来开放 webhook，需在 provider 实现里加 HMAC。
    """
    service = _get_service(db)
    try:
        auth = await service.callback(
            provider_id=provider_id,
            state=state,
            code=code,
        )
    except OAuthStateError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except OAuthProviderError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except OAuthFlowError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return CallbackOut(success=True, authorization=_serialize_authorization(auth))


# ---------------------------------------------------------------------------
# POST /{id}/refresh — 续期
# ---------------------------------------------------------------------------


@router.post(
    "/{authorization_id}/refresh",
    response_model=AppAuthorizationOut,
)
async def refresh_authorization(
    authorization_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> AppAuthorizationOut:
    """主动触发 refresh_token（也可由后台定时任务调）。"""
    service = _get_service(db)
    try:
        auth = await service._load_authorization(authorization_id)
    except OAuthNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    if str(auth.user_id) != str(user.id):
        raise HTTPException(status_code=403, detail="无权操作他人授权")

    try:
        auth = await service.refresh(authorization_id)
    except OAuthNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except OAuthProviderError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return _serialize_authorization(auth)


# ---------------------------------------------------------------------------
# DELETE /{id} — 断开
# ---------------------------------------------------------------------------


@router.delete(
    "/{authorization_id}",
    status_code=status.HTTP_200_OK,
    response_model=AppAuthorizationOut,
)
async def disconnect_authorization(
    authorization_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> AppAuthorizationOut:
    """断开第三方授权（标记 status=revoked + 调 provider.revoke）。"""
    service = _get_service(db)
    try:
        auth = await service._load_authorization(authorization_id)
    except OAuthNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    if str(auth.user_id) != str(user.id):
        raise HTTPException(status_code=403, detail="无权操作他人授权")

    auth = await service.disconnect(authorization_id)
    return _serialize_authorization(auth)
