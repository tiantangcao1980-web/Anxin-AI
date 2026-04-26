# -*- coding: utf-8 -*-
"""
SkillRegistry —— 进程内运行时技能注册表

按 ``name`` / ``trigger`` / ``domain (type)`` 三种方式查询。
P5 阶段对接 agent runtime：当用户输入到达时，先用 ``find_by_trigger``
召回若干候选 skill，再注入到 system prompt / function-call 列表。
"""

from __future__ import annotations

from src.services.skill_registry.models import Skill


class SkillRegistry:
    """单例运行时技能注册表。

    使用方式（推荐通过 ``SkillRegistry.instance()`` 拿全局实例）::

        registry = SkillRegistry.instance()
        for skill in loader.load_from_directory("skills/"):
            registry.register(skill)

        candidates = registry.find_by_trigger(user_input)
    """

    _instance: "SkillRegistry | None" = None

    def __init__(self) -> None:
        self._by_name: dict[str, Skill] = {}

    # ------------------------------------------------------------------
    # 单例
    # ------------------------------------------------------------------
    @classmethod
    def instance(cls) -> "SkillRegistry":
        """返回全局单例（懒初始化）。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例（仅用于测试）。"""
        cls._instance = None

    # ------------------------------------------------------------------
    # 注册 / 查询
    # ------------------------------------------------------------------
    def register(self, skill: Skill) -> None:
        """注册一条技能（同名覆盖）。

        P5 实现升级：同名时按 version 比较，旧版打 WARN；
        触发词冲突在加载完毕后批量检测。
        """
        if not skill.name:
            raise ValueError("Skill.name 不能为空")
        self._by_name[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        """按 name 精确查询。"""
        return self._by_name.get(name)

    def find_by_trigger(self, text: str) -> list[Skill]:
        """按 trigger 子串匹配召回候选 skill 列表。

        骨架阶段使用 ``Skill.matches_trigger`` 简单包含匹配；
        P5 实现升级为：分词 + 向量召回 + LLM 重排。
        """
        if not text:
            return []
        return [s for s in self._by_name.values() if s.matches_trigger(text)]

    def list_by_domain(self, domain: str) -> list[Skill]:
        """按 ``type`` 过滤（例：'legal' / 'office' / 'research'）。"""
        return [s for s in self._by_name.values() if s.type == domain]

    def all(self) -> list[Skill]:
        """返回所有已注册 skill（拷贝列表）。"""
        return list(self._by_name.values())

    def __len__(self) -> int:
        return len(self._by_name)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._by_name
