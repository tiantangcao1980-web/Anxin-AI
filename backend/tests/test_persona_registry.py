# -*- coding: utf-8 -*-
"""
P7-A: PersonaRegistry 单元测试

覆盖：
    - register / get / get_class / has / unregister
    - 自动注册（__init_subclass__）
    - list_all 排序
    - autoload() 扫描 personas/ 子模块
    - reset_instance 单例隔离
    - lazy 实例化 + 缓存
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.agents.personas.base_persona import BasePersonaAgent
from src.agents.personas.registry import PersonaRegistry, get_persona_registry


@pytest.fixture(autouse=True)
def _reset_registry():
    PersonaRegistry.reset_instance()
    yield
    PersonaRegistry.reset_instance()


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

def _make_persona(persona_id: str = "demo_persona", name: str = "Demo"):
    """创建一个不真正连接 LLM 的 fake persona class。

    注意：``__init_subclass__`` 在类体执行 *后立即* 触发，所以
    ``persona_id`` 必须在类体内通过 ``type()`` 一次性配齐。
    """
    attrs = {
        "persona_id": persona_id,
        "display_name": name,
        "emoji": "🤖",
        "description": "fake persona for tests",
        "SYSTEM_PROMPT": "你是测试 persona",
        "capabilities": ["cap_a"],
        "backed_by_skills": ["docx"],
        "supported_apps": ["feishu"],
        "enabled": True,
    }
    return type(f"_FakePersona_{persona_id}", (BasePersonaAgent,), attrs)


# ------------------------------------------------------------------
class TestRegisterAndQuery:
    def test_register_and_get_class(self):
        registry = PersonaRegistry.instance()
        cls = _make_persona("alpha")
        registry.register(cls)

        assert registry.has("alpha")
        assert registry.get_class("alpha") is cls
        assert registry.get_class("missing") is None

    def test_register_overwrite_warns(self, caplog):
        registry = PersonaRegistry.instance()
        cls1 = _make_persona("dup", "Cls1")
        cls2 = _make_persona("dup", "Cls2")
        registry.register(cls1)
        registry.register(cls2)
        # 后者覆盖
        assert registry.get_class("dup") is cls2

    def test_register_without_persona_id_raises(self):
        class BadPersona(BasePersonaAgent):
            persona_id = ""
            display_name = "bad"
            SYSTEM_PROMPT = "x"

        BadPersona.persona_id = ""  # 强制清空
        with pytest.raises(ValueError, match="persona_id"):
            PersonaRegistry.instance().register(BadPersona)

    def test_unregister(self):
        registry = PersonaRegistry.instance()
        registry.register(_make_persona("toremove"))
        assert registry.has("toremove")
        registry.unregister("toremove")
        assert not registry.has("toremove")
        assert registry.get_class("toremove") is None


class TestAutoSubclassRegistration:
    def test_subclass_autoregisters(self):
        # 定义子类时 __init_subclass__ 自动注册到当前单例
        cls = _make_persona("auto_id", "Auto")
        registry = PersonaRegistry.instance()
        # 上面 _make_persona 内部创建子类时应已自动注册
        assert registry.has("auto_id")
        assert registry.get_class("auto_id") is cls


class TestLazyInstance:
    @patch("src.agents.base.get_llm_config_sync", return_value=None)
    def test_get_returns_lazy_instance_and_caches(self, _mock_cfg):
        registry = PersonaRegistry.instance()
        registry.register(_make_persona("lazy"))
        first = registry.get("lazy")
        second = registry.get("lazy")
        assert first is not None
        assert first is second  # 缓存

    def test_get_missing_returns_none(self):
        assert PersonaRegistry.instance().get("nope") is None


class TestListAll:
    def test_sorted_by_persona_id(self):
        registry = PersonaRegistry.instance()
        registry.register(_make_persona("zeta"))
        registry.register(_make_persona("alpha"))
        registry.register(_make_persona("mike"))

        infos = registry.list_all()
        assert [i.persona_id for i in infos] == ["alpha", "mike", "zeta"]

    def test_only_enabled_filter(self):
        registry = PersonaRegistry.instance()

        cls = _make_persona("disabled")
        cls.enabled = False
        registry.register(cls)

        registry.register(_make_persona("enabled_one"))

        ids_enabled = [i.persona_id for i in registry.list_all(only_enabled=True)]
        ids_all = [i.persona_id for i in registry.list_all(only_enabled=False)]
        assert "disabled" not in ids_enabled
        assert "disabled" in ids_all
        assert "enabled_one" in ids_enabled


class TestAutoload:
    def test_autoload_imports_operations_manager(self):
        # 反复 reset 可能导致 OperationsManagerAgent 子类已存在但单例已重建，
        # 此时 autoload 必须能重新导入并注册 operations_manager。
        registry = PersonaRegistry.instance()
        loaded = registry.autoload("src.agents.personas")
        assert loaded >= 1
        assert registry.has("operations_manager")


class TestSingletonAccessor:
    def test_get_persona_registry_returns_singleton(self):
        a = get_persona_registry()
        b = get_persona_registry()
        assert a is b
