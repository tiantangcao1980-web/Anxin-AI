"""
FastAPI依赖注入
包含认证、授权、权限控制、频率限制等
"""

from collections.abc import Awaitable, Callable
from enum import Enum

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.core.security import (
    RateLimitBackendUnavailable,
    RateLimitConfig,
    get_rate_limiter,
    verify_token,
    verify_token_with_blacklist,
)
from src.models.user import User

# HTTP Bearer认证
security = HTTPBearer(auto_error=False)
UserDependency = Callable[..., Awaitable[User]]
RateLimitDependency = Callable[..., Awaitable[None]]


# ========== 角色枚举 ==========


class UserRole(str, Enum):
    """用户角色 — 企业微信/飞书式多层级权限体系"""

    # 平台层
    SUPER_ADMIN = "super_admin"  # 超级管理员：平台级全局配置
    ADMIN = "admin"  # 管理员（兼容旧角色，等同 org_admin）

    # 租户层
    ORG_ADMIN = "org_admin"  # 企业/律所管理员
    DEPT_ADMIN = "dept_admin"  # 部门管理员

    # 业务层
    PARTNER = "partner"  # 合伙人：全面访问+数据分析
    LAWYER = "lawyer"  # 律师：案件管理、合同审查
    PARALEGAL = "paralegal"  # 助理（兼容旧 paralegal）
    ENTERPRISE_USER = "enterprise_user"  # 企业用户：法务/HR/经营者
    INDIVIDUAL_USER = "individual_user"  # 个人用户：法律咨询

    # 平台入驻律师
    PLATFORM_LAWYER = "platform_lawyer"  # 入驻律师：接单、计费、评价

    # 兼容旧角色
    MEMBER = "member"  # 普通成员（映射为 enterprise_user）
    CLIENT = "client"  # 客户（映射为 individual_user）
    VIEWER = "viewer"  # 访客：只读权限


# ========== 权限枚举 ==========


class Permission(str, Enum):
    """权限定义"""

    # 案件权限
    READ_CASES = "read:cases"
    WRITE_CASES = "write:cases"
    DELETE_CASES = "delete:cases"
    ASSIGN_CASES = "assign:cases"

    # 文档权限
    READ_DOCUMENTS = "read:documents"
    WRITE_DOCUMENTS = "write:documents"
    DELETE_DOCUMENTS = "delete:documents"
    DOWNLOAD_DOCUMENTS = "download:documents"

    # 合同权限
    READ_CONTRACTS = "read:contracts"
    WRITE_CONTRACTS = "write:contracts"
    DELETE_CONTRACTS = "delete:contracts"
    REVIEW_CONTRACTS = "review:contracts"
    SIGN_CONTRACTS = "sign:contracts"

    # 用户权限
    READ_USERS = "read:users"
    WRITE_USERS = "write:users"
    DELETE_USERS = "delete:users"
    MANAGE_ROLES = "manage:roles"

    # 组织权限
    READ_ORGANIZATION = "read:organization"
    WRITE_ORGANIZATION = "write:organization"
    MANAGE_ORGANIZATION = "manage:organization"

    # 知识库权限
    READ_KNOWLEDGE = "read:knowledge"
    WRITE_KNOWLEDGE = "write:knowledge"
    DELETE_KNOWLEDGE = "delete:knowledge"

    # 对话权限
    USE_CHAT = "use:chat"
    VIEW_ALL_CHATS = "view:all_chats"

    # 资产权限
    READ_ASSETS = "read:assets"
    WRITE_ASSETS = "write:assets"
    DELETE_ASSETS = "delete:assets"

    # 系统权限
    VIEW_AUDIT_LOGS = "view:audit_logs"
    MANAGE_SYSTEM = "manage:system"
    MANAGE_LLM_CONFIG = "manage:llm_config"
    EXPORT_DATA = "export:data"

    # 找律师/委托权限
    FIND_LAWYER = "find:lawyer"
    ACCEPT_CASE = "accept:case"  # 入驻律师接单
    CREATE_DELEGATION = "create:delegation"  # 一键委托
    MANAGE_PAYMENTS = "manage:payments"  # 支付/收款

    # 审批权限
    CREATE_APPROVAL = "create:approval"
    REVIEW_APPROVAL = "review:approval"
    MANAGE_APPROVALS = "manage:approvals"

    # 获客/营销权限
    MANAGE_MARKETING = "manage:marketing"
    VIEW_ANALYTICS = "view:analytics"

    # 律所内部管理
    MANAGE_TIMESHEET = "manage:timesheet"
    MANAGE_BILLING = "manage:billing"
    MANAGE_CRM = "manage:crm"

    # 律师入驻管理
    VERIFY_LAWYER = "verify:lawyer"  # 审核律师认证
    MANAGE_ONBOARDING = "manage:onboarding"  # 管理入驻流程

    # 计费管理
    MANAGE_PLANS = "manage:plans"  # 管理计费方案
    MANAGE_SUBSCRIPTIONS = "manage:subscriptions"  # 管理订阅
    MANAGE_REFUNDS = "manage:refunds"  # 管理退款
    VIEW_REPORTS = "view:reports"  # 查看报表

    # AI 助手管理
    MANAGE_AI_ASSISTANT = "manage:ai_assistant"  # 管理 AI 私有助手配置


