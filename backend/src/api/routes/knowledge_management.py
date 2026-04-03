# -*- coding: utf-8 -*-
"""
律所知识管理 API 路由

对外暴露 KnowledgeManagementService 的能力：
- 案例经验 CRUD + 搜索
- 智能推荐
- 自定义模板管理
- 知识沉淀（从审查结果自动提取）
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from loguru import logger

from src.core.deps import get_current_user_required
from src.core.responses import UnifiedResponse
from src.models.user import User

router = APIRouter(prefix="/knowledge-mgmt", tags=["知识管理"])


# ===== 请求模型 =====

class AddExperienceRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    category: str = Field(..., description="法律领域分类")
    summary: str = Field(..., min_length=10, max_length=5000)
    key_points: List[str] = Field(default_factory=list)
    outcome: str = Field("", description="案件结果")
    applicable_laws: List[str] = Field(default_factory=list)
    lessons_learned: str = Field("", max_length=2000)
    tags: List[str] = Field(default_factory=list)


class AddTemplateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    content: str = Field(..., min_length=10)
    template_type: str = Field("contract")
    tags: List[str] = Field(default_factory=list)


class RecommendRequest(BaseModel):
    task_description: str = Field(..., min_length=5)
    task_type: str = Field("general")


# ===== 案例经验 =====

@router.post("/experiences")
async def add_experience(
    req: AddExperienceRequest,
    user: User = Depends(get_current_user_required),
):
    """添加案例经验"""
    from src.services.knowledge_management import knowledge_management_service
    exp = await knowledge_management_service.add_experience(
        org_id=user.org_id or "default",
        title=req.title,
        category=req.category,
        summary=req.summary,
        key_points=req.key_points,
        outcome=req.outcome,
        applicable_laws=req.applicable_laws,
        lessons_learned=req.lessons_learned,
        author_id=str(user.id),
        tags=req.tags,
    )
    return UnifiedResponse.success(data=exp.to_dict(), message="经验已添加")


@router.get("/experiences")
async def search_experiences(
    query: str = Query(""),
    category: Optional[str] = None,
    outcome: Optional[str] = None,
    top_k: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user_required),
):
    """搜索案例经验"""
    from src.services.knowledge_management import knowledge_management_service
    results = await knowledge_management_service.search_experiences(
        org_id=user.org_id or "default",
        query=query,
        category=category,
        outcome=outcome,
        top_k=top_k,
    )
    return UnifiedResponse.success(data=results)


@router.get("/experiences/{experience_id}")
async def get_experience(
    experience_id: str,
    user: User = Depends(get_current_user_required),
):
    """获取经验详情"""
    from src.services.knowledge_management import knowledge_management_service
    result = await knowledge_management_service.get_experience(
        org_id=user.org_id or "default",
        experience_id=experience_id,
    )
    if not result:
        return UnifiedResponse.error(message="经验不存在")
    return UnifiedResponse.success(data=result)


@router.post("/experiences/{experience_id}/useful")
async def mark_useful(
    experience_id: str,
    user: User = Depends(get_current_user_required),
):
    """标记经验有用"""
    from src.services.knowledge_management import knowledge_management_service
    success = await knowledge_management_service.mark_useful(
        org_id=user.org_id or "default",
        experience_id=experience_id,
    )
    return UnifiedResponse.success(data={"marked": success})


# ===== 智能推荐 =====

@router.post("/recommend")
async def recommend_for_task(
    req: RecommendRequest,
    user: User = Depends(get_current_user_required),
):
    """根据任务智能推荐经验+模板+法条"""
    from src.services.knowledge_management import knowledge_management_service
    result = await knowledge_management_service.recommend_for_task(
        org_id=user.org_id or "default",
        task_description=req.task_description,
        task_type=req.task_type,
    )
    return UnifiedResponse.success(data=result)


# ===== 自定义模板 =====

@router.post("/templates")
async def add_template(
    req: AddTemplateRequest,
    user: User = Depends(get_current_user_required),
):
    """添加律所自定义模板"""
    from src.services.knowledge_management import knowledge_management_service
    tmpl = await knowledge_management_service.add_custom_template(
        org_id=user.org_id or "default",
        name=req.name,
        content=req.content,
        template_type=req.template_type,
        author_id=str(user.id),
        tags=req.tags,
    )
    return UnifiedResponse.success(data=tmpl, message="模板已添加")


@router.get("/templates")
async def list_templates(
    template_type: Optional[str] = None,
    user: User = Depends(get_current_user_required),
):
    """列出律所自定义模板"""
    from src.services.knowledge_management import knowledge_management_service
    results = await knowledge_management_service.list_custom_templates(
        org_id=user.org_id or "default",
        template_type=template_type,
    )
    return UnifiedResponse.success(data=results)


# ===== 统计 =====

@router.get("/stats")
async def get_stats(
    user: User = Depends(get_current_user_required),
):
    """获取知识库统计"""
    from src.services.knowledge_management import knowledge_management_service
    return UnifiedResponse.success(
        data=knowledge_management_service.get_stats(user.org_id or "default")
    )


# ===== 知识分类 =====

@router.get("/categories")
async def list_categories():
    """列出所有经验分类"""
    from src.services.knowledge_management import EXPERIENCE_CATEGORIES, OUTCOME_TYPES
    return UnifiedResponse.success(data={
        "categories": EXPERIENCE_CATEGORIES,
        "outcomes": OUTCOME_TYPES,
    })
