"""
律所知识管理 API 路由

对外暴露 KnowledgeManagementService 的能力：
- 案例经验 CRUD + 搜索
- 智能推荐
- 自定义模板管理
- 知识沉淀（从审查结果自动提取）
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.core.deps import Permission, require_permission
from src.core.responses import UnifiedResponse
from src.models.user import User

router = APIRouter(prefix="/knowledge-mgmt", tags=["知识管理"])


# ===== 请求模型 =====


class AddExperienceRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    category: str = Field(..., description="法律领域分类")
    summary: str = Field(..., min_length=10, max_length=5000)
    key_points: list[str] = Field(default_factory=list, max_length=20)
    outcome: str = Field("", description="案件结果")
    applicable_laws: list[str] = Field(default_factory=list, max_length=50)
    lessons_learned: str = Field("", max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=30)


class AddTemplateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    content: str = Field(..., min_length=10, max_length=50000)
    template_type: str = Field("contract")
    tags: list[str] = Field(default_factory=list, max_length=30)


class RecommendRequest(BaseModel):
    task_description: str = Field(..., min_length=5, max_length=5000)
    task_type: str = Field("general")


def _require_org_id(user: User) -> str:
    if not user.org_id:
        raise HTTPException(status_code=403, detail="用户未关联组织，请联系管理员")
    return user.org_id


# ===== 案例经验 =====


@router.post("/experiences")
async def add_experience(
    req: AddExperienceRequest,
    user: User = Depends(require_permission(Permission.WRITE_KNOWLEDGE)),
) -> dict[str, Any]:
    """添加案例经验"""
    from src.services.knowledge_management import knowledge_management_service

    exp = await knowledge_management_service.add_experience(
        org_id=_require_org_id(user),
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
    category: str | None = None,
    outcome: str | None = None,
    top_k: int = Query(10, ge=1, le=50),
    user: User = Depends(require_permission(Permission.READ_KNOWLEDGE)),
) -> dict[str, Any]:
    """搜索案例经验"""
    from src.services.knowledge_management import knowledge_management_service

    results = await knowledge_management_service.search_experiences(
        org_id=_require_org_id(user),
        query=query,
        category=category,
        outcome=outcome,
        top_k=top_k,
    )
    return UnifiedResponse.success(data=results)


@router.get("/experiences/{experience_id}")
async def get_experience(
    experience_id: str,
    user: User = Depends(require_permission(Permission.READ_KNOWLEDGE)),
) -> dict[str, Any]:
    """获取经验详情"""
    from src.services.knowledge_management import knowledge_management_service

    result = await knowledge_management_service.get_experience(
        org_id=_require_org_id(user),
        experience_id=experience_id,
    )
    if not result:
        return UnifiedResponse.error(message="经验不存在")
    return UnifiedResponse.success(data=result)


@router.post("/experiences/{experience_id}/useful")
async def mark_useful(
    experience_id: str,
    user: User = Depends(require_permission(Permission.READ_KNOWLEDGE)),
) -> dict[str, Any]:
    """标记经验有用"""
    from src.services.knowledge_management import knowledge_management_service

    success = await knowledge_management_service.mark_useful(
        org_id=_require_org_id(user),
        experience_id=experience_id,
    )
    return UnifiedResponse.success(data={"marked": success})


# ===== 智能推荐 =====


@router.post("/recommend")
async def recommend_for_task(
    req: RecommendRequest,
    user: User = Depends(require_permission(Permission.READ_KNOWLEDGE)),
) -> dict[str, Any]:
    """根据任务智能推荐经验+模板+法条"""
    from src.services.knowledge_management import knowledge_management_service

    result = await knowledge_management_service.recommend_for_task(
        org_id=_require_org_id(user),
        task_description=req.task_description,
        task_type=req.task_type,
    )
    return UnifiedResponse.success(data=result)


# ===== 自定义模板 =====


@router.post("/templates")
async def add_template(
    req: AddTemplateRequest,
    user: User = Depends(require_permission(Permission.WRITE_KNOWLEDGE)),
) -> dict[str, Any]:
    """添加律所自定义模板"""
    from src.services.knowledge_management import knowledge_management_service

    tmpl = await knowledge_management_service.add_custom_template(
        org_id=_require_org_id(user),
        name=req.name,
        content=req.content,
        template_type=req.template_type,
        author_id=str(user.id),
        tags=req.tags,
    )
    return UnifiedResponse.success(data=tmpl, message="模板已添加")


@router.get("/templates")
async def list_templates(
    template_type: str | None = None,
    user: User = Depends(require_permission(Permission.READ_KNOWLEDGE)),
) -> dict[str, Any]:
    """列出律所自定义模板"""
    from src.services.knowledge_management import knowledge_management_service

    results = await knowledge_management_service.list_custom_templates(
        org_id=_require_org_id(user),
        template_type=template_type,
    )
    return UnifiedResponse.success(data=results)


# ===== 统计 =====


@router.get("/stats")
async def get_stats(
    user: User = Depends(require_permission(Permission.READ_KNOWLEDGE)),
) -> dict[str, Any]:
    """获取知识库统计"""
    from src.services.knowledge_management import knowledge_management_service

    return UnifiedResponse.success(
        data=knowledge_management_service.get_stats(_require_org_id(user))
    )


# ===== 知识分类 =====


@router.get("/categories")
async def list_categories(
    user: User = Depends(require_permission(Permission.READ_KNOWLEDGE)),
) -> dict[str, Any]:
    """列出所有经验分类"""
    from src.services.knowledge_management import EXPERIENCE_CATEGORIES, OUTCOME_TYPES

    return UnifiedResponse.success(
        data={
            "categories": EXPERIENCE_CATEGORIES,
            "outcomes": OUTCOME_TYPES,
        }
    )
