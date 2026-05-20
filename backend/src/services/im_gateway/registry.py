"""
IM 适配器注册表

按 ``channel_type`` 路由到具体 ``BaseIMAdapter`` 子类，
默认会在导入时自动注册 5 个内置 adapter（飞书 / 微信 / 钉钉 / Telegram / Slack）。

用法::

    registry = IMAdapterRegistry.default()
    adapter = registry.build("feishu", config={"app_id": "...", "app_secret": "..."})
    await adapter.send_message("oc_xxx", "hello")
"""

from __future__ import annotations

from typing import Any

from src.services.im_gateway.base import BaseIMAdapter
from src.services.im_gateway.models import IMChannelType


class IMAdapterRegistry:
    """IM 适配器注册表。

    单实例 / 全局缺省可通过 ``IMAdapterRegistry.default()`` 获取。
    """

    _default: IMAdapterRegistry | None = None

    def __init__(self) -> None:
        self._adapters: dict[str, type[BaseIMAdapter]] = {}

    # ------------------------------------------------------------------
    # 注册 / 路由
    # ------------------------------------------------------------------
    def register(self, adapter_cls: type[BaseIMAdapter]) -> None:
        """注册一个 adapter 类。

        要求 ``adapter_cls.channel_type`` 非空。
        """
        if not adapter_cls.channel_type:
            raise ValueError(f"{adapter_cls.__name__} 缺少 channel_type 类属性")
        self._adapters[adapter_cls.channel_type] = adapter_cls

    def get(self, channel_type: str) -> type[BaseIMAdapter]:
        """按 ``channel_type`` 取出 adapter 类。"""
        if channel_type not in self._adapters:
            raise KeyError(f"未注册的 IM 通道类型: {channel_type}")
        return self._adapters[channel_type]

    def build(
        self,
        channel_type: str,
        config: dict[str, Any] | None = None,
    ) -> BaseIMAdapter:
        """实例化指定通道的 adapter（注入 config）。"""
        return self.get(channel_type)(config=config)

    def list_supported(self) -> list[str]:
        """列出已注册的通道类型。"""
        return sorted(self._adapters.keys())

    # ------------------------------------------------------------------
    # 默认注册表（含 5 个内置 adapter）
    # ------------------------------------------------------------------
    @classmethod
    def default(cls) -> IMAdapterRegistry:
        """返回（懒初始化的）默认注册表。"""
        if cls._default is None:
            # 延迟导入，避免循环引用
            from src.services.im_gateway.dingtalk_adapter import DingTalkAdapter
            from src.services.im_gateway.feishu_adapter import FeishuAdapter
            from src.services.im_gateway.slack_adapter import SlackAdapter
            from src.services.im_gateway.telegram_adapter import TelegramAdapter
            from src.services.im_gateway.wechat_adapter import WeChatAdapter

            registry = cls()
            for adapter_cls in (
                FeishuAdapter,
                WeChatAdapter,
                DingTalkAdapter,
                TelegramAdapter,
                SlackAdapter,
            ):
                registry.register(adapter_cls)
            cls._default = registry
        return cls._default

    # 测试用：清空单例
    @classmethod
    def reset_default(cls) -> None:
        """重置默认注册表（仅用于测试）。"""
        cls._default = None


# 兼容性：枚举值可枚举
SUPPORTED_CHANNEL_TYPES: tuple[str, ...] = tuple(t.value for t in IMChannelType)
