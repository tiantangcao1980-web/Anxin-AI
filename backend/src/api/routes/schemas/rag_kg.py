"""rag_kg 路由 Pydantic schemas（请求 / 响应 DTO）。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 请求
# ---------------------------------------------------------------------------


class SegmentInput(BaseModel):
    """构建 KG 时的 segment 入参（与 P13-A IngestResult.segments 对齐）。

    在 P13-A 合并主分支前，前端 / 调用方可直接传入此格式；P13-A 落地后由
    后端从 ingest_task_id 反查。
    """

    segment_id: str
    modality: str = "text"
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class BuildKGBody(BaseModel):
    """``POST /rag/kg/build`` 请求体。"""

    document_id: str = Field(..., description="目标文档 ID（KG 内部以此关联）")
    # 二选一：ingest_task_id 走 P13-A pipeline；inline_segments 直接传切片
    ingest_task_id: str | None = Field(
        None,
        description="P13-A 解析任务 ID；后端反查 IngestResult 后构图（P13-A 合入后启用）",
    )
    inline_segments: list[SegmentInput] | None = Field(
        None, description="直接传入 segments（mock / 测试 / 调试用）"
    )
    structure: dict[str, Any] | None = Field(
        None, description="P13-A 输出的 layout structure（含 outline 树）"
    )
    use_llm: bool = Field(False, description="是否启用 LLM 抽取（默认走关键词 fallback）")
    persist_to_neo4j: bool = Field(False, description="是否写入 Neo4j")


# ---------------------------------------------------------------------------
# 响应
# ---------------------------------------------------------------------------


class EntityOut(BaseModel):
    entity_id: str
    type: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    mentions: list[dict[str, Any]] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0


class RelationOut(BaseModel):
    relation_id: str
    type: str
    source_entity: str
    target_entity: str
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    cross_modal: bool = False


class KGStatistics(BaseModel):
    entity_count: int = 0
    relation_count: int = 0
    cross_modal_relation_count: int = 0
    entities_by_type: dict[str, int] = Field(default_factory=dict)
    relations_by_type: dict[str, int] = Field(default_factory=dict)
    nodes_written: int | None = None
    rels_written: int | None = None


class BuildKGOut(BaseModel):
    kg_id: str
    document_id: str
    statistics: KGStatistics


class EntitiesOut(BaseModel):
    kg_id: str
    items: list[EntityOut]
    total: int


class RelationsOut(BaseModel):
    kg_id: str
    items: list[RelationOut]
    total: int
    cross_modal_only: bool = False


__all__ = [
    "BuildKGBody",
    "BuildKGOut",
    "EntitiesOut",
    "EntityOut",
    "KGStatistics",
    "RelationOut",
    "RelationsOut",
    "SegmentInput",
]
