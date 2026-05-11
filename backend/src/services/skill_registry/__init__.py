# -*- coding: utf-8 -*-
"""
Skill 注册表服务模块

运行时加载 cowork / Anthropic Skills 风格的 ``SKILL.md`` 文件，
让 agent 按 trigger 自动选择"技能包"调用。

主要导出：
- ``Skill``：运行时技能对象（dataclass，不入库）
- ``SkillLoader``：从单文件 / 目录递归加载 SKILL.md
- ``SkillRegistry``：进程内单例注册表（trigger / domain / persona 路由 + watchdog 热更）
- ``SkillParseError``：解析失败异常
- ``validate_skill`` / ``validate_all``：静态校验器

实现阶段：P5（详见 ``README.md``）。
"""

from src.services.skill_registry.loader import SkillLoader, SkillParseError
from src.services.skill_registry.models import Skill
from src.services.skill_registry.registry import SkillRegistry
from src.services.skill_registry.validators import (
    REQUIRED_FIELDS,
    validate_all,
    validate_skill,
)

__all__ = [
    "Skill",
    "SkillLoader",
    "SkillParseError",
    "SkillRegistry",
    "REQUIRED_FIELDS",
    "validate_skill",
    "validate_all",
]
