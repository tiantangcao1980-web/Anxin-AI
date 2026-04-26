# -*- coding: utf-8 -*-
"""
飞书（Lark）适配器 —— P3 优先实现

依赖（P3 安装）：
    - ``lark-oapi`` 官方 SDK，或直接使用 ``aiohttp`` + Open API
    - ``app_id`` / ``app_secret`` 通过 ``IMChannel.config`` 注入

P3 实现重点：
    1. tenant_access_token 自动刷新与缓存
    2. 加密回调 + V1/V2 事件订阅签名校验
    3. 卡片消息（interactive card）模板化
"""

from __future__ import annotations

from typing import Any

from src.services.im_gateway.base import BaseIMAdapter
from src.services.im_gateway.models import IMChannelType


class FeishuAdapter(BaseIMAdapter):
    """飞书 IM 适配器（P3 实现）。"""

    channel_type: str = IMChannelType.FEISHU.value

    async def send_message(
        self,
        channel_id: str,
        content: str,
        **extra: Any,
    ) -> dict[str, Any]:
        """发送飞书消息。

        P3 实现：调用 ``POST /open-apis/im/v1/messages``，
        ``msg_type`` 默认 ``text``；``extra`` 可指定 ``interactive`` + ``card``。
        """
        raise NotImplementedError("P3 实现")

    async def receive_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """处理飞书事件回调。

        P3 实现：
            - URL 校验事件（``challenge``）直接回包
            - 加密载荷解密 + 签名校验
            - 转换为内部统一事件格式
        """
        raise NotImplementedError("P3 实现")

    async def register_bot(self, config: dict[str, Any]) -> dict[str, Any]:
        """注册飞书机器人。

        P3 实现：写入 webhook、订阅 ``im.message.receive_v1`` 等事件。
        """
        raise NotImplementedError("P3 实现")

    async def list_groups(self) -> list[dict[str, Any]]:
        """拉取 bot 所在的群列表。

        P3 实现：``GET /open-apis/im/v1/chats``，分页聚合。
        """
        raise NotImplementedError("P3 实现")
