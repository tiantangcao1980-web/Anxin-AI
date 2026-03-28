"""
LLM配置服务
管理大模型API配置的CRUD操作和连接测试
"""

from typing import List, Optional, Dict, Any
from uuid import uuid4
import httpx
from loguru import logger
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.fernet import Fernet
import base64

from src.core.config import settings
from src.models.llm_config import LLMConfig, LLM_PROVIDER_CONFIGS


class LLMService:
    """LLM配置服务"""
    
    # 用于加密API密钥的密钥（从settings获取，如果没有配置则自动生成）
    _encryption_key = None
    _fernet = None
    
    @classmethod
    def _get_encryption_key(cls) -> str:
        """获取加密密钥"""
        if cls._encryption_key is None:
            # 优先从settings获取
            if settings.LLM_ENCRYPTION_KEY:
                cls._encryption_key = settings.LLM_ENCRYPTION_KEY
            else:
                # 自动生成（注意：重启后会变化，导致无法解密已保存的密钥）
                cls._encryption_key = Fernet.generate_key().decode()
                logger.warning("LLM_ENCRYPTION_KEY 未设置，已自动生成。生产环境建议在.env中设置固定密钥。")
        return cls._encryption_key
    
    @classmethod
    def _get_fernet(cls):
        """获取加密器"""
        if cls._fernet is None:
            try:
                key = cls._get_encryption_key()
                cls._fernet = Fernet(key.encode())
            except Exception:
                # 如果密钥无效，生成新的
                cls._encryption_key = Fernet.generate_key().decode()
                cls._fernet = Fernet(cls._encryption_key.encode())
                logger.warning("加密密钥无效，已重新生成。")
        return cls._fernet
    
    @classmethod
    def encrypt_api_key(cls, api_key: str) -> str:
        """加密API密钥"""
        if not api_key:
            return ""
        try:
            fernet = cls._get_fernet()
            encrypted = fernet.encrypt(api_key.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            # ===== [S-09] 加密失败不再回退为明文 =====
            # 原因：原代码 return api_key 会将明文密钥直接存入数据库
            # 修复方式：抛出异常，让调用方感知加密失败，避免敏感数据泄露
            logger.error(f"加密API密钥失败: {e}")
            raise ValueError(f"API密钥加密失败，请检查加密配置: {e}")
    
    @classmethod
    def decrypt_api_key(cls, encrypted_key: str) -> str:
        """解密API密钥"""
        if not encrypted_key:
            return ""
        try:
            fernet = cls._get_fernet()
            decoded = base64.urlsafe_b64decode(encrypted_key.encode())
            decrypted = fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.warning(f"解密API密钥失败: {e}")
            return encrypted_key
    
    @staticmethod
    def mask_api_key(api_key: str) -> str:
        """遮罩API密钥，只显示前4位和后4位"""
        if not api_key or len(api_key) < 12:
            return "****"
        return f"{api_key[:4]}...{api_key[-4:]}"
    
    @staticmethod
    async def create_config(
        db: AsyncSession,
        name: str,
        provider: str,
        model_name: str,
        config_type: str = "llm",
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None,
        description: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        is_default: bool = False,
        org_id: Optional[str] = None,
        extra_params: Optional[Dict] = None,
        local_endpoint: Optional[str] = None,
        **kwargs
    ) -> LLMConfig:
        """创建LLM配置"""
        
        # 如果设为默认，先取消其他默认配置
        if is_default:
            await db.execute(
                update(LLMConfig)
                .where(LLMConfig.config_type == config_type)
                .where(LLMConfig.is_default == True)
                .values(is_default=False)
            )
        
        # 加密API密钥
        encrypted_key = LLMService.encrypt_api_key(api_key) if api_key else None
        
        # 设置默认API基础URL
        if not api_base_url and provider in LLM_PROVIDER_CONFIGS:
            api_base_url = LLM_PROVIDER_CONFIGS[provider].get("base_url", "")
        
        config = LLMConfig(
            id=str(uuid4()),
            name=name,
            provider=provider,
            config_type=config_type,
            model_name=model_name,
            description=description,
            api_key=encrypted_key,
            api_base_url=api_base_url,
            max_tokens=max_tokens,
            temperature=temperature,
            is_default=is_default,
            org_id=org_id,
            extra_params=extra_params or {},
            local_endpoint=local_endpoint,
            **{k: v for k, v in kwargs.items() if hasattr(LLMConfig, k)}
        )
        
        db.add(config)
        await db.commit()
        await db.refresh(config)
        
        logger.info(f"创建LLM配置: {name} ({provider}/{model_name})")
        return config
    
    @staticmethod
    async def get_config(db: AsyncSession, config_id: str) -> Optional[LLMConfig]:
        """获取单个配置"""
        result = await db.execute(
            select(LLMConfig).where(LLMConfig.id == config_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_default_config(
        db: AsyncSession, 
        config_type: str = "llm"
    ) -> Optional[LLMConfig]:
        """获取默认配置"""
        result = await db.execute(
            select(LLMConfig)
            .where(LLMConfig.config_type == config_type)
            .where(LLMConfig.is_default == True)
            .where(LLMConfig.is_active == True)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_configs(
        db: AsyncSession,
        config_type: Optional[str] = None,
        provider: Optional[str] = None,
        is_active: Optional[bool] = None,
        org_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """列出配置"""
        query = select(LLMConfig)
        
        if config_type:
            query = query.where(LLMConfig.config_type == config_type)
        if provider:
            query = query.where(LLMConfig.provider == provider)
        if is_active is not None:
            query = query.where(LLMConfig.is_active == is_active)
        if org_id:
            query = query.where(LLMConfig.org_id == org_id)
        
        # 排序
        query = query.order_by(LLMConfig.is_default.desc(), LLMConfig.priority.desc(), LLMConfig.created_at.desc())
        
        # 分页
        total_result = await db.execute(query)
        total = len(total_result.all())
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        items = result.scalars().all()
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    
    @staticmethod
    async def update_config(
        db: AsyncSession,
        config_id: str,
        **updates
    ) -> Optional[LLMConfig]:
        """更新配置"""
        config = await LLMService.get_config(db, config_id)
        if not config:
            return None
        
        # 如果设为默认，先取消其他默认配置
        if updates.get("is_default"):
            config_type = updates.get("config_type", config.config_type)
            await db.execute(
                update(LLMConfig)
                .where(LLMConfig.config_type == config_type)
                .where(LLMConfig.is_default == True)
                .where(LLMConfig.id != config_id)
                .values(is_default=False)
            )
        
        # 如果更新了API密钥，需要加密
        if "api_key" in updates and updates["api_key"]:
            updates["api_key"] = LLMService.encrypt_api_key(updates["api_key"])
        
        for key, value in updates.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)
        
        await db.commit()
        await db.refresh(config)
        
        logger.info(f"更新LLM配置: {config.name}")
        return config
    
    @staticmethod
    async def delete_config(db: AsyncSession, config_id: str) -> bool:
        """删除配置"""
        config = await LLMService.get_config(db, config_id)
        if not config:
            return False
        
        await db.execute(
            delete(LLMConfig).where(LLMConfig.id == config_id)
        )
        await db.commit()
        
        logger.info(f"删除LLM配置: {config.name}")
        return True
    
    @staticmethod
    async def test_connection(
        provider: str,
        api_key: str,
        api_base_url: str,
        model_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """测试LLM连接"""
        try:
            provider_config = LLM_PROVIDER_CONFIGS.get(provider, {})
            is_openai_compatible = provider_config.get("openai_compatible", False)
            
            # 构建请求
            headers = {
                "Content-Type": "application/json"
            }
            
            if api_key:
                if provider == "anthropic":
                    headers["x-api-key"] = api_key
                    headers["anthropic-version"] = "2023-06-01"
                else:
                    headers["Authorization"] = f"Bearer {api_key}"
            
            # 添加额外的headers
            extra_headers = provider_config.get("extra_headers", {})
            headers.update(extra_headers)
            headers.update(kwargs.get("headers", {}))
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                # 对于OpenAI兼容的API，使用标准的chat/completions接口
                if is_openai_compatible or provider in ["openai", "deepseek", "qwen", "glm", "minimax", "moonshot", "baichuan", "doubao", "stepfun", "yi", "ollama", "localai", "vllm", "xinference", "custom"]:
                    url = f"{api_base_url.rstrip('/')}/chat/completions"
                    payload = {
                        "model": model_name,
                        "messages": [{"role": "user", "content": "Hello"}],
                        "max_tokens": 10,
                        "stream": False
                    }
                elif provider == "anthropic":
                    url = f"{api_base_url.rstrip('/')}/messages"
                    payload = {
                        "model": model_name,
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "Hello"}]
                    }
                else:
                    # 尝试通用的OpenAI格式
                    url = f"{api_base_url.rstrip('/')}/chat/completions"
                    payload = {
                        "model": model_name,
                        "messages": [{"role": "user", "content": "Hello"}],
                        "max_tokens": 10
                    }
                
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "连接成功",
                        "response_time_ms": response.elapsed.total_seconds() * 1000
                    }
                else:
                    error_detail = response.text
                    try:
                        error_json = response.json()
                        error_detail = error_json.get("error", {}).get("message", error_detail)
                    except:
                        pass
                    return {
                        "success": False,
                        "message": f"API返回错误: {response.status_code}",
                        "error": error_detail
                    }
                    
        except httpx.TimeoutException:
            return {
                "success": False,
                "message": "连接超时",
                "error": "请检查API地址是否正确，或者网络是否通畅"
            }
        except httpx.ConnectError as e:
            return {
                "success": False,
                "message": "连接失败",
                "error": f"无法连接到服务器: {str(e)}"
            }
        except Exception as e:
            logger.error(f"测试LLM连接失败: {e}")
            return {
                "success": False,
                "message": "测试失败",
                "error": str(e)
            }
    
    @staticmethod
    def get_provider_configs() -> Dict[str, Any]:
        """获取所有提供商配置模板"""
        return LLM_PROVIDER_CONFIGS
    
    @staticmethod
    async def set_default(db: AsyncSession, config_id: str) -> Optional[LLMConfig]:
        """设置默认配置"""
        config = await LLMService.get_config(db, config_id)
        if not config:
            return None
        
        # 取消其他同类型的默认配置
        await db.execute(
            update(LLMConfig)
            .where(LLMConfig.config_type == config.config_type)
            .where(LLMConfig.is_default == True)
            .values(is_default=False)
        )
        
        # 设置当前配置为默认
        config.is_default = True
        await db.commit()
        await db.refresh(config)
        
        return config
    
    @staticmethod
    async def toggle_active(db: AsyncSession, config_id: str) -> Optional[LLMConfig]:
        """切换启用状态"""
        config = await LLMService.get_config(db, config_id)
        if not config:
            return None
        
        config.is_active = not config.is_active
        await db.commit()
        await db.refresh(config)
        
        return config
    
    @staticmethod
    async def update_usage_stats(
        db: AsyncSession,
        config_id: str,
        tokens_used: int,
        latency_ms: float
    ) -> None:
        """更新使用统计"""
        config = await LLMService.get_config(db, config_id)
        if not config:
            return
        
        config.total_calls = (config.total_calls or 0) + 1
        config.total_tokens = (config.total_tokens or 0) + tokens_used
        
        # 计算移动平均延迟
        if config.avg_latency:
            config.avg_latency = (config.avg_latency * 0.9) + (latency_ms * 0.1)
        else:
            config.avg_latency = latency_ms
        
        await db.commit()
