"""
LLM配置管理API路由
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.services.llm_service import LLMService
from src.models.llm_config import LLM_PROVIDER_CONFIGS

router = APIRouter()


# ============ Pydantic模型 ============

class LLMConfigCreate(BaseModel):
    """创建LLM配置请求"""
    name: str = Field(..., description="配置名称")
    provider: str = Field(..., description="提供商")
    model_name: str = Field(..., description="模型名称")
    config_type: str = Field(default="llm", description="配置类型: llm/embedding/reranker")
    description: Optional[str] = Field(None, description="配置描述")
    api_key: Optional[str] = Field(None, description="API密钥")
    api_base_url: Optional[str] = Field(None, description="API基础URL")
    max_tokens: int = Field(default=4096, description="最大token数")
    temperature: float = Field(default=0.7, description="温度参数")
    top_p: float = Field(default=1.0, description="Top-P采样")
    frequency_penalty: float = Field(default=0.0, description="频率惩罚")
    presence_penalty: float = Field(default=0.0, description="存在惩罚")
    is_default: bool = Field(default=False, description="是否为默认配置")
    local_endpoint: Optional[str] = Field(None, description="本地服务端点")
    local_model_path: Optional[str] = Field(None, description="本地模型路径")
    context_length: int = Field(default=4096, description="上下文长度")
    extra_params: Optional[Dict[str, Any]] = Field(default=None, description="额外参数")
    headers: Optional[Dict[str, str]] = Field(default=None, description="自定义请求头")


class LLMConfigUpdate(BaseModel):
    """更新LLM配置请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    model_name: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    local_endpoint: Optional[str] = None
    local_model_path: Optional[str] = None
    context_length: Optional[int] = None
    extra_params: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None


class LLMConfigResponse(BaseModel):
    """LLM配置响应"""
    id: str
    name: str
    provider: str
    config_type: str
    model_name: str
    description: Optional[str]
    api_base_url: Optional[str]
    api_key_masked: Optional[str] = None
    max_tokens: int
    temperature: float
    top_p: Optional[float]
    frequency_penalty: Optional[float]
    presence_penalty: Optional[float]
    is_active: bool
    is_default: bool
    local_endpoint: Optional[str]
    local_model_path: Optional[str]
    context_length: Optional[int]
    extra_params: Optional[Dict[str, Any]]
    total_calls: Optional[int]
    total_tokens: Optional[int]
    avg_latency: Optional[float]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class TestConnectionRequest(BaseModel):
    """测试连接请求"""
    provider: str
    api_key: Optional[str] = None
    api_base_url: str
    model_name: str
    headers: Optional[Dict[str, str]] = None


class TestConnectionResponse(BaseModel):
    """测试连接响应"""
    success: bool
    message: str
    error: Optional[str] = None
    response_time_ms: Optional[float] = None


class ProviderInfo(BaseModel):
    """提供商信息"""
    name: str
    base_url: str
    models: Dict[str, List[str]]
    supports_streaming: bool
    api_key_required: bool
    is_local: Optional[bool] = False
    openai_compatible: Optional[bool] = False
    note: Optional[str] = None


# ============ API端点 ============

@router.get("/providers", response_model=Dict[str, ProviderInfo])
async def get_providers():
    """获取所有支持的LLM提供商"""
    return LLM_PROVIDER_CONFIGS


@router.get("/providers/{provider}/models")
async def get_provider_models(provider: str):
    """获取指定提供商的模型列表"""
    if provider not in LLM_PROVIDER_CONFIGS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"不支持的提供商: {provider}"
        )
    
    config = LLM_PROVIDER_CONFIGS[provider]
    return {
        "provider": provider,
        "name": config["name"],
        "models": config.get("models", {}),
        "base_url": config.get("base_url", ""),
        "api_key_required": config.get("api_key_required", True),
        "is_local": config.get("is_local", False),
        "note": config.get("note")
    }


