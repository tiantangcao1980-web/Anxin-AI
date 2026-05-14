# -*- coding: utf-8 -*-
"""
SkillRegistry.register 运行时 gate 单测 — E5 (2026-05-14)

覆盖:
1. test_register_with_valid_required_tools  — 全部 tool 已注册 → enabled=True
2. test_register_with_missing_tool_warns    — 默认 warn-only → enabled=False
3. test_register_strict_mode_raises         — strict 模式 → SkillValidationError
4. test_register_no_required_tools_passes   — 无 required_tools 字段 → 正常
5. test_disabled_skill_not_findable         — auto-disabled skill 不出现在 find_by_trigger 结果
"""

import pytest

from src.services.skill_registry.models import Skill
from src.services.skill_registry.registry import SkillRegistry, SkillValidationError


@pytest.fixture(autouse=True)
def _reset_registry(monkeypatch):
    """每个测试用独立 registry, 避免污染全局单例。"""
    monkeypatch.delenv("HARNESS_SKILL_STRICT_TOOLS", raising=False)
    SkillRegistry.reset_instance()
    yield
    SkillRegistry.reset_instance()


def test_register_with_valid_required_tools():
    """search_knowledge 是 builtin → 注册成功 + 仍 enabled。"""
    reg = SkillRegistry()
    skill = Skill(
        name="e5_ok",
        description="使用内置工具",
        required_tools=["search_knowledge"],
        triggers=["e5触发"],
    )
    reg.register(skill)
    assert reg.get("e5_ok") is not None
    assert reg.get("e5_ok").enabled is True


def test_register_with_missing_tool_warns():
    """默认 warn-only 模式: 缺失工具 → 注册成功但 enabled=False。"""
    reg = SkillRegistry()
    skill = Skill(
        name="e5_missing",
        description="工具拼错",
        required_tools=["search_knowlege"],  # typo
        triggers=["e5miss"],
    )
    reg.register(skill)
    assert reg.get("e5_missing") is not None
    assert reg.get("e5_missing").enabled is False  # auto-disabled


def test_register_strict_mode_raises(monkeypatch):
    """HARNESS_SKILL_STRICT_TOOLS=true → SkillValidationError。"""
    monkeypatch.setenv("HARNESS_SKILL_STRICT_TOOLS", "true")
    reg = SkillRegistry()
    skill = Skill(
        name="e5_strict",
        description="strict 拒绝",
        required_tools=["ghost_tool_xx"],
    )
    with pytest.raises(SkillValidationError) as exc_info:
        reg.register(skill)
    assert "ghost_tool_xx" in str(exc_info.value)


def test_register_no_required_tools_passes():
    """没声明 required_tools → 不触发 gate。"""
    reg = SkillRegistry()
    skill = Skill(name="e5_none", description="无依赖")
    reg.register(skill)
    assert reg.get("e5_none").enabled is True


def test_disabled_skill_not_findable():
    """auto-disabled skill 不应被 find_by_trigger 召回。"""
    reg = SkillRegistry()
    bad = Skill(
        name="e5_bad",
        description="bad",
        required_tools=["ghost_tool"],
        triggers=["关键词A"],
    )
    good = Skill(
        name="e5_good",
        description="good",
        required_tools=["search_knowledge"],
        triggers=["关键词A"],
    )
    reg.register(bad)
    reg.register(good)
    results = reg.find_by_trigger("我想找关键词A")
    names = [s.name for s in results]
    assert "e5_good" in names
    assert "e5_bad" not in names
