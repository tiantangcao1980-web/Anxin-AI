"""
LLM配置服务
管理大模型API配置的CRUD操作和连接测试
"""

import asyncio
import base64
import copy
import time
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

import httpx
from cryptography.fernet import Fernet
from loguru import logger
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.llm_helper import LLMConfigResult
from src.models.llm_config import LLM_PROVIDER_CONFIGS, LLMConfig


class LLMService:
    """LLM配置服务"""

    # 用于加密API密钥的密钥（从settings获取，如果没有配置则自动生成）
    _encryption_key: str | None = None
    _fernet: Fernet | None = None
    _default_config_cache: dict[str, tuple[float, LLMConfigResult]] = {}
    _default_config_cache_lock: asyncio.Lock = asyncio.Lock()

    @staticmethod
    def _string_dict(value: object) -> dict[str, str]:
        """将未知对象收窄为字符串字典，用于 headers 等 JSON 边界。"""
        if not isinstance(value, Mapping):
            return {}

        result: dict[str, str] = {}
        for key, item in value.items():
            if isinstance(key, str) and isinstance(item, str):
                result[key] = item
        return result

    @classmethod
    def _get_encryption_key(cls) -> str:
        """获取加密密钥。

        生产/预发环境必须显式设置 ``LLM_ENCRYPTION_KEY``，否则会 raise
        以防止"重启后所有已加密 API key 解密失败"的静默事故。
        开发环境允许自动生成（仅本进程有效）。
        """
        if cls._encryption_key is None:
            if settings.LLM_ENCRYPTION_KEY:
                cls._encryption_key = settings.LLM_ENCRYPTION_KEY
            elif settings.ENVIRONMENT in {"production", "staging"}:
                raise RuntimeError(
                    "[SEC-S2.3] 生产/预发环境必须设置 LLM_ENCRYPTION_KEY 环境变量。"
                    "未设置会导致重启后所有已加密的 LLM API key 无法解密。"
                    "生成方式：python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )
            else:
                # 仅开发环境允许自动生成（本进程有效，重启失效）
                cls._encryption_key = Fernet.generate_key().decode()
                logger.warning(
                    "[dev] LLM_ENCRYPTION_KEY 未设置，已为本进程自动生成。"
                    "生产环境必须在 .env 中显式配置。"
                )
        return cls._encryption_key

    @classmethod
    def _get_fernet(cls) -> Fernet:
        """获取加密器。

        密钥格式无效时：开发环境回退到生成新 key（旧加密数据无法解密但服务可启动）；
        生产环境直接抛错以暴露问题。
        """
        if cls._fernet is None:
            try:
                key = cls._get_encryption_key()
                cls._fernet = Fernet(key.encode())
            except Exception:
                if settings.ENVIRONMENT in {"production", "staging"}:
                    raise
                # 仅开发环境回退
                logger.warning("[dev] LLM_ENCRYPTION_KEY 格式无效，生成临时 key（仅开发环境）")
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
            raise ValueError(f"API密钥加密失败，请检查加密配置: {e}") from e

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

    @classmethod
    def invalidate_default_config_cache(cls, config_type: str | None = None) -> None:
        """失效默认/有效 LLM 配置缓存"""
        if config_type:
            cls._default_config_cache.pop(config_type, None)
            logger.debug(f"LLM 默认配置缓存已失效: {config_type}")
            return

        cls._default_config_cache.clear()
        logger.debug("LLM 默认配置缓存已全部失效")

    @classmethod
    def _to_config_snapshot(cls, config: LLMConfig | None) -> LLMConfigResult | None:
        """将 ORM 配置转为可跨会话复用的只读快照"""
        if not config or not config.is_active:
            return None

        api_key = cls.decrypt_api_key(config.api_key) if config.api_key else ""
        return LLMConfigResult(
            provider=config.provider,
            api_key=api_key,
            api_base_url=config.api_base_url or "",
            model_name=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            config_id=getattr(config, "id", None),
            source="db",
            extra_params=copy.deepcopy(config.extra_params) if config.extra_params else None,
        )

    @classmethod
    async def _fetch_effective_config_snapshot(
        cls,
        db: AsyncSession,
        config_type: str = "llm",
    ) -> LLMConfigResult | None:
        """从数据库加载有效配置快照，优先默认配置，其次最近更新的启用配置"""
        config = await cls.get_default_config(db, config_type)

        if not config:
            result = await db.execute(
                select(LLMConfig)
                .where(LLMConfig.config_type == config_type)
                .where(LLMConfig.is_active == True)
                .order_by(LLMConfig.updated_at.desc())
                .limit(1)
            )
            config = result.scalar_one_or_none()

        return cls._to_config_snapshot(config)

    @classmethod
    async def _load_effective_config_snapshot_from_db(
        cls,
        config_type: str = "llm",
    ) -> LLMConfigResult | None:
        """打开独立会话并加载有效配置快照"""
        from src.core.database import async_session_maker

        async with async_session_maker() as db:
            return await cls._fetch_effective_config_snapshot(db, config_type)

    @classmethod
    async def get_cached_effective_config(
        cls,
        config_type: str = "llm",
    ) -> LLMConfigResult | None:
        """获取带 TTL 的有效配置快照，供热路径复用"""
        ttl = max(0, settings.LLM_DEFAULT_CONFIG_CACHE_TTL_SECONDS)
        now = time.monotonic()
        cached = cls._default_config_cache.get(config_type)

        if cached and (now - cached[0]) < ttl:
            return copy.deepcopy(cached[1])

        async with cls._default_config_cache_lock:
            cached = cls._default_config_cache.get(config_type)
            now = time.monotonic()
            if cached and (now - cached[0]) < ttl:
                return copy.deepcopy(cached[1])

            snapshot = await cls._load_effective_config_snapshot_from_db(config_type)
            if snapshot is None:
                cls._default_config_cache.pop(config_type, None)
                return None

            cls._default_config_cache[config_type] = (now, snapshot)
            return copy.deepcopy(snapshot)

    @staticmethod
    async def create_config(
        db: AsyncSession,
        name: str,
        provider: str,
        model_name: str,
        config_type: str = "llm",
        api_key: str | None = None,
        api_base_url: str | None = None,
        description: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        is_default: bool = False,
        org_id: str | None = None,
        extra_params: dict[str, Any] | None = None,
        local_endpoint: str | None = None,
        **kwargs: object,
    ) -> LLMConfig:
        """创建LLM配置"""

        # 如果设为默认，先取消其他默认配置
        if is_default:
            clear_default = (
                update(LLMConfig)
                .where(LLMConfig.config_type == config_type)
                .where(LLMConfig.is_default == True)
            )
            if org_id is not None:
                clear_default = clear_default.where(LLMConfig.org_id == org_id)
            await db.execute(clear_default.values(is_default=False))

        # 加密API密钥
        encrypted_key = LLMService.encrypt_api_key(api_key) if api_key else None

        # 设置默认API基础URL
        if not api_base_url and provider in LLM_PROVIDER_CONFIGS:
            configured_base_url = LLM_PROVIDER_CONFIGS[provider].get("base_url", "")
            if isinstance(configured_base_url, str):
                api_base_url = configured_base_url

        model_kwargs: dict[str, object] = {
            key: value for key, value in kwargs.items() if hasattr(LLMConfig, key)
        }

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
            **model_kwargs,
        )

        db.add(config)
        await db.commit()
        await db.refresh(config)
        LLMService.invalidate_default_config_cache(config_type)

        logger.info(f"创建LLM配置: {name} ({provider}/{model_name})")
        return config

    @staticmethod
    async def get_config(db: AsyncSession, config_id: str) -> LLMConfig | None:
        """获取单个配置"""
        result = await db.execute(
            select(LLMConfig).where(LLMConfig.id == config_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_default_config(
        db: AsyncSession,
        config_type: str = "llm",
        org_id: str | None = None,
        require_org_filter: bool = False,
    ) -> LLMConfig | None:
        """获取默认配置"""
        if require_org_filter and org_id is None:
            return None

        query = (
            select(LLMConfig)
            .where(LLMConfig.config_type == config_type)
            .where(LLMConfig.is_default == True)
            .where(LLMConfig.is_active == True)
        )
        if require_org_filter:
            query = query.where(LLMConfig.org_id == org_id)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_configs(
        db: AsyncSession,
        config_type: str | None = None,
        provider: str | None = None,
        is_active: bool | None = None,
        org_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
        require_org_filter: bool = True,
    ) -> dict[str, Any]:
        """
        列出配置

        参数:
            require_org_filter: 是否强制按组织隔离（默认 True，fail-closed）。
                - True 且 org_id=None：直接返回空（普通无 org 用户不可见全部）
                - True 且 org_id 有值：仅返回该组织的配置
                - False：不做组织过滤（仅 super_admin 调用方应传 False）

        注意：S-104 修复后再次加固（避免 `if org_id:` 在 None 时跳过过滤的 falsy bug）
        """
        # Fail-closed：require_org_filter=True 且无 org_id 时，直接返回空结果
        if require_org_filter and org_id is None:
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

        query = select(LLMConfig)

        if config_type:
            query = query.where(LLMConfig.config_type == config_type)
        if provider:
            query = query.where(LLMConfig.provider == provider)
        if is_active is not None:
            query = query.where(LLMConfig.is_active == is_active)
        # 显式 is not None 比较，避免 falsy bug（空字符串等）
        if org_id is not None:
            query = query.where(LLMConfig.org_id == org_id)

        # 排序
        query = query.order_by(LLMConfig.is_default.desc(), LLMConfig.priority.desc(), LLMConfig.created_at.desc())

        # 分页（Harness优化: 用 count() 替代 len(all())，避免加载全部行到内存）
        from sqlalchemy import func as sa_func
        count_query = select(sa_func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

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
        **updates: object,
    ) -> LLMConfig | None:
        """更新配置"""
        config = await LLMService.get_config(db, config_id)
        if not config:
            return None

        # 如果设为默认，先取消其他默认配置
        if updates.get("is_default"):
            config_type = updates.get("config_type")
            if not isinstance(config_type, str):
                config_type = config.config_type
            clear_default = (
                update(LLMConfig)
                .where(LLMConfig.config_type == config_type)
                .where(LLMConfig.is_default == True)
                .where(LLMConfig.id != config_id)
            )
            if config.org_id is not None:
                clear_default = clear_default.where(LLMConfig.org_id == config.org_id)
            await db.execute(clear_default.values(is_default=False))

        # 如果更新了API密钥，需要加密
        api_key_update = updates.get("api_key")
        if isinstance(api_key_update, str) and api_key_update:
            updates["api_key"] = LLMService.encrypt_api_key(api_key_update)

        for key, value in updates.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)

        await db.commit()
        await db.refresh(config)
        LLMService.invalidate_default_config_cache(config.config_type)

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
        LLMService.invalidate_default_config_cache(config.config_type)

        logger.info(f"删除LLM配置: {config.name}")
        return True

    @staticmethod
    async def test_connection(
        provider: str,
        api_key: str,
        api_base_url: str,
        model_name: str,
        **kwargs: object,
    ) -> dict[str, Any]:
        """测试LLM连接"""
        try:
            provider_config = LLM_PROVIDER_CONFIGS.get(provider, {})
            is_openai_compatible = bool(provider_config.get("openai_compatible", False))

            # 构建请求
            headers: dict[str, str] = {
                "Content-Type": "application/json"
            }

            if api_key:
                if provider == "anthropic":
                    headers["x-api-key"] = api_key
                    headers["anthropic-version"] = "2023-06-01"
                else:
                    headers["Authorization"] = f"Bearer {api_key}"

            # 添加额外的headers
            extra_headers = LLMService._string_dict(provider_config.get("extra_headers", {}))
            headers.update(extra_headers)
            headers.update(LLMService._string_dict(kwargs.get("headers", {})))

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
                        if isinstance(error_json, dict):
                            error_obj = error_json.get("error")
                            if isinstance(error_obj, dict):
                                message = error_obj.get("message")
                                if isinstance(message, str):
                                    error_detail = message
                    except Exception:
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
    def get_provider_configs() -> dict[str, Any]:
        """获取所有提供商配置模板"""
        return LLM_PROVIDER_CONFIGS

    @staticmethod
    async def set_default(
        db: AsyncSession,
        config_id: str,
        org_id: str | None = None,
        require_org_filter: bool = False,
    ) -> LLMConfig | None:
        """设置默认配置"""
        if require_org_filter and org_id is None:
            return None

        config = await LLMService.get_config(db, config_id)
        if not config:
            return None
        if require_org_filter and config.org_id != org_id:
            return None

        # 取消其他同类型的默认配置
        clear_default = (
            update(LLMConfig)
            .where(LLMConfig.config_type == config.config_type)
            .where(LLMConfig.is_default == True)
        )
        if require_org_filter:
            clear_default = clear_default.where(LLMConfig.org_id == org_id)
        await db.execute(clear_default.values(is_default=False))

        # 设置当前配置为默认
        config.is_default = True
        await db.commit()
        await db.refresh(config)
        LLMService.invalidate_default_config_cache(config.config_type)

        return config

    @staticmethod
    async def toggle_active(db: AsyncSession, config_id: str) -> LLMConfig | None:
        """切换启用状态"""
        config = await LLMService.get_config(db, config_id)
        if not config:
            return None

        config.is_active = not config.is_active
        await db.commit()
        await db.refresh(config)
        LLMService.invalidate_default_config_cache(config.config_type)

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
