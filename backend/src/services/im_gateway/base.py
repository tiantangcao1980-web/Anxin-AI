"""
IM 适配器抽象基类

所有 IM 平台（飞书 / 微信 / 钉钉 / Telegram / Slack / Discord …）
必须继承 ``BaseIMAdapter``，实现统一的 4 个抽象方法。

设计目标：
- 上层业务（agent 推送 / 配对授权）只依赖抽象接口，不关心具体平台 SDK；
- 通过 ``IMAdapterRegistry`` 按 ``channel_type`` 路由到具体实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseIMAdapter(ABC):
    """IM 平台适配器抽象基类（P3 实现具体子类）。

    子类必须提供 ``channel_type`` 类属性，用于注册与路由。
    """

    #: 通道标识（与 ``IMChannelType`` 枚举值一致）
    channel_type: str = ""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """构造函数。

        参数：
            config: 通道配置（API Key / Secret / Webhook URL / Bot Token 等）；
                    P3 实现中由 ``IMChannel.config`` JSONB 字段反序列化注入。
        """
        self.config = config or {}

    # ------------------------------------------------------------------
    # 抽象接口
    # ------------------------------------------------------------------
    @abstractmethod
    async def send_message(
        self,
        channel_id: str,
        content: str,
        **extra: Any,
    ) -> dict[str, Any]:
        """向某个会话/群发送一条消息。

        参数：
            channel_id: 平台侧的 chat / group / open_chat_id
            content: 消息文本（P3 后期支持富文本 / 卡片，``extra`` 透传）
            **extra: 平台特定参数（如飞书的 ``msg_type='interactive'`` + ``card``）

        返回：
            平台返回的 message_id / raw_response。

        阶段：P3。
        """
        raise NotImplementedError

    @abstractmethod
    async def receive_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """处理平台回调（事件订阅 / 用户消息 / 配对回执）。

        参数：
            payload: 平台原样回调体

        返回：
            归一化后的内部事件（含 channel_type / external_user_id /
            event_type / data），由路由层进一步分发到 task_orchestrator
            或 pairing 流程。

        阶段：P3。
        """
        raise NotImplementedError

    @abstractmethod
    async def register_bot(self, config: dict[str, Any]) -> dict[str, Any]:
        """注册/初始化平台 bot（首次接入或配置变更）。

        典型动作：上传 webhook URL、订阅事件、创建机器人凭据。

        阶段：P3。
        """
        raise NotImplementedError

    @abstractmethod
    async def list_groups(self) -> list[dict[str, Any]]:
        """拉取 bot 所在的群/频道列表。

        返回元素结构（统一）::

            {
                "id": "...",          # 平台侧 chat_id
                "name": "...",        # 群名
                "type": "group|im",
                "raw": {...},         # 原始字段
            }

        阶段：P3。
        """
        raise NotImplementedError
