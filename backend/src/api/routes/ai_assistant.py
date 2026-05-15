"""AI 私有助手 API 路由"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import (
    Permission,
    get_current_user_required,
    require_permission,
)
from src.core.responses import UnifiedResponse
from src.models.user import User
from src.services.ai_assistant_service import AIAssistantService
from src.services.private_llm_service import PrivateLLMService

router = APIRouter(prefix="/ai-assistant", tags=["AI私有助手"])


def _require_org_id(user: User) -> str:
    """AI 助手配置与反馈接口必须绑定组织范围。"""
    if not user.org_id:
        raise HTTPException(status_code=403, detail="用户未关联组织，请联系管理员")
    return user.org_id


# ===== Pydantic Schemas =====


class AssistantConfigRequest(BaseModel):
    name: str = Field(default="安心智能助手助手", min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)
    avatar_url: str | None = Field(None, max_length=500)
    welcome_message: str | None = Field(None, max_length=2000)
    system_prompt: str | None = Field(None, max_length=5000)
    personality: dict[str, Any] | None = None
    enabled_agents: list[str] | None = None
    knowledge_base_ids: list[str] | None = None
    max_context_turns: int = Field(default=10, ge=1, le=50)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    llm_config_id: str | None = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: str | None = None


class FeedbackRequest(BaseModel):
    conversation_id: str | None = None
    message_id: str | None = None
    rating: int = Field(..., ge=1, le=5)
    feedback_text: str | None = Field(None, max_length=1000)
    feedback_type: str = Field(
        default="helpful", pattern=r"^(helpful|unhelpful|incorrect|offensive|other)$"
    )


class TestConnectionRequest(BaseModel):
    endpoint: str = Field(..., min_length=1, max_length=500)
    model: str | None = Field(None, max_length=200)


# ===== 助手配置 =====


@router.get("/config")
async def get_assistant_config(
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """获取当前组织的 AI 助手配置"""
    service = AIAssistantService(db)
    config = await service.get_or_create_config(_require_org_id(user))
    return UnifiedResponse.success(data=config)


@router.post("/config")
async def update_assistant_config(
    req: AssistantConfigRequest,
    user: User = Depends(require_permission(Permission.MANAGE_AI_ASSISTANT)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """创建或更新 AI 助手配置"""
    service = AIAssistantService(db)
    # 先获取现有配置
    existing = await service.get_or_create_config(_require_org_id(user))
    config = await service.update_config(existing["id"], req.model_dump(exclude_none=True))
    return UnifiedResponse.success(data=config, message="配置已更新")


@router.get("/agents")
async def list_available_agents(
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """获取可用的 Agent 列表"""
    service = AIAssistantService(db)
    agents = await service.get_available_agents()
    return UnifiedResponse.success(data=agents)


# ===== 对话增强 =====


@router.post("/summarize/{conversation_id}")
async def generate_summary(
    conversation_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """为指定对话生成 AI 摘要"""
    service = AIAssistantService(db)
    try:
        summary = await service.generate_summary(conversation_id, user.id)
        return UnifiedResponse.success(data=summary)
    except ValueError as e:
        return UnifiedResponse.error(code=404, message=str(e))
    except Exception as e:
        logger.error(f"生成对话摘要失败: {e}")
        return UnifiedResponse.error(code=500, message="摘要生成失败，请稍后重试")


@router.get("/summaries")
async def list_summaries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """获取用户的对话摘要列表"""
    service = AIAssistantService(db)
    offset = (page - 1) * page_size
    summaries = await service.get_summaries(user.id, limit=page_size, offset=offset)
    return UnifiedResponse.success(data=summaries)


# ===== 反馈 =====


@router.post("/feedback")
async def submit_feedback(
    req: FeedbackRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """提交 AI 助手反馈"""
    service = AIAssistantService(db)
    # 获取组织的助手配置 ID
    config = await service.get_or_create_config(_require_org_id(user))
    feedback = await service.submit_feedback(
        {
            "assistant_config_id": config["id"],
            "user_id": user.id,
            **req.model_dump(),
        }
    )
    return UnifiedResponse.success(data=feedback, message="感谢您的反馈")


@router.get("/feedback/stats")
async def get_feedback_stats(
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(require_permission(Permission.MANAGE_AI_ASSISTANT)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """获取反馈统计"""
    service = AIAssistantService(db)
    config = await service.get_or_create_config(_require_org_id(user))
    stats = await service.get_feedback_stats(config["id"], days=days)
    return UnifiedResponse.success(data=stats)


# ===== 私有 LLM =====


@router.get("/private-llm/detect")
async def detect_local_llm(
    user: User = Depends(require_permission(Permission.MANAGE_AI_ASSISTANT)),
) -> dict[str, Any]:
    """检测本地 LLM 服务"""
    service = PrivateLLMService()
    results = await service.detect_local_llm()
    return UnifiedResponse.success(data=results)


@router.post("/private-llm/test")
async def test_local_connection(
    req: TestConnectionRequest,
    user: User = Depends(require_permission(Permission.MANAGE_AI_ASSISTANT)),
) -> dict[str, Any]:
    """测试本地 LLM 连接"""
    service = PrivateLLMService()
    result = await service.test_connection(req.endpoint, req.model)
    return UnifiedResponse.success(data=result)


@router.get("/private-llm/models")
async def get_recommended_models(
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取推荐模型列表"""
    service = PrivateLLMService()
    models = service.get_recommended_models()
    return UnifiedResponse.success(data=models)


@router.get("/private-llm/guide/{provider}")
async def get_deployment_guide(
    provider: str,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取部署指南"""
    service = PrivateLLMService()
    guide = service.get_deployment_guide(provider)
    if not guide:
        return UnifiedResponse.error(code=404, message=f"未找到 {provider} 的部署指南")
    return UnifiedResponse.success(data=guide)
