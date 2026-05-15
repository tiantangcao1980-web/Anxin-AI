"""
法律文书层级链构建：文档 → 章 → 节 → 条 → 款 → 项

输入是 P13-A ``IngestResult.structure``，理想形态：

::

    {
        "document": {"id": "doc_xxx", "title": "...."},
        "outline": [
            {"id": "ch_1", "level": "chapter", "title": "第一章 总则", "children": [
                {"id": "art_1", "level": "article", "title": "第一条 ...", "children": [
                    {"id": "cl_1", "level": "clause", "title": "第（一）款 ..."},
                ]}
            ]}
        ]
    }

P13-A 真实结构若略有出入，本模块按 ``level`` 字段做容错；缺失时退化为
**只产出 document → article 的两层链**（用 ``ARTICLE_REGEX`` 在文本里抓"第 N 条"）。

下游用法：检索时拿到一条命中条款，可以沿 BELONGS_TO 链向上拉父章上下文（任务卡说的
"检索时按链向上找上下文"）。
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from src.services.rag.kg.base import (
    Entity,
    EntityType,
    Modality,
    Relation,
    RelationType,
    Segment,
    SegmentLikeProtocol,
)
from src.services.rag.kg.ontology import ARTICLE_REGEX

LEVEL_ORDER = ("document", "part", "chapter", "section", "article", "clause", "item")


@dataclass
class _Node:
    node_id: str
    level: str
    title: str
    parent_id: str | None = None
    children: list[_Node] = field(default_factory=list)


class BelongsToChainBuilder:
    """从结构树（或文本）构建 BELONGS_TO 关系链。"""

    def build(
        self,
        document_id: str,
        structure: dict[str, Any] | None,
        segments: Iterable[SegmentLikeProtocol] | None = None,
    ) -> tuple[list[Entity], list[Relation]]:
        """返回 (新增层级实体列表, BELONGS_TO 关系列表)。

        - 层级实体类型统一为 :attr:`EntityType.LEGAL_TERM`，``properties.level`` 标识层级
        - 文档实体类型 :attr:`EntityType.GENERIC`，``properties.level="document"``
        """
        # 1. 文档根节点（始终生成）
        doc_entity = Entity(
            entity_id=f"doc_{_short_hash(document_id)}",
            type=EntityType.GENERIC,
            name=(structure or {}).get("document", {}).get("title") or document_id,
            aliases=[document_id],
            mentions=[],
            properties={"level": "document", "document_id": document_id},
            confidence=1.0,
        )

        entities: list[Entity] = [doc_entity]
        relations: list[Relation] = []

        # 2. 优先走 outline 树
        outline = (structure or {}).get("outline") if structure else None
        if outline:
            self._walk_outline(outline, doc_entity, entities, relations, document_id)
            return entities, relations

        # 3. fallback：从 segments 中抓 "第 N 条" / "第 N 章"
        if segments is None:
            return entities, relations

        chapter_node: Entity | None = None
        for raw_seg in segments:
            seg = Segment.from_protocol(raw_seg)
            if seg.modality and seg.modality != Modality.TEXT.value:
                continue
            text = seg.content or ""
            for m in ARTICLE_REGEX.finditer(text):
                title = m.group(0)
                if "章" in title or "节" in title:
                    chapter_node = self._make_level_entity(title, "chapter", document_id)
                    entities.append(chapter_node)
                    relations.append(self._belongs(chapter_node, doc_entity))
                else:
                    article_node = self._make_level_entity(title, "article", document_id)
                    entities.append(article_node)
                    parent = chapter_node or doc_entity
                    relations.append(self._belongs(article_node, parent))

        return entities, relations

    # ------------------------------------------------------------------

    def _walk_outline(
        self,
        nodes: list[dict[str, Any]],
        parent_entity: Entity,
        entities: list[Entity],
        relations: list[Relation],
        document_id: str,
    ) -> None:
        for raw in nodes:
            level = raw.get("level") or "article"
            title = raw.get("title") or raw.get("id") or ""
            ent = self._make_level_entity(
                title, level, document_id, node_id=raw.get("id")
            )
            entities.append(ent)
            relations.append(self._belongs(ent, parent_entity))

            children = raw.get("children") or []
            if children:
                self._walk_outline(children, ent, entities, relations, document_id)

    @staticmethod
    def _make_level_entity(
        title: str,
        level: str,
        document_id: str,
        *,
        node_id: str | None = None,
    ) -> Entity:
        seed = node_id or f"{document_id}::{level}::{title}"
        eid = f"struct_{_short_hash(seed)}"
        return Entity(
            entity_id=eid,
            type=EntityType.LEGAL_TERM,
            name=title or level,
            aliases=[],
            mentions=[],
            properties={"level": level, "document_id": document_id},
            confidence=1.0,
        )

    @staticmethod
    def _belongs(child: Entity, parent: Entity) -> Relation:
        seed = f"belongs::{child.entity_id}::{parent.entity_id}"
        rid = f"rel_{_short_hash(seed)}"
        return Relation(
            relation_id=rid,
            type=RelationType.BELONGS_TO,
            source_entity=child.entity_id,
            target_entity=parent.entity_id,
            properties={
                "child_level": child.properties.get("level"),
                "parent_level": parent.properties.get("level"),
            },
            confidence=1.0,
            cross_modal=False,
        )


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------


def _short_hash(seed: str) -> str:
    return hashlib.md5(seed.encode("utf-8")).hexdigest()[:16]


__all__ = ["BelongsToChainBuilder"]
