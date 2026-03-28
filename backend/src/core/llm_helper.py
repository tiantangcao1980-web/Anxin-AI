"""
LLM配置辅助模块

提供统一的LLM配置获取接口，支持：
1. 优先从数据库获取默认配置（通过LLM管理页面配置）
2. 如果数据库没有配置，回退到环境变量配置
3. 支持解密API密钥
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger

from src.core.config import settings


@dataclass
class LLMConfigResult:
    """LLM配置结果"""
    provider: str
    api_key: str
    api_base_url: str
    model_name: str
    temperature: float
    max_tokens: int
    config_id: Optional[str] = None  # 如果来自数据库，则有ID
    source: str = "env"  # 配置来源: "db" 或 "env"
    extra_params: Optional[Dict[str, Any]] = None


async def get_llm_config(
    config_type: str = "llm",
    db_session = None,
) -> LLMConfigResult:
    """
    获取LLM配置
    
    优先级:
    1. 数据库中的默认配置（通过LLM管理页面设置）
    2. 环境变量配置（.env文件）
    
    Args:
        config_type: 配置类型 - "llm", "embedding", "reranker"
        db_session: 数据库会话（可选）
        
    Returns:
        LLMConfigResult: LLM配置
    """
    # 尝试从数据库获取默认配置
    if db_session:
        try:
            from src.services.llm_service import LLMService
            config = await LLMService.get_default_config(db_session, config_type)
            
            if config and config.is_active:
                # 解密API密钥
                api_key = LLMService.decrypt_api_key(config.api_key) if config.api_key else ""
                
                logger.debug(f"使用数据库LLM配置: {config.name} ({config.provider}/{config.model_name})")
                
                return LLMConfigResult(
                    provider=config.provider,
                    api_key=api_key,
                    api_base_url=config.api_base_url or "",
                    model_name=config.model_name,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    config_id=config.id,
                    source="db",
                    extra_params=config.extra_params,
                )
        except Exception as e:
            logger.warning(f"从数据库获取LLM配置失败，将使用环境变量配置: {e}")
    
    # 回退到环境变量配置
    if config_type == "llm":
        logger.debug("使用环境变量LLM配置")
        return LLMConfigResult(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            api_base_url=settings.LLM_BASE_URL,
            model_name=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            source="env",
        )
    elif config_type == "embedding":
        logger.debug("使用环境变量Embedding配置")
        return LLMConfigResult(
            provider="openai",
            api_key=settings.EMBEDDING_API_KEY or settings.LLM_API_KEY,
            api_base_url=settings.EMBEDDING_BASE_URL,
            model_name=settings.EMBEDDING_MODEL,
            temperature=0,
            max_tokens=0,
            source="env",
        )
    else:
        # 其他类型回退到LLM配置
        return LLMConfigResult(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            api_base_url=settings.LLM_BASE_URL,
            model_name=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            source="env",
        )


def get_llm_config_sync(config_type: str = "llm") -> LLMConfigResult:
    """
    同步获取LLM配置（仅从环境变量）
    
    用于不方便使用异步的场景，如智能体初始化
    """
    if config_type == "llm":
        return LLMConfigResult(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            api_base_url=settings.LLM_BASE_URL,
            model_name=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            source="env",
        )
    elif config_type == "embedding":
        return LLMConfigResult(
            provider="openai",
            api_key=settings.EMBEDDING_API_KEY or settings.LLM_API_KEY,
            api_base_url=settings.EMBEDDING_BASE_URL,
            model_name=settings.EMBEDDING_MODEL,
            temperature=0,
            max_tokens=0,
            source="env",
        )
    else:
        return LLMConfigResult(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            api_base_url=settings.LLM_BASE_URL,
            model_name=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            source="env",
        )


# 提供商到CAMEL平台类型的映射
PROVIDER_TO_PLATFORM = {
    "openai": "OPENAI",
    "anthropic": "ANTHROPIC",
    "deepseek": "OPENAI_COMPATIBLE_MODEL",
    "qwen": "OPENAI_COMPATIBLE_MODEL",
    "glm": "OPENAI_COMPATIBLE_MODEL",
    "minimax": "OPENAI_COMPATIBLE_MODEL",
    "moonshot": "OPENAI_COMPATIBLE_MODEL",
    "baichuan": "OPENAI_COMPATIBLE_MODEL",
    "doubao": "OPENAI_COMPATIBLE_MODEL",
    "stepfun": "OPENAI_COMPATIBLE_MODEL",
    "yi": "OPENAI_COMPATIBLE_MODEL",
    "ollama": "OLLAMA",
    "localai": "OPENAI_COMPATIBLE_MODEL",
    "vllm": "VLLM",
    "custom": "OPENAI_COMPATIBLE_MODEL",
}


def get_camel_platform_type(provider: str) -> str:
    """获取CAMEL平台类型"""
    return PROVIDER_TO_PLATFORM.get(provider, "OPENAI_COMPATIBLE_MODEL")