# ========== 角色权限映射 ==========


ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    # ===== 平台层 =====
    UserRole.SUPER_ADMIN.value: set(Permission),  # 超管拥有所有权限
    UserRole.ADMIN.value: set(Permission),  # 管理员（兼容旧角色）
    # ===== 租户层 =====
    UserRole.ORG_ADMIN.value: {
        # 除平台级系统管理外的所有权限
        p
        for p in Permission
        if p not in {Permission.MANAGE_SYSTEM}
    },
    UserRole.DEPT_ADMIN.value: {
        Permission.READ_CASES,
        Permission.WRITE_CASES,
        Permission.ASSIGN_CASES,
        Permission.READ_DOCUMENTS,
        Permission.WRITE_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.DOWNLOAD_DOCUMENTS,
        Permission.READ_CONTRACTS,
        Permission.WRITE_CONTRACTS,
        Permission.REVIEW_CONTRACTS,
        Permission.READ_USERS,
        Permission.READ_ORGANIZATION,
        Permission.READ_KNOWLEDGE,
        Permission.WRITE_KNOWLEDGE,
        Permission.USE_CHAT,
        Permission.VIEW_ALL_CHATS,
        Permission.READ_ASSETS,
        Permission.WRITE_ASSETS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.EXPORT_DATA,
        Permission.CREATE_APPROVAL,
        Permission.REVIEW_APPROVAL,
        Permission.VIEW_ANALYTICS,
        Permission.MANAGE_AI_ASSISTANT,
    },
    # ===== 业务层 =====
    UserRole.PARTNER.value: {
        # 合伙人：全面访问+数据分析+计费
        Permission.READ_CASES,
        Permission.WRITE_CASES,
        Permission.DELETE_CASES,
        Permission.ASSIGN_CASES,
        Permission.READ_DOCUMENTS,
        Permission.WRITE_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.DOWNLOAD_DOCUMENTS,
        Permission.READ_CONTRACTS,
        Permission.WRITE_CONTRACTS,
        Permission.DELETE_CONTRACTS,
        Permission.REVIEW_CONTRACTS,
        Permission.SIGN_CONTRACTS,
        Permission.READ_USERS,
        Permission.WRITE_USERS,
        Permission.READ_ORGANIZATION,
        Permission.WRITE_ORGANIZATION,
        Permission.READ_KNOWLEDGE,
        Permission.WRITE_KNOWLEDGE,
        Permission.DELETE_KNOWLEDGE,
        Permission.USE_CHAT,
        Permission.VIEW_ALL_CHATS,
        Permission.READ_ASSETS,
        Permission.WRITE_ASSETS,
        Permission.DELETE_ASSETS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.EXPORT_DATA,
        Permission.MANAGE_LLM_CONFIG,
        Permission.CREATE_APPROVAL,
        Permission.REVIEW_APPROVAL,
        Permission.MANAGE_APPROVALS,
        Permission.VIEW_ANALYTICS,
        Permission.MANAGE_TIMESHEET,
        Permission.MANAGE_BILLING,
        Permission.MANAGE_CRM,
        Permission.MANAGE_AI_ASSISTANT,
        Permission.VIEW_REPORTS,
    },
    UserRole.LAWYER.value: {
        Permission.READ_CASES,
        Permission.WRITE_CASES,
        Permission.DELETE_CASES,
        Permission.ASSIGN_CASES,
        Permission.READ_DOCUMENTS,
        Permission.WRITE_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.DOWNLOAD_DOCUMENTS,
        Permission.READ_CONTRACTS,
        Permission.WRITE_CONTRACTS,
        Permission.DELETE_CONTRACTS,
        Permission.REVIEW_CONTRACTS,
        Permission.SIGN_CONTRACTS,
        Permission.READ_KNOWLEDGE,
        Permission.WRITE_KNOWLEDGE,
        Permission.READ_USERS,
        Permission.READ_ORGANIZATION,
        Permission.USE_CHAT,
        Permission.VIEW_ALL_CHATS,
        Permission.READ_ASSETS,
        Permission.WRITE_ASSETS,
        Permission.DELETE_ASSETS,
        Permission.EXPORT_DATA,
        Permission.CREATE_APPROVAL,
        Permission.MANAGE_TIMESHEET,
    },
    UserRole.PARALEGAL.value: {
        Permission.READ_CASES,
        Permission.WRITE_CASES,
        Permission.READ_DOCUMENTS,
        Permission.WRITE_DOCUMENTS,
        Permission.DOWNLOAD_DOCUMENTS,
        Permission.READ_CONTRACTS,
        Permission.REVIEW_CONTRACTS,
        Permission.READ_KNOWLEDGE,
        Permission.READ_USERS,
        Permission.READ_ORGANIZATION,
        Permission.USE_CHAT,
        Permission.READ_ASSETS,
        Permission.WRITE_ASSETS,
        Permission.CREATE_APPROVAL,
    },
    UserRole.ENTERPRISE_USER.value: {
        # 企业用户：合规管理+法律咨询+合同审查+找律师
        Permission.USE_CHAT,
        Permission.READ_CASES,
        Permission.READ_DOCUMENTS,
        Permission.READ_CONTRACTS,
        Permission.WRITE_CONTRACTS,
        Permission.REVIEW_CONTRACTS,
        Permission.DOWNLOAD_DOCUMENTS,
        Permission.READ_KNOWLEDGE,
        Permission.FIND_LAWYER,
        Permission.CREATE_DELEGATION,
        Permission.MANAGE_PAYMENTS,
        Permission.CREATE_APPROVAL,
        Permission.READ_ASSETS,
    },
    UserRole.INDIVIDUAL_USER.value: {
        # 个人用户：AI咨询+找律师（限次）
        Permission.USE_CHAT,
        Permission.READ_CONTRACTS,
        Permission.READ_KNOWLEDGE,
        Permission.FIND_LAWYER,
        Permission.CREATE_DELEGATION,
        Permission.MANAGE_PAYMENTS,
    },
    # ===== 入驻律师 =====
    UserRole.PLATFORM_LAWYER.value: {
        Permission.USE_CHAT,
        Permission.ACCEPT_CASE,
        Permission.READ_CASES,
        Permission.WRITE_CASES,
        Permission.READ_CONTRACTS,
        Permission.WRITE_CONTRACTS,
        Permission.REVIEW_CONTRACTS,
        Permission.READ_DOCUMENTS,
        Permission.WRITE_DOCUMENTS,
        Permission.DOWNLOAD_DOCUMENTS,
        Permission.READ_KNOWLEDGE,
        Permission.MANAGE_PAYMENTS,
        Permission.MANAGE_TIMESHEET,
        Permission.MANAGE_ONBOARDING,
    },
    # ===== 兼容旧角色 =====
    UserRole.MEMBER.value: {
        # member 映射为 enterprise_user 级别
        Permission.USE_CHAT,
        Permission.READ_CASES,
        Permission.WRITE_CASES,
        Permission.READ_DOCUMENTS,
        Permission.WRITE_DOCUMENTS,
        Permission.DOWNLOAD_DOCUMENTS,
        Permission.READ_CONTRACTS,
        Permission.READ_KNOWLEDGE,
        Permission.READ_ASSETS,
        Permission.CREATE_APPROVAL,
    },
    UserRole.CLIENT.value: {
        # client 映射为 individual_user 级别
        Permission.USE_CHAT,
        Permission.READ_CASES,
        Permission.READ_DOCUMENTS,
        Permission.DOWNLOAD_DOCUMENTS,
        Permission.READ_CONTRACTS,
        Permission.FIND_LAWYER,
    },
    UserRole.VIEWER.value: {
        Permission.READ_CASES,
        Permission.READ_DOCUMENTS,
        Permission.READ_CONTRACTS,
        Permission.READ_KNOWLEDGE,
        Permission.READ_ASSETS,
    },
}


