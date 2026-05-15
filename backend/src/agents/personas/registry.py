"""
PersonaRegistry —— V3 user-facing persona 单例注册表

功能：
    - register(persona_class)        : 手动注册（一般由 ``__init_subclass__`` 自动触发）
    - get(persona_id) -> agent       : 获取已实例化的 persona（lazy 初始化）
    - get_class(persona_id) -> cls   : 获取注册的 class
    - list_all() -> list[PersonaInfo]: 列出所有已注册 persona（API 使用）
    - autoload()                     : 扫描 ``personas/`` 目录，import 所有
                                       子模块以触发自动注册（避免漏注册）
                                       幂等：实例级 ``_autoloaded`` 标志
                                       已 True 时直接返回，避免重复扫描。
    - clear()                        : 清空已注册 class / instance / autoload 标志，
                                       但保留单例自身（区别于 reset_instance）
    - reset_instance()               : 测试用，销毁单例 + 复位调用方的 autoload
                                       guard（``src.api.routes.personas._AUTOLOADED``），
                                       让下次 ``autoload()`` 真正重新扫描，
                                       避免单例池污染。

并发：lazy instance 字典使用 dict + 原子写，单进程内足够；
高并发情况下 instances 重复创建只是冗余无副作用，不引入 lock。
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from src.agents.personas.base_persona import BasePersonaAgent, PersonaInfo


class PersonaRegistry:
    """全局单例 persona 注册表。"""

    _instance: PersonaRegistry | None = None

    def __init__(self) -> None:
        self._classes: dict[str, type[BasePersonaAgent]] = {}
        self._instances: dict[str, BasePersonaAgent] = {}
        # 幂等 autoload 标志（实例级 → reset_instance 后随单例销毁自动复位）
        self._autoloaded: bool = False

    # ------------------------------------------------------------------
    # 单例
    # ------------------------------------------------------------------
    @classmethod
    def instance(cls) -> PersonaRegistry:
        if cls._instance is None:
            cls._instance = cls()
            # 不在 instance() 中自动 bootstrap：会破坏依赖 reset_instance + 手动
            # 注入 stub 的测试（典型如 test_anxin_assistant_orchestrate）。
            # autoload guard 由 reset_instance 显式复位后，下次外部调用 autoload
            # 时会真正重新扫描 + bootstrap。
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """测试用：销毁单例，并复位调用方的 autoload guard。

        - 销毁单例 → 下次 ``instance()`` 拿到全新空 registry；
        - 复位 ``src.api.routes.personas._AUTOLOADED`` (如已 import) →
          路由层下次 ``_ensure_autoloaded()`` 会重新 ``autoload()``，
          避免「单例新建但路由 guard 仍 True」造成 registry 看起来空。

        ⚠️ 不主动 bootstrap：让需要真实 persona 的调用方（routes）显式
        调 autoload()；让需要注入 stub 的测试自由编排。
        """
        cls._instance = None
        # 反射复位路由层 autoload guard（弱依赖：路由模块未加载时安全跳过）
        try:
            import sys

            routes_mod = sys.modules.get("src.api.routes.personas")
            if routes_mod is not None and hasattr(routes_mod, "_AUTOLOADED"):
                routes_mod._AUTOLOADED = False
        except Exception:  # pragma: no cover - 防御
            pass

    # ------------------------------------------------------------------
    # 工具：从已 import 的 BasePersonaAgent 子类树补全注册
    # ------------------------------------------------------------------
    def _bootstrap_from_subclasses(self) -> int:
        """从 ``BasePersonaAgent.__subclasses__()`` 重新注册所有 persona。

        典型场景：
            - 测试用 ``reset_instance()`` 后单例为空，但 persona 模块早已
              被 import，``__init_subclass__`` 不会再次触发 → 用此方法补全。
        """
        try:
            from src.agents.personas.base_persona import BasePersonaAgent
        except Exception:  # pragma: no cover - 防御
            return 0

        added = 0
        for sub_cls in BasePersonaAgent.__subclasses__():
            pid = getattr(sub_cls, "persona_id", "")
            if pid and pid not in self._classes:
                try:
                    self.register(sub_cls)
                    added += 1
                except Exception as exc:  # pragma: no cover
                    logger.warning(f"bootstrap persona {pid} 失败: {exc}")
        return added

    # ------------------------------------------------------------------
    # 注册 / 查询
    # ------------------------------------------------------------------
    def register(self, persona_class: type[BasePersonaAgent]) -> None:
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

    def clear(self) -> None:
        """显式清空当前注册表（区别于 ``reset_instance``：保留单例自身）。

        清空内容：
            - 所有已注册的 persona class
            - 所有已实例化的 persona instance 缓存
            - autoload guard，下次 ``autoload()`` 会重新扫描

        典型场景：测试 fixture 在不销毁单例的前提下做隔离。
        """
        self._classes.clear()
        self._instances.clear()
        self._autoloaded = False

    def get_class(self, persona_id: str) -> type[BasePersonaAgent] | None:
        return self._classes.get(persona_id)

    def get(self, persona_id: str) -> BasePersonaAgent | None:
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

    def list_classes(self) -> list[type[BasePersonaAgent]]:
        return list(self._classes.values())

    def list_all(self, *, only_enabled: bool = True) -> list[PersonaInfo]:
        """列出所有 persona 元信息（不实例化）。"""
        infos: list[PersonaInfo] = []
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

        幂等：实例属性 ``_autoloaded`` 已 True 时直接返回 0（仍补一次
        bootstrap，保证调用方拿到的 registry 一定是满的）。完成后置
        ``_autoloaded = True``。

        实现细节：
            - 子模块**已被 import 过**时，``importlib.import_module`` 不会再次
              执行类体 → ``__init_subclass__`` 不会触发。此时直接遍历
              ``BasePersonaAgent.__subclasses__()`` 重新注册一次（覆盖
              ``reset_instance()`` 后单例为空的场景，常见于测试）。
        """
        if self._autoloaded:
            # 已扫描过：仅做一次兜底 bootstrap，保证 registry 不空
            self._bootstrap_from_subclasses()
            return 0

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
        self._bootstrap_from_subclasses()

        # 完成置位：后续重复调用直接走幂等分支
        self._autoloaded = True

        logger.info(
            f"PersonaRegistry.autoload: 扫描 {package_name}，"
            f"加载 {loaded} 模块，共注册 {len(self._classes)} persona"
        )
        return loaded


def get_persona_registry() -> PersonaRegistry:
    """FastAPI 依赖注入用工厂。"""
    return PersonaRegistry.instance()
