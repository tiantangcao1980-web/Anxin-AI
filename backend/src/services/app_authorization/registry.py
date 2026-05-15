"""
OAuthProviderRegistry — 单例注册表（P4-A）

按 ``provider_id`` 路由到具体 ``BaseOAuthProvider`` 子类。

注册方式
--------
1. **装饰器自动注册**（推荐）::

       @register_provider
       class FeishuOAuthProvider(BaseOAuthProvider):
           provider_id = "feishu"
           ...

2. **手动注册**::

       OAuthProviderRegistry.default().register(FeishuOAuthProvider)

启动时 ``providers/__init__.py`` 会自动扫描同目录下所有 ``*_oauth.py`` 模块
并触发装饰器 → 完成注册。这样 P4-B/C/D/E 新增 provider 只需放一个文件，
无需改任何调用方代码。
"""

from __future__ import annotations

from src.services.app_authorization.base import BaseOAuthProvider


class OAuthProviderRegistry:
    """OAuth provider 单例注册表。"""

    _default: OAuthProviderRegistry | None = None

    def __init__(self) -> None:
        self._providers: dict[str, type[BaseOAuthProvider]] = {}

    # ------------------------------------------------------------------
    # 注册 / 路由
    # ------------------------------------------------------------------
    def register(self, provider_cls: type[BaseOAuthProvider]) -> type[BaseOAuthProvider]:
        """注册一个 provider 类。重复注册同 id 会覆盖（便于热替换/测试）。"""
        pid = getattr(provider_cls, "provider_id", None)
        if not pid:
            raise ValueError(f"{provider_cls.__name__} 缺少 provider_id 类属性（必须设置）")
        if not getattr(provider_cls, "display_name", None):
            raise ValueError(f"{provider_cls.__name__} 缺少 display_name 类属性")
        if not getattr(provider_cls, "category", None):
            raise ValueError(f"{provider_cls.__name__} 缺少 category 类属性")
        self._providers[pid] = provider_cls
        return provider_cls

    def unregister(self, provider_id: str) -> None:
        """注销（仅测试用）。"""
        self._providers.pop(provider_id, None)

    def get(self, provider_id: str) -> type[BaseOAuthProvider]:
        """按 ``provider_id`` 取出 provider 类，不存在抛 KeyError。"""
        if provider_id not in self._providers:
            raise KeyError(f"未注册的 OAuth provider: {provider_id}")
        return self._providers[provider_id]

    def has(self, provider_id: str) -> bool:
        """provider 是否已注册。"""
        return provider_id in self._providers

    def build(self, provider_id: str) -> BaseOAuthProvider:
        """实例化 provider（无参构造，配置由 provider 自己读 settings）。"""
        return self.get(provider_id)()

    def list_all(self) -> list[type[BaseOAuthProvider]]:
        """返回所有已注册 provider 的类列表（按 provider_id 排序）。"""
        return [self._providers[pid] for pid in sorted(self._providers.keys())]

    def list_by_category(self, category: str) -> list[type[BaseOAuthProvider]]:
        """按 category 过滤 provider 列表。"""
        return [cls for cls in self.list_all() if getattr(cls, "category", None) == category]

    # ------------------------------------------------------------------
    # 单例
    # ------------------------------------------------------------------
    @classmethod
    def default(cls) -> OAuthProviderRegistry:
        """获取默认（全局）注册表实例（懒初始化）。"""
        if cls._default is None:
            cls._default = cls()
            # 触发 providers/ 自动加载（注意：必须在 _default 赋值之后导入，
            # 否则装饰器导入 registry 时拿到的是 None）
            from src.services.app_authorization.providers import (  # noqa: F401
                _autoload_providers,
            )

            _autoload_providers()
        return cls._default

    @classmethod
    def reset_default(cls) -> None:
        """重置默认注册表（仅测试用）。"""
        cls._default = None


def register_provider(
    provider_cls: type[BaseOAuthProvider],
) -> type[BaseOAuthProvider]:
    """装饰器：把 provider 类注册到默认注册表。

    用法::

        @register_provider
        class FeishuOAuthProvider(BaseOAuthProvider):
            provider_id = "feishu"
            ...
    """
    OAuthProviderRegistry.default().register(provider_cls)
    return provider_cls


__all__ = ["OAuthProviderRegistry", "register_provider"]
