"""
sandbox_executor.config —— 沙箱模块的配置访问层

不直接定义 Settings 字段，而是从 ``src.core.config.settings`` 读取
``SANDBOX_PROVIDER``，以保持单一配置真相源。

如果未来需要更复杂的沙箱专属配置（如 E2B API Key、Docker host 等），
在 core/config.py 加字段后这里再补 helper 即可。
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.config import settings as _core_settings


@dataclass(frozen=True)
class SandboxSettings:
    """从 core.settings 投影出来的沙箱配置视图。"""

    SANDBOX_PROVIDER: str

    @classmethod
    def from_core(cls) -> SandboxSettings:
        return cls(SANDBOX_PROVIDER=getattr(_core_settings, "SANDBOX_PROVIDER", "local"))


def get_sandbox_settings() -> SandboxSettings:
    """获取沙箱配置（每次构造，不缓存——core settings 已是单例）。"""
    return SandboxSettings.from_core()


__all__ = ["SandboxSettings", "get_sandbox_settings"]
