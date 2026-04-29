# -*- coding: utf-8 -*-
"""
Neo4j KG 写入器

设计：
- **不持有 driver**：构造函数接受 ``driver`` 或 ``session_factory`` 之一；这样既可在
  生产中复用 :class:`GraphService` 的 driver，也可在测试中注入 Mock。
- **批量写入**：使用 Cypher ``UNWIND`` 一次性写多条记录，避免逐条 round-trip。
- **MERGE 幂等**：节点 ``MERGE (e:Entity {entity_id})``，边 ``MERGE (a)-[r:RELATION_TYPE
  {relation_id}]->(b)``，重跑构建不会重复写入。
- **失败降级**：driver 不可用时仅记录日志（与 GraphService 保持一致）。

接口：
- :meth:`write_kg` —— 写一个 :class:`KGResult`
- :meth:`delete_document_kg` —— 按 document_id 清理（重建场景）
"""

from __future__ import annotations

import os
from typing import Any, Callable, ContextManager, Iterable, Optional

from loguru import logger

from src.services.rag.kg.base import (
    Entity,
    KGResult,
    Relation,
    RelationType,
)


SessionFactory = Callable[[], ContextManager[Any]]


class Neo4jKGWriter:
    """KG 批量写入器。"""

    # Cypher 模板：UNWIND 批量 MERGE 节点
    _MERGE_NODES_CYPHER = """
    UNWIND $nodes AS n
    MERGE (e:Entity {entity_id: n.entity_id})
    SET e.name = n.name,
        e.type = n.type,
        e.aliases = n.aliases,
        e.confidence = n.confidence,
        e.document_id = n.document_id,
        e.modality = n.modality,
        e.properties = n.properties,
        e.updated_at = timestamp()
    """

    # Cypher 模板：UNWIND 批量 MERGE 关系（按 relation_id 幂等）
    # type 字段动态——通过 apoc.create.relationship 或手工 case 切。这里我们按 type
    # 拆批（每个 RelationType 一次 UNWIND），避免依赖 APOC。
    _MERGE_RELS_CYPHER_TEMPLATE = """
    UNWIND $rels AS r
    MATCH (a:Entity {{entity_id: r.source_entity}})
    MATCH (b:Entity {{entity_id: r.target_entity}})
    MERGE (a)-[rel:{rel_label} {{relation_id: r.relation_id}}]->(b)
    SET rel.confidence = r.confidence,
        rel.cross_modal = r.cross_modal,
        rel.properties = r.properties,
        rel.document_id = r.document_id,
        rel.updated_at = timestamp()
    """

    _DELETE_DOC_CYPHER = """
    MATCH (e:Entity {document_id: $document_id})
    DETACH DELETE e
    """

    def __init__(
        self,
        *,
        session_factory: Optional[SessionFactory] = None,
        driver: Any = None,
        batch_size: int = 200,
    ) -> None:
        """
        Parameters
        ----------
        session_factory:
            返回 ``with`` 兼容 session 对象的工厂；优先级最高（便于注入 Mock）
        driver:
            neo4j ``Driver`` 或 camel ``Neo4jGraph`` 实例（取后者的 ``.driver``）
        """
        if session_factory is not None:
            self._session_factory: Optional[SessionFactory] = session_factory
        elif driver is not None:
            real_driver = getattr(driver, "driver", driver)
            if real_driver is None or not hasattr(real_driver, "session"):
                logger.warning("Neo4jKGWriter: driver 不可用，将以 no-op 模式运行")
                self._session_factory = None
            else:
                self._session_factory = real_driver.session  # type: ignore[assignment]
        else:
            self._session_factory = None

        self.batch_size = batch_size

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        return self._session_factory is not None

    def write_kg(self, kg: KGResult) -> dict[str, int]:
        """把 ``KGResult`` 写入 Neo4j，返回 ``{nodes_written, rels_written}``。"""
        if not self.is_available():
            logger.warning("Neo4j 不可用，跳过 KG 写入")
            return {"nodes_written": 0, "rels_written": 0}

        # 跑测时拒绝真写
        if os.environ.get("PYTEST_CURRENT_TEST") and not getattr(
            self, "_force_in_pytest", False
        ):
            logger.info("PYTEST 环境，跳过真实 Neo4j 写入")
            return {"nodes_written": 0, "rels_written": 0}

        nodes_written = 0
        rels_written = 0

        with self._session_factory() as session:  # type: ignore[misc]
            # 1. 写节点（按 batch）
            node_payload = [self._entity_to_payload(e, kg.document_id) for e in kg.entities]
            for chunk in _chunks(node_payload, self.batch_size):
                session.run(self._MERGE_NODES_CYPHER, nodes=chunk)
                nodes_written += len(chunk)

            # 2. 写关系（按 RelationType 分批 UNWIND）
            by_type: dict[RelationType, list[dict]] = {}
            for r in kg.relations:
                by_type.setdefault(r.type, []).append(
                    self._relation_to_payload(r, kg.document_id)
                )
            for rtype, payload in by_type.items():
                cypher = self._MERGE_RELS_CYPHER_TEMPLATE.format(
                    rel_label=_safe_label(rtype.value)
                )
                for chunk in _chunks(payload, self.batch_size):
                    session.run(cypher, rels=chunk)
                    rels_written += len(chunk)

        return {"nodes_written": nodes_written, "rels_written": rels_written}

    def delete_document_kg(self, document_id: str) -> int:
        if not self.is_available():
            return 0
        if os.environ.get("PYTEST_CURRENT_TEST") and not getattr(
            self, "_force_in_pytest", False
        ):
            return 0
        with self._session_factory() as session:  # type: ignore[misc]
            result = session.run(self._DELETE_DOC_CYPHER, document_id=document_id)
            try:
                summary = result.consume()
                return getattr(summary.counters, "nodes_deleted", 0)
            except Exception:
                return 0

    # ------------------------------------------------------------------
    # Payload 转换（把 dataclass 拍平成 Neo4j 友好的属性字典）
    # ------------------------------------------------------------------

    @staticmethod
    def _entity_to_payload(ent: Entity, document_id: str) -> dict[str, Any]:
        modality = ""
        if ent.mentions:
            modality = ent.mentions[0].get("modality") or ""
        return {
            "entity_id": ent.entity_id,
            "name": ent.name,
            "type": ent.type.value,
            "aliases": list(ent.aliases),
            "confidence": float(ent.confidence),
            "document_id": document_id,
            "modality": modality,
            "properties": _stringify_properties(ent.properties),
        }

    @staticmethod
    def _relation_to_payload(rel: Relation, document_id: str) -> dict[str, Any]:
        return {
            "relation_id": rel.relation_id,
            "source_entity": rel.source_entity,
            "target_entity": rel.target_entity,
            "confidence": float(rel.confidence),
            "cross_modal": bool(rel.cross_modal),
            "document_id": document_id,
            "properties": _stringify_properties(rel.properties),
        }


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------


def _chunks(seq: list, size: int) -> Iterable[list]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


_RELATION_LABEL_WHITELIST = {rt.value for rt in RelationType}


def _safe_label(label: str) -> str:
    """避免 Cypher 注入：只允许已知 RelationType。"""
    if label not in _RELATION_LABEL_WHITELIST:
        raise ValueError(f"Unsafe relation label: {label}")
    return label.upper()


def _stringify_properties(props: dict[str, Any]) -> dict[str, Any]:
    """Neo4j 不支持嵌套 dict 作为属性值——把非原语类型 JSON 化。"""
    import json

    safe: dict[str, Any] = {}
    for k, v in (props or {}).items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            safe[k] = v
        elif isinstance(v, (list, tuple)) and all(
            isinstance(x, (str, int, float, bool)) for x in v
        ):
            safe[k] = list(v)
        else:
            try:
                safe[k] = json.dumps(v, ensure_ascii=False, default=str)
            except Exception:
                safe[k] = str(v)
    return safe


__all__ = ["Neo4jKGWriter", "SessionFactory"]
