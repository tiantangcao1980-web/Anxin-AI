"""
管理后台 API 路由
提供系统仪表盘、用户管理、角色权限、审计日志、系统配置、组织管理等管理功能
"""

import time
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from loguru import logger
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import (
    ROLE_PERMISSIONS,
    Permission,
    UserRole,
    get_admin_user,
)
from src.core.responses import UnifiedResponse
from src.core.security import get_password_hash
from src.models.audit import AuditAction, AuditLog, ResourceType
from src.models.case import Case
from src.models.contract import Contract
from src.models.document import Document
from src.models.user import Organization, User
from src.models.webhook import WebhookReceived
from src.services.audit_service import AuditService
from src.services.user_service import UserService
from src.services.webhook_retry_service import WebhookRetryError, retry_failed_webhook

router = APIRouter(prefix="/admin")

# 系统启动时间（用于计算 uptime）
_system_start_time = time.time()


# ========== Pydantic 请求/响应模型 ==========


class DashboardResponse(BaseModel):
    """系统仪表盘响应"""
    total_users: int = 0
    active_users: int = 0
    total_cases: int = 0
    total_contracts: int = 0
    total_documents: int = 0
    storage_used_mb: float = 0.0
    system_uptime_seconds: float = 0.0
    users_by_role: dict[str, int] = Field(default_factory=dict)


class UserListResponse(BaseModel):
    """用户列表响应"""
    total: int
    items: list[dict[str, Any]]
    skip: int
    limit: int


class UserDetailResponse(BaseModel):
    """用户详情响应"""
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    org_id: str | None = None
    avatar_url: str | None = None
    login_type: str = "email"
    created_at: str | None = None
    updated_at: str | None = None


class AdminCreateUserRequest(BaseModel):
    """管理员创建用户请求"""
    email: EmailStr
    password: str = Field(..., min_length=6, description="密码，至少6位")
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="member", description="角色: admin/lawyer/paralegal/client/member/viewer")
    org_id: str | None = None
    is_active: bool = True


class AdminUpdateUserRequest(BaseModel):
    """管理员更新用户请求"""
    name: str | None = Field(None, min_length=1, max_length=100)
    role: str | None = None
    is_active: bool | None = None
    org_id: str | None = None
    avatar_url: str | None = None


class ToggleStatusRequest(BaseModel):
    """切换用户状态请求"""
    is_active: bool


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    new_password: str = Field(..., min_length=6, description="新密码，至少6位")


class RoleDefinition(BaseModel):
    """角色定义"""
    role_name: str
    display_name: str
    permissions: list[str]


class UpdateRolePermissionsRequest(BaseModel):
    """更新角色权限请求"""
    permissions: list[str]


class AuditLogListResponse(BaseModel):
    """审计日志列表响应"""
    total: int
    items: list[dict[str, Any]]
    skip: int
    limit: int


class AuditLogStatsResponse(BaseModel):
    """审计统计响应"""
    actions_per_day: list[dict[str, Any]] = Field(default_factory=list)
    top_users: list[dict[str, Any]] = Field(default_factory=list)
    top_actions: list[dict[str, Any]] = Field(default_factory=list)


class SystemConfigResponse(BaseModel):
    """系统配置响应"""
    app_name: str
    app_version: str
    environment: str
    debug: bool
    rate_limit_enabled: bool
    rate_limit_per_minute: int
    cors_origins: list[str]
    password_min_length: int
    # E签宝 配置（非敏感项 + 脱敏的敏感项）
    esign: dict[str, Any] | None = None
    # 法大大 配置（非敏感项 + 脱敏的敏感项）
    fadada: dict[str, Any] | None = None
    # 微信支付 配置（非敏感项 + 脱敏的敏感项）
    wechat_pay: dict[str, Any] | None = None
    # 支付宝 配置（非敏感项 + 脱敏的敏感项）
    alipay: dict[str, Any] | None = None


class UpdateSystemConfigRequest(BaseModel):
    """更新系统配置请求"""
    rate_limit_per_minute: int | None = None
    password_min_length: int | None = None
    # E签宝 配置
    esign: dict[str, Any] | None = None
    # 法大大 配置
    fadada: dict[str, Any] | None = None
    # 微信支付 配置
    wechat_pay: dict[str, Any] | None = None
    # 支付宝 配置
    alipay: dict[str, Any] | None = None


