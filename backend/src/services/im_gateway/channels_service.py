# -*- coding: utf-8 -*-
"""IM 渠道管理服务（P3-C）。

负责"渠道配置管理"的真实 DB 持久化：CRUD + 状态机 + 绑定 persona，按组织隔离。
对应前端 contract（frontend/src/lib/api/imChannels.ts /
mobile/src/lib/api/imChannels.ts）的 6 个端点。

⚠️ 重要边界：本服务**不做真实第三方 IM 协议握手**。``status`` 仅依据 ``config``
是否包含该平台必填字段推导（见 ``_required_config_keys`` / ``_derive_status``），
``/test`` 端点同理——它只做"配置完整性自检"，**不会真的连上飞书/Slack/...**。
真实协议连接属 P3+ 后续工作（adapter 层 ``send_message`` 已具雏形，但建链与健康
探活尚未接入）。``stats`` 计数从 ``im_gateway_bindings`` / ``im_gateway_pairings``
真实聚合；无绑定数据时自然为 0。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.im_gateway.models import (
    IMBinding,
    IMChannel,
    IMChannelStatus,
    IMChannelType,
    PairingRequest,
    PairingStatus,
)


class ChannelNotFoundError(Exception):
    """渠道不存在（或不属于当前组织）。"""


class InvalidChannelTypeError(Exception):
    """非法的 channel_type。"""


# 各平台"配置完整"所需的必填 config 键。
# 仅用于推导 status / test 自检，不代表凭据有效（不做真实握手）。
_REQUIRED_CONFIG_KEYS: dict[IMChannelType, tuple[str, ...]] = {
    IMChannelType.FEISHU: ("app_id", "app_secret"),
    IMChannelType.WECHAT: ("corp_id", "secret"),
    IMChannelType.DINGTALK: ("app_key", "app_secret"),
    IMChannelType.TELEGRAM: ("bot_token",),
    IMChannelType.SLACK: ("bot_token",),
    IMChannelType.DISCORD: ("bot_token",),
}

# channel_type 展示名（setup 时若未带 name 则用作默认名）。
_DEFAULT_NAMES: dict[IMChannelType, str] = {
    IMChannelType.FEISHU: "飞书机器人",
    IMChannelType.WECHAT: "企业微信",
    IMChannelType.DINGTALK: "钉钉",
    IMChannelType.TELEGRAM: "Telegram Bot",
    IMChannelType.SLACK: "Slack",
    IMChannelType.DISCORD: "Discord",
}


def _required_config_keys(channel_type: IMChannelType) -> tuple[str, ...]:
    return _REQUIRED_CONFIG_KEYS.get(channel_type, ())


def _config_is_complete(channel_type: IMChannelType, config: dict | None) -> bool:
    """config 是否含该平台全部必填键且非空。"""
    if not config:
        return _required_config_keys(channel_type) == ()
    for key in _required_config_keys(channel_type):
        value = config.get(key)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return False
    return True


def _missing_config_keys(channel_type: IMChannelType, config: dict | None) -> list[str]:
    cfg = config or {}
    missing: list[str] = []
    for key in _required_config_keys(channel_type):
        value = cfg.get(key)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            missing.append(key)
    return missing


def _derive_status(
    channel_type: IMChannelType,
    config: dict | None,
) -> IMChannelStatus:
    """依据 config 完整度推导状态（不做真实握手）。"""
    if _config_is_complete(channel_type, config):
        return IMChannelStatus.CONNECTED
    return IMChannelStatus.UNCONFIGURED


def parse_channel_type(raw: str) -> IMChannelType:
    """把路径里的 channel_type 字符串转为枚举；非法值抛 InvalidChannelTypeError。"""
    try:
        return IMChannelType(raw)
    except ValueError as e:
        raise InvalidChannelTypeError(raw) from e


class IMChannelsService:
    """IM 渠道管理服务（按组织隔离）。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------ 查询
    async def list_channels(self, org_id: str | None) -> list[IMChannel]:
        """列出当前组织的全部渠道（org_id 为 None 时仅列系统级 NULL 通道）。"""
        stmt = (
            select(IMChannel)
            .where(IMChannel.org_id == org_id)
            .order_by(IMChannel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_channel(self, channel_id: str, org_id: str | None) -> IMChannel:
        """按 id + org 取单个渠道；不存在或越权抛 ChannelNotFoundError。"""
        channel = await self.session.get(IMChannel, channel_id)
        if channel is None or channel.org_id != org_id:
            raise ChannelNotFoundError(channel_id)
        return channel

    # ------------------------------------------------------------------ 写入
    async def setup_channel(
        self,
        channel_type: IMChannelType,
        config: dict | None,
        org_id: str | None,
        created_by: str | None,
        name: str | None = None,
    ) -> IMChannel:
        """配置/重配某类型渠道。

        语义：同一组织同一 channel_type 只保留一条（upsert）。已存在则更新其
        config，并依据完整度刷新 status；不存在则新建。
        """
        stmt = select(IMChannel).where(
            IMChannel.org_id == org_id,
            IMChannel.channel_type == channel_type,
        )
        existing = (await self.session.execute(stmt)).scalars().first()

        status = _derive_status(channel_type, config)
        if existing is not None:
            existing.config = config
            existing.status = status
            if name:
                existing.name = name
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        channel = IMChannel(
            channel_type=channel_type,
            name=name or _DEFAULT_NAMES.get(channel_type, channel_type.value),
            config=config,
            enabled=False,
            status=status,
            org_id=org_id,
            created_by=created_by,
        )
        self.session.add(channel)
        await self.session.flush()
        await self.session.refresh(channel)
        return channel

    async def bind_agent(
        self,
        channel_id: str,
        org_id: str | None,
        agent_persona: str,
    ) -> IMChannel:
        """绑定 agent persona 到渠道。"""
        channel = await self.get_channel(channel_id, org_id)
        channel.bound_agent_persona = agent_persona
        await self.session.flush()
        await self.session.refresh(channel)
        return channel

    async def set_enabled(
        self,
        channel_id: str,
        org_id: str | None,
        enabled: bool,
    ) -> IMChannel:
        """启用/停用渠道（状态机：仅切 enabled，不改 connect 状态）。"""
        channel = await self.get_channel(channel_id, org_id)
        channel.enabled = enabled
        await self.session.flush()
        await self.session.refresh(channel)
        return channel

    # ------------------------------------------------------------------ 统计
    async def channel_stats(self, channel_id: str) -> dict[str, int]:
        """从绑定 / 配对真实聚合 stats。

        无绑定数据时自然返回 0。``pending_pairings`` 只数状态 PENDING 的请求。
        """
        bound_users = await self.session.scalar(
            select(func.count(IMBinding.id)).where(IMBinding.channel_id == channel_id)
        )
        pending_pairings = await self.session.scalar(
            select(func.count(PairingRequest.id)).where(
                PairingRequest.channel_id == channel_id,
                PairingRequest.status == PairingStatus.PENDING,
            )
        )
        return {
            # bound_groups 暂为 0：群组绑定模型尚未落地（P3+ 后续），此处先占位。
            "bound_users": int(bound_users or 0),
            "bound_groups": 0,
            "pending_pairings": int(pending_pairings or 0),
        }

    # ------------------------------------------------------------------ 连接自检
    async def test_connection(
        self,
        channel_id: str,
        org_id: str | None,
    ) -> dict:
        """渠道"连接"自检。

        ⚠️ 不做真实第三方协议握手——仅校验 config 必填字段是否齐全。齐全则
        ``ok=True``（视为"配置就绪，可建链"），缺字段则 ``ok=False`` 并在
        ``detail.missing`` 列出。返回结构对齐前端 ``TestConnectionResult``。
        """
        channel = await self.get_channel(channel_id, org_id)
        missing = _missing_config_keys(channel.channel_type, channel.config)
        if missing:
            return {
                "ok": False,
                "message": "配置不完整，缺少必填字段",
                "detail": {
                    "missing": missing,
                    "note": "未执行真实协议握手；仅校验配置完整性",
                },
            }
        return {
            "ok": True,
            "message": "配置完整（未执行真实协议握手，仅配置自检）",
            "detail": {
                "channel_type": channel.channel_type.value,
                "note": "real protocol handshake not implemented (P3+)",
            },
        }
