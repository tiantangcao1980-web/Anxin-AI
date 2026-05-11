# -*- coding: utf-8 -*-
"""P13-B Neo4jKGWriter 单元测试（mock session）。"""

from __future__ import annotations

import os
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from src.services.rag.kg.base import (
    Entity,
    EntityType,
    KGResult,
    Relation,
    RelationType,
)
from src.services.rag.kg.neo4j_writer import (
    Neo4jKGWriter,
    _safe_label,
    _stringify_properties,
)


# ---------------------------------------------------------------------------
# 辅助：Mock session 工厂
# ---------------------------------------------------------------------------


class _MockSession:
    def __init__(self) -> None:
        self.runs: list[tuple[str, dict]] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def run(self, cypher: str, **params):
        self.runs.append((cypher, params))
        result = MagicMock()
        consume = MagicMock()
        consume.counters.nodes_deleted = 0
        result.consume.return_value = consume
        return result


@pytest.fixture
def mock_session_factory():
    """返回 (factory_callable, session_instance)。"""
    session = _MockSession()

    @contextmanager
    def factory():
        yield session

    return factory, session


# ---------------------------------------------------------------------------
# 准备样例 KG
# ---------------------------------------------------------------------------


def _sample_kg() -> KGResult:
    e1 = Entity(
        entity_id="ent_a",
        type=EntityType.LEGAL_PARTY,
        name="甲方",
        confidence=0.9,
    )
    e2 = Entity(
        entity_id="ent_b",
        type=EntityType.OBLIGATION,
        name="支付义务",
        confidence=0.7,
        properties={"clause": "应当支付货款", "tags": ["payment"]},
    )
    e3 = Entity(
        entity_id="ent_c",
        type=EntityType.SEAL,
        name="甲方公章",
        mentions=[{"segment_id": "seal_1", "char_offset": 0, "modality": "seal"}],
    )

    r1 = Relation(
        relation_id="rel_1",
        type=RelationType.OBLIGES,
        source_entity="ent_a",
        target_entity="ent_b",
        confidence=0.8,
    )
    r2 = Relation(
        relation_id="rel_2",
        type=RelationType.ATTACHED_TO,
        source_entity="ent_c",
        target_entity="ent_a",
        confidence=0.85,
        cross_modal=True,
    )

    kg = KGResult(
        document_id="doc_001",
        entities=[e1, e2, e3],
        relations=[r1, r2],
    )
    kg.compute_statistics()
    return kg


# ---------------------------------------------------------------------------
# 写入测试
# ---------------------------------------------------------------------------


def test_write_kg_with_mock_session(mock_session_factory, monkeypatch):
    factory, session = mock_session_factory
    # 强制写入：绕过 PYTEST_CURRENT_TEST 守卫
    writer = Neo4jKGWriter(session_factory=factory)
    writer._force_in_pytest = True  # type: ignore[attr-defined]

    kg = _sample_kg()
    out = writer.write_kg(kg)

    assert out["nodes_written"] == 3
    assert out["rels_written"] == 2

    # 验证 session.run 至少被调用 1 次写节点 + 2 次写关系（按 RelationType 分批）
    assert len(session.runs) >= 3
    cyphers = [c for c, _ in session.runs]
    assert any("MERGE (e:Entity" in c for c in cyphers)
    assert any("OBLIGES" in c for c in cyphers)
    assert any("ATTACHED_TO" in c for c in cyphers)


def test_write_kg_payload_stringifies_complex_properties(mock_session_factory):
    factory, session = mock_session_factory
    writer = Neo4jKGWriter(session_factory=factory)
    writer._force_in_pytest = True  # type: ignore[attr-defined]

    kg = _sample_kg()
    writer.write_kg(kg)

    # 找到节点写入那一次
    node_calls = [
        params for cypher, params in session.runs if "MERGE (e:Entity" in cypher
    ]
    assert node_calls
    nodes = node_calls[0]["nodes"]
    # ent_b 的 properties 含 list，应原样保留
    e_b = next(n for n in nodes if n["entity_id"] == "ent_b")
    assert e_b["properties"]["clause"] == "应当支付货款"
    assert e_b["properties"]["tags"] == ["payment"]


def test_write_kg_no_op_without_session():
    """没有 driver / session_factory 时只记录日志，不抛错。"""
    writer = Neo4jKGWriter()
    assert writer.is_available() is False
    out = writer.write_kg(_sample_kg())
    assert out == {"nodes_written": 0, "rels_written": 0}


def test_pytest_guard_prevents_real_write_by_default(mock_session_factory):
    """默认情况下，``PYTEST_CURRENT_TEST`` 阻止真实写入。"""
    factory, session = mock_session_factory
    writer = Neo4jKGWriter(session_factory=factory)
    # 不设 _force_in_pytest，PYTEST_CURRENT_TEST 由 pytest 自动设置

    out = writer.write_kg(_sample_kg())
    assert out == {"nodes_written": 0, "rels_written": 0}
    assert session.runs == []


def test_safe_label_rejects_unknown_relation():
    with pytest.raises(ValueError):
        _safe_label("DROP TABLE")


def test_safe_label_accepts_known_relation():
    assert _safe_label("obliges") == "OBLIGES"
    assert _safe_label("belongs_to") == "BELONGS_TO"
    assert _safe_label("attached_to") == "ATTACHED_TO"
    assert _safe_label("depicts") == "DEPICTS"


def test_stringify_properties_handles_nested():
    out = _stringify_properties(
        {
            "scalar": 1,
            "string": "hi",
            "bool": True,
            "primitives_list": [1, 2, "x"],
            "nested": {"a": 1, "b": [1, 2]},
        }
    )
    assert out["scalar"] == 1
    assert out["bool"] is True
    assert out["primitives_list"] == [1, 2, "x"]
    # 嵌套 dict 序列化为字符串
    assert isinstance(out["nested"], str)
    assert "a" in out["nested"]


def test_delete_document_kg_uses_correct_cypher(mock_session_factory):
    factory, session = mock_session_factory
    writer = Neo4jKGWriter(session_factory=factory)
    writer._force_in_pytest = True  # type: ignore[attr-defined]

    writer.delete_document_kg("doc_001")

    assert any(
        "DETACH DELETE" in c and params.get("document_id") == "doc_001"
        for c, params in session.runs
    )


def test_writer_accepts_camel_neo4j_graph_like_object():
    """传入有 ``.driver.session`` 属性的对象时（camel Neo4jGraph），写入器应能识别。"""
    fake_session = _MockSession()

    @contextmanager
    def session_cm():
        yield fake_session

    fake_driver = MagicMock()
    fake_driver.session = session_cm

    fake_camel_graph = MagicMock()
    fake_camel_graph.driver = fake_driver

    writer = Neo4jKGWriter(driver=fake_camel_graph)
    assert writer.is_available()
