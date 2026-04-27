# -*- coding: utf-8 -*-
"""
PersonaRegistry —— V3 user-facing persona 单例注册表

功能：
    - register(persona_class)        : 手动注册（一般由 ``__init_subclass__`` 自动触发）
    - get(persona_id) -> agent       : 获取已实例化的 persona（lazy 初始化）
    - get_class(persona_id) -> cls   : 获取注册的 class
    - list_all() -> list[PersonaInfo]: 列出所有已注册 persona（API 使用）
    - autoload()                     : 扫描 ``personas/`` 目录，import 所有
                                       子模块以触发自动注册（避免漏注册）
    - reset_instance()               : 测试用，清空单例

并发：lazy instance 字典使用 dict + 原子写，单进程内足够；
高并发情况下 instances 重复创建只是冗余无副作用，不引入 lock。
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from loguru import logger

if TYPE_CHECKING:
    from src.agents.personas.base_persona import BasePersonaAgent, PersonaInfo


class PersonaRegistry:
    """全局单例 persona 注册表。"""

    _instance: Optional["PersonaRegistry"] = None

    def __init__(self) -> None:
        self._classes: Dict[str, Type["BasePersonaAgent"]] = {}
        self._instances: Dict[str, "BasePersonaAgent"] = {}

    # ------------------------------------------------------------------
    # 单例
    # ------------------------------------------------------------------
    @classmethod
    def instance(cls) -> "PersonaRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """测试用：清空单例。"""
        cls._instance = None

    # ------------------------------------------------------------------
    # 注册 / 查询
    # ------------------------------------------------------------------
    def register(self, persona_class: Type["BasePersonaAgent"]) -> None:
        persona_id = getattr(persona_class, "persona_id", "")
        if not persona_id:
            raise ValueError(
                f"无法注册 {persona_class.__name__}：缺少 persona_id 属性"
            )
        existing = self._classes.get(persona_id)
        if existing is not None and existing is not persona_class:
            logger.warning(
                f"PersonaRegistry: persona_id={persona_id} 被重复注册，"
                f"覆盖 {existing.__name__} → {persona_class.__name__}"
            )
        self._classes[persona_id] = persona_class
        # 注册时清掉缓存的旧实例（避免热重载残留）
        self._instances.pop(persona_id, None)
        logger.debug(f"PersonaRegistry: 已注册 {persona_id} → {persona_class.__name__}")

    def unregister(self, persona_id: str) -> None:
        self._classes.pop(persona_id, None)
        self._instances.pop(persona_id, None)

    def get_class(self, persona_id: str) -> Optional[Type["BasePersonaAgent"]]:
        return self._classes.get(persona_id)

    def get(self, persona_id: str) -> Optional["BasePersonaAgent"]:
        """lazy 实例化。"""
        if persona_id in self._instances:
            return self._instances[persona_id]
        cls = self._classes.get(persona_id)
        if cls is None:
            return None
        try:
            agent = cls()
        except Exception as exc:
            logger.error(f"实例化 persona {persona_id} 失败: {exc}")
            return None
        self._instances[persona_id] = agent
        return agent

    def has(self, persona_id: str) -> bool:
        return persona_id in self._classes

    def list_classes(self) -> List[Type["BasePersonaAgent"]]:
        return list(self._classes.values())

    def list_all(self, *, only_enabled: bool = True) -> List["PersonaInfo"]:
        """列出所有 persona 元信息（不实例化）。"""
        infos: List["PersonaInfo"] = []
        for cls in self._classes.values():
            info = cls.get_info()
            if only_enabled and not info.enabled:
                continue
            infos.append(info)
        # 稳定排序：按 persona_id 字母序
        infos.sort(key=lambda i: i.persona_id)
        return infos

    # ------------------------------------------------------------------
    # autoload
    # ------------------------------------------------------------------
    def autoload(self, package_name: str = "src.agents.personas") -> int:
        """扫描 ``personas/`` 子模块并 import，触发各子类的 ``__init_subclass__``。

        返回扫到并加载成功的子模块数量。

        实现细节：
            - 子模块**已被 import 过**时，``importlib.import_module`` 不会再次
              执行类体 → ``__init_subclass__`` 不会触发。此时直接遍历
              ``BasePersonaAgent.__subclasses__()`` 重新注册一次（覆盖
              ``reset_instance()`` 后单例为空的场景，常见于测试）。
        """
        try:
            package = importlib.import_module(package_name)
        except ImportError as exc:
            logger.warning(f"PersonaRegistry.autoload: 无法 import {package_name}: {exc}")
            return 0

        # 跳过基础模块，避免重复导入造成的 __init_subclass__ 噪音
        skip = {"__init__", "base_persona", "registry"}
        loaded = 0
        for module_info in pkgutil.iter_modules(package.__path__):
            if module_info.ispkg or module_info.name in skip:
                continue
            full_name = f"{package_name}.{module_info.name}"
            try:
                importlib.import_module(full_name)
                loaded += 1
            except Exception as exc:  # pragma: no cover - 防御
                logger.error(f"加载 persona 模块失败 {full_name}: {exc}")

        # 兜底：扫描已存在的子类，确保单例 reset 后能重新注册
        try:
            from src.agents.personas.base_persona import BasePersonaAgent

            for cls in BasePersonaAgent.__subclasses__():
                pid = getattr(cls, "persona_id", "")
                if pid and pid not in self._classes:
                    try:
                        self.register(cls)
                    except Exception as exc:  # pragma: no cover
                        logger.warning(f"补注册 persona {pid} 失败: {exc}")
        except Exception:  # pragma: no cover
            pass

        logger.info(
            f"PersonaRegistry.autoload: 扫描 {package_name}，"
            f"加载 {loaded} 模块，共注册 {len(self._classes)} persona"
        )
        return loaded


def get_persona_registry() -> PersonaRegistry:
    """FastAPI 依赖注入用工厂。"""
    return PersonaRegistry.instance()
