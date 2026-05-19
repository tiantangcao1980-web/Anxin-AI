"""
配置管理 (Enhanced Configuration)
包含安全增强、CORS配置、输入验证等
"""

import secrets
from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置 (Enhanced with Security)"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ========== 基础配置 ==========
    APP_NAME: str = "Anxin AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    DEV_MODE: bool = False  # 开发模式：启用后允许无Token访问API
    ENVIRONMENT: str = "development"  # development, staging, production
    ADMIN_INITIAL_PASSWORD: str | None = None  # 管理员初始密码（开发环境用）

    # 服务端口
    BACKEND_PORT: int = 8001
    FRONTEND_PORT: int = 3000

    # ========== 安全配置 ==========
    # JWT配置 (生产环境必须使用强密钥)
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 120  # 2小时（配合 refresh_token 实现无感续期）
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # 7天

    # 功能开关
    EMAIL_VERIFY_ENABLED: bool = False  # 邮箱验证开关（关闭时注册即可登录）
    SMS_ENABLED: bool = False  # 短信服务开关
    OAUTH_WECHAT_ENABLED: bool = False  # 微信登录开关
    OAUTH_ALIPAY_ENABLED: bool = False  # 支付宝登录开关
    CAPTCHA_ENABLED: bool = False
    CAPTCHA_PROVIDER: str = "turnstile"
    TURNSTILE_SITE_KEY: str = ""
    TURNSTILE_SECRET_KEY: str = ""

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
    # 认证敏感入口在 Redis 不可用时是否 fail-closed。
    # staging/production 会在依赖层自动按 fail-closed 处理；此开关用于开发/测试显式演练。
    AUTH_REDIS_FAIL_CLOSED: bool = False
    # 临时迁移开关：是否继续接受 /auth/refresh 请求体中的 refresh_token。
    # 商业交付默认只接受 HttpOnly Cookie；旧客户端迁移窗口需显式开启。
    AUTH_REFRESH_BODY_COMPAT_ENABLED: bool = False

    # CORS配置
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "tauri://localhost",          # Tauri 桌面端
        "https://tauri.localhost",    # Tauri v2 移动端 (Android/iOS)
        "http://tauri.localhost",     # Tauri v2 移动端 (备用)
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: list[str] = [
        "Authorization", "Content-Type", "Accept", "X-Requested-With",
        "X-Integration-Key", "X-Request-ID",
        # 反Bot防御头
        "X-Request-Timestamp", "X-Request-Nonce", "X-Request-Signature",
        "X-Client-ID", "X-Bot-Signals",
        "X-Challenge-ID", "X-Challenge-Solution",
        "X-Capability-Route-Token",
    ]

    # 输入验证配置
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    MAX_QUERY_LENGTH: int = 1000  # 最大查询长度
    ALLOWED_FILE_EXTENSIONS: list[str] = [
        ".pdf", ".doc", ".docx", ".txt", ".md",
        ".xlsx", ".xls", ".csv", ".pptx",
    ]

    # 敏感数据加密
    ENCRYPTION_KEY: str | None = None  # 用于加密敏感数据

    # 集成 API 密钥（用于 OA/Webhook 回调验证）
    INTEGRATION_API_KEY: str | None = None
    # 独立 MCP Server 没有 HTTP 用户上下文；商业环境默认关闭，统一走带 RBAC 的 /api/v1/mcp。
    MCP_STANDALONE_ENABLED: bool = False
    # 外部 MCP 连接治理：商业环境下 stdio 默认禁用，SSE/stdio 需显式 allowlist。
    MCP_STDIO_ENABLED: bool = False
    MCP_STDIO_ALLOWED_COMMANDS: list[str] = []
    MCP_STDIO_ALLOWED_COMMAND_LINES: list[str] = []
    MCP_STDIO_ALLOWED_ENV_KEYS: list[str] = []
    MCP_SSE_ALLOWED_HOSTS: list[str] = []
    MCP_SSE_ALLOWED_SCHEMES: list[str] = ["https"]
    # MCP tool execution route governance. staging/production fail closed even
    # when this explicit switch is false; the switch lets tests/dev rehearse it.
    MCP_TOOL_ROUTE_TOKEN_REQUIRED: bool = False
    # CLI command execution route governance. staging/production fail closed even
    # when this explicit switch is false; the switch lets tests/dev rehearse it.
    CLI_ROUTE_TOKEN_REQUIRED: bool = False
    # LLM runtime route governance. staging/production fail closed even when
    # this explicit switch is false; the switch lets tests/dev rehearse it.
    LLM_ROUTE_TOKEN_REQUIRED: bool = False
    # Browser/crawler execution route governance. staging/production fail
    # closed even when this explicit switch is false; the switch lets tests/dev
    # rehearse it before deployment.
    BROWSER_FETCH_ROUTE_TOKEN_REQUIRED: bool = False

    # ========== 反Bot防御配置 ==========
    ANTIBOT_ENABLED: bool = False               # 总开关
    ANTIBOT_HMAC_ENABLED: bool = False          # HMAC 签名验证
    ANTIBOT_HMAC_ENFORCE: bool = False          # False=仅记录, True=拦截
    ANTIBOT_PUBLIC_SIGNING_KEY: str = ""        # 公共签名密钥
    ANTIBOT_TIMESTAMP_DRIFT: int = 300          # 时间偏移容忍（秒）
    ANTIBOT_NONCE_TTL: int = 600                # Nonce TTL（秒）
    ANTIBOT_WAF_ENABLED: bool = False           # WAF 开关
    ANTIBOT_WAF_LOG_ONLY: bool = True           # WAF 仅记录模式
    ANTIBOT_FINGERPRINT_ENABLED: bool = False   # 浏览器指纹检测
    ANTIBOT_MAX_IPS_PER_FP: int = 5             # 单指纹最大 IP 数
    ANTIBOT_MAX_FPS_PER_IP: int = 10            # 单 IP 最大指纹数
    ANTIBOT_RISK_SCORING_ENABLED: bool = False  # 风控引擎
    ANTIBOT_CHALLENGE_THRESHOLD: int = 30       # 挑战阈值
    ANTIBOT_BLOCK_THRESHOLD: int = 70           # 阻断阈值
    ANTIBOT_POW_ENABLED: bool = False           # PoW 挑战
    ANTIBOT_POW_DIFFICULTY: int = 4             # PoW 难度（前缀零个数）
    WECHAT_PAY_WEBHOOK_SECRET: str | None = None
    PAYMENT_NOTIFY_BASE_URL: str | None = None
    WECHAT_PAY_APP_ID: str | None = None
    WECHAT_PAY_MCH_ID: str | None = None
    WECHAT_PAY_MERCHANT_SERIAL_NO: str | None = None
    WECHAT_PAY_MERCHANT_PRIVATE_KEY: str | None = None
    WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH: str | None = None
    WECHAT_PAY_API_BASE_URL: str = "https://api.mch.weixin.qq.com"
    WECHAT_PAY_OFFICIAL_WEBHOOK_ENABLED: bool = False
    WECHAT_PAY_PLATFORM_SERIAL: str | None = None
    WECHAT_PAY_PLATFORM_PUBLIC_KEY: str | None = None
    WECHAT_PAY_PLATFORM_PUBLIC_KEY_PATH: str | None = None
    WECHAT_PAY_API_V3_KEY: str | None = None
    ALIPAY_WEBHOOK_SECRET: str | None = None
    ALIPAY_APP_ID: str = ""
    ALIPAY_PRIVATE_KEY: str = ""
    ALIPAY_PRIVATE_KEY_PATH: str | None = None
    ALIPAY_GATEWAY_URL: str = "https://openapi.alipay.com/gateway.do"
    ALIPAY_OFFICIAL_WEBHOOK_ENABLED: bool = False
    ALIPAY_PUBLIC_KEY: str = ""
    ALIPAY_PUBLIC_KEY_PATH: str | None = None
    ESIGN_OFFICIAL_WEBHOOK_ENABLED: bool = False
    ESIGN_BAO_APP_ID: str | None = None
    ESIGN_BAO_APP_SECRET: str | None = None
    ESIGN_BAO_API_URL: str = "https://smlopenapi.esign.cn"
    ESIGN_BAO_CREATE_FLOW_PATH: str = "/api/v2/signflows/createFlowOneStep"
    ESIGN_BAO_START_FLOW_PATH: str = "/v1/signflows/{flow_id}/start"
    ESIGN_BAO_SIGN_URL_PATH: str = "/v1/signflows/{flow_id}/executeUrl"
    ESIGN_BAO_STATUS_PATH: str = "/v1/signflows/{flow_id}"
    ESIGN_BAO_DOWNLOAD_PATH: str = "/v1/signflows/{flow_id}/documents"
    ESIGN_BAO_CANCEL_PATH: str = "/v1/signflows/{flow_id}/revoke"
    ESIGN_WEBHOOK_SECRET: str | None = None
    FADADA_APP_ID: str | None = None
    FADADA_APP_SECRET: str | None = None
    FADADA_API_URL: str = "https://api.fadada.com/api/v5"
    FADADA_ACCESS_TOKEN: str | None = None
    FADADA_ACCESS_TOKEN_PATH: str = "/service/get-access-token"
    FADADA_CREATE_TASK_PATH: str = "/sign-task/create"
    FADADA_SIGN_URL_PATH: str = "/sign-task/actor/get-url"
    FADADA_STATUS_PATH: str = "/sign-task/app/get-detail"
    FADADA_DOWNLOAD_URL_PATH: str = "/sign-task/owner/get-download-url"
    FADADA_CANCEL_PATH: str = "/sign-task/cancel"
    WEBHOOK_SIGNATURE_MAX_AGE_SECONDS: int = 300
    WEBHOOK_RETRY_WORKER_ENABLED: bool = False
    WEBHOOK_RETRY_INTERVAL_SECONDS: int = 60
    WEBHOOK_RETRY_BATCH_SIZE: int = 20
    WEBHOOK_RETRY_MAX_ATTEMPTS: int = 5
    WEBHOOK_RETRY_BASE_DELAY_SECONDS: int = 60
    WEBHOOK_RETRY_MAX_DELAY_SECONDS: int = 3600
    WEBHOOK_PROCESSING_LOCK_TTL_SECONDS: int = 30
    WEBHOOK_PROCESSING_LOCK_WAIT_SECONDS: float = 5.0
    # auto=生产/预发布走 Redis，开发/测试走本地锁；redis=强制 Redis；local=仅本地开发
    WEBHOOK_PROCESSING_LOCK_BACKEND: str = "auto"
    LIC_ALLOWED_HOSTS: list[str] = []
    LIC_DEFAULT_HOST_RATE_LIMIT_SECONDS: float = 1.0
    LIC_HOST_RATE_LIMIT_SECONDS: dict[str, float] = {}

    # ========== 阿里云服务（短信 + 邮件共用 AccessKey） ==========
    ALIYUN_ACCESS_KEY_ID: str = ""
    ALIYUN_ACCESS_KEY_SECRET: str = ""

    # 阿里云短信 (Dysmsapi)
    # 控制台：https://dysms.console.aliyun.com
    ALIYUN_SMS_REGION: str = "cn-hangzhou"
    ALIYUN_SMS_SIGN_NAME: str = ""  # 短信签名，如「安心智能助手」
    ALIYUN_SMS_TEMPLATE_VERIFY: str = ""  # 注册验证码模板 Code
    ALIYUN_SMS_TEMPLATE_LOGIN: str = ""  # 登录验证码模板 Code
    ALIYUN_SMS_TEMPLATE_RESET: str = ""  # 密码重置模板 Code

    # 阿里云邮件推送 (DirectMail)
    # 控制台：https://dm.console.aliyun.com
    ALIYUN_EMAIL_REGION: str = "cn-hangzhou"
    ALIYUN_EMAIL_ACCOUNT: str = ""  # 发信地址，如 noreply@mail.anxinai.com
    ALIYUN_EMAIL_ALIAS: str = "安心智能助手"  # 发件人昵称

    # ========== 品牌定制 ==========
    BRAND_NAME: str = "安心智能助手"
    BRAND_LOGO_URL: str = ""
    BRAND_PRIMARY_COLOR: str = "#D4A574"
    BRAND_FAVICON_URL: str = ""

    # ========== LiveKit 音视频服务 ==========
    # 文档：https://docs.livekit.io
    LIVEKIT_URL: str = ""  # ws://localhost:7880
    LIVEKIT_API_KEY: str = ""  # livekit.yaml 中 keys 的键名
    LIVEKIT_API_SECRET: str = ""  # livekit.yaml 中 keys 的值

    # ========== LLM配置 ==========
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096
    LLM_PROVIDER: str = "openai"
    LLM_ENCRYPTION_KEY: str | None = None
    LLM_DEFAULT_CONFIG_CACHE_TTL_SECONDS: int = 3600  # Harness优化: 60s→1h（配置很少变）

    # ========== 本地 LLM 兜底配置（支持 LOCAL / NAS-Lite 运行模式） ==========
    # 当未配置 LLM_API_KEY 时，系统优先尝试调用 Ollama 本地服务。
    # 用户在家用 NAS 或桌面端装好 Ollama 后，无需额外配置 Key 即可使用。
    OLLAMA_BASE_URL: str = ""  # 例如 http://host.docker.internal:11434 或 http://localhost:11434
    OLLAMA_DEFAULT_MODEL: str = "qwen2.5:7b"

    # 整体运行模式：cloud / hybrid / nas-lite / local
    # 影响：是否强制本地 LLM、是否跳过云端依赖、数据分桶策略
    RUNTIME_MODE: str = "cloud"

    # ========== 沙箱执行器（P3-E）==========
    # 默认 Provider：local / docker / e2b / codex_cloud
    SANDBOX_PROVIDER: str = "local"

    # ========== Embedding配置 ==========
    EMBEDDING_API_KEY: str | None = None
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
    QDRANT_API_KEY: str | None = None
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
    STORAGE_BACKEND: str = "local"  # local / minio
    STORAGE_LOCAL_PATH: str = "data/storage"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "password"
    MINIO_BUCKET: str = "legal-documents"
    MINIO_USE_SSL: bool = False

    # ========== 搜索服务 ==========
    SEARCH_PROVIDER: str = "perplexity"
    SEARCH_API_KEY: str | None = None

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
    # 合同审查业务超时（秒）：商业交付 P0 要求单次审查 90s 内完成或标记失败
    CONTRACT_REVIEW_TIMEOUT_SECONDS: int = 90
    # 合同审查互斥锁 TTL（秒），应大于 CONTRACT_REVIEW_TIMEOUT_SECONDS
    CONTRACT_REVIEW_LOCK_TTL_SECONDS: int = 150
    # auto=生产/预发布走 Redis，开发/测试走本地锁；redis=强制 Redis；local=仅本地开发
    CONTRACT_REVIEW_LOCK_BACKEND: str = "auto"
    # DAG 最大执行轮次（防止无限循环）
    AGENT_MAX_DAG_ROUNDS: int = 30
    # 单个 Agent 最大重试次数
    AGENT_MAX_RETRIES: int = 2

    # ========== 法律数据采集配置 ==========
    DATA_DIR: str = "data"  # 数据存储根目录
    COLLECTOR_RATE_LIMIT: float = 2.0  # 请求间隔(秒)
    COLLECTOR_MAX_RETRIES: int = 3  # 最大重试次数
    COLLECTOR_REQUEST_TIMEOUT: int = 30  # 请求超时(秒)
    COLLECTOR_MAX_CONCURRENT: int = 3  # 最大并发采集器数

    # ========== 企业调查数据源 API ==========
    TIANYANCHA_API_KEY: str | None = None  # 天眼查 API
    QICHACHA_API_KEY: str | None = None  # 企查查 API
    AIQICHA_API_KEY: str | None = None  # 爱企查 API
    CREDIT_CHINA_API_KEY: str | None = None  # 信用中国 API

    # ========== 法律数据源（P6-C） ==========
    PKULAW_API_KEY: str = ""  # 北大法宝商业 API（缺省走 mock）
    PKULAW_BASE_URL: str = "https://api.pkulaw.com/v1"
    WKINFO_API_KEY: str = ""  # 威科先行商业 API（缺省走 mock）
    WKINFO_BASE_URL: str = "https://api.wkinfo.com.cn/v1"

    # ========== 日志配置 ==========
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: str | None = None

    # ========== P19-A 可观测层 ==========
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    METRICS_ENABLED: bool = True
    METRICS_AUTH_TOKEN: str = ""
    SLO_DASHBOARD_REFRESH_SECONDS: int = 60

    # ========== OpenAI兼容 ==========
    OPENAI_API_KEY: str | None = None

    # ========== 搜索服务 API ==========
    TAVILY_API_KEY: str = ""        # Tavily Search API (https://tavily.com)
    BING_SEARCH_KEY: str = ""       # Bing Web Search API

    # ===== Crawl4AI 配置 =====
    CRAWL4AI_ENABLED: bool = True
    CRAWL4AI_TIMEOUT: int = 30          # 单页超时（秒）
    CRAWL4AI_MAX_CONCURRENT: int = 3    # 最大并发爬取数
    CRAWL4AI_CACHE_ENABLED: bool = True # 启用 Crawl4AI 内置缓存
    CRAWL4AI_VERBOSE: bool = False

    # ===== SearXNG 配置 =====
    SEARXNG_ENABLED: bool = True
    SEARXNG_URL: str = "http://searxng:8080"  # Docker 内部地址
    SEARXNG_TIMEOUT: int = 15
    SEARXNG_MAX_RESULTS: int = 10

    # ===== Open-WebSearch 配置 =====
    OPEN_WEBSEARCH_ENABLED: bool = True
    OPEN_WEBSEARCH_URL: str = "http://localhost:3080"
    OPEN_WEBSEARCH_ENGINES: str = "bing,duckduckgo,baidu"
    OPEN_WEBSEARCH_TIMEOUT: int = 15

    # ===== HeadlessX 反检测抓取层（P6-B） =====
    # self-hosted Camoufox-based scraping platform: https://github.com/saifyxpro/HeadlessX
    HEADLESSX_BASE_URL: str = ""                # http://headlessx:3000 (Docker 内部) 或 https://headlessx.example.com
    HEADLESSX_API_KEY: str = ""                 # x-api-key 鉴权
    HEADLESSX_TIMEOUT: int = 60                 # 单次渲染超时 (秒)
    HEADLESSX_FALLBACK_TIER: str = "l2_crawl4ai"  # L3 失败时回退到哪一层

    # ===== OAuth 第三方登录 =====
    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""
    WECHAT_REDIRECT_URI: str = ""
    WECHAT_MINI_APP_ID: str = ""
    WECHAT_MINI_APP_SECRET: str = ""

    ALIPAY_REDIRECT_URI: str = ""

    # ===== Notion OAuth (P4-D) =====
    # 控制台：https://www.notion.so/my-integrations
    NOTION_CLIENT_ID: str = ""
    NOTION_CLIENT_SECRET: str = ""

    # 前端登录页 URL（OAuth 回调后重定向）
    FRONTEND_LOGIN_URL: str = "http://localhost:3001/login"

    # ===== 飞书（Lark）IM 适配器（P3） =====
    # 控制台：https://open.feishu.cn → 应用凭证
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""
    FEISHU_VERIFY_TOKEN: str = ""    # 事件订阅 Verification Token
    FEISHU_ENCRYPT_KEY: str = ""     # 事件订阅 Encrypt Key（开启加密推送时使用）
    # P16-C: fail-closed —— 默认要求飞书签名校验。仅当显式置为 False 时才允许
    # 在 encrypt_key 缺失的情况下放行（仅推荐本地调试 / 联调环境）。
    FEISHU_VERIFY_SIGNATURE: bool = True
    # X-Lark-Request-Timestamp 与服务器时间允许的最大偏差（秒），防 replay。
    FEISHU_TIMESTAMP_MAX_AGE_SECONDS: int = 300

    # ===== 通用应用授权（P4-A） =====
    # Fernet base64-urlsafe key（生成: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"）
    # 支持逗号分隔多 key 用于 key rotation（首位为新 key，其余为待淘汰旧 key）
    OAUTH_TOKEN_ENCRYPTION_KEY: str = ""
    # 第三方授权回调基础 URL（不含 /api/v1/...），如 https://api.anxin-fawu.com
    APP_AUTH_REDIRECT_BASE_URL: str = "http://localhost:8001"

    # ===== 钉钉 OAuth Provider（P4-C） =====
    DINGTALK_APP_KEY: str = ""
    DINGTALK_APP_SECRET: str = ""

    # ===== Shopify OAuth Provider（P4-E） =====
    # 控制台：https://partners.shopify.com → Apps → API credentials
    SHOPIFY_API_KEY: str = ""
    SHOPIFY_API_SECRET: str = ""
    SHOPIFY_API_VERSION: str = "2024-10"

    # ===== 跨境电商数据源凭据（P6-D） =====
    # Amazon SP-API（mock 阶段不强制；真实接入需 LWA + AWS SigV4）
    AMAZON_SP_LWA_CLIENT_ID: str = ""
    AMAZON_SP_LWA_CLIENT_SECRET: str = ""
    AMAZON_SP_REFRESH_TOKEN: str = ""
    AMAZON_SP_REGION: str = "us-east-1"
    # 阿里 1688 开放平台（ISV 凭据；mock 阶段为空即可）
    ALIBABA_1688_APP_KEY: str = ""
    ALIBABA_1688_APP_SECRET: str = ""
    # Shopee Open Platform（Partner 凭据；mock 阶段为空即可）
    SHOPEE_PARTNER_ID: str = ""
    SHOPEE_PARTNER_KEY: str = ""
    # TikTok Shop（Partner Center 凭据；mock 阶段为空即可）
    TIKTOK_SHOP_APP_KEY: str = ""
    TIKTOK_SHOP_APP_SECRET: str = ""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # 自动生成安全的 JWT 密钥（如果未设置）
        if self.JWT_SECRET_KEY == "your-super-secret-jwt-key-change-in-production":
            if self.ENVIRONMENT in {"production", "staging"}:
                raise ValueError(
                    "生产/预发环境必须设置安全的 JWT_SECRET_KEY！"
                    "请在环境变量中设置强密钥。"
                )
            elif self.ENVIRONMENT == "development":
                # 开发环境自动生成密钥
                self.JWT_SECRET_KEY = secrets.token_urlsafe(32)

        # [SEC-S1.4] 生产环境强制安全档：fail-closed + WAF 拦截模式 + DEV_MODE 关闭
        if self.ENVIRONMENT in {"production", "staging"}:
            problems: list[str] = []
            if self.DEV_MODE:
                problems.append("DEV_MODE 必须为 false（当前为 true，会绕过认证）")
            if not self.AUTH_REDIS_FAIL_CLOSED:
                problems.append(
                    "AUTH_REDIS_FAIL_CLOSED 必须为 true（当前 false，"
                    "Redis 不可用时会 fail-open 放过过期 token）"
                )
            if self.ANTIBOT_ENABLED and self.ANTIBOT_WAF_ENABLED and self.ANTIBOT_WAF_LOG_ONLY:
                problems.append(
                    "ANTIBOT_WAF_LOG_ONLY 必须为 false（当前 true，WAF 仅日志不拦截）"
                )
            if self.WEBHOOK_PROCESSING_LOCK_BACKEND == "auto":
                problems.append(
                    "WEBHOOK_PROCESSING_LOCK_BACKEND 必须显式设置为 'redis'（当前 'auto'，"
                    "可能退化到本地锁，无分布式幂等保证）"
                )
            # [SEC-S2.3] CORS：生产环境禁止 localhost / 通配
            localhost_origins = [
                o for o in self.CORS_ORIGINS
                if "localhost" in o or "127.0.0.1" in o or o == "*"
            ]
            if localhost_origins:
                problems.append(
                    f"CORS_ORIGINS 包含开发用源 {localhost_origins}。"
                    "生产环境必须通过 env 覆盖为真实域名列表（如 https://anxinai.com）。"
                    "Tauri 桌面端如需访问，请使用 tauri://localhost / https://tauri.localhost 而非 http://localhost。"
                )
            if problems:
                raise ValueError(
                    f"[{self.ENVIRONMENT}] 安全配置不合规，禁止启动：\n  - "
                    + "\n  - ".join(problems)
                    + "\n请通过环境变量修正后重启。"
                )

    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return self.ENVIRONMENT == "production"

    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return self.ENVIRONMENT in ("development", "dev")


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
