"""
基础记忆服务类
定义所有记忆服务的通用接口和功能
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from loguru import logger


class BaseMemoryService(ABC):
    """
    记忆服务基类
    定义所有记忆服务的通用接口
    """

    def __init__(self) -> None:
        self._initialized = False

    @abstractmethod
    async def ensure_initialized(self) -> None:
        """确保服务已初始化"""
        pass

    @abstractmethod
    async def add(self, data: dict[str, Any]) -> str | None:
        """添加记忆"""
        pass

    @abstractmethod
    async def get(self, memory_id: str) -> dict[str, Any] | None:
        """获取单个记忆"""
        pass

    @abstractmethod
    async def search(
        self, query: str, top_k: int = 5, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """搜索记忆"""
        pass

    @abstractmethod
    async def update(self, memory_id: str, updates: dict[str, Any]) -> bool:
        """更新记忆"""
        pass

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        pass

    async def health_check(self) -> dict[str, Any]:
        """健康检查"""
        return {
            "service": self.__class__.__name__,
            "initialized": self._initialized,
            "timestamp": datetime.now().isoformat(),
        }

    def _log_debug(self, message: str, **kwargs: Any) -> None:
        """调试日志"""
        logger.debug(f"[{self.__class__.__name__}] {message}", **kwargs)

    def _log_info(self, message: str, **kwargs: Any) -> None:
        """信息日志"""
        logger.info(f"[{self.__class__.__name__}] {message}", **kwargs)

    def _log_warning(self, message: str, **kwargs: Any) -> None:
        """警告日志"""
        logger.warning(f"[{self.__class__.__name__}] {message}", **kwargs)

    def _log_error(self, message: str, **kwargs: Any) -> None:
        """错误日志"""
        logger.error(f"[{self.__class__.__name__}] {message}", **kwargs)