def get_user_permissions(role: str) -> set[Permission]:
    """获取角色对应的权限集合"""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: str, permission: Permission) -> bool:
    """检查角色是否拥有指定权限"""
    permissions = get_user_permissions(role)
    return permission in permissions


# ========== 认证依赖 ==========


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    获取当前用户（可选认证）
    """
    if not credentials:
        return None

    token = credentials.credentials

    # 使用带黑名单检查的验证（Redis 不可用时降级为无黑名单验证）
    try:
        user_id = await verify_token_with_blacklist(token)
    except Exception:
        logger.warning("Redis不可用，降级为无黑名单Token验证")
        user_id = verify_token(token)

    if not user_id:
        return None

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()

    return user


async def get_current_user_required(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    获取当前用户（必须认证）
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # 使用带黑名单检查的验证（Redis 不可用时降级）
    try:
        user_id = await verify_token_with_blacklist(token)
    except Exception:
        logger.warning("Redis不可用，降级为无黑名单Token验证")
        user_id = verify_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证Token或Token已失效",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_admin_user(
    user: User = Depends(get_current_user_required),
) -> User:
    """
    获取管理员用户（super_admin / admin / org_admin）
    """
    admin_roles = {UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value, UserRole.ORG_ADMIN.value}
    if user.role not in admin_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user


# ========== 权限依赖工厂 ==========


def require_permission(*permissions: Permission) -> UserDependency:
    """
    创建权限检查依赖

    可以检查单个或多个权限，用户需要拥有所有指定权限

    Example:
        @router.get("/cases")
        async def list_cases(
            user: User = Depends(require_permission(Permission.READ_CASES))
        ):
            ...

        @router.delete("/cases/{case_id}")
        async def delete_case(
            case_id: str,
            user: User = Depends(require_permission(
                Permission.READ_CASES,
                Permission.DELETE_CASES
            ))
        ):
            ...
    """

    async def dependency(
        user: User = Depends(get_current_user_required),
    ) -> User:
        user_permissions = get_user_permissions(user.role)

        missing_permissions = []
        for permission in permissions:
            if permission not in user_permissions:
                missing_permissions.append(permission.value)

        if missing_permissions:
            logger.warning(
                f"权限不足: user={user.email}, role={user.role}, " f"missing={missing_permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，缺少以下权限: {', '.join(missing_permissions)}",
            )

        return user

    return dependency


def require_any_permission(*permissions: Permission) -> UserDependency:
    """
    创建权限检查依赖（满足任一权限即可）

    Example:
        @router.get("/cases/{case_id}")
        async def get_case(
            user: User = Depends(require_any_permission(
                Permission.READ_CASES,
                Permission.WRITE_CASES
            ))
        ):
            ...
    """

    async def dependency(
        user: User = Depends(get_current_user_required),
    ) -> User:
        user_permissions = get_user_permissions(user.role)

        for permission in permissions:
            if permission in user_permissions:
                return user

        permission_names = [p.value for p in permissions]
        logger.warning(
            f"权限不足: user={user.email}, role={user.role}, " f"required_any={permission_names}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足，需要以下权限之一: {', '.join(permission_names)}",
        )

    return dependency


def require_role(*roles: UserRole) -> UserDependency:
    """
    创建角色检查依赖

    Example:
        @router.post("/admin/users")
        async def create_user(
            user: User = Depends(require_role(UserRole.ADMIN))
        ):
            ...
    """

    async def dependency(
        user: User = Depends(get_current_user_required),
    ) -> User:
        role_values = [r.value for r in roles]

        if user.role not in role_values:
            logger.warning(
                f"角色不匹配: user={user.email}, current_role={user.role}, "
                f"required_roles={role_values}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要以下角色之一: {', '.join(role_values)}",
            )

        return user

    return dependency


# ========== 频率限制依赖 ==========


def rate_limit(
    limit: int = RateLimitConfig.API_DEFAULT["limit"],
    window: int = RateLimitConfig.API_DEFAULT["window"],
    endpoint: str | None = None,
    by_user: bool = True,
    fail_closed: bool = False,
) -> RateLimitDependency:
    """
    创建频率限制依赖

    Args:
        limit: 限制次数
        window: 时间窗口（秒）
        endpoint: 端点标识（默认使用路由路径）
        by_user: 是否按用户限制（否则按IP）
        fail_closed: Redis 后端不可用时是否拒绝服务（认证敏感入口使用）

    Example:
        @router.post("/chat")
        async def chat(
            request: Request,
            _: None = Depends(rate_limit(limit=30, window=60, endpoint="chat"))
        ):
            ...
    """

    async def dependency(
        request: Request,
        user: User | None = Depends(get_current_user),
    ) -> None:
        rate_limiter = get_rate_limiter()

        # 确定标识符
        if by_user and user:
            identifier = user.id
        else:
            # 使用IP地址
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                identifier = forwarded.split(",")[0].strip()
            else:
                identifier = request.client.host if request.client else "unknown"

        # 确定端点
        ep = endpoint or request.url.path

        auth_fail_closed = fail_closed and bool(
            settings.AUTH_REDIS_FAIL_CLOSED
            or settings.ENVIRONMENT.lower() in {"staging", "production"}
        )

        # 检查频率限制
        try:
            allowed, current, remaining = await rate_limiter.check_rate_limit(
                identifier=identifier,
                endpoint=ep,
                limit=limit,
                window=window,
                fail_closed=auth_fail_closed,
            )
        except RateLimitBackendUnavailable:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="认证限流服务暂不可用，请稍后重试",
                headers={"Retry-After": str(window)},
            ) from None

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"请求过于频繁，请在{window}秒后重试",
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(window),
                },
            )

        # 可以在响应头中添加限流信息（需要在路由中处理）
        request.state.rate_limit_info = {
            "limit": limit,
            "remaining": remaining,
            "reset": window,
        }

    return dependency


# 预定义的限流依赖
rate_limit_default = rate_limit()
rate_limit_auth = rate_limit(
    limit=RateLimitConfig.AUTH_LOGIN["limit"],
    window=RateLimitConfig.AUTH_LOGIN["window"],
    endpoint="auth",
    fail_closed=True,
)
rate_limit_chat = rate_limit(
    limit=RateLimitConfig.CHAT["limit"],
    window=RateLimitConfig.CHAT["window"],
    endpoint="chat",
)
rate_limit_search = rate_limit(
    limit=RateLimitConfig.SEARCH["limit"],
    window=RateLimitConfig.SEARCH["window"],
    endpoint="search",
)
rate_limit_upload = rate_limit(
    limit=RateLimitConfig.UPLOAD["limit"],
    window=RateLimitConfig.UPLOAD["window"],
    endpoint="upload",
)


# ========== 组合依赖 ==========


def authenticated_with_permission(*permissions: Permission) -> UserDependency:
    """
    组合认证和权限检查

    Example:
        @router.delete("/cases/{case_id}")
        async def delete_case(
            case_id: str,
            user: User = Depends(authenticated_with_permission(Permission.DELETE_CASES))
        ):
            ...
    """
    return require_permission(*permissions)


def rate_limited_user(
    limit: int = 60,
    window: int = 60,
) -> UserDependency:
    """
    组合认证和频率限制

    返回已认证的用户，同时应用频率限制
    """

    async def dependency(
        request: Request,
        user: User = Depends(get_current_user_required),
    ) -> User:
        rate_limiter = get_rate_limiter()

        allowed, _, _ = await rate_limiter.check_rate_limit(
            identifier=user.id,
            endpoint=request.url.path,
            limit=limit,
            window=window,
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"请求过于频繁，请在{window}秒后重试",
            )

        return user

    return dependency


# ========== 租户上下文依赖 ==========


class TenantContext:
    """租户上下文"""

    def __init__(self, org_id: str, user: User):
        self.org_id = org_id
        self.user = user


async def get_tenant_context(
    user: User = Depends(get_current_user_required),
) -> TenantContext:
    """
    获取当前用户的租户上下文

    自动从用户信息中提取 org_id，确保多租户数据隔离
    """
    if not user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户未关联组织，请联系管理员",
        )
    return TenantContext(org_id=user.org_id, user=user)


async def get_optional_tenant_context(
    user: User | None = Depends(get_current_user),
) -> TenantContext | None:
    """
    获取可选的租户上下文（用于可选认证场景）
    """
    if user and user.org_id:
        return TenantContext(org_id=user.org_id, user=user)
    return None
