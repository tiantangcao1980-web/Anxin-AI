"""
配置管理 (Enhanced Configuration)
包含安全增强、CORS配置、输入验证等
"""

import secrets
from typing import Optional, List
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """应用配置 (Enhanced with Security)"""

    # ========== 基础配置 ==========
    APP_NAME: str = "AI Legal Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    DEV_MODE: bool = False  # 开发模式：启用后允许无Token访问API
    ENVIRONMENT: str = "development"  # development, staging, production
    ADMIN_INITIAL_PASSWORD: Optional[str] = None  # 管理员初始密码（开发环境用）

    # 服务端口
    BACKEND_PORT: int = 8001
    FRONTEND_PORT: int = 3000

    # ========== 安全配置 ==========
    # JWT配置 (生产环境必须使用强密钥)
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # 密码策略
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = False

    # API 限流配置
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # CORS配置
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001", "tauri://localhost"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # 输入验证配置
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    MAX_QUERY_LENGTH: int = 1000  # 最大查询长度
    ALLOWED_FILE_EXTENSIONS: List[str] = [
        ".pdf", ".doc", ".docx", ".txt", ".md"
    ]

    # 敏感数据加密
    ENCRYPTION_KEY: Optional[str] = None  # 用于加密敏感数据

    # ========== 品牌定制 ==========
    BRAND_NAME: str = "安心法务"
    BRAND_LOGO_URL: str = ""
    BRAND_PRIMARY_COLOR: str = "#D4A574"
    BRAND_FAVICON_URL: str = ""

    # ========== LLM配置 ==========
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096
    LLM_PROVIDER: str = "openai"
    LLM_ENCRYPTION_KEY: Optional[str] = None
    LLM_DEFAULT_CONFIG_CACHE_TTL_SECONDS: int = 60

    # ========== Embedding配置 ==========
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_BASE_URL: str = "https://api.openai.com/v1"
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    EMBEDDING_DIMENSIONS: int = 3072
    USE_LOCAL_EMBEDDING: bool = False
    LOCAL_EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"

    # ========== 数据库配置 ==========
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/legal_agent_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ========== Redis配置 ==========
    REDIS_URL: str = "redis://localhost:6379/0"

    # ========== Qdrant配置 ==========
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_NAME: str = "legal_knowledge"

    # ========== RAG配置 ==========
    RAG_TOP_K: int = 5
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 50
    RAG_SCORE_THRESHOLD: float = 0.5
    RAG_CONTEXT_MAX_LENGTH: int = 4000

    # ========== Neo4j配置 ==========
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # ========== MinIO配置 ==========
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "password"
    MINIO_BUCKET: str = "legal-documents"
    MINIO_USE_SSL: bool = False

    # ========== 搜索服务 ==========
    SEARCH_PROVIDER: str = "perplexity"
    SEARCH_API_KEY: Optional[str] = None

    # ========== 智能体并行与资源配置 ==========
    # 同一 DAG 层级最大并行 Agent 数（当前推荐 30，未来可扩至 200）
    AGENT_MAX_PARALLEL: int = 30
    # LLM 并发请求信号量（控制同时向 LLM API 发送的请求数）
    AGENT_LLM_CONCURRENCY: int = 15
    # HTTP 连接池最大连接数（应 >= AGENT_LLM_CONCURRENCY）
    AGENT_HTTP_MAX_CONNECTIONS: int = 50
    # HTTP 连接池最大保活连接数
    AGENT_HTTP_KEEPALIVE_CONNECTIONS: int = 25
    # LLM API 请求超时时间（秒，法律分析等复杂任务需要较长时间）
    AGENT_LLM_TIMEOUT: int = 180
    # LLM API 连接超时时间（秒）
    AGENT_LLM_CONNECT_TIMEOUT: int = 15
    # LLM 调用最大重试次数
    AGENT_LLM_MAX_RETRIES: int = 3
    # LLM 重试基础延迟（秒）
    AGENT_LLM_RETRY_BASE_DELAY: float = 1.5
    # LLM 重试最大延迟（秒）
    AGENT_LLM_RETRY_MAX_DELAY: float = 12.0
    # 单个 Agent 任务超时时间（秒）
    AGENT_TASK_TIMEOUT: int = 120
    # 全局任务超时时间（秒，所有 Agent 完成的总时限）
    AGENT_GLOBAL_TIMEOUT: int = 600
    # DAG 最大执行轮次（防止无限循环）
    AGENT_MAX_DAG_ROUNDS: int = 30
    # 单个 Agent 最大重试次数
    AGENT_MAX_RETRIES: int = 2

    # ========== 日志配置 ==========
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None

    # ========== OpenAI兼容 ==========
    OPENAI_API_KEY: Optional[str] = None

    # ===== OAuth 第三方登录 =====
    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""
    WECHAT_REDIRECT_URI: str = ""

    ALIPAY_APP_ID: str = ""
    ALIPAY_PRIVATE_KEY: str = ""
    ALIPAY_PUBLIC_KEY: str = ""
    ALIPAY_REDIRECT_URI: str = ""

    # 前端登录页 URL（OAuth 回调后重定向）
    FRONTEND_LOGIN_URL: str = "http://localhost:3001/login"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 自动生成安全的 JWT 密钥（如果未设置）
        if self.JWT_SECRET_KEY == "your-super-secret-jwt-key-change-in-production":
            if self.ENVIRONMENT == "production":
                raise ValueError(
                    "生产环境必须设置安全的 JWT_SECRET_KEY！"
                    "请在环境变量中设置强密钥。"
                )
            elif self.ENVIRONMENT == "development":
                # 开发环境自动生成密钥
                self.JWT_SECRET_KEY = secrets.token_urlsafe(32)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return self.ENVIRONMENT == "production"

    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return self.ENVIRONMENT in ("development", "dev")


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
