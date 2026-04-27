# -*- coding: utf-8 -*-
"""im_pairing 路由 Pydantic schemas（请求 / 响应 DTO）。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.services.im_gateway.models import PairingStatus


# ---------------------------------------------------------------------------
# 请求体
# ---------------------------------------------------------------------------


class PairingRequestCreate(BaseModel):
    """创建配对请求（webhook 内部调用，外部不直接打）。"""

    channel_id: str = Field(..., description="im_gateway_channels.id")
    external_user_id: str = Field(..., max_length=128, description="平台侧用户 ID")
    external_user_name: str | None = Field(
        default=None,
        max_length=128,
        description="平台侧昵称（仅日志用）",
    )


class PairingRejectBody(BaseModel):
    """驳回请求体。"""

    reason: str = Field(..., min_length=1, max_length=500, description="驳回理由")


class PairingApproveBody(BaseModel):
    """审批通过请求体（可选 reason，仅留痕）。"""

    reason: str | None = Field(default=None, max_length=500)


# ---------------------------------------------------------------------------
# 响应体
# ---------------------------------------------------------------------------


class PairingRequestOut(BaseModel):
    """配对请求详情 DTO。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    channel_id: str
    external_user_id: str
    status: PairingStatus
    expires_at: datetime
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PairingRequestListOut(BaseModel):
    """待审核请求分页响应。"""

    items: list[PairingRequestOut]
    limit: int
    channel_id: str | None = None


class IMBindingOut(BaseModel):
    """已生效绑定 DTO。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    channel_id: str
    external_user_id: str
    internal_user_id: str
    bound_at: datetime
    created_at: datetime
    updated_at: datetime


class IMBindingListOut(BaseModel):
    """已授权列表分页响应。"""

    items: list[IMBindingOut]
    limit: int
    channel_id: str | None = None