class SystemHealthResponse(BaseModel):
    """系统健康检查响应"""
    status: str
    database: str
    redis: str
    uptime_seconds: float


class OrgCreateRequest(BaseModel):
    """创建组织请求"""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    logo_url: str | None = None


class OrgUpdateRequest(BaseModel):
    """更新组织请求"""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    logo_url: str | None = None
    is_active: bool | None = None


class OrgListResponse(BaseModel):
    """组织列表响应"""
    total: int
    items: list[dict[str, Any]]
    skip: int
    limit: int


# ========== 辅助函数 ==========


def _user_to_dict(user: User) -> dict[str, Any]:
    """将用户模型转为字典"""
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "is_active": user.is_active,
        "org_id": user.org_id,
        "avatar_url": user.avatar_url,
        "login_type": user.login_type,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def _org_to_dict(org: Organization) -> dict[str, Any]:
    """将组织模型转为字典"""
    return {
        "id": org.id,
        "name": org.name,
        "description": org.description,
        "logo_url": org.logo_url,
        "is_active": org.is_active,
        "created_at": org.created_at.isoformat() if org.created_at else None,
        "updated_at": org.updated_at.isoformat() if org.updated_at else None,
    }


def _webhook_to_dict(record: WebhookReceived) -> dict[str, Any]:
    """将 webhook 处理记录转为后台可展示字典"""
    return {
        "id": record.id,
        "scope": record.scope,
        "idempotency_key": record.idempotency_key,
        "status": record.status,
        "payload": record.payload,
        "processed_at": record.processed_at.isoformat() if record.processed_at else None,
        "error": record.error,
        "retry_count": record.retry_count,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


# 角色中文名映射
ROLE_DISPLAY_NAMES = {
    "admin": "管理员",
    "lawyer": "律师",
    "paralegal": "律师助理",
    "client": "客户",
    "member": "普通成员",
    "viewer": "访客",
}


# ========== 系统仪表盘 ==========


@router.get("/dashboard", response_model=DashboardResponse, summary="系统概览仪表盘")
async def get_dashboard(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """获取系统概览统计数据"""
    # 用户总数
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0

    # 活跃用户数
    active_users_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = active_users_result.scalar() or 0

    # 案件总数
    try:
        total_cases_result = await db.execute(select(func.count(Case.id)))
        total_cases = total_cases_result.scalar() or 0
    except Exception as e:
        logger.warning(f"统计案件数失败（表可能不存在）: {e}")
        total_cases = 0

    # 合同总数
    try:
        total_contracts_result = await db.execute(select(func.count(Contract.id)))
        total_contracts = total_contracts_result.scalar() or 0
    except Exception as e:
        logger.warning(f"统计合同数失败（表可能不存在）: {e}")
        total_contracts = 0

    # 文档总数
    try:
        total_documents_result = await db.execute(select(func.count(Document.id)))
        total_documents = total_documents_result.scalar() or 0
    except Exception as e:
        logger.warning(f"统计文档数失败（表可能不存在）: {e}")
        total_documents = 0

    # 按角色分组统计用户
    role_stats_result = await db.execute(
        select(User.role, func.count(User.id)).group_by(User.role)
    )
    users_by_role = {row[0]: row[1] for row in role_stats_result.all()}

    # 系统运行时间
    uptime = time.time() - _system_start_time

    return DashboardResponse(
        total_users=total_users,
        active_users=active_users,
        total_cases=total_cases,
        total_contracts=total_contracts,
        total_documents=total_documents,
        storage_used_mb=0.0,  # 可扩展：统计文件存储大小
        system_uptime_seconds=round(uptime, 2),
        users_by_role=users_by_role,
    )


@router.get("/webhooks", summary="Webhook 处理记录")
async def list_webhook_records(
    scope: str | None = Query(None, description="按 webhook scope 过滤"),
    status_filter: str | None = Query(None, alias="status", description="按处理状态过滤"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(50, ge=1, le=200, description="返回数量上限"),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """查看 webhook 幂等处理记录，供支付/电签回调排障使用。"""
    query = select(WebhookReceived)
    count_query = select(func.count(WebhookReceived.id))
    conditions = []
    if scope:
        conditions.append(WebhookReceived.scope == scope)
    if status_filter:
        conditions.append(WebhookReceived.status == status_filter)
    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    result = await db.execute(
        query.order_by(WebhookReceived.created_at.desc()).offset(skip).limit(limit)
    )
    records = result.scalars().all()

    stats_result = await db.execute(
        select(WebhookReceived.status, func.count(WebhookReceived.id)).group_by(WebhookReceived.status)
    )
    stats: dict[str, int] = {}
    for status, count in stats_result.all():
        stats[status] = count

    return {
        "total": total,
        "items": [_webhook_to_dict(record) for record in records],
        "skip": skip,
        "limit": limit,
        "stats": stats,
    }


@router.post("/webhooks/{record_id}/retry", summary="重试失败 Webhook")
async def retry_webhook_record(
    record_id: str,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """手动重试失败 webhook，供支付/电签回调排障后恢复业务状态。"""
    record = await db.get(WebhookReceived, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Webhook 记录不存在")
    if record.status != "failed":
        raise HTTPException(status_code=409, detail="仅 failed webhook 记录可重试")

    try:
        result = await retry_failed_webhook(db, record)
        await db.commit()
    except WebhookRetryError as exc:
        await db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await db.refresh(record)
    return {
        "record": _webhook_to_dict(record),
        "result": result,
    }


# ========== 用户管理 ==========


@router.get("/users", response_model=UserListResponse, summary="用户列表")
async def list_users(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    search: str | None = Query(None, description="搜索关键词（邮箱/姓名）"),
    role: str | None = Query(None, description="按角色筛选"),
    is_active: bool | None = Query(None, description="按状态筛选"),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    """获取用户列表，支持分页、搜索和筛选"""
    query = select(User)
    count_query = select(func.count(User.id))

    conditions = []

    if search:
        search_pattern = f"%{search}%"
        conditions.append(
            or_(
                User.email.ilike(search_pattern),
                User.name.ilike(search_pattern),
            )
        )

    if role:
        conditions.append(User.role == role)

    if is_active is not None:
        conditions.append(User.is_active == is_active)

    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))

    # 总数
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return UserListResponse(
        total=total,
        items=[_user_to_dict(u) for u in users],
        skip=skip,
        limit=limit,
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse, summary="用户详情")
async def get_user_detail(
    user_id: str,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UserDetailResponse:
    """获取单个用户详情"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    data = _user_to_dict(user)
    return UserDetailResponse(**data)


@router.post("/users", response_model=UserDetailResponse, status_code=201, summary="创建用户")
async def create_user(
    body: AdminCreateUserRequest,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UserDetailResponse:
    """管理员创建用户"""
    # 验证密码强度
    from src.api.routes.auth import validate_password
    validate_password(body.password)

    # 校验角色有效性
    valid_roles = [r.value for r in UserRole]
    if body.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"无效角色: {body.role}，可选值: {', '.join(valid_roles)}",
        )

    user_service = UserService(db)

    try:
        user = await user_service.create_user(
            email=body.email,
            password=body.password,
            name=body.name,
            org_id=body.org_id,
            role=body.role,
        )
        if not body.is_active:
            user.is_active = False
            await db.flush()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # 审计日志
    audit_service = AuditService(db)
    await audit_service.log_from_request(
        request=request,
        action=AuditAction.USER_REGISTER.value,
        resource_type=ResourceType.USER.value,
        resource_id=user.id,
        user=admin,
        new_value={"email": user.email, "name": user.name, "role": user.role},
    )

    data = _user_to_dict(user)
    return UserDetailResponse(**data)


@router.put("/users/{user_id}", response_model=UserDetailResponse, summary="更新用户")
async def update_user(
    user_id: str,
    body: AdminUpdateUserRequest,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UserDetailResponse:
    """管理员更新用户信息"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    old_value = {"name": user.name, "role": user.role, "is_active": user.is_active, "org_id": user.org_id}

    # 校验角色有效性
    if body.role is not None:
        valid_roles = [r.value for r in UserRole]
        if body.role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"无效角色: {body.role}，可选值: {', '.join(valid_roles)}",
            )
        user.role = body.role

    if body.name is not None:
        user.name = body.name
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.org_id is not None:
        user.org_id = body.org_id
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url

    await db.flush()

    new_value = {"name": user.name, "role": user.role, "is_active": user.is_active, "org_id": user.org_id}

    # 审计日志
    audit_service = AuditService(db)
    await audit_service.log_from_request(
        request=request,
        action=AuditAction.USER_PROFILE_UPDATE.value,
        resource_type=ResourceType.USER.value,
        resource_id=user.id,
        user=admin,
        old_value=old_value,
        new_value=new_value,
    )

    data = _user_to_dict(user)
    return UserDetailResponse(**data)


@router.put("/users/{user_id}/toggle-status", response_model=UserDetailResponse, summary="切换用户状态")
async def toggle_user_status(
    user_id: str,
    body: ToggleStatusRequest,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> UserDetailResponse:
    """启用/禁用用户"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 禁止禁用自己
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能禁用自己的账户")

    old_status = user.is_active
    user.is_active = body.is_active
    await db.flush()

    # 审计日志
    audit_service = AuditService(db)
    await audit_service.log_from_request(
        request=request,
        action=AuditAction.USER_PROFILE_UPDATE.value,
        resource_type=ResourceType.USER.value,
        resource_id=user.id,
        user=admin,
        old_value={"is_active": old_status},
        new_value={"is_active": user.is_active},
        extra_data={"operation": "toggle_status"},
    )

    data = _user_to_dict(user)
    return UserDetailResponse(**data)


@router.put("/users/{user_id}/reset-password", summary="重置用户密码")
async def reset_user_password(
    user_id: str,
    body: ResetPasswordRequest,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """管理员重置用户密码"""
    from src.api.routes.auth import validate_password
    validate_password(body.new_password)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.hashed_password = get_password_hash(body.new_password)
    await db.flush()

    # 审计日志
    audit_service = AuditService(db)
    await audit_service.log_from_request(
        request=request,
        action=AuditAction.USER_PASSWORD_CHANGE.value,
        resource_type=ResourceType.USER.value,
        resource_id=user.id,
        user=admin,
        extra_data={"operation": "admin_reset_password", "target_email": user.email},
    )

    return {"message": f"用户 {user.email} 的密码已重置"}


# ========== 角色与权限管理 ==========


@router.get("/roles", response_model=list[RoleDefinition], summary="角色列表")
async def list_roles(
    admin: User = Depends(get_admin_user),
) -> list[RoleDefinition]:
    """获取所有角色定义及其权限"""
    roles = []
    for role_value, permissions in ROLE_PERMISSIONS.items():
        roles.append(RoleDefinition(
            role_name=role_value,
            display_name=ROLE_DISPLAY_NAMES.get(role_value, role_value),
            permissions=sorted([p.value for p in permissions]),
        ))
    return roles


@router.put("/roles/{role_name}/permissions", response_model=RoleDefinition, summary="更新角色权限")
async def update_role_permissions(
    role_name: str,
    body: UpdateRolePermissionsRequest,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> RoleDefinition:
    """更新指定角色的权限（运行时修改，重启后恢复默认）"""
    if role_name not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=404, detail=f"角色 {role_name} 不存在")

    # 不允许修改 admin 角色权限
    if role_name == UserRole.ADMIN.value:
        raise HTTPException(status_code=400, detail="不允许修改管理员角色的权限")

    # 校验权限值的有效性
    valid_permissions = {p.value for p in Permission}
    invalid = [p for p in body.permissions if p not in valid_permissions]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"无效权限值: {', '.join(invalid)}",
        )

    old_permissions = sorted([p.value for p in ROLE_PERMISSIONS[role_name]])

    # 更新权限
    new_perms = set()
    for p_value in body.permissions:
        for p in Permission:
            if p.value == p_value:
                new_perms.add(p)
                break
    ROLE_PERMISSIONS[role_name] = new_perms

    # 审计日志
    audit_service = AuditService(db)
    await audit_service.log_from_request(
        request=request,
        action=AuditAction.PERMISSION_GRANT.value,
        resource_type=ResourceType.PERMISSION.value,
        resource_id=role_name,
        user=admin,
        old_value={"permissions": old_permissions},
        new_value={"permissions": sorted(body.permissions)},
    )

    return RoleDefinition(
        role_name=role_name,
        display_name=ROLE_DISPLAY_NAMES.get(role_name, role_name),
        permissions=sorted(body.permissions),
    )


# ========== 审计日志 ==========


@router.get("/audit-logs/stats", response_model=AuditLogStatsResponse, summary="审计统计")
async def get_audit_stats(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AuditLogStatsResponse:
    """获取审计日志统计数据"""
    start_time = datetime.utcnow() - timedelta(days=days)

    audit_service = AuditService(db)

    # 操作类型统计（top actions）
    top_actions = await audit_service.get_action_stats(start_time=start_time)

    # 按日统计
    daily_query = select(
        func.date(AuditLog.created_at).label("date"),
        func.count(AuditLog.id).label("count"),
    ).where(
        AuditLog.created_at >= start_time
    ).group_by(
        func.date(AuditLog.created_at)
    ).order_by(
        func.date(AuditLog.created_at).asc()
    )
    daily_result = await db.execute(daily_query)
    actions_per_day = [
        {"date": str(row[0]), "count": row[1]}
        for row in daily_result.all()
    ]

    # 活跃用户统计（top users）
    user_query = select(
        AuditLog.user_email,
        func.count(AuditLog.id).label("count"),
    ).where(
        and_(
            AuditLog.created_at >= start_time,
            AuditLog.user_email.isnot(None),
        )
    ).group_by(
        AuditLog.user_email
    ).order_by(
        func.count(AuditLog.id).desc()
    ).limit(10)
    user_result = await db.execute(user_query)
    top_users = [
        {"user_email": row[0], "count": row[1]}
        for row in user_result.all()
    ]

    return AuditLogStatsResponse(
        actions_per_day=actions_per_day,
        top_users=top_users,
        top_actions=top_actions,
    )


@router.get("/audit-logs", response_model=AuditLogListResponse, summary="审计日志列表")
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    action: str | None = Query(None, description="按操作类型筛选"),
    user_id: str | None = Query(None, description="按用户ID筛选"),
    resource_type: str | None = Query(None, description="按资源类型筛选"),
    start_date: datetime | None = Query(None, description="开始时间"),
    end_date: datetime | None = Query(None, description="结束时间"),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    """获取审计日志列表，支持多维度筛选"""
    audit_service = AuditService(db)

    # 查询日志
    logs = await audit_service.query(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        start_time=start_date,
        end_time=end_date,
        limit=limit,
        offset=skip,
    )

    # 统计总数
    total = await audit_service.count(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        start_time=start_date,
        end_time=end_date,
    )

    return AuditLogListResponse(
        total=total,
        items=[log.to_dict() for log in logs],
        skip=skip,
        limit=limit,
    )


@router.get("/audit-logs/{log_id}", summary="审计日志详情")
async def get_audit_log_detail(
    log_id: str,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """获取单条审计日志详情"""
    result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(status_code=404, detail="审计日志不存在")

    return log.to_dict()


# ========== V2: 合规审计报告导出 ==========


@router.get("/audit-logs/export", summary="导出合规审计报告")
async def export_audit_report(
    days: int = Query(30, ge=1, le=365, description="导出天数范围"),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """导出合规审计报告（JSON 格式，可用于律所合规证明）"""
    start_time = datetime.utcnow() - timedelta(days=days)
    audit_service = AuditService(db)
    report = await audit_service.export_audit_report(
        org_id=getattr(admin, 'org_id', None),
        start_time=start_time,
    )
    return UnifiedResponse.success(data=report)


@router.get("/audit-logs/compliance-report", summary="V2 律所合规审计报告")
async def get_compliance_report(
    days: int = Query(30, ge=1, le=365, description="报告天数范围"),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    V2：生成律所合规审计报告（用于导出 PDF）

    返回结构化数据：操作统计 / 用户活跃度 / 异常操作。
    前端接到数据后渲染为 PDF 格式下载。
    """
    org_id = getattr(admin, 'org_id', None)
    if not org_id:
        return UnifiedResponse.error(code=400, message="当前账号无组织归属，无法生成合规报告")
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=days)
    audit_service = AuditService(db)
    report = await audit_service.generate_compliance_report(
        org_id=str(org_id),
        start_time=start_time,
        end_time=end_time,
    )
    return UnifiedResponse.success(data=report)


# ========== 系统配置 ==========


@router.get("/system/config", response_model=SystemConfigResponse, summary="获取系统配置")
async def get_system_config(
    admin: User = Depends(get_admin_user),
) -> SystemConfigResponse:
    """获取系统配置（敏感项脱敏返回）"""
    from src.core.config import settings

    def _mask(value: str | None) -> str:
        """脱敏敏感字段，只返回是否已配置。"""
        if not value:
            return ""
        return "*" * 8 + value[-4:] if len(value) > 4 else "*" * len(value)

    return SystemConfigResponse(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        rate_limit_enabled=settings.RATE_LIMIT_ENABLED,
        rate_limit_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        cors_origins=settings.CORS_ORIGINS,
        password_min_length=settings.PASSWORD_MIN_LENGTH,
        esign={
            "app_id": settings.ESIGN_BAO_APP_ID or "",
            "app_secret_masked": _mask(settings.ESIGN_BAO_APP_SECRET),
            "has_app_secret": bool(settings.ESIGN_BAO_APP_SECRET),
            "api_url": settings.ESIGN_BAO_API_URL,
            "webhook_secret_masked": _mask(settings.ESIGN_WEBHOOK_SECRET),
            "has_webhook_secret": bool(settings.ESIGN_WEBHOOK_SECRET),
            "official_webhook_enabled": settings.ESIGN_OFFICIAL_WEBHOOK_ENABLED,
        },
        fadada={
            "app_id": settings.FADADA_APP_ID or "",
            "app_secret_masked": _mask(settings.FADADA_APP_SECRET),
            "has_app_secret": bool(settings.FADADA_APP_SECRET),
            "api_url": settings.FADADA_API_URL,
        },
        wechat_pay={
            "app_id": settings.WECHAT_PAY_APP_ID or "",
            "mch_id": settings.WECHAT_PAY_MCH_ID or "",
            "api_base_url": settings.WECHAT_PAY_API_BASE_URL,
            "has_private_key": bool(settings.WECHAT_PAY_MERCHANT_PRIVATE_KEY),
            "has_api_v3_key": bool(settings.WECHAT_PAY_API_V3_KEY),
            "official_webhook_enabled": settings.WECHAT_PAY_OFFICIAL_WEBHOOK_ENABLED,
        },
        alipay={
            "app_id": settings.ALIPAY_APP_ID or "",
            "gateway_url": settings.ALIPAY_GATEWAY_URL,
            "has_private_key": bool(settings.ALIPAY_PRIVATE_KEY),
            "has_public_key": bool(settings.ALIPAY_PUBLIC_KEY),
            "official_webhook_enabled": settings.ALIPAY_OFFICIAL_WEBHOOK_ENABLED,
        },
    )


# [SEC-S1.3] 敏感字段：只能通过环境变量 / 挂载文件配置，禁止通过此 API 设置
# Why：API 写入 settings 内存对象不持久化（重启即失效）且无加密；
#      管理员账户被攻陷即可窃取并伪造支付/电签签名。
_FORBIDDEN_SECRET_FIELDS = {
    "esign": {"app_secret", "webhook_secret"},
    "fadada": {"app_secret"},
    "wechat_pay": {"merchant_private_key", "api_v3_key", "webhook_secret"},
    "alipay": {"private_key", "webhook_secret"},
}


def _reject_secret_fields_in_body(body: "UpdateSystemConfigRequest") -> None:
    """如果 body 中包含敏感字段，立即拒绝并指引正确配置方式。"""
    offenders: list[str] = []
    for provider, secrets in _FORBIDDEN_SECRET_FIELDS.items():
        section = getattr(body, provider, None)
        if not section:
            continue
        for key in secrets:
            if section.get(key):
                offenders.append(f"{provider}.{key}")
    if offenders:
        raise HTTPException(
            status_code=400,
            detail=(
                "敏感凭据不允许通过 API 修改："
                f"{', '.join(offenders)}。"
                "请通过环境变量（.env）或挂载的密钥文件配置，并重启服务生效。"
                "API 写入不持久化且无加密，已禁用此路径。"
            ),
        )


@router.put("/system/config", response_model=SystemConfigResponse, summary="更新系统配置")
async def update_system_config(
    body: UpdateSystemConfigRequest,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> SystemConfigResponse:
    """更新系统配置（运行时修改，重启后恢复默认）。

    敏感凭据（app_secret / private_key / webhook_secret 等）必须通过
    环境变量或挂载文件配置，此 API 仅接受非敏感字段（app_id / api_url /
    public_key / official_webhook_enabled 等）。
    """
    from src.core.config import settings

    # [SEC-S1.3] 在任何写入前先拒绝敏感字段
    _reject_secret_fields_in_body(body)

    old_config = {
        "rate_limit_per_minute": settings.RATE_LIMIT_PER_MINUTE,
        "password_min_length": settings.PASSWORD_MIN_LENGTH,
        "esign_app_id": settings.ESIGN_BAO_APP_ID,
        "esign_official_webhook_enabled": settings.ESIGN_OFFICIAL_WEBHOOK_ENABLED,
        "fadada_app_id": settings.FADADA_APP_ID,
        "wechat_pay_app_id": settings.WECHAT_PAY_APP_ID,
        "wechat_pay_mch_id": settings.WECHAT_PAY_MCH_ID,
        "alipay_app_id": settings.ALIPAY_APP_ID,
    }

    if body.rate_limit_per_minute is not None:
        settings.RATE_LIMIT_PER_MINUTE = body.rate_limit_per_minute

    if body.password_min_length is not None:
        if body.password_min_length < 4:
            raise HTTPException(status_code=400, detail="密码最小长度不能低于4位")
        settings.PASSWORD_MIN_LENGTH = body.password_min_length

    # E签宝 配置：仅非敏感字段
    if body.esign is not None:
        e = body.esign
        if "app_id" in e:
            settings.ESIGN_BAO_APP_ID = (e["app_id"] or None)
        if "api_url" in e and e["api_url"]:
            settings.ESIGN_BAO_API_URL = e["api_url"]
        if "official_webhook_enabled" in e:
            settings.ESIGN_OFFICIAL_WEBHOOK_ENABLED = bool(e["official_webhook_enabled"])

    # 法大大 配置：仅非敏感字段
    if body.fadada is not None:
        f = body.fadada
        if "app_id" in f:
            settings.FADADA_APP_ID = (f["app_id"] or None)
        if "api_url" in f and f["api_url"]:
            settings.FADADA_API_URL = f["api_url"]

    # 微信支付 配置：仅非敏感字段
    if body.wechat_pay is not None:
        w = body.wechat_pay
        if "app_id" in w:
            settings.WECHAT_PAY_APP_ID = (w["app_id"] or None)
        if "mch_id" in w:
            settings.WECHAT_PAY_MCH_ID = (w["mch_id"] or None)
        if "official_webhook_enabled" in w:
            settings.WECHAT_PAY_OFFICIAL_WEBHOOK_ENABLED = bool(w["official_webhook_enabled"])

    # 支付宝 配置：仅非敏感字段（public_key 为公钥，非密钥）
    if body.alipay is not None:
        a = body.alipay
        if "app_id" in a:
            settings.ALIPAY_APP_ID = a["app_id"] or ""
        if a.get("public_key"):
            settings.ALIPAY_PUBLIC_KEY = a["public_key"]
        if "official_webhook_enabled" in a:
            settings.ALIPAY_OFFICIAL_WEBHOOK_ENABLED = bool(a["official_webhook_enabled"])

    new_config = {
        "rate_limit_per_minute": settings.RATE_LIMIT_PER_MINUTE,
        "password_min_length": settings.PASSWORD_MIN_LENGTH,
        "esign_app_id": settings.ESIGN_BAO_APP_ID,
        "esign_official_webhook_enabled": settings.ESIGN_OFFICIAL_WEBHOOK_ENABLED,
        "fadada_app_id": settings.FADADA_APP_ID,
        "wechat_pay_app_id": settings.WECHAT_PAY_APP_ID,
        "wechat_pay_mch_id": settings.WECHAT_PAY_MCH_ID,
        "alipay_app_id": settings.ALIPAY_APP_ID,
    }

    # 审计日志
    audit_service = AuditService(db)
    await audit_service.log_from_request(
        request=request,
        action=AuditAction.CONFIG_CHANGE.value,
        resource_type=ResourceType.CONFIG.value,
        user=admin,
        old_value=old_config,
        new_value=new_config,
    )

    return SystemConfigResponse(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        rate_limit_enabled=settings.RATE_LIMIT_ENABLED,
        rate_limit_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        cors_origins=settings.CORS_ORIGINS,
        password_min_length=settings.PASSWORD_MIN_LENGTH,
    )


@router.get("/system/health", response_model=SystemHealthResponse, summary="系统健康检查")
async def system_health_check(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> SystemHealthResponse:
    """系统健康检查（数据库、Redis、Qdrant 连接状态）"""
    uptime = time.time() - _system_start_time

    # 数据库连接检查
    db_status = "healthy"
    try:
        await db.execute(select(func.count(User.id)))
    except Exception as e:
        db_status = f"unhealthy: {e}"

    # Redis 连接检查
    redis_status = "healthy"
    try:
        from src.core.security import get_rate_limiter
        rate_limiter = get_rate_limiter()
        if hasattr(rate_limiter, "redis") and rate_limiter.redis:
            await rate_limiter.redis.ping()
        else:
            redis_status = "not_configured"
    except Exception as e:
        redis_status = f"unhealthy: {e}"

    overall = "healthy"
    if "unhealthy" in db_status:
        overall = "degraded"

    return SystemHealthResponse(
        status=overall,
        database=db_status,
        redis=redis_status,
        uptime_seconds=round(uptime, 2),
    )


# ========== 组织管理 ==========


@router.get("/organizations", response_model=OrgListResponse, summary="组织列表")
async def list_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="搜索组织名称"),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> OrgListResponse:
    """获取组织列表"""
    query = select(Organization)
    count_query = select(func.count(Organization.id))

    if search:
        pattern = f"%{search}%"
        query = query.where(Organization.name.ilike(pattern))
        count_query = count_query.where(Organization.name.ilike(pattern))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Organization.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    orgs = result.scalars().all()

    return OrgListResponse(
        total=total,
        items=[_org_to_dict(o) for o in orgs],
        skip=skip,
        limit=limit,
    )


@router.post("/organizations", status_code=201, summary="创建组织")
async def create_organization(
    body: OrgCreateRequest,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """创建新组织"""
    # 检查名称是否重复
    existing = await db.execute(
        select(Organization).where(Organization.name == body.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="组织名称已存在")

    org = Organization(
        name=body.name,
        description=body.description,
        logo_url=body.logo_url,
        is_active=True,
    )
    db.add(org)
    await db.flush()

    # 审计日志
    audit_service = AuditService(db)
    await audit_service.log_from_request(
        request=request,
        action="organization.create",
        resource_type=ResourceType.ORGANIZATION.value,
        resource_id=org.id,
        user=admin,
        new_value={"name": org.name, "description": org.description},
    )

    return _org_to_dict(org)


@router.put("/organizations/{org_id}", summary="更新组织")
async def update_organization(
    org_id: str,
    body: OrgUpdateRequest,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """更新组织信息"""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="组织不存在")

    old_value = {"name": org.name, "description": org.description, "is_active": org.is_active}

    if body.name is not None:
        # 检查名称是否与其他组织重复
        dup_check = await db.execute(
            select(Organization).where(
                and_(Organization.name == body.name, Organization.id != org_id)
            )
        )
        if dup_check.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="组织名称已存在")
        org.name = body.name
    if body.description is not None:
        org.description = body.description
    if body.logo_url is not None:
        org.logo_url = body.logo_url
    if body.is_active is not None:
        org.is_active = body.is_active

    await db.flush()

    new_value = {"name": org.name, "description": org.description, "is_active": org.is_active}

    # 审计日志
    audit_service = AuditService(db)
    await audit_service.log_from_request(
        request=request,
        action="organization.update",
        resource_type=ResourceType.ORGANIZATION.value,
        resource_id=org.id,
        user=admin,
        old_value=old_value,
        new_value=new_value,
    )

    return _org_to_dict(org)
