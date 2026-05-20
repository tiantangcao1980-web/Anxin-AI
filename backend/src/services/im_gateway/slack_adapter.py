"""
Slack 适配器（占位，P3+ 实现）。

要点：
    - 使用 ``slack_sdk`` 异步客户端
    - Events API + 签名校验（``X-Slack-Signature`` + ``X-Slack-Request-Timestamp``）
    - 卡片消息使用 Block Kit
"""

from __future__ import annotations

from typing import Any

from src.services.im_gateway.base import BaseIMAdapter
from src.services.im_gateway.models import IMChannelType


class SlackAdapter(BaseIMAdapter):
    """Slack IM 适配器（占位，P3+ 实现）。"""

    channel_type: str = IMChannelType.SLACK.value

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
