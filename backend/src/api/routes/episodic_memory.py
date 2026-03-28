"""
情景记忆/经验中心 API 路由
提供经验记忆的 CRUD、评分、检索功能
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from loguru import logger

from src.core.deps import get_current_user_required
from src.core.responses import UnifiedResponse
from src.services.episodic_memory_service import episodic_memory
from src.models.user import User

router = APIRouter()


# ============ 请求/响应模型 ============

class MemoryCreate(BaseModel):
    """创建经验记忆"""
    task_description: str = Field(..., description="任务描述")
    plan: List[dict] = Field(default_factory=list, description="执行计划")
    final_result: dict = Field(default_factory=dict, description="最终结果")
    user_feedback: Optional[dict] = Field(None, description="用户反馈 {rating, comment}")
    metadata: Optional[dict] = Field(None, description="额外元数据")


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
    memory_id: Optional[str] = None
    task: Optional[str] = None
    plan: List[dict] = []
    result_summary: Optional[str] = None
    timestamp: Optional[str] = None
    rating: Optional[int] = None
    similarity_score: Optional[float] = None


class EvolutionStatus(BaseModel):
    """自进化状态"""
    total_memories: int = 0
    avg_rating: float = 0.0
    high_rated_count: int = 0  # 4-5分
    low_rated_count: int = 0   # 1-2分
    unrated_count: int = 0     # 未评分
    last_evolution_time: Optional[str] = None
    evolution_tasks_total: int = 0


# ============ API 端点 ============

@router.post("/memories")
async def create_memory(
    request: MemoryCreate,
    user: User = Depends(get_current_user_required),
):
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
        }
    )

    if memory_id:
        return UnifiedResponse.success(
            data={"memory_id": memory_id},
            message="经验记忆创建成功"
        )
    return UnifiedResponse.error(message="创建失败，向量存储不可用")


@router.post("/memories/search")
async def search_memories(
    request: MemorySearchRequest,
    user: User = Depends(get_current_user_required),
):
    """
    语义检索相似的历史经验
    """
    results = await episodic_memory.retrieve_similar_cases(
        task_description=request.query,
        top_k=request.top_k,
        score_threshold=request.score_threshold,
    )

    items = [MemoryItem(**r) for r in results]
    return UnifiedResponse.success(data={
        "items": items,
        "total": len(items),
        "query": request.query,
    })


@router.get("/memories/recent")
async def list_recent_memories(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user_required),
):
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
    return UnifiedResponse.success(data={
        "items": items,
        "total": len(items),
    })


@router.put("/memories/{memory_id}/feedback")
async def update_memory_feedback(
    memory_id: str,
    feedback: MemoryFeedback,
    user: User = Depends(get_current_user_required),
):
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
):
    """
    获取自进化引擎状态概览
    """
    from src.services.crawler_service import crawler_service

    # 获取爬虫任务统计
    tasks = getattr(crawler_service, 'tasks', {})
    total_tasks = len(tasks)
    last_time = None
    if tasks:
        # 找到最近完成的任务时间
        for tid, task in tasks.items():
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
):
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
    user: User = Depends(get_current_user_required),
):
    """
    搜索知识图谱中的实体及其关联关系
    """
    from src.services.graph_service import graph_service

    result = graph_service.search_entities(query, depth=depth, limit=limit)
    return UnifiedResponse.success(data=result)


@router.get("/graph/entity/{entity_name}")
async def get_entity_relations(
    entity_name: str,
    depth: int = Query(1, ge=1, le=3),
    user: User = Depends(get_current_user_required),
):
    """
    获取指定实体的关联实体和关系（用于图谱展开）
    """
    from src.services.graph_service import graph_service

    relations = graph_service.get_related_entities(entity_name, depth=depth)

    # 转换为前端图谱格式
    nodes = {}
    edges = []

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

        if source and source not in nodes:
            node_type = _infer_node_type(source, relation)
            nodes[source] = {"id": source, "label": source, "type": node_type}
        if target and target not in nodes:
            node_type = _infer_node_type(target, relation)
            nodes[target] = {"id": target, "label": target, "type": node_type}

        if source and target:
            edges.append({
                "source": source,
                "target": target,
                "relation": relation,
                "label": relation,
            })

    data = {
        "nodes": list(nodes.values()),
        "edges": edges,
        "center_entity": entity_name,
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
