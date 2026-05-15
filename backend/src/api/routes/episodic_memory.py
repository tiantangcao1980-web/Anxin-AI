"""
情景记忆/经验中心 API 路由
提供经验记忆的 CRUD、评分、检索功能
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from loguru import logger
from pydantic import BaseModel, Field

from src.core.deps import Permission, get_current_user_required, require_permission
from src.core.responses import UnifiedResponse
from src.models.user import User
from src.services.episodic_memory_service import episodic_memory

router = APIRouter()


# ============ 请求/响应模型 ============


class MemoryCreate(BaseModel):
    """创建经验记忆"""

    task_description: str = Field(..., description="任务描述")
    plan: list[dict[str, Any]] = Field(default_factory=list, description="执行计划")
    final_result: dict[str, Any] = Field(default_factory=dict, description="最终结果")
    user_feedback: dict[str, Any] | None = Field(None, description="用户反馈 {rating, comment}")
    metadata: dict[str, Any] | None = Field(None, description="额外元数据")


class MemoryFeedback(BaseModel):
    """经验评分反馈"""

    rating: int = Field(..., ge=1, le=5, description="评分 1-5")
    comment: str = Field("", description="评价内容")


class MemorySearchRequest(BaseModel):
    """经验检索请求"""

    query: str = Field(..., description="检索关键词/描述")
    top_k: int = Field(5, ge=1, le=20, description="返回结果数量")
    score_threshold: float = Field(0.5, ge=0, le=1.0, description="最低相似度阈值")


class MemoryItem(BaseModel):
    """经验记忆条目"""

    memory_id: str | None = None
    task: str | None = None
    plan: list[dict[str, Any]] = Field(default_factory=list)
    result_summary: str | None = None
    timestamp: str | None = None
    rating: int | None = None
    similarity_score: float | None = None


class EvolutionStatus(BaseModel):
    """自进化状态"""

    total_memories: int = 0
    avg_rating: float = 0.0
    high_rated_count: int = 0  # 4-5分
    low_rated_count: int = 0  # 1-2分
    unrated_count: int = 0  # 未评分
    last_evolution_time: str | None = None
    evolution_tasks_total: int = 0


# ============ API 端点 ============


@router.post("/memories")
async def create_memory(
    request: MemoryCreate,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """
    创建一条新的经验记忆
    """
    memory_id = await episodic_memory.add_memory(
        task_description=request.task_description,
        plan=request.plan,
        final_result=request.final_result,
        user_feedback=request.user_feedback,
        metadata={
            **(request.metadata or {}),
            "created_by": user.id,
        },
    )

    if memory_id:
        return UnifiedResponse.success(data={"memory_id": memory_id}, message="经验记忆创建成功")
    return UnifiedResponse.error(message="创建失败，向量存储不可用")


@router.post("/memories/search")
async def search_memories(
    request: MemorySearchRequest,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """
    语义检索相似的历史经验
    """
    results = await episodic_memory.retrieve_similar_cases(
        task_description=request.query,
        top_k=request.top_k,
        score_threshold=request.score_threshold,
    )

    items = [MemoryItem(**r) for r in results]
    return UnifiedResponse.success(
        data={
            "items": items,
            "total": len(items),
            "query": request.query,
        }
    )


@router.get("/memories/recent")
async def list_recent_memories(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """
    获取最近的经验记忆列表
    """
    # 用一个通用查询来获取最近的记忆
    results = await episodic_memory.retrieve_similar_cases(
        task_description="法律案件处理经验",
        top_k=limit,
        score_threshold=0.0,  # 不做相似度过滤，获取所有
    )

    items = [MemoryItem(**r) for r in results]
    return UnifiedResponse.success(
        data={
            "items": items,
            "total": len(items),
        }
    )


@router.put("/memories/{memory_id}/feedback")
async def update_memory_feedback(
    memory_id: str,
    feedback: MemoryFeedback,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """
    更新经验记忆的评分和反馈
    """
    success = await episodic_memory.update_feedback(
        memory_id=memory_id,
        rating=feedback.rating,
        comment=feedback.comment,
    )

    if success:
        return UnifiedResponse.success(message="反馈更新成功")
    return UnifiedResponse.error(message="更新失败")


@router.get("/evolution/status")
async def get_evolution_status(
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """
    获取自进化引擎状态概览
    """
    from src.services.crawler_service import crawler_service

    # 获取爬虫任务统计
    tasks = getattr(crawler_service, "tasks", {})
    total_tasks = len(tasks)
    last_time = None
    if tasks:
        # 找到最近完成的任务时间
        for _, task in tasks.items():
            task_time = task.get("updated_at") or task.get("created_at")
            if task_time and (not last_time or task_time > last_time):
                last_time = task_time

    # 获取记忆统计 (从向量库检索概览)
    total_memories = 0
    avg_rating = 0.0
    high_count = 0
    low_count = 0
    unrated = 0

    try:
        all_memories = await episodic_memory.retrieve_similar_cases(
            task_description="法律咨询案件合同",
            top_k=100,
            score_threshold=0.0,
        )
        total_memories = len(all_memories)
        ratings = [m.get("rating", 0) for m in all_memories]
        rated = [r for r in ratings if r and r > 0]
        avg_rating = sum(rated) / len(rated) if rated else 0.0
        high_count = sum(1 for r in rated if r >= 4)
        low_count = sum(1 for r in rated if r <= 2)
        unrated = sum(1 for r in ratings if not r or r == 0)
    except Exception as e:
        logger.warning(f"获取记忆统计失败: {e}")

    data = EvolutionStatus(
        total_memories=total_memories,
        avg_rating=round(avg_rating, 2),
        high_rated_count=high_count,
        low_rated_count=low_count,
        unrated_count=unrated,
        last_evolution_time=last_time,
        evolution_tasks_total=total_tasks,
    )
    return UnifiedResponse.success(data=data)


@router.get("/graph/overview")
async def get_graph_overview(
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """
    获取知识图谱概览统计
    """
    from src.services.graph_service import graph_service

    stats = graph_service.get_graph_stats()
    return UnifiedResponse.success(data=stats)


@router.get("/graph/search")
async def search_graph_entities(
    query: str = Query(..., description="实体名称或关键词"),
    depth: int = Query(1, ge=1, le=3, description="关系深度"),
    limit: int = Query(30, ge=1, le=100, description="返回结果限制"),
    skip: int = Query(0, ge=0, description="分页偏移量"),
    entity_type: str | None = Query(None, description="实体类型过滤"),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """
    搜索知识图谱中的实体及其关联关系
    支持分页和实体类型过滤
    """
    from src.services.graph_service import graph_service

    # 如果传入了 skip 或 entity_type，使用分页搜索
    if skip > 0 or entity_type:
        result = await graph_service.search_with_pagination(
            keyword=query, skip=skip, limit=limit, entity_type=entity_type
        )
    else:
        result = graph_service.search_entities(query, depth=depth, limit=limit)
    return UnifiedResponse.success(data=result)


@router.get("/graph/entity/{entity_name}")
async def get_entity_relations(
    entity_name: str,
    depth: int = Query(1, ge=1, le=3, description="关系深度"),
    max_nodes: int = Query(50, ge=10, le=200, description="最大节点数"),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """
    获取指定实体的关联实体和关系（用于图谱展开）
    支持深度和最大节点数限制
    """
    from src.services.graph_service import graph_service

    relations = graph_service.get_related_entities(entity_name, depth=depth)

    # 转换为前端图谱格式
    nodes: dict[str, dict[str, str]] = {}
    edges: list[dict[str, str]] = []

    # 添加中心节点
    nodes[entity_name] = {
        "id": entity_name,
        "label": entity_name,
        "type": "entity",
    }

    for rel in relations:
        source = rel.get("source", "")
        target = rel.get("target", "")
        relation = rel.get("relation", "")

        if source and source not in nodes and len(nodes) < max_nodes:
            node_type = _infer_node_type(source, relation)
            nodes[source] = {"id": source, "label": source, "type": node_type}
        if target and target not in nodes and len(nodes) < max_nodes:
            node_type = _infer_node_type(target, relation)
            nodes[target] = {"id": target, "label": target, "type": node_type}

        if source and target and source in nodes and target in nodes:
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "relation": relation,
                    "label": relation,
                }
            )

    data = {
        "nodes": list(nodes.values()),
        "edges": edges,
        "center_entity": entity_name,
        "max_nodes": max_nodes,
    }
    return UnifiedResponse.success(data=data)


def _infer_node_type(name: str, relation: str) -> str:
    """根据名称和关系推断节点类型"""
    relation_upper = relation.upper()
    if relation_upper in ("REFERENCES", "CITED_BY"):
        return "law"
    if relation_upper in ("HEARD_BY", "RULED_BY"):
        return "entity"
    if "案" in name or "案件" in name:
        return "document"
    if "法" in name or "条例" in name or "规定" in name:
        return "law"
    if "法院" in name or "仲裁" in name:
        return "entity"
    return "entity"


# ============ 图谱增强端点 ============


@router.get("/graph/entity/{entity_name}/detail")
async def get_entity_detail(
    entity_name: str,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """
    获取实体详情 + 所有出入关系
    """
    from src.services.graph_service import graph_service

    result = await graph_service.get_entity_detail(entity_name)
    if result.get("entity") is None:
        return UnifiedResponse.error(message=f"实体 '{entity_name}' 未找到")
    return UnifiedResponse.success(data=result)


@router.get("/graph/path")
async def get_shortest_path(
    from_entity: str = Query(..., alias="from", description="起始实体名称"),
    to_entity: str = Query(..., alias="to", description="目标实体名称"),
    max_depth: int = Query(10, ge=1, le=20, description="最大搜索深度"),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """
    查询两个实体间的最短路径
    """
    from src.services.graph_service import graph_service

    result = await graph_service.get_shortest_path(from_entity, to_entity, max_depth=max_depth)
    if not result.get("found", False):
        return UnifiedResponse.success(
            data=result, message=f"未找到 '{from_entity}' 到 '{to_entity}' 的路径"
        )
    return UnifiedResponse.success(data=result)


@router.get("/graph/subgraph/{entity_name}")
async def get_subgraph(
    entity_name: str,
    depth: int = Query(2, ge=1, le=5, description="子图深度"),
    max_nodes: int = Query(50, ge=10, le=200, description="最大节点数"),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """
    提取实体子图（限制节点数防止数据爆炸）
    """
    from src.services.graph_service import graph_service

    result = await graph_service.get_subgraph(entity_name, depth=depth, max_nodes=max_nodes)
    return UnifiedResponse.success(data=result)


@router.post("/graph/import")
async def batch_import(
    entities: list[dict[str, Any]],
    user: User = Depends(require_permission(Permission.WRITE_KNOWLEDGE)),
) -> dict[str, Any]:
    """
    批量导入实体三元组
    每条记录格式: {subject, predicate, object, properties?}
    """
    from src.services.graph_service import graph_service

    if not entities:
        return UnifiedResponse.error(message="导入列表不能为空")

    if len(entities) > 1000:
        return UnifiedResponse.error(message="单次导入不能超过 1000 条")

    result = await graph_service.batch_import_entities(entities)
    return UnifiedResponse.success(data=result, message=f"成功导入 {result['imported']} 条")


@router.get("/graph/types")
async def get_entity_types(
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """
    获取所有实体类型列表及统计
    """
    from src.services.graph_service import graph_service

    result = await graph_service.get_entity_types()
    return UnifiedResponse.success(data=result)


# ============ 图谱实体/关系 CRUD ============


class EntityCreate(BaseModel):
    """创建实体"""

    name: str = Field(..., description="实体名称")
    entity_type: str = Field("Entity", description="实体类型（Neo4j标签）")
    properties: dict[str, Any] | None = Field(None, description="实体属性")


class EntityUpdate(BaseModel):
    """更新实体"""

    properties: dict[str, Any] = Field(..., description="要更新的属性")


class RelationCreate(BaseModel):
    """创建关系"""

    subject: str = Field(..., description="主体实体名称")
    predicate: str = Field(..., description="关系类型")
    object: str = Field(..., description="客体实体名称")


class RelationDelete(BaseModel):
    """删除关系"""

    subject: str
    predicate: str
    object: str


class EntityExtractRequest(BaseModel):
    """LLM实体抽取请求"""

    text: str = Field(..., description="待抽取的文本内容")
    auto_import: bool = Field(False, description="是否自动导入到图谱")


@router.post("/graph/entity")
async def create_entity(
    request: EntityCreate,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """创建图谱实体"""
    from src.services.graph_service import graph_service

    result = await graph_service.create_entity(
        name=request.name, entity_type=request.entity_type, properties=request.properties
    )
    if not result.get("success"):
        return UnifiedResponse.error(message=result.get("error", "创建失败"))
    return UnifiedResponse.success(data=result, message="实体创建成功")


@router.put("/graph/entity/{entity_name}")
async def update_entity(
    entity_name: str,
    request: EntityUpdate,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """更新图谱实体属性"""
    from src.services.graph_service import graph_service

    result = await graph_service.update_entity(entity_name, request.properties)
    if not result.get("success"):
        return UnifiedResponse.error(message=result.get("error", "更新失败"))
    return UnifiedResponse.success(data=result, message="实体更新成功")


@router.delete("/graph/entity/{entity_name}")
async def delete_entity(
    entity_name: str,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """删除图谱实体（DETACH DELETE）"""
    from src.services.graph_service import graph_service

    result = await graph_service.delete_entity(entity_name)
    if not result.get("success"):
        return UnifiedResponse.error(message=result.get("error", "删除失败"))
    return UnifiedResponse.success(data=result, message="实体已删除")


@router.post("/graph/relation")
async def create_relation(
    request: RelationCreate,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """创建图谱关系"""
    from src.services.graph_service import graph_service

    result = await graph_service.create_relation(
        subject=request.subject, predicate=request.predicate, obj=request.object
    )
    if not result.get("success"):
        return UnifiedResponse.error(message=result.get("error", "创建失败"))
    return UnifiedResponse.success(data=result, message="关系创建成功")


@router.delete("/graph/relation")
async def delete_relation(
    request: RelationDelete,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """删除图谱关系"""
    from src.services.graph_service import graph_service

    result = await graph_service.delete_relation(
        subject=request.subject, predicate=request.predicate, obj=request.object
    )
    if not result.get("success"):
        return UnifiedResponse.error(message=result.get("error", "删除失败"))
    return UnifiedResponse.success(data=result, message="关系已删除")


@router.post("/graph/export")
async def export_graph(
    entity_type: str | None = Query(None, description="按实体类型过滤"),
    limit: int = Query(10000, ge=1, le=50000, description="导出上限"),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """导出图谱三元组（CSV格式数据）"""
    from src.services.graph_service import graph_service

    triples = await graph_service.export_triples(entity_type=entity_type, limit=limit)
    return UnifiedResponse.success(
        data={"triples": triples, "total": len(triples), "format": "subject,predicate,object"}
    )


@router.post("/graph/extract")
async def extract_entities(
    request: EntityExtractRequest,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """LLM智能实体关系抽取"""
    from src.services.entity_extraction_service import entity_extraction_service
    from src.services.graph_service import graph_service

    result = await entity_extraction_service.extract(request.text)

    if request.auto_import and result.get("entities"):
        # 自动导入到图谱
        imported = 0
        for entity in result.get("entities", []):
            r = await graph_service.create_entity(
                name=entity["name"],
                entity_type=entity.get("type", "Entity"),
                properties=entity.get("properties"),
            )
            if r.get("success"):
                imported += 1
        for rel in result.get("relations", []):
            await graph_service.create_relation(
                subject=rel["subject"], predicate=rel["predicate"], obj=rel["object"]
            )
        result["imported_entities"] = imported
        result["imported_relations"] = len(result.get("relations", []))

    return UnifiedResponse.success(data=result)
