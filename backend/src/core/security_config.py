"""
安全加固配置

覆盖：
1. 数据分类分级（个人信息、商业秘密、一般数据）
2. API 安全策略（限流、CORS、认证）
3. 敏感操作审计日志
4. 密钥管理规范
5. 输入验证与注入防护
"""

from enum import Enum

# ===== 数据分类分级 =====

class DataClassification(str, Enum):
    """数据敏感等级（参考 GB/T 35273）"""
    PUBLIC = "public"              # 公开数据（法规条文、公开判例）
    INTERNAL = "internal"          # 内部数据（系统配置、操作日志）
    CONFIDENTIAL = "confidential"  # 机密数据（合同内容、案件详情）
    SENSITIVE = "sensitive"        # 敏感数据（个人信息、支付信息）
    TOP_SECRET = "top_secret"      # 绝密数据（密码哈希、API 密钥）


# 字段级数据分级映射
FIELD_CLASSIFICATION: dict[str, DataClassification] = {
    # 用户数据
    "email": DataClassification.SENSITIVE,
    "hashed_password": DataClassification.TOP_SECRET,
    "name": DataClassification.CONFIDENTIAL,
    "phone": DataClassification.SENSITIVE,
    "id_card": DataClassification.SENSITIVE,
    "wechat_openid": DataClassification.SENSITIVE,
    "alipay_user_id": DataClassification.SENSITIVE,

    # 业务数据
    "contract_content": DataClassification.CONFIDENTIAL,
    "case_detail": DataClassification.CONFIDENTIAL,
    "original_description": DataClassification.CONFIDENTIAL,  # 找律师原始描述
    "anonymous_summary": DataClassification.INTERNAL,          # 脱敏后的摘要

    # 财务数据
    "payment_amount": DataClassification.CONFIDENTIAL,
    "bank_account": DataClassification.SENSITIVE,
    "credit_card": DataClassification.TOP_SECRET,

    # 法律数据
    "law_text": DataClassification.PUBLIC,
    "case_number": DataClassification.PUBLIC,
    "investigation_result": DataClassification.CONFIDENTIAL,
}


# ===== API 安全策略 =====

CORS_CONFIG = {
    "allow_origins": [
        "https://anxinassistant.com",
        "https://www.anxinassistant.com",
        "http://localhost:3001",  # 开发环境
    ],
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type", "X-Request-ID"],
    "allow_credentials": True,
    "max_age": 3600,
}

RATE_LIMIT_CONFIG = {
    "default": "60/minute",           # 默认限流
    "auth": "10/minute",               # 认证接口
    "ai_generation": "20/minute",      # AI 生成（成本控制）
    "file_upload": "10/minute",        # 文件上传
    "investigation": "5/minute",       # 尽职调查（成本高）
    "export": "10/minute",             # 导出操作
}


# ===== 敏感操作审计 =====

AUDITABLE_ACTIONS = [
    "user_login",
    "user_logout",
    "password_change",
    "role_change",
    "data_export",
    "data_delete",
    "contract_sign",
    "payment_execute",
    "investigation_start",
    "admin_action",
    "api_key_access",
]


# ===== 输入验证规则 =====

INPUT_VALIDATION = {
    "max_message_length": 10000,       # 单条消息最大字符
    "max_document_size_mb": 50,        # 文档上传最大 MB
    "max_batch_size": 100,             # 批量操作最大数量
    "allowed_file_types": [
        ".pdf", ".doc", ".docx", ".txt", ".md",
        ".xls", ".xlsx", ".csv",
        ".jpg", ".jpeg", ".png", ".gif",
    ],
    "sql_injection_patterns": [
        r";\s*DROP\s+TABLE",
        r";\s*DELETE\s+FROM",
        r"UNION\s+SELECT",
        r"OR\s+1\s*=\s*1",
    ],
    "xss_patterns": [
        r"<script",
        r"javascript:",
        r"on\w+\s*=",
    ],
}


# ===== 密钥管理 =====

SECRET_KEY_ROTATION = {
    "jwt_secret_rotation_days": 90,      # JWT 密钥轮换周期
    "api_key_max_age_days": 365,         # API Key 最长有效期
    "session_max_age_hours": 24,         # 会话最长时间
    "refresh_token_max_age_days": 30,    # 刷新令牌有效期
}


# ===== 安全检查清单 =====

SECURITY_CHECKLIST = {
    "authentication": [
        "JWT token 签名验证",
        "刷新令牌安全存储（HttpOnly Cookie）",
        "密码强度要求（8+字符，大小写+数字）",
        "登录失败锁定（5次后锁定30分钟）",
        "多因素认证支持（可选）",
    ],
    "authorization": [
        "RBAC 角色权限模型",
        "资源级别访问控制",
        "API 端点权限注解",
        "数据行级隔离（org_id）",
    ],
    "data_protection": [
        "传输加密（TLS 1.2+）",
        "敏感字段加密存储",
        "日志脱敏（PII 字段）",
        "备份加密",
    ],
    "compliance": [
        "GB 45438-2025 AI 内容标识",
        "个人信息保护法合规",
        "数据安全法分级分类",
        "生成式 AI 服务备案",
    ],
}


def get_field_classification(field_name: str) -> DataClassification:
    """获取字段的数据分级"""
    return FIELD_CLASSIFICATION.get(field_name, DataClassification.INTERNAL)


def is_auditable(action: str) -> bool:
    """检查操作是否需要审计"""
    return action in AUDITABLE_ACTIONS
