# -*- coding: utf-8 -*-
"""
P13-B 知识图谱核心数据契约

设计原则：
1. 与 P13-A 解耦——只通过 :class:`SegmentLikeProtocol` (duck typing) 消费
   ``IngestResult.segments``，避免 import 跨模块。
2. ``Entity`` / ``Relation`` 携带 ``confidence`` 与 ``cross_modal`` 标记，便于
   下游 P13-C 在 retrieval re-rank 时按权重融合。
3. ``KGBuilder`` 是 orchestration 抽象——子类按需组合 extractor/mapper/writer。

对外字段命名沿用任务描述（``entity_id``/``source_entity``/``target_entity`` 等），
保持与 P13-C / 前端 KG 可视化的契约一致。
"""

from __future__ import annotations

import abc
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Iterable, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Modality（与 P13-A 的多模态切片对齐）
# ---------------------------------------------------------------------------


class Modality(str, Enum):
    """与 P13-A IngestResult.segments 的 modality 字段共享词表。"""

    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    FORMULA = "formula"
    SEAL = "seal"
    SIGNATURE = "signature"
    UNKNOWN = "unknown"


@runtime_checkable
class SegmentLikeProtocol(Protocol):
    """P13-A IngestResult.segments 的最小消费契约。

    只读取下列字段，避免对 P13-A 的具体实现产生强依赖。
    P13-A 真实落地后只需保证其 Segment 类含有以下属性即可（dataclass / pydantic 均可）。
    """

    segment_id: str
    modality: str
    content: str
    metadata: dict[str, Any]


@dataclass
class Segment:
    """KG 模块自带的 Segment 数据类。

    在 P13-A 尚未合入主分支前，本类作为契约 stub；P13-A 合入后亦可直接用其
    ``Segment`` 替换——两者通过 :class:`SegmentLikeProtocol` 兼容。
    """

    segment_id: str
    modality: str = Modality.TEXT.value
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_protocol(cls, seg: SegmentLikeProtocol) -> "Segment":
        return cls(
            segment_id=seg.segment_id,
            modality=str(seg.modality),
            content=seg.content,
            metadata=dict(seg.metadata or {}),
        )


# ---------------------------------------------------------------------------
# Entity / Relation 类型枚举
# ---------------------------------------------------------------------------


class EntityType(str, Enum):
    """法律领域实体类型（11 种）。"""

    LEGAL_PARTY = "legal_party"          # 合同当事人（甲方/乙方/丙方/抬头）
    LEGAL_TERM = "legal_term"            # 法律术语
    OBLIGATION = "obligation"            # 义务条款
    RIGHT = "right"                      # 权利条款
    REGULATION = "regulation"            # 法规引用（《民法典》第 N 条等）
    AMOUNT = "amount"                    # 金额
    DATE = "date"                        # 日期
    SEAL = "seal"                        # 公章
    SIGNATURE = "signature"              # 签字
    TABLE_DATA = "table_data"            # 表格数据点
    GENERIC = "generic"                  # 兜底


class RelationType(str, Enum):
    """实体关系类型（7 种）。"""

    BELONGS_TO = "belongs_to"            # 第二条 → 第一章 → 文档
    OBLIGES = "obliges"                  # 甲方 → 付款义务
    REFERENCES = "references"            # 引用法规
    ATTACHED_TO = "attached_to"          # 公章 → 合同
    SAME_AS = "same_as"                  # 别名等价
    DEPICTS = "depicts"                  # 图片 → 描述
    CONTAINS = "contains"                # 表格 → 数据点


# ---------------------------------------------------------------------------
# Entity / Relation / KGResult
# ---------------------------------------------------------------------------


@dataclass
class Entity:
    """图谱中的实体节点。"""

    entity_id: str
    type: EntityType
    name: str
    aliases: list[str] = field(default_factory=list)
    # mentions: 列举此实体在哪些 segment / 何处被引用，包含 modality 便于 cross-modal
    # 形如 [{"segment_id": "...", "char_offset": 12, "modality": "text"}]
    mentions: list[dict[str, Any]] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    def merge(self, other: "Entity") -> "Entity":
        """同名实体合并：合并 aliases / mentions / properties，confidence 取较大。"""
        if other.name != self.name and other.name not in self.aliases:
            self.aliases.append(other.name)
        for alias in other.aliases:
            if alias not in self.aliases and alias != self.name:
                self.aliases.append(alias)
        self.mentions.extend(other.mentions)
        for k, v in other.properties.items():
            self.properties.setdefault(k, v)
        self.confidence = max(self.confidence, other.confidence)
        return self

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["type"] = self.type.value
        return d


@dataclass
class Relation:
    """图谱中的边。"""

    relation_id: str
    type: RelationType
    source_entity: str  # entity_id
    target_entity: str  # entity_id
    properties: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    cross_modal: bool = False  # 是否跨模态——下游可据此加权

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["type"] = self.type.value
        return d


@dataclass
class KGResult:
    """单文档 KG 构建产物。"""

    document_id: str
    entities: list[Entity] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)

    def cross_modal_relations(self) -> list[Relation]:
        return [r for r in self.relations if r.cross_modal]

    def compute_statistics(self) -> dict[str, Any]:
        """重新统计，写回 ``statistics`` 字段。"""
        by_type: dict[str, int] = {}
        for e in self.entities:
            by_type[e.type.value] = by_type.get(e.type.value, 0) + 1

        rel_by_type: dict[str, int] = {}
        cross_modal_count = 0
        for r in self.relations:
            rel_by_type[r.type.value] = rel_by_type.get(r.type.value, 0) + 1
            if r.cross_modal:
                cross_modal_count += 1

        stats = {
            "entity_count": len(self.entities),
            "relation_count": len(self.relations),
            "cross_modal_relation_count": cross_modal_count,
            "entities_by_type": by_type,
            "relations_by_type": rel_by_type,
        }
        self.statistics = stats
        return stats

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "entities": [e.to_dict() for e in self.entities],
            "relations": [r.to_dict() for r in self.relations],
            "statistics": self.statistics,
        }


# ---------------------------------------------------------------------------
# KGBuilder 抽象基类
# ---------------------------------------------------------------------------


class KGBuilder(abc.ABC):
    """从 segments 构建 KG 的 orchestration 抽象。

    标准流程：
    1. ``extract_entities(segments)`` → list[Entity]
    2. ``map_relations(entities, segments)`` → list[Relation]
    3. ``build_belongs_to_chain(structure)`` → list[Relation]
    4. ``write(kg_result)`` → 落库
    """

    @abc.abstractmethod
    async def build(
        self,
        document_id: str,
        segments: Iterable[SegmentLikeProtocol],
        structure: dict[str, Any] | None = None,
    ) -> KGResult:
        """主入口。"""
        raise NotImplementedError


__all__ = [
    "Entity",
    "EntityType",
    "KGBuilder",
    "KGResult",
    "Modality",
    "Relation",
    "RelationType",
    "Segment",
    "SegmentLikeProtocol",
]
