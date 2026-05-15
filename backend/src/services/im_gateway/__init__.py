"""
IM 网关服务模块（多通道 IM 适配）

参考 Hermes-Agent 多 IM 设计 + Accio Work 消息渠道 UI。
飞书优先（P3），后续扩 微信 / 钉钉 / Telegram / Slack / Discord。

主要导出：
- ``BaseIMAdapter``：所有 IM 适配器的抽象基类
- ``FeishuAdapter`` / ``WeChatAdapter`` / ``DingTalkAdapter`` /
  ``TelegramAdapter`` / ``SlackAdapter``：5 个通道的占位实现
- ``IMAdapterRegistry``：按 ``channel_type`` 路由 adapter 的注册表
- ``IMChannel`` / ``IMBinding`` / ``PairingRequest``：ORM 模型
- ``IMChannelType`` / ``PairingStatus``：枚举

实现阶段：P3（详见 ``README.md``）。
"""

from src.services.im_gateway.base import BaseIMAdapter
from src.services.im_gateway.dingtalk_adapter import DingTalkAdapter
from src.services.im_gateway.feishu_adapter import FeishuAdapter
from src.services.im_gateway.models import (
    IMBinding,
    IMChannel,
    IMChannelType,
    PairingRequest,
    PairingStatus,
)
from src.services.im_gateway.registry import IMAdapterRegistry
from src.services.im_gateway.slack_adapter import SlackAdapter
from src.services.im_gateway.telegram_adapter import TelegramAdapter
from src.services.im_gateway.wechat_adapter import WeChatAdapter

__all__ = [
    "BaseIMAdapter",
    "FeishuAdapter",
    "WeChatAdapter",
    "DingTalkAdapter",
    "TelegramAdapter",
    "SlackAdapter",
    "IMAdapterRegistry",
    "IMChannel",
    "IMBinding",
    "PairingRequest",
    "IMChannelType",
    "PairingStatus",
]
