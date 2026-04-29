# -*- coding: utf-8 -*-
"""
rag_kg 路由 —— P13-B 跨模态知识图谱对外 API

挂载点（``api/routes/__init__.py`` 用 ``prefix="/rag/kg"`` 注册）::

    POST  /api/v1/rag/kg/build                    构建 KG → 返回 kg_id
    GET   /api/v1/rag/kg/{kg_id}/entities         列出实体
    GET   /api/v1/rag/kg/{kg_id}/relations        列出关系
    GET   /api/v1/rag/kg/{kg_id}/cross-modal      仅返跨模态关系（前端可视化）

权限：登录用户即可调用；写 Neo4j 由 ``persist_to_neo4j`` 入参控制。

KG 索引：当前用进程内 dict（``_KG_INDEX``）保存最近构建的结果，便于快速实现 GET 接口。
后续若需要长期持久化，可替换为 Postgres / Redis；不影响本路由签名。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.routes.schemas.rag_kg import (
    BuildKGBody,
    BuildKGOut,
    EntitiesOut,
    EntityOut,
    KGStatistics,
    RelationOut,
    RelationsOut,
)
from src.core.deps import get_current_user_required
from src.models.user import User
from src.services.rag.kg import (
    BelongsToChainBuilder,
    EntityExtractor,
    KGResult,
    LegalKGBuilder,
    Neo4jKGWriter,
    RelationMapper,
    Segment,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# 进程内 KG 索引（生产可换 Redis / Postgres）
# ---------------------------------------------------------------------------


@dataclass
class _IndexedKG:
    kg_id: str
    owner_id: str
    result: KGResult


_KG_INDEX: dict[str, _IndexedKG] = {}


def _get_kg_or_404(kg_id: str, user: User) -> _IndexedKG:
    item = _KG_INDEX.get(kg_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"KG {kg_id} 不存在"
        )
    # 简单按 owner 隔离（管理员场景留待后续 RBAC 细化）
    if item.owner_id != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该 KG"
        )
    return item


# ---------------------------------------------------------------------------
# 序列化
# ---------------------------------------------------------------------------


def _serialize_entity(ent) -> EntityOut:
    return EntityOut(
        entity_id=ent.entity_id,
        type=ent.type.value,
        name=ent.name,
        aliases=list(ent.aliases),
        mentions=list(ent.mentions),
        properties=dict(ent.properties),
        confidence=ent.confidence,
    )


def _serialize_relation(rel) -> RelationOut:
    return RelationOut(
        relation_id=rel.relation_id,
        type=rel.type.value,
        source_entity=rel.source_entity,
        target_entity=rel.target_entity,
        properties=dict(rel.properties),
        confidence=rel.confidence,
        cross_modal=rel.cross_modal,
    )


def _statistics_from_kg(kg: KGResult) -> KGStatistics:
    s = kg.statistics or {}
    return KGStatistics(
        entity_count=s.get("entity_count", 0),
        relation_count=s.get("relation_count", 0),
        cross_modal_relation_count=s.get("cross_modal_relation_count", 0),
        entities_by_type=s.get("entities_by_type", {}),
        relations_by_type=s.get("relations_by_type", {}),
        nodes_written=s.get("nodes_written"),
        rels_written=s.get("rels_written"),
    )


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------


@router.post("/build", response_model=BuildKGOut, status_code=status.HTTP_201_CREATED)
async def build_kg(
    body: BuildKGBody,
    user: User = Depends(get_current_user_required),
) -> BuildKGOut:
    """从 segments 构建 KG。

    - ``inline_segments`` 直接传入（推荐用于测试 / mock 场景）
    - ``ingest_task_id`` 由 P13-A 反查（合入主分支后启用）
    """
    if not body.inline_segments and not body.ingest_task_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供 inline_segments 或 ingest_task_id 之一",
        )

    if body.ingest_task_id and not body.inline_segments:
        # P13-A 尚未合入主分支：返回 501，提示后续启用
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="ingest_task_id 反查依赖 P13-A 合入；当前请使用 inline_segments",
        )

    # 把 SegmentInput → Segment（KG 模块的数据契约）
    segments = [
        Segment(
            segment_id=s.segment_id,
            modality=s.modality,
            content=s.content,
            metadata=dict(s.metadata),
        )
        for s in (body.inline_segments or [])
    ]

    # 是否启用 LLM —— 当前路由层不直接拼 LLMService（避免循环依赖），如需启用真 LLM
    # 由调用方在更上层注入 callable；此处只暴露开关
    extractor = EntityExtractor(mode="llm" if body.use_llm else "mock")

    writer: Neo4jKGWriter | None = None
    if body.persist_to_neo4j:
        try:
            from src.services.graph_service import GraphService  # 局部 import 避免循环

            graph_svc = GraphService()
            writer = Neo4jKGWriter(driver=graph_svc.graph)
        except Exception:
            writer = None

    builder = LegalKGBuilder(
        extractor=extractor,
        mapper=RelationMapper(),
        chain_builder=BelongsToChainBuilder(),
        writer=writer,
    )

    kg = await builder.build(
        document_id=body.document_id,
        segments=segments,
        structure=body.structure,
    )

    kg_id = f"kg_{uuid.uuid4().hex[:16]}"
    _KG_INDEX[kg_id] = _IndexedKG(kg_id=kg_id, owner_id=str(user.id), result=kg)

    return BuildKGOut(
        kg_id=kg_id,
        document_id=kg.document_id,
        statistics=_statistics_from_kg(kg),
    )


@router.get("/{kg_id}/entities", response_model=EntitiesOut)
async def list_entities(
    kg_id: str,
    user: User = Depends(get_current_user_required),
) -> EntitiesOut:
    item = _get_kg_or_404(kg_id, user)
    return EntitiesOut(
        kg_id=kg_id,
        items=[_serialize_entity(e) for e in item.result.entities],
        total=len(item.result.entities),
    )


@router.get("/{kg_id}/relations", response_model=RelationsOut)
async def list_relations(
    kg_id: str,
    user: User = Depends(get_current_user_required),
) -> RelationsOut:
    item = _get_kg_or_404(kg_id, user)
    return RelationsOut(
        kg_id=kg_id,
        items=[_serialize_relation(r) for r in item.result.relations],
        total=len(item.result.relations),
        cross_modal_only=False,
    )


@router.get("/{kg_id}/cross-modal", response_model=RelationsOut)
async def list_cross_modal(
    kg_id: str,
    user: User = Depends(get_current_user_required),
) -> RelationsOut:
    item = _get_kg_or_404(kg_id, user)
    cross_relations = item.result.cross_modal_relations()
    return RelationsOut(
        kg_id=kg_id,
        items=[_serialize_relation(r) for r in cross_relations],
        total=len(cross_relations),
        cross_modal_only=True,
    )


__all__ = ["router"]
