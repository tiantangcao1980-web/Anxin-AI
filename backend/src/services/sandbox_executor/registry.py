# -*- coding: utf-8 -*-
"""
sandbox_executor.registry —— SandboxProvider 注册表

用法：

    @SandboxProviderRegistry.register
    class MyProvider(BaseSandboxProvider):
        provider_type = "my"
        ...

    provider = SandboxProviderRegistry.get("my")()      # 取注册的类并实例化
    default  = SandboxProviderRegistry.default()        # 按 config 取默认 Provider 实例
"""

from __future__ import annotations

from typing import Type

from loguru import logger

from src.services.sandbox_executor.base import BaseSandboxProvider
from src.services.sandbox_executor.codex_cloud_provider import CodexCloudProvider
from src.services.sandbox_executor.config import get_sandbox_settings
from src.services.sandbox_executor.docker_provider import DockerProvider
from src.services.sandbox_executor.e2b_provider import E2BProvider
from src.services.sandbox_executor.local_provider import LocalProvider


class SandboxProviderRegistry:
    """全局 Provider 注册中心。

    类级单例风格：所有方法都是 classmethod。
    """

    _registry: dict[str, Type[BaseSandboxProvider]] = {}

    # ------------------------------------------------------------------
    # 注册
    # ------------------------------------------------------------------

    @classmethod
    def register(cls, provider_class: Type[BaseSandboxProvider]) -> Type[BaseSandboxProvider]:
        """装饰器：把 Provider 类按 ``provider_type`` 注册进表。"""
        ptype = getattr(provider_class, "provider_type", "")
        if not ptype:
            raise ValueError(f"{provider_class.__name__} 必须设置 provider_type 类属性")
        if ptype in cls._registry and cls._registry[ptype] is not provider_class:
            logger.warning(f"[SandboxRegistry] 覆盖注册 provider_type={ptype}")
        cls._registry[ptype] = provider_class
        return provider_class

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    @classmethod
    def get(cls, provider_type: str) -> Type[BaseSandboxProvider]:
        """根据 provider_type 取 Provider **类**（未实例化）。"""
        if provider_type not in cls._registry:
            available = ", ".join(sorted(cls._registry.keys())) or "<empty>"
            raise KeyError(f"未注册的 provider_type={provider_type!r}，已注册：{available}")
        return cls._registry[provider_type]

    @classmethod
    def default(cls) -> BaseSandboxProvider:
        """从配置读默认 provider_type，返回**实例化**好的 Provider。"""
        settings = get_sandbox_settings()
        provider_cls = cls.get(settings.SANDBOX_PROVIDER)
        return provider_cls()

    @classmethod
    def all(cls) -> dict[str, Type[BaseSandboxProvider]]:
        """返回当前注册表的浅拷贝（调试用）。"""
        return dict(cls._registry)

    @classmethod
    def reset(cls) -> None:
        """清空注册表（仅测试用）。"""
        cls._registry.clear()


# ---------------------------------------------------------------------------
# 模块加载即注册内置 Provider
# ---------------------------------------------------------------------------

SandboxProviderRegistry.register(LocalProvider)
SandboxProviderRegistry.register(DockerProvider)
SandboxProviderRegistry.register(E2BProvider)
SandboxProviderRegistry.register(CodexCloudProvider)


__all__ = ["SandboxProviderRegistry"]
