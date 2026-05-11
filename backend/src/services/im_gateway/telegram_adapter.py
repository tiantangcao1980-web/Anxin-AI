# -*- coding: utf-8 -*-
"""
Telegram 适配器（占位，P3+ 实现）。

要点：
    - 通过 ``python-telegram-bot`` 或直接 HTTPS 调用 Bot API
    - Webhook 模式（推荐）+ Long Polling 模式（开发期）
    - 国内访问需配置出网代理
"""

from __future__ import annotations

from typing import Any

from src.services.im_gateway.base import BaseIMAdapter
from src.services.im_gateway.models import IMChannelType


class TelegramAdapter(BaseIMAdapter):
    """Telegram IM 适配器（占位，P3+ 实现）。"""

    channel_type: str = IMChannelType.TELEGRAM.value

    async def send_message(
        self,
        channel_id: str,
        content: str,
        **extra: Any,
    ) -> dict[str, Any]:
        raise NotImplementedError("P3+ 实现")

    async def receive_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("P3+ 实现")

    async def register_bot(self, config: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("P3+ 实现")

    async def list_groups(self) -> list[dict[str, Any]]:
        raise NotImplementedError("P3+ 实现")
