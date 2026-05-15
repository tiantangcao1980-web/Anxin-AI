"""
FetchService — 信息获取栈 4 层门面（P6-A）。

对外暴露：
- ``FetchService`` / ``fetch_service`` 全局单例
- ``FetchRequest`` / ``FetchResponse`` / ``FetchTier`` / ``ExtractConfig``
- 路由 / 限流 / 合规子模块（高级用户可绕过门面直接用）

内部实现见 ``service.py``、``router.py``、``tiers/``、``compliance/``。
"""

from src.services.fetch.models import (
    ExtractConfig,
    ExtractFormat,
    FetchRequest,
    FetchResponse,
    FetchTier,
)
from src.services.fetch.service import FetchService, fetch_service

__all__ = [
    "ExtractConfig",
    "ExtractFormat",
    "FetchRequest",
    "FetchResponse",
    "FetchService",
    "FetchTier",
    "fetch_service",
]
