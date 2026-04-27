# -*- coding: utf-8 -*-
"""app_authorizations 路由 Pydantic schemas（请求 / 响应 DTO）。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Provider 元数据
# ---------------------------------------------------------------------------


class ProviderMetadataOut(BaseModel):
    """provider 元数据（应用市场卡片用）。"""

    provider_id: str
    display_name: str
    category: str
    icon_url: str | None = None
    default_scopes: list[str] = Field(default_factory=list)


class ProviderListOut(BaseModel):
    """provider 列表响应。"""

    items: list[ProviderMetadataOut]
    total: int


# ---------------------------------------------------------------------------
# 已连接的授权
# ---------------------------------------------------------------------------


class AppAuthorizationOut(BaseModel):
    """单条授权 DTO（不含 token）。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    provider_id: str
    status: str
    scopes: list[str] = Field(default_factory=list)
    connected_at: datetime | None = None
    last_refresh_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class AppAuthorizationListOut(BaseModel):
    """已连接授权列表响应。"""

    items: list[AppAuthorizationOut]
    total: int


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------


class StartAuthorizeBody(BaseModel):
    """POST /start 可选请求体（覆盖默认 redirect / scopes）。"""

    redirect_uri: str | None = Field(
        default=None,
        description="覆盖默认回调地址（多端时用，如 desktop:// / app://）",
    )
    scopes: list[str] | None = Field(
        default=None,
        description="覆盖 provider 的 default_scopes",
    )


class StartAuthorizeOut(BaseModel):
    """POST /start 响应：返回授权 URL + state。"""

    provider_id: str
    authorize_url: str
    state: str


# ---------------------------------------------------------------------------
# callback
# ---------------------------------------------------------------------------


class CallbackOut(BaseModel):
    """OAuth 回调响应（含新建/更新的授权信息）。"""

    success: bool = True
    authorization: AppAuthorizationOut
