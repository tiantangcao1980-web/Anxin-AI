"""
P5-A: SkillRegistry validators 单元测试

覆盖：
    - 缺字段（name / description）
    - trigger 内重复 / 跨 skill 冲突
    - 依赖不存在
    - 自依赖
    - 循环依赖
"""

from __future__ import annotations

from src.services.skill_registry import Skill, validate_all, validate_skill


def _ok_skill(**kwargs) -> Skill:
    return Skill(name="ok", description="ok", **kwargs)


class TestValidateSkill:
    def test_minimum_ok(self) -> None:
        assert validate_skill(_ok_skill()) == []

    def test_missing_name(self) -> None:
        s = Skill(name="", description="x")
        errs = validate_skill(s)
        assert any("name" in e for e in errs)

    def test_missing_description(self) -> None:
        s = Skill(name="n", description="")
        errs = validate_skill(s)
        assert any("description" in e for e in errs)

    def test_name_with_space(self) -> None:
        errs = validate_skill(Skill(name="bad name", description="x"))
        assert any("空格" in e for e in errs)

    def test_self_dependency(self) -> None:
        s = Skill(name="self", description="x", dependencies=["self"])
        errs = validate_skill(s)
        assert any("自依赖" in e for e in errs)

    def test_trigger_duplicate_inside_one_skill(self) -> None:
        s = Skill(name="dup", description="x", triggers=["a", "A", "b"])
        errs = validate_skill(s)
        assert any("triggers 内部重复" in e for e in errs)

    def test_empty_trigger_string(self) -> None:
        s = Skill(name="x", description="y", triggers=["a", ""])
        errs = validate_skill(s)
        assert any("空字符串" in e for e in errs)


class TestValidateAll:
    def test_trigger_conflict_across_skills(self) -> None:
        a = Skill(name="a", description="a", triggers=["合同审查"])
        b = Skill(name="b", description="b", triggers=["合同审查"])
        errs = validate_all([a, b])
        assert any("trigger 冲突" in e for e in errs)

    def test_missing_dependency(self) -> None:
        a = Skill(name="a", description="x", dependencies=["nope"])
        errs = validate_all([a])
        assert any("依赖不存在的 skill" in e for e in errs)

    def test_simple_cycle(self) -> None:
        a = Skill(name="a", description="x", dependencies=["b"])
        b = Skill(name="b", description="x", dependencies=["a"])
        errs = validate_all([a, b])
        assert any("循环依赖" in e for e in errs)

    def test_three_node_cycle(self) -> None:
        a = Skill(name="a", description="x", dependencies=["b"])
        b = Skill(name="b", description="x", dependencies=["c"])
        c = Skill(name="c", description="x", dependencies=["a"])
        errs = validate_all([a, b, c])
        assert any("循环依赖" in e for e in errs)

    def test_no_cycle_dag(self) -> None:
        a = Skill(name="a", description="x", dependencies=["b"])
        b = Skill(name="b", description="x", dependencies=["c"])
        c = Skill(name="c", description="x")
        errs = validate_all([a, b, c])
        assert not any("循环依赖" in e for e in errs)
