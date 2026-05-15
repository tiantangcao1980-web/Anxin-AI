"""
:class:`LegalKGBuilder` —— 法律领域 KG 构建 orchestration

把 ``EntityExtractor`` / ``RelationMapper`` / ``BelongsToChainBuilder`` 串起来，
可选 ``Neo4jKGWriter`` 在末尾落库。

调用方典型用法：

    extractor = EntityExtractor(llm_call=my_llm_call)
    builder = LegalKGBuilder(
        extractor=extractor,
        mapper=RelationMapper(),
        chain_builder=BelongsToChainBuilder(),
        writer=None,  # 测试不写库；生产传 Neo4jKGWriter(...)
    )
    kg = await builder.build("doc_001", segments, structure)
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from loguru import logger

from src.services.rag.kg.base import (
    KGBuilder,
    KGResult,
    SegmentLikeProtocol,
)
from src.services.rag.kg.belongs_to_chain import BelongsToChainBuilder
from src.services.rag.kg.entity_extractor import EntityExtractor
from src.services.rag.kg.neo4j_writer import Neo4jKGWriter
from src.services.rag.kg.relation_mapper import RelationMapper


class LegalKGBuilder(KGBuilder):
    """法律领域 KG 构建器（默认实现）。"""

    def __init__(
        self,
        *,
        extractor: EntityExtractor | None = None,
        mapper: RelationMapper | None = None,
        chain_builder: BelongsToChainBuilder | None = None,
        writer: Neo4jKGWriter | None = None,
    ) -> None:
        self.extractor = extractor or EntityExtractor(mode="mock")
        self.mapper = mapper or RelationMapper()
        self.chain_builder = chain_builder or BelongsToChainBuilder()
        self.writer = writer

    async def build(
        self,
        document_id: str,
        segments: Iterable[SegmentLikeProtocol],
        structure: dict[str, Any] | None = None,
    ) -> KGResult:
        # 把 segments 物化为 list（多次遍历）
        seg_list = list(segments)

        # 1. 实体抽取
        entities = await self.extractor.extract(seg_list)

        # 2. 关系映射（同模态 + 跨模态）
        relations = self.mapper.map(entities, seg_list)

        # 3. 层级链
        chain_entities, chain_relations = self.chain_builder.build(document_id, structure, seg_list)
        entities = entities + chain_entities
        relations = relations + chain_relations

        # 4. 汇总
        kg = KGResult(
            document_id=document_id,
            entities=entities,
            relations=relations,
        )
        kg.compute_statistics()

        # 5. 可选落库
        if self.writer is not None and self.writer.is_available():
            try:
                wr = self.writer.write_kg(kg)
                kg.statistics.update(wr)
            except Exception as exc:
                logger.warning(f"KG 写入 Neo4j 失败：{exc}")

        return kg


__all__ = ["LegalKGBuilder"]
