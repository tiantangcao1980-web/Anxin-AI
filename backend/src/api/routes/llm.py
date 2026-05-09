"""
LLM配置管理API路由
"""

from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_admin_user, get_current_user_required
from src.models.llm_config import LLM_PROVIDER_CONFIGS, LLMConfig
from src.models.user import User
from src.services.llm_service import LLMService

router = APIRouter()


# ============ Pydantic模型 ============

class LLMConfigCreate(BaseModel):
    """创建LLM配置请求"""
    name: str = Field(..., description="配置名称")
    provider: str = Field(..., description="提供商")
    model_name: str = Field(..., description="模型名称")
    config_type: str = Field(default="llm", description="配置类型: llm/embedding/reranker")
    description: str | None = Field(None, description="配置描述")
    api_key: str | None = Field(None, description="API密钥")
    api_base_url: str | None = Field(None, description="API基础URL")
    max_tokens: int = Field(default=4096, description="最大token数")
    temperature: float = Field(default=0.7, description="温度参数")
    top_p: float = Field(default=1.0, description="Top-P采样")
    frequency_penalty: float = Field(default=0.0, description="频率惩罚")
    presence_penalty: float = Field(default=0.0, description="存在惩罚")
    is_default: bool = Field(default=False, description="是否为默认配置")
    local_endpoint: str | None = Field(None, description="本地服务端点")
    local_model_path: str | None = Field(None, description="本地模型路径")
    context_length: int = Field(default=4096, description="上下文长度")
    extra_params: dict[str, Any] | None = Field(default=None, description="额外参数")
    headers: dict[str, str] | None = Field(default=None, description="自定义请求头")


class LLMConfigUpdate(BaseModel):
    """更新LLM配置请求"""
    name: str | None = None
    description: str | None = None
    api_key: str | None = None
    api_base_url: str | None = None
    model_name: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    local_endpoint: str | None = None
    local_model_path: str | None = None
    context_length: int | None = None
    extra_params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None


