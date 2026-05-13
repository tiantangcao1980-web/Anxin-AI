# -*- coding: utf-8 -*-
"""
P5-A: SkillLoader YAML 解析单元测试

覆盖：
    - 完整 frontmatter（嵌套 list / 多行字符串）
    - 必需字段缺失 / 非法 YAML / 缺 frontmatter
    - 字段兼容（``trigger``/``triggers``、``apps``/``requires_apps``）
    - 字符串容错（单字符串当 list）
    - load_from_directory 递归 + 跳过坏文件
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from src.services.skill_registry import SkillLoader, SkillParseError


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
    return path


class TestLoaderFullYAML:
    def test_full_frontmatter(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "SKILL.md", """
            ---
            name: contract-review
            description: 合同审查与风险点识别
            version: 1.2.0
            category: legal
            triggers:
              - 合同审查
              - 帮我看看这份合同
              - 风险审核
            personas:
              - lawyer
              - executive
            requires_apps:
              - dingtalk
              - feishu
            dependencies:
              - knowledge-base
            enabled: true
            author: 安心智能助手团队
            ---

            # 合同审查 SKILL

            正文内容。
            """)
        skill = SkillLoader().load_from_file(f)
        assert skill.name == "contract-review"
        assert skill.version == "1.2.0"
        assert skill.category == "legal"
        assert skill.type == "legal"  # 兼容映射
        assert skill.triggers == ["合同审查", "帮我看看这份合同", "风险审核"]
        assert skill.personas == ["lawyer", "executive"]
        assert skill.requires_apps == ["dingtalk", "feishu"]
        assert skill.dependencies == ["knowledge-base"]
        assert skill.enabled is True
        assert skill.author == "安心智能助手团队"
        assert "正文内容" in skill.body

    def test_string_value_coerced_to_list(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "SKILL.md", """
            ---
            name: x
            description: y
            triggers: 单个字符串
            personas: lawyer
            ---

            body
            """)
        skill = SkillLoader().load_from_file(f)
        assert skill.triggers == ["单个字符串"]
        assert skill.personas == ["lawyer"]

    def test_field_aliases(self, tmp_path: Path) -> None:
        # 用 cowork 风格的 ``trigger``（单数）+ ``apps``
        f = _write(tmp_path / "SKILL.md", """
            ---
            name: alias-skill
            description: 字段别名兼容
            trigger:
              - 别名触发
            apps:
              - feishu
            ---

            body
            """)
        skill = SkillLoader().load_from_file(f)
        assert skill.triggers == ["别名触发"]
        assert skill.requires_apps == ["feishu"]

    def test_nested_dict_in_frontmatter_does_not_crash(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "SKILL.md", """
            ---
            name: nested
            description: 嵌套 dict 也不报错
            extras:
              owner:
                team: 法务
                contact: a@b.com
              flags:
                - alpha
                - beta
            ---

            body
            """)
        skill = SkillLoader().load_from_file(f)
        assert skill.name == "nested"

    def test_disabled_via_frontmatter(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "SKILL.md", """
            ---
            name: disabled-skill
            description: 显式禁用
            enabled: false
            ---
            body
            """)
        skill = SkillLoader().load_from_file(f)
        assert skill.enabled is False


class TestLoaderEdgeCases:
    def test_missing_frontmatter(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "SKILL.md", "# 没有 frontmatter 的纯 markdown\n正文")
        with pytest.raises(SkillParseError):
            SkillLoader().load_from_file(f)

    def test_missing_required_fields(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "SKILL.md", """
            ---
            name: only-name
            ---
            body
            """)
        with pytest.raises(SkillParseError):
            SkillLoader().load_from_file(f)

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "SKILL.md", """
            ---
            name: x
            description: y
            triggers:
              - "未闭合
            ---
            body
            """)
        with pytest.raises(SkillParseError):
            SkillLoader().load_from_file(f)

    def test_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            SkillLoader().load_from_file("/tmp/__nope__skill__.md")

    def test_frontmatter_must_be_mapping(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "SKILL.md", """
            ---
            - 1
            - 2
            ---
            body
            """)
        with pytest.raises(SkillParseError):
            SkillLoader().load_from_file(f)


class TestLoadFromDirectory:
    def test_recursive_load(self, tmp_path: Path) -> None:
        _write(tmp_path / "a" / "SKILL.md", """
            ---
            name: a
            description: A
            ---
            body
            """)
        _write(tmp_path / "b" / "nested" / "SKILL.md", """
            ---
            name: b
            description: B
            ---
            body
            """)
        # 一个坏文件应被跳过
        _write(tmp_path / "broken" / "SKILL.md", "no frontmatter")

        skills = SkillLoader().load_from_directory(tmp_path)
        names = sorted(s.name for s in skills)
        assert names == ["a", "b"]

    def test_lowercase_filename(self, tmp_path: Path) -> None:
        _write(tmp_path / "x" / "skill.md", """
            ---
            name: lower
            description: lower
            ---
            body
            """)
        skills = SkillLoader().load_from_directory(tmp_path)
        assert [s.name for s in skills] == ["lower"]

    def test_not_a_directory(self, tmp_path: Path) -> None:
        f = tmp_path / "file.md"
        f.write_text("hi", encoding="utf-8")
        with pytest.raises(NotADirectoryError):
            SkillLoader().load_from_directory(f)


# ===== T10: SKILL.md required_tools + tool_registry 协同 =====

class TestRequiredToolsField:
    def test_required_tools_parsed_from_frontmatter(self, tmp_path: Path) -> None:
        """T10: required_tools 列表正确解析。"""
        f = _write(tmp_path / "SKILL.md", """
            ---
            name: tool-using
            description: 需要 search_knowledge 与 legal_citation_validator
            required_tools:
              - search_knowledge
              - legal_citation_validator
            ---
            body
            """)
        skill = SkillLoader().load_from_file(f)
        assert skill.required_tools == ["search_knowledge", "legal_citation_validator"]

    def test_required_tools_dashed_alias(self, tmp_path: Path) -> None:
        """T10: required-tools (短横线) 别名兼容。"""
        f = _write(tmp_path / "SKILL.md", """
            ---
            name: dashed
            description: dashed key alias
            required-tools:
              - search_knowledge
            ---
            body
            """)
        skill = SkillLoader().load_from_file(f)
        assert skill.required_tools == ["search_knowledge"]

    def test_required_tools_default_empty(self, tmp_path: Path) -> None:
        """T10: 没声明 required_tools 时默认空列表。"""
        f = _write(tmp_path / "SKILL.md", """
            ---
            name: no-tools
            description: stateless
            ---
            body
            """)
        skill = SkillLoader().load_from_file(f)
        assert skill.required_tools == []

    def test_validate_required_tools_all_registered(self, tmp_path: Path) -> None:
        """T10: validate_required_tools 对所有已注册工具返回空列表。"""
        from src.harness.tool_registry import tool_registry
        # search_knowledge 是 builtin
        f = _write(tmp_path / "SKILL.md", """
            ---
            name: builtin
            description: only builtin
            required_tools:
              - search_knowledge
            ---
            body
            """)
        skill = SkillLoader().load_from_file(f)
        missing = skill.validate_required_tools(tool_registry)
        assert missing == []

    def test_validate_required_tools_returns_missing(self, tmp_path: Path) -> None:
        """T10: validate_required_tools 把未注册的 tool 名列出来。"""
        from src.harness.tool_registry import tool_registry
        f = _write(tmp_path / "SKILL.md", """
            ---
            name: typo
            description: has typo
            required_tools:
              - search_knowlege
              - ghost_tool_xxx
              - search_knowledge
            ---
            body
            """)
        skill = SkillLoader().load_from_file(f)
        missing = skill.validate_required_tools(tool_registry)
        assert sorted(missing) == sorted(["search_knowlege", "ghost_tool_xxx"])
