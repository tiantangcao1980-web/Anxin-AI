"""
微信适配器（占位，P3+ 实现）。

要点：
    - 需区分三种载体：企业微信（推荐）/ 公众号 / 小程序
    - 公众号回调走 XML，需做 ``echostr`` 验证
    - 主动推送受限（需用户先互动）；agent 提醒优先用「客服消息」窗口
"""

from __future__ import annotations

from typing import Any

from src.services.im_gateway.base import BaseIMAdapter
from src.services.im_gateway.models import IMChannelType


class WeChatAdapter(BaseIMAdapter):
    """微信 IM 适配器（占位，P3+ 实现）。"""

    channel_type: str = IMChannelType.WECHAT.value

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