class LLMConfigResponse(BaseModel):
    """LLM配置响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    provider: str
    config_type: str
    model_name: str
    description: str | None
    api_base_url: str | None
    api_key_masked: str | None = None
    max_tokens: int
    temperature: float
    top_p: float | None
    frequency_penalty: float | None
    presence_penalty: float | None
    is_active: bool
    is_default: bool
    local_endpoint: str | None
    local_model_path: str | None
    context_length: int | None
    extra_params: dict[str, Any] | None
    total_calls: int | None
    total_tokens: int | None
    avg_latency: float | None
    created_at: str
    updated_at: str

class TestConnectionRequest(BaseModel):
    """测试连接请求"""
    provider: str
    api_key: str | None = None
    api_base_url: str
    model_name: str
    headers: dict[str, str] | None = None


class TestConnectionResponse(BaseModel):
    """测试连接响应"""
    success: bool
    message: str
    error: str | None = None
    response_time_ms: float | None = None


class ProviderInfo(BaseModel):
    """提供商信息"""
    name: str
    base_url: str
    models: dict[str, list[str]]
    supports_streaming: bool
    api_key_required: bool
    is_local: bool | None = False
    openai_compatible: bool | None = False
    note: str | None = None


DeleteConfigResponse = dict[str, bool | str]
ProviderModelsResponse = dict[str, Any]
LLMConfigListResponse = dict[str, Any]


# ============ API端点 ============

def _is_superuser(user: User) -> bool:
    return bool(getattr(user, 'is_superuser', False))


def _admin_org_id_or_403(user: User) -> str:
    org_id = getattr(user, 'org_id', None)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理员缺少组织范围，不能管理 LLM 配置",
        )
    return str(org_id)


def _can_access_config(config: LLMConfig, user: User) -> bool:
    if _is_superuser(user):
        return True
    user_org = getattr(user, 'org_id', None)
    return bool(user_org) and str(config.org_id) == str(user_org)


async def _get_scoped_config_or_404(
    db: AsyncSession,
    config_id: str,
    user: User,
) -> LLMConfig:
    config = await LLMService.get_config(db, config_id)
    if not config or not _can_access_config(config, user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )
    return config

@router.get("/providers", response_model=dict[str, ProviderInfo])
async def get_providers(user: User = Depends(get_current_user_required)) -> dict[str, ProviderInfo]:
    """获取所有支持的LLM提供商"""
    return {
        provider: ProviderInfo(
            name=cast(str, config["name"]),
            base_url=cast(str, config["base_url"]),
            models=cast(dict[str, list[str]], config["models"]),
            supports_streaming=cast(bool, config["supports_streaming"]),
            api_key_required=cast(bool, config["api_key_required"]),
            is_local=cast(bool | None, config.get("is_local", False)),
            openai_compatible=cast(bool | None, config.get("openai_compatible", False)),
            note=cast(str | None, config.get("note")),
        )
        for provider, config in LLM_PROVIDER_CONFIGS.items()
    }


@router.get("/providers/{provider}/models")
async def get_provider_models(
    provider: str,
    user: User = Depends(get_current_user_required),
) -> ProviderModelsResponse:
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
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> LLMConfigResponse:
    """创建LLM配置"""
    payload = data.model_dump()
    if not _is_superuser(admin):
        payload["org_id"] = _admin_org_id_or_403(admin)

    config = await LLMService.create_config(
        db=db,
        **payload
    )

    return _config_to_response(config)


@router.get("/configs", response_model=dict[str, Any])
async def list_configs(
    config_type: str | None = None,
    provider: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> LLMConfigListResponse:
    """列出LLM配置（按组织隔离，管理员可见所有）"""
    # S-104 修复 + 二次加固：
    # - 超级管理员：require_org_filter=False，可见全部配置
    # - 普通用户：require_org_filter=True，强制按 org_id 过滤；org_id 为空则返回空（fail-closed）
    is_superuser = bool(getattr(user, 'is_superuser', False))
    if is_superuser:
        org_id_filter = None
        require_org_filter = False
    else:
        org_id_filter = getattr(user, 'org_id', None)
        require_org_filter = True

    result = await LLMService.list_configs(
        db=db,
        config_type=config_type,
        provider=provider,
        is_active=is_active,
        org_id=org_id_filter,
        page=page,
        page_size=page_size,
        require_org_filter=require_org_filter,
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
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> LLMConfigResponse:
    """获取默认配置"""
    config = await LLMService.get_default_config(
        db,
        config_type,
        org_id=None if _is_superuser(user) else getattr(user, 'org_id', None),
        require_org_filter=not _is_superuser(user),
    )
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到默认配置"
        )

    return _config_to_response(config)


@router.get("/configs/{config_id}", response_model=LLMConfigResponse)
async def get_config(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> LLMConfigResponse:
    """获取单个配置（含组织隔离检查）"""
    config = await _get_scoped_config_or_404(db, config_id, user)
    return _config_to_response(config)


@router.put("/configs/{config_id}", response_model=LLMConfigResponse)
async def update_config(
    config_id: str,
    data: LLMConfigUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> LLMConfigResponse:
    """更新LLM配置"""
    await _get_scoped_config_or_404(db, config_id, admin)
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
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> DeleteConfigResponse:
    """删除LLM配置"""
    await _get_scoped_config_or_404(db, config_id, admin)
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
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> LLMConfigResponse:
    """设置默认配置"""
    await _get_scoped_config_or_404(db, config_id, admin)
    config = await LLMService.set_default(
        db,
        config_id,
        org_id=None if _is_superuser(admin) else getattr(admin, 'org_id', None),
        require_org_filter=not _is_superuser(admin),
    )
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )

    return _config_to_response(config)


@router.post("/configs/{config_id}/toggle-active", response_model=LLMConfigResponse)
async def toggle_active(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> LLMConfigResponse:
    """切换启用状态"""
    await _get_scoped_config_or_404(db, config_id, admin)
    config = await LLMService.toggle_active(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )

    return _config_to_response(config)


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_connection(
    data: TestConnectionRequest,
    admin: User = Depends(get_admin_user),
) -> TestConnectionResponse:
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
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> TestConnectionResponse:
    """测试已保存的配置连接"""
    config = await _get_scoped_config_or_404(db, config_id, admin)

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

def _config_to_response(config: LLMConfig) -> LLMConfigResponse:
    """将配置对象转换为响应格式"""
    # 遮罩API密钥
    api_key_masked = None
    if config.api_key:
        decrypted = LLMService.decrypt_api_key(config.api_key)
        api_key_masked = LLMService.mask_api_key(decrypted)

    return LLMConfigResponse(
        id=config.id,
        name=config.name,
        provider=config.provider,
        config_type=config.config_type,
        model_name=config.model_name,
        description=config.description,
        api_base_url=config.api_base_url,
        api_key_masked=api_key_masked,
        max_tokens=config.max_tokens,
        temperature=config.temperature,
        top_p=config.top_p,
        frequency_penalty=config.frequency_penalty,
        presence_penalty=config.presence_penalty,
        is_active=config.is_active,
        is_default=config.is_default,
        local_endpoint=config.local_endpoint,
        local_model_path=config.local_model_path,
        context_length=config.context_length,
        extra_params=config.extra_params,
        total_calls=config.total_calls,
        total_tokens=config.total_tokens,
        avg_latency=config.avg_latency,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )
