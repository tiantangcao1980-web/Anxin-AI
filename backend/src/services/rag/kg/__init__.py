"""
P13-B 跨模态知识图谱构建包

借鉴 HKUDS RAG-Anything 的思想：实体抽取 + 跨模态关系映射 → Neo4j。
对外的"积木"组件：

- :class:`KGBuilder` 抽象基类与数据契约（``base.py``）
- :class:`EntityExtractor` LLM/关键词混合抽取（``entity_extractor.py``）
- :class:`RelationMapper` 同模态 + 跨模态关系映射（``relation_mapper.py``）
- :class:`Neo4jKGWriter` 批量写入 Neo4j（``neo4j_writer.py``）
- 法律领域本体（``ontology.py``）
- 章-条-款-项层级链（``belongs_to_chain.py``）
"""

from src.services.rag.kg.base import (
    Entity,
    EntityType,
    KGBuilder,
    KGResult,
    Modality,
    Relation,
    RelationType,
    Segment,
    SegmentLikeProtocol,
)
from src.services.rag.kg.belongs_to_chain import BelongsToChainBuilder
from src.services.rag.kg.builder import LegalKGBuilder
from src.services.rag.kg.entity_extractor import EntityExtractor
from src.services.rag.kg.neo4j_writer import Neo4jKGWriter
from src.services.rag.kg.ontology import (
    LEGAL_OBLIGATION_KEYWORDS,
    LEGAL_PARTY_KEYWORDS,
    LEGAL_REGULATION_PATTERNS,
    LEGAL_RIGHT_KEYWORDS,
    classify_entity,
)
from src.services.rag.kg.relation_mapper import RelationMapper

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
    "EntityExtractor",
    "LegalKGBuilder",
    "RelationMapper",
    "Neo4jKGWriter",
    "BelongsToChainBuilder",
    "classify_entity",
    "LEGAL_PARTY_KEYWORDS",
    "LEGAL_OBLIGATION_KEYWORDS",
    "LEGAL_RIGHT_KEYWORDS",
    "LEGAL_REGULATION_PATTERNS",
]
