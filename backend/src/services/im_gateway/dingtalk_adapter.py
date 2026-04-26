# -*- coding: utf-8 -*-
"""
钉钉适配器（占位，P3+ 实现）。

要点：
    - 钉钉机器人有「群机器人」与「企业内部应用」两种形态，回调签名规则不同
    - ``send_message`` 推荐走「企业内部应用 → 工作通知」消息，避免群机器人 20 条/分钟限频
"""

from __future__ import annotations

from typing import Any

from src.services.im_gateway.base import BaseIMAdapter
from src.services.im_gateway.models import IMChannelType


class DingTalkAdapter(BaseIMAdapter):
    """钉钉 IM 适配器（占位，P3+ 实现）。"""

    channel_type: str = IMChannelType.DINGTALK.value

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