@router.post("/configs", response_model=LLMConfigResponse)
async def create_config(
    data: LLMConfigCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建LLM配置"""
    config = await LLMService.create_config(
        db=db,
        **data.model_dump()
    )
    
    return _config_to_response(config)


@router.get("/configs", response_model=Dict[str, Any])
async def list_configs(
    config_type: Optional[str] = None,
    provider: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """列出LLM配置"""
    result = await LLMService.list_configs(
        db=db,
        config_type=config_type,
        provider=provider,
        is_active=is_active,
        page=page,
        page_size=page_size
    )
    
    return {
        "items": [_config_to_response(item) for item in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"]
    }


@router.get("/configs/default")
async def get_default_config(
    config_type: str = "llm",
    db: AsyncSession = Depends(get_db)
):
    """获取默认配置"""
    config = await LLMService.get_default_config(db, config_type)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到默认配置"
        )
    
    return _config_to_response(config)


@router.get("/configs/{config_id}", response_model=LLMConfigResponse)
async def get_config(
    config_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取单个配置"""
    config = await LLMService.get_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )
    
    return _config_to_response(config)


@router.put("/configs/{config_id}", response_model=LLMConfigResponse)
async def update_config(
    config_id: str,
    data: LLMConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新LLM配置"""
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    
    config = await LLMService.update_config(db, config_id, **updates)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )
    
    return _config_to_response(config)


@router.delete("/configs/{config_id}")
async def delete_config(
    config_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除LLM配置"""
    success = await LLMService.delete_config(db, config_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )
    
    return {"success": True, "message": "配置已删除"}


@router.post("/configs/{config_id}/set-default", response_model=LLMConfigResponse)
async def set_default_config(
    config_id: str,
    db: AsyncSession = Depends(get_db)
):
    """设置默认配置"""
    config = await LLMService.set_default(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )
    
    return _config_to_response(config)


@router.post("/configs/{config_id}/toggle-active", response_model=LLMConfigResponse)
async def toggle_active(
    config_id: str,
    db: AsyncSession = Depends(get_db)
):
    """切换启用状态"""
    config = await LLMService.toggle_active(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )
    
    return _config_to_response(config)


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_connection(data: TestConnectionRequest):
    """测试LLM连接"""
    result = await LLMService.test_connection(
        provider=data.provider,
        api_key=data.api_key or "",
        api_base_url=data.api_base_url,
        model_name=data.model_name,
        headers=data.headers or {}
    )
    
    return TestConnectionResponse(**result)


@router.post("/configs/{config_id}/test", response_model=TestConnectionResponse)
async def test_config_connection(
    config_id: str,
    db: AsyncSession = Depends(get_db)
):
    """测试已保存的配置连接"""
    config = await LLMService.get_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )
    
    # 解密API密钥
    api_key = LLMService.decrypt_api_key(config.api_key) if config.api_key else ""
    
    result = await LLMService.test_connection(
        provider=config.provider,
        api_key=api_key,
        api_base_url=config.api_base_url or "",
        model_name=config.model_name,
        headers=config.headers or {}
    )
    
    return TestConnectionResponse(**result)


# ============ 辅助函数 ============

def _config_to_response(config) -> dict:
    """将配置对象转换为响应格式"""
    # 遮罩API密钥
    api_key_masked = None
    if config.api_key:
        decrypted = LLMService.decrypt_api_key(config.api_key)
        api_key_masked = LLMService.mask_api_key(decrypted)
    
    return {
        "id": config.id,
        "name": config.name,
        "provider": config.provider,
        "config_type": config.config_type,
        "model_name": config.model_name,
        "description": config.description,
        "api_base_url": config.api_base_url,
        "api_key_masked": api_key_masked,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "top_p": config.top_p,
        "frequency_penalty": config.frequency_penalty,
        "presence_penalty": config.presence_penalty,
        "is_active": config.is_active,
        "is_default": config.is_default,
        "local_endpoint": config.local_endpoint,
        "local_model_path": config.local_model_path,
        "context_length": config.context_length,
        "extra_params": config.extra_params,
        "total_calls": config.total_calls,
        "total_tokens": config.total_tokens,
        "avg_latency": config.avg_latency,
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }
