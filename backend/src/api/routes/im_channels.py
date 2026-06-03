# -*- coding: utf-8 -*-
"""im_channels 路由 —— P3-C IM 渠道配置管理后端。

挂载点（在 ``api/routes/__init__.py`` 用 ``prefix="/im"`` 注册）::

    GET    /api/v1/im/channels                      列出当前组织全部渠道
    POST   /api/v1/im/channels/{channelType}/setup  配置/重配某类型渠道  body {config}
    PUT    /api/v1/im/channels/{id}/agent           绑定 agent persona  body {agent_persona}
    PUT    /api/v1/im/channels/{id}/enable          启用渠道
    PUT    /api/v1/im/channels/{id}/disable         停用渠道
    GET    /api/v1/im/channels/{id}/test            连接自检（配置完整性，非真实握手）

权限：全部需登录（``get_current_user_required``）；数据按 ``user.org_id`` 隔离。

⚠️ ``/test`` 与 ``status`` 推导**不做真实第三方协议握手**，仅依据 config 完整度，
详见 ``services/im_gateway/channels_service.py`` 顶部说明。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.schemas.im_channels import (
    BindAgentRequest,
    IMChannelOut,
    SetupChannelRequest,
    TestConnectionResult,
)
from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.models.user import User
from src.services.im_gateway.channels_service import (
    ChannelNotFoundError,
    IMChannelsService,
    InvalidChannelTypeError,
    parse_channel_type,
)

router = APIRouter()


def _get_service(db: AsyncSession) -> IMChannelsService:
    return IMChannelsService(db)


async def _to_out(service: IMChannelsService, channel) -> IMChannelOut:  # noqa: ANN001
    stats = await service.channel_stats(str(channel.id))
    return IMChannelOut.from_orm_with_stats(channel, stats)


# ---------------------------------------------------------------------------
# 列表
# ---------------------------------------------------------------------------


@router.get("/channels", response_model=list[IMChannelOut])
async def list_channels(
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> list[IMChannelOut]:
    """列出当前组织的全部 IM 渠道。"""
    service = _get_service(db)
    channels = await service.list_channels(org_id=user.org_id)
    return [await _to_out(service, c) for c in channels]


# ---------------------------------------------------------------------------
# 配置（setup）
# ---------------------------------------------------------------------------


@router.post(
    "/channels/{channel_type}/setup",
    response_model=IMChannelOut,
    status_code=status.HTTP_200_OK,
)
async def setup_channel(
    channel_type: str,
    body: SetupChannelRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> IMChannelOut:
    """配置/重配某类型渠道（同组织同类型 upsert）。"""
    try:
        ctype = parse_channel_type(channel_type)
    except InvalidChannelTypeError as e:
        raise HTTPException(
            status_code=422,
            detail=f"不支持的渠道类型: {channel_type}",
        ) from e

    service = _get_service(db)
    channel = await service.setup_channel(
        channel_type=ctype,
        config=body.config,
        org_id=user.org_id,
        created_by=str(user.id),
    )
    return await _to_out(service, channel)


# ---------------------------------------------------------------------------
# 绑定 agent persona
# ---------------------------------------------------------------------------


@router.put("/channels/{channel_id}/agent", response_model=IMChannelOut)
async def bind_agent(
    channel_id: str,
    body: BindAgentRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> IMChannelOut:
    """绑定 agent persona 到指定渠道。"""
    service = _get_service(db)
    try:
        channel = await service.bind_agent(
            channel_id=channel_id,
            org_id=user.org_id,
            agent_persona=body.agent_persona,
        )
    except ChannelNotFoundError as e:
        raise HTTPException(status_code=404, detail="渠道不存在") from e
    return await _to_out(service, channel)


# ---------------------------------------------------------------------------
# 启用 / 停用
# ---------------------------------------------------------------------------


@router.put("/channels/{channel_id}/enable", response_model=IMChannelOut)
async def enable_channel(
    channel_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> IMChannelOut:
    """启用渠道。"""
    service = _get_service(db)
    try:
        channel = await service.set_enabled(
            channel_id=channel_id, org_id=user.org_id, enabled=True
        )
    except ChannelNotFoundError as e:
        raise HTTPException(status_code=404, detail="渠道不存在") from e
    return await _to_out(service, channel)


@router.put("/channels/{channel_id}/disable", response_model=IMChannelOut)
async def disable_channel(
    channel_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> IMChannelOut:
    """停用渠道。"""
    service = _get_service(db)
    try:
        channel = await service.set_enabled(
            channel_id=channel_id, org_id=user.org_id, enabled=False
        )
    except ChannelNotFoundError as e:
        raise HTTPException(status_code=404, detail="渠道不存在") from e
    return await _to_out(service, channel)


# ---------------------------------------------------------------------------
# 连接自检
# ---------------------------------------------------------------------------


@router.get("/channels/{channel_id}/test", response_model=TestConnectionResult)
async def test_connection(
    channel_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> TestConnectionResult:
    """渠道连接自检（仅校验配置完整性，不做真实第三方协议握手）。"""
    service = _get_service(db)
    try:
        result = await service.test_connection(
            channel_id=channel_id, org_id=user.org_id
        )
    except ChannelNotFoundError as e:
        raise HTTPException(status_code=404, detail="渠道不存在") from e
    return TestConnectionResult(**result)
