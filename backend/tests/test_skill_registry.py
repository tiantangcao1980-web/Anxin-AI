# -*- coding: utf-8 -*-
"""
P5-A: SkillRegistry 单元测试

覆盖：
    - load_directory（recursive=True/False）
    - find_by_trigger 评分排序 + top_k
    - list_by_persona / list_by_category / list_by_domain
    - toggle 启停
    - watch_directory：使用 ``_handle_fs_event`` 模拟事件，避免起 watchdog 线程
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from src.services.skill_registry import Skill, SkillRegistry


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")
    return path


@pytest.fixture
def registry() -> SkillRegistry:
    SkillRegistry.reset_instance()
    yield SkillRegistry.instance()
    SkillRegistry.reset_instance()


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    _write(tmp_path / "contract-review" / "SKILL.md", """
        ---
        name: contract-review
        description: 合同审查
        category: legal
        triggers:
          - 合同审查
          - 风险审核
        personas:
          - lawyer
        ---
        body A
        """)
    _write(tmp_path / "doc-summary" / "SKILL.md", """
        ---
        name: doc-summary
        description: 文档摘要
        category: office
        triggers:
          - 摘要
          - 总结
        personas:
          - hr
          - lawyer
        ---
        body B
        """)
    _write(tmp_path / "research" / "deep" / "SKILL.md", """
        ---
        name: deep-research
        description: 深度研究
        category: research
        triggers:
          - 深度研究
        ---
        body C
        """)
    return tmp_path


class TestLoadDirectory:
    def test_recursive_returns_count(self, registry: SkillRegistry, skills_dir: Path) -> None:
        n = registry.load_directory(skills_dir)
        assert n == 3
        assert len(registry) == 3
        assert "contract-review" in registry
        assert registry.get("deep-research").category == "research"

    def test_non_recursive_only_top_level(self, registry: SkillRegistry, tmp_path: Path) -> None:
        _write(tmp_path / "SKILL.md", """
            ---
            name: top
            description: top-level
            ---
            body
            """)
        _write(tmp_path / "child" / "SKILL.md", """
            ---
            name: child
            description: child
            ---
            body
            """)
        n = registry.load_directory(tmp_path, recursive=False)
        assert n == 1
        assert "top" in registry
        assert "child" not in registry

    def test_not_a_dir(self, registry: SkillRegistry, tmp_path: Path) -> None:
        f = tmp_path / "x.md"
        f.write_text("hi", encoding="utf-8")
        with pytest.raises(NotADirectoryError):
            registry.load_directory(f)


class TestFindByTrigger:
    def test_scores_and_top_k(self, registry: SkillRegistry, skills_dir: Path) -> None:
        registry.load_directory(skills_dir)

        # "合同审查" 命中 contract-review 一个 trigger（1分）
        results = registry.find_by_trigger("合同审查", top_k=10)
        assert [s.name for s in results] == ["contract-review"]

        # "合同审查 风险审核" 命中 contract-review 两个 trigger（2分），doc-summary 0
        results = registry.find_by_trigger("合同审查 风险审核 摘要", top_k=10)
        assert [s.name for s in results[:2]] == ["contract-review", "doc-summary"]

    def test_top_k_truncates(self, registry: SkillRegistry, skills_dir: Path) -> None:
        registry.load_directory(skills_dir)
        results = registry.find_by_trigger("合同审查 摘要 深度研究", top_k=2)
        assert len(results) == 2

    def test_disabled_skill_excluded(self, registry: SkillRegistry, skills_dir: Path) -> None:
        registry.load_directory(skills_dir)
        registry.toggle("contract-review", False)
        results = registry.find_by_trigger("合同审查", top_k=10)
        assert results == []

    def test_empty_query(self, registry: SkillRegistry) -> None:
        assert registry.find_by_trigger("") == []


class TestListByCategoryPersona:
    def test_list_by_persona(self, registry: SkillRegistry, skills_dir: Path) -> None:
        registry.load_directory(skills_dir)
        # lawyer 可见 contract-review + doc-summary + deep-research（personas 为空 = 全员）
        lawyer = sorted(s.name for s in registry.list_by_persona("lawyer"))
        assert lawyer == ["contract-review", "deep-research", "doc-summary"]

        hr = sorted(s.name for s in registry.list_by_persona("hr"))
        assert hr == ["deep-research", "doc-summary"]

    def test_list_by_category(self, registry: SkillRegistry, skills_dir: Path) -> None:
        registry.load_directory(skills_dir)
        legal = [s.name for s in registry.list_by_category("legal")]
        assert legal == ["contract-review"]

    def test_list_by_domain_old_alias(self, registry: SkillRegistry, skills_dir: Path) -> None:
        registry.load_directory(skills_dir)
        # list_by_domain 同时匹配 type 与 category
        assert any(s.name == "contract-review" for s in registry.list_by_domain("legal"))


class TestToggle:
    def test_toggle_existing(self, registry: SkillRegistry) -> None:
        registry.register(Skill(name="x", description="x"))
        s = registry.toggle("x", False)
        assert s is not None and s.enabled is False
        assert registry.get("x").enabled is False

    def test_toggle_missing(self, registry: SkillRegistry) -> None:
        assert registry.toggle("nope", True) is None

    def test_unregister(self, registry: SkillRegistry) -> None:
        registry.register(Skill(name="x", description="x"))
        assert registry.unregister("x") is True
        assert registry.unregister("x") is False


class TestWatchDirectory:
    """直接调 ``_handle_fs_event`` 模拟事件，无需起 watchdog 线程。"""

    def test_modified_event_reloads(self, registry: SkillRegistry, tmp_path: Path) -> None:
        f = _write(tmp_path / "SKILL.md", """
            ---
            name: w
            description: 初始版本
            version: 1.0.0
            ---
            v1
            """)
        registry.load_directory(tmp_path)
        assert registry.get("w").description == "初始版本"

        events: list[tuple[str, str | None]] = []

        def cb(event_type, skill):
            events.append((event_type, skill.name if skill else None))

        registry._watch_handlers.append(cb)

        # 改文件 → 触发 modified 事件
        _write(f, """
            ---
            name: w
            description: 新版本
            version: 1.0.1
            ---
            v2
            """)
        registry._handle_fs_event("modified", str(f))

        assert registry.get("w").description == "新版本"
        assert registry.get("w").version == "1.0.1"
        assert events == [("modified", "w")]

    def test_deleted_event_removes(self, registry: SkillRegistry, tmp_path: Path) -> None:
        f = _write(tmp_path / "SKILL.md", """
            ---
            name: gone
            description: x
            ---
            body
            """)
        registry.load_directory(tmp_path)
        assert "gone" in registry
        f.unlink()

        registry._handle_fs_event("deleted", str(f))
        assert "gone" not in registry

    def test_non_skill_file_ignored(self, registry: SkillRegistry, tmp_path: Path) -> None:
        f = tmp_path / "not_a_skill.txt"
        f.write_text("hi", encoding="utf-8")
        registry._handle_fs_event("modified", str(f))
        assert len(registry) == 0

    def test_observer_starts_and_stops(self, registry: SkillRegistry, tmp_path: Path) -> None:
        # 真启动一次 observer 验证集成正确，立刻停掉避免污染其它测试
        observer = registry.watch_directory(tmp_path)
        try:
            assert observer is not None
            assert observer.is_alive()
        finally:
            registry.stop_watching()
        # 停掉后 _observer 应被清空
        assert registry._observer is None
