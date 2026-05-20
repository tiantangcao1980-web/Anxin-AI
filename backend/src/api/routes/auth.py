"""认证路由"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.core.deps import get_current_user_required, rate_limit, rate_limit_auth
from src.core.security import (
    create_token_pair,
    get_password_hash,
    get_token_blacklist,
    refresh_access_token,
    revoke_token,
)
from src.models.audit import AuditAction, ResourceType
from src.models.user import PasswordResetToken, User
from src.services.audit_service import AuditService
from src.services.captcha_service import captcha_service
from src.services.oauth_service import AlipayOAuth, WeChatMiniProgramOAuth, WeChatOAuth
from src.services.user_service import UserService

router = APIRouter()

# 用于获取Bearer Token
security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    """登录请求"""

    email: EmailStr
    password: str
    captcha_token: str | None = None


class RegisterRequest(BaseModel):
    """注册请求"""

    email: EmailStr
    password: str
    name: str
    user_type: str = "individual"  # individual / enterprise / platform_lawyer / institution
    phone: str | None = None  # 手机号（用于短信验证）
    captcha_token: str | None = None


class VerifyEmailRequest(BaseModel):
    """邮箱验证请求"""

    email: EmailStr
    code: str


class ResendVerificationRequest(BaseModel):
    """重发验证码请求"""

    email: EmailStr
    captcha_token: str | None = None


class RefreshTokenRequest(BaseModel):
    """Token刷新请求"""

    refresh_token: str | None = None


class TokenResponse(BaseModel):
    """Token响应"""

    access_token: str
    refresh_token: str
    token_type: str
    user: dict[str, Any]


class TokenPairResponse(BaseModel):
    """Token对响应"""

    access_token: str
    refresh_token: str
    access_expires_in: int
    refresh_expires_in: int
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """用户信息响应"""

    id: str
    email: str
    name: str
    role: str
    user_type: str = "individual"
    # V2 架构：主客户端偏好 (needer=需求方端 / provider=服务方端)
    primary_client: str = "needer"
    avatar_url: str | None = None
    email_verified: bool = True


class UserUpdate(BaseModel):
    """用户更新请求"""

    name: str | None = None
    avatar_url: str | None = None


class LogoutRequest(BaseModel):
    """登出请求（可选）"""

    all_devices: bool = False  # 是否登出所有设备


# 账号锁定配置
ACCOUNT_LOCKOUT_THRESHOLD = 5
ACCOUNT_LOCKOUT_MINUTES = 30
OAUTH_STATE_EXPIRES_MINUTES = 10


class EmailVerifyTokenData(TypedDict):
    user_id: str
    email: str
    expires_at: datetime


class OAuthStateTokenData(TypedDict):
    provider: str
    expires_at: datetime


def _issue_oauth_state(provider: str) -> str:
    state = secrets.token_urlsafe(24)
    _oauth_state_tokens[state] = {
        "provider": provider,
        "expires_at": datetime.now(UTC) + timedelta(minutes=OAUTH_STATE_EXPIRES_MINUTES),
    }
    return state


def _consume_oauth_state(provider: str, state: str | None) -> None:
    if not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state 缺失")

    token_data = _oauth_state_tokens.get(state)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state 无效")

    if token_data["provider"] != provider:
        _oauth_state_tokens.pop(state, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state 不匹配")

    if datetime.now(UTC) > token_data["expires_at"]:
        _oauth_state_tokens.pop(state, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state 已过期")

    _oauth_state_tokens.pop(state, None)


def validate_password(password: str) -> None:
    """验证密码强度"""
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"密码长度至少 {settings.PASSWORD_MIN_LENGTH} 位",
        )
    if settings.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="密码必须包含至少一个大写字母"
        )
    if settings.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="密码必须包含至少一个小写字母"
        )
    if settings.PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="密码必须包含至少一个数字"
        )


async def _require_captcha(request: Request, captcha_token: str | None) -> None:
    if not captcha_service.is_enabled():
        return
    if not captcha_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先完成人机验证",
        )

    forwarded = request.headers.get("X-Forwarded-For")
    remote_ip = (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else None)
    )
    if not await captcha_service.verify_token(captcha_token, remote_ip=remote_ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="人机验证未通过，请重试",
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    response: Response,
    login_request: LoginRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_auth),
) -> dict[str, Any]:
    """
    用户登录

    限流：10次/分钟
    """
    await _require_captcha(request, login_request.captcha_token)

    # 检查账号锁定状态
    stmt = select(User).where(User.email == login_request.email)
    user_result = await db.execute(stmt)
    existing_user = user_result.scalar_one_or_none()

    if existing_user:
        if (
            existing_user.login_attempts >= ACCOUNT_LOCKOUT_THRESHOLD
            and existing_user.last_login_at
            and existing_user.last_login_at
            > datetime.now(UTC) - timedelta(minutes=ACCOUNT_LOCKOUT_MINUTES)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="账号已被锁定，请 30 分钟后重试"
            )

    service = UserService(db)
    result = await service.login(login_request.email, login_request.password)

    # 记录审计日志
    audit_service = AuditService(db)

    if not result:
        # 更新登录失败计数
        if existing_user:
            existing_user.login_attempts = (existing_user.login_attempts or 0) + 1
            existing_user.last_login_at = datetime.now(UTC)

        # 记录登录失败
        await audit_service.log_from_request(
            request=request,
            action=AuditAction.USER_LOGIN.value,
            resource_type=ResourceType.USER.value,
            status="failed",
            error_message="邮箱或密码错误",
            extra_data={"email": login_request.email},
        )
        await db.commit()

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")

    # 检查邮箱是否已验证（仅在开关启用时）
    if settings.EMAIL_VERIFY_ENABLED and existing_user and not existing_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="邮箱未验证，请先完成邮箱验证",
        )

    # 登录成功：重置登录失败计数，更新最后登录时间
    if existing_user:
        existing_user.login_attempts = 0
        existing_user.last_login_at = datetime.now(UTC)

    # 记录登录成功
    await audit_service.log_from_request(
        request=request,
        action=AuditAction.USER_LOGIN.value,
        resource_type=ResourceType.USER.value,
        resource_id=result["user"]["id"],
        extra_data={"email": login_request.email},
    )
    await db.commit()

    # 将 refresh_token 设置到 HttpOnly cookie 中
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=not settings.DEV_MODE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
    )

    return result


@router.post("/register", response_model=UserResponse)
async def register(
    request: Request,
    register_request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit(limit=5, window=300, endpoint="auth_register", fail_closed=True)),
) -> dict[str, Any]:
    """
    用户注册

    支持四种用户类型：
    - individual: 个人用户 → 初始 role=individual_user
    - enterprise: 企业用户 → 初始 role=enterprise_user（受限，认证后解锁完整权限）
    - platform_lawyer: 律师 → 初始 role=viewer（待认证，通过后升级为 platform_lawyer）
    - institution: 律所/机构 → 初始 role=viewer（待审核，通过后升级为 org_admin）

    限流：5次/5分钟
    """
    await _require_captcha(request, register_request.captcha_token)

    # 验证密码强度
    validate_password(register_request.password)

    # 验证用户类型并映射初始角色
    user_type_role_map = {
        "individual": "individual_user",
        "enterprise": "enterprise_user",
        "platform_lawyer": "viewer",  # 待律师认证通过后升级
        "institution": "viewer",  # 待机构审核通过后升级
    }
    user_type = register_request.user_type
    if user_type not in user_type_role_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的用户类型: {user_type}，可选: individual, enterprise, platform_lawyer, institution",
        )
    initial_role = user_type_role_map[user_type]

    service = UserService(db)
    audit_service = AuditService(db)

    try:
        user = await service.create_user(
            email=register_request.email,
            password=register_request.password,
            name=register_request.name,
            role=initial_role,
            user_type=user_type,
            phone=register_request.phone,
        )

        debug_code = None
        if settings.EMAIL_VERIFY_ENABLED:
            # 生成邮箱验证码（6位数字，15分钟有效）
            verify_code = f"{secrets.randbelow(1000000):06d}"
            _email_verify_tokens[verify_code] = {
                "user_id": str(user.id),
                "email": user.email,
                "expires_at": datetime.now(UTC) + timedelta(minutes=15),
            }
            logger.info(f"邮箱验证码已生成 (用户: {user.email}, 类型: {user_type})")
            debug_code = verify_code

            # 发送邮箱验证码
            from src.services.email_service import email_service

            await email_service.send_verification_code(user.email, verify_code)
        else:
            # 邮箱验证未启用时，自动标记为已验证
            user.email_verified = True

        # 记录注册成功
        await audit_service.log_from_request(
            request=request,
            action=AuditAction.USER_REGISTER.value,
            resource_type=ResourceType.USER.value,
            resource_id=user.id,
            extra_data={
                "email": register_request.email,
                "name": register_request.name,
                "user_type": user_type,
                "initial_role": initial_role,
            },
        )
        await db.commit()

        return {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "user_type": user_type,
            "primary_client": getattr(user, "primary_client", "needer") or "needer",
            "email_verified": user.email_verified,
            "message": (
                "注册成功"
                if not settings.EMAIL_VERIFY_ENABLED
                else "注册成功，请查收邮箱验证码完成验证"
            ),
            # 开发模式返回验证码，方便调试
            **({"debug_verify_code": debug_code} if settings.DEV_MODE and debug_code else {}),
        }
    except ValueError as e:
        # 记录注册失败
        await audit_service.log_from_request(
            request=request,
            action=AuditAction.USER_REGISTER.value,
            resource_type=ResourceType.USER.value,
            status="failed",
            error_message=str(e),
            extra_data={"email": register_request.email},
        )
        await db.commit()

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: User = Depends(get_current_user_required)) -> UserResponse:
    """获取当前用户信息"""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        user_type=getattr(user, "user_type", "individual") or "individual",
        primary_client=getattr(user, "primary_client", "needer") or "needer",
        avatar_url=user.avatar_url,
        email_verified=user.email_verified,
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> UserResponse:
    """更新当前用户信息"""
    service = UserService(db)
    updated_user = await service.update_user(
        user_id=user.id, name=update.name, avatar_url=update.avatar_url
    )

    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    return UserResponse(
        id=updated_user.id,
        email=updated_user.email,
        name=updated_user.name,
        role=updated_user.role,
        avatar_url=updated_user.avatar_url,
        email_verified=updated_user.email_verified,
    )


@router.post("/logout")
async def logout(
    request: Request,
    logout_request: LogoutRequest | None = None,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_required),
) -> dict[str, str]:
    """
    用户登出

    将当前Token加入黑名单，使其立即失效

    可选参数：
    - all_devices: 是否登出所有设备（撤销所有Token）
    """
    if credentials:
        token = credentials.credentials

        if logout_request and logout_request.all_devices and user:
            # 撤销用户所有Token
            blacklist = get_token_blacklist()
            await blacklist.revoke_all_user_tokens(user.id)
            message = "已登出所有设备"
        else:
            # 只撤销当前Token
            await revoke_token(token, reason="logout")
            message = "登出成功"

        # 记录审计日志
        audit_service = AuditService(db)
        await audit_service.log_from_request(
            request=request,
            action=AuditAction.USER_LOGOUT.value,
            resource_type=ResourceType.USER.value,
            resource_id=user.id if user else None,
            user=user,
            extra_data={
                "all_devices": logout_request.all_devices if logout_request else False,
            },
        )
        await db.commit()

        return {"message": message}

    return {"message": "登出成功"}


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh_token_endpoint(
    request: Request,
    response: Response,
    refresh_request: RefreshTokenRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit(limit=30, window=60, endpoint="auth_refresh", fail_closed=True)),
) -> TokenPairResponse:
    """
    刷新访问Token

    优先从 HttpOnly Cookie 获取 refresh_token。
    请求体 refresh_token 仅在 AUTH_REFRESH_BODY_COMPAT_ENABLED=true 时作为迁移兼容路径启用。
    旧的refresh_token会被加入黑名单，只能使用一次。

    限流：30次/分钟
    """
    cookie_token = request.cookies.get("refresh_token")
    body_token = refresh_request.refresh_token if refresh_request else None

    if cookie_token:
        token = cookie_token
    elif body_token and settings.AUTH_REFRESH_BODY_COMPAT_ENABLED:
        token = body_token
    elif body_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refresh_token 请求体兼容期已结束，请使用 HttpOnly Cookie 刷新会话",
        )
    else:
        token = None

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未提供 refresh_token",
        )

    token_pair = await refresh_access_token(token)

    if not token_pair:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新Token无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 记录审计日志
    audit_service = AuditService(db)
    await audit_service.log_from_request(
        request=request,
        action=AuditAction.TOKEN_REFRESH.value,
        resource_type=ResourceType.TOKEN.value,
    )
    await db.commit()

    # 更新 HttpOnly Cookie 中的 refresh_token
    response.set_cookie(
        key="refresh_token",
        value=token_pair.refresh_token,
        httponly=True,
        secure=not settings.DEV_MODE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
    )

    logger.info("Token刷新成功")

    return TokenPairResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        access_expires_in=token_pair.access_expires_in,
        refresh_expires_in=token_pair.refresh_expires_in,
    )


@router.post("/revoke")
async def revoke_token_endpoint(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, str]:
    """
    撤销Token

    主动撤销当前Token，使其立即失效
    """
    if not credentials:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未提供Token")

    token = credentials.credentials
    success = await revoke_token(token, reason="user_revoke")

    if success:
        # 记录审计日志
        audit_service = AuditService(db)
        await audit_service.log_from_request(
            request=request,
            action=AuditAction.TOKEN_REVOKE.value,
            resource_type=ResourceType.TOKEN.value,
            user=user,
        )
        await db.commit()

        # 清除 Cookie
        response.delete_cookie("refresh_token")

        return {"message": "Token已撤销"}

    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Token撤销失败")


# ============ 邮箱验证 ============


@router.post("/verify-email", summary="验证邮箱 - 使用注册验证码")
async def verify_email(
    req: VerifyEmailRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(
        rate_limit(limit=10, window=300, endpoint="verify_email", by_user=False, fail_closed=True)
    ),
) -> dict[str, Any]:
    """使用验证码完成邮箱验证"""
    token_data = _email_verify_tokens.get(req.code)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码无效或已过期")

    if datetime.now(UTC) > token_data["expires_at"]:
        del _email_verify_tokens[req.code]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="验证码已过期，请重新获取"
        )

    if token_data["email"] != req.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码与邮箱不匹配")

    # 更新用户邮箱验证状态
    result = await db.execute(select(User).where(User.id == token_data["user_id"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.email_verified = True
    await db.commit()

    # 清除已使用的验证码
    del _email_verify_tokens[req.code]

    logger.info(f"用户 {user.email} 邮箱验证成功")

    # 验证成功后自动颁发 Token，允许直接登录
    tokens = create_token_pair(user.id)

    # 设置 HttpOnly Cookie
    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=not settings.DEV_MODE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
    )

    return {
        "message": "邮箱验证成功",
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
        },
    }


@router.post("/resend-verification", summary="重发邮箱验证码")
async def resend_verification(
    request: Request,
    req: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit(limit=3, window=300, endpoint="resend_verify", fail_closed=True)),
) -> dict[str, Any]:
    """重新发送邮箱验证码（限流：3次/5分钟）"""
    await _require_captcha(request, req.captcha_token)

    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    debug_code = None
    if user and not user.email_verified:
        # 清除该邮箱旧的验证码
        to_remove = [k for k, v in _email_verify_tokens.items() if v["email"] == req.email]
        for k in to_remove:
            del _email_verify_tokens[k]

        # 生成新验证码
        verify_code = f"{secrets.randbelow(1000000):06d}"
        _email_verify_tokens[verify_code] = {
            "user_id": str(user.id),
            "email": user.email,
            "expires_at": datetime.now(UTC) + timedelta(minutes=15),
        }
        logger.info(f"邮箱验证码已重新发送 (用户: {user.email})")
        logger.debug(f"[DEV] 验证码: {verify_code}")
        debug_code = verify_code
        # 发送邮箱验证码
        from src.services.email_service import email_service

        await email_service.send_verification_code(user.email, verify_code)

    # 无论邮箱是否存在都返回成功（防止枚举攻击）
    return {
        "message": "如果该邮箱已注册且未验证，我们将发送新的验证码",
        "expires_in": 900,
        # 开发模式返回验证码
        **({"debug_verify_code": debug_code} if settings.DEV_MODE and debug_code else {}),
    }


# ============ 功能开关查询 ============


@router.get("/features")
async def get_auth_features() -> dict[str, Any]:
    """查询认证相关功能开关状态（公开端点，供前端判断UI展示）"""
    return {
        "email_verify_enabled": settings.EMAIL_VERIFY_ENABLED,
        "sms_enabled": settings.SMS_ENABLED,
        "oauth_wechat_enabled": settings.OAUTH_WECHAT_ENABLED,
        "oauth_alipay_enabled": settings.OAUTH_ALIPAY_ENABLED,
        **captcha_service.get_public_config(),
    }


# ============ OAuth 第三方登录 ============


class OAuthCallbackRequest(BaseModel):
    """OAuth 回调请求"""

    code: str
    state: str | None = None


class WeChatCode2SessionRequest(BaseModel):
    """微信小程序登录请求"""

    code: str


def _wechat_user_email(openid: str) -> str:
    return f"wx_{openid[:16]}@wechat.user"


async def _find_or_create_wechat_user(
    db: AsyncSession,
    *,
    openid: str,
    unionid: str | None = None,
    nickname: str = "微信用户",
    avatar: str = "",
) -> tuple[User, bool]:
    query = select(User).where(User.wechat_openid == openid)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user and unionid:
        query = select(User).where(User.wechat_unionid == unionid)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

    if user:
        return user, False

    default_org_id = "00000000-0000-0000-0000-000000000001"
    user = User(
        id=str(uuid4()),
        email=_wechat_user_email(openid),
        hashed_password=get_password_hash(secrets.token_urlsafe(32)),
        name=nickname,
        avatar_url=avatar,
        role="member",
        org_id=default_org_id,
        is_active=True,
        email_verified=True,
        wechat_openid=openid,
        wechat_unionid=unionid,
        login_type="wechat",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user, True


def _wechat_token_response(user: User, *, is_new_user: bool) -> dict[str, Any]:
    tokens = create_token_pair(user.id)
    return {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "nickname": user.name,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "login_type": user.login_type,
        },
        "is_new_user": is_new_user,
    }


@router.get("/oauth/wechat/url")
async def get_wechat_login_url() -> dict[str, str]:
    """获取微信登录授权 URL"""
    if not settings.OAUTH_WECHAT_ENABLED:
        raise HTTPException(status_code=404, detail="微信登录未启用")
    state = _issue_oauth_state("wechat")
    url = WeChatOAuth.get_authorize_url(state)
    return {"url": url, "state": state}


@router.post("/oauth/wechat/callback")
async def wechat_oauth_callback(
    request: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """微信 OAuth 回调 -- 用 code 换 token，查找或创建用户"""
    try:
        _consume_oauth_state("wechat", request.state)
        token_data = await WeChatOAuth.get_access_token(request.code)
        user_info = await WeChatOAuth.get_user_info(
            token_data["access_token"], token_data["openid"]
        )

        openid = user_info["openid"]
        unionid = user_info.get("unionid")
        nickname = user_info.get("nickname", "微信用户")
        avatar = user_info.get("headimgurl", "")

        user, created = await _find_or_create_wechat_user(
            db,
            openid=openid,
            unionid=unionid,
            nickname=nickname,
            avatar=avatar,
        )
        return _wechat_token_response(user, is_new_user=created)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"微信 OAuth 回调失败: {e}")
        raise HTTPException(status_code=500, detail="微信登录失败，请重试") from e


@router.post("/wechat/code2session", response_model=TokenResponse)
async def wechat_mini_code2session(
    request: WeChatCode2SessionRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_auth),
) -> dict[str, Any]:
    """微信小程序登录：wx.login code -> 本地 JWT 会话。"""
    if not settings.OAUTH_WECHAT_ENABLED:
        raise HTTPException(status_code=404, detail="微信登录未启用")
    try:
        session = await WeChatMiniProgramOAuth.code2session(request.code)
        user, created = await _find_or_create_wechat_user(
            db,
            openid=session["openid"],
            unionid=session.get("unionid"),
            nickname="微信用户",
            avatar="",
        )
        result = _wechat_token_response(user, is_new_user=created)
        response.set_cookie(
            key="refresh_token",
            value=result["refresh_token"],
            httponly=True,
            secure=not settings.DEV_MODE,
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"微信小程序登录失败: {e}")
        raise HTTPException(status_code=500, detail="微信登录失败，请重试") from e


@router.post("/wechat-login", response_model=TokenResponse, include_in_schema=False)
async def wechat_login_compat(
    request: WeChatCode2SessionRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_auth),
) -> dict[str, Any]:
    return await wechat_mini_code2session(request, response, db, _)


@router.get("/oauth/alipay/url")
async def get_alipay_login_url() -> dict[str, str]:
    """获取支付宝登录授权 URL"""
    if not settings.OAUTH_ALIPAY_ENABLED:
        raise HTTPException(status_code=404, detail="支付宝登录未启用")
    state = _issue_oauth_state("alipay")
    url = AlipayOAuth.get_authorize_url(state)
    return {"url": url, "state": state}


@router.post("/oauth/alipay/callback")
async def alipay_oauth_callback(
    request: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """支付宝 OAuth 回调"""
    try:
        _consume_oauth_state("alipay", request.state)
        token_data = await AlipayOAuth.get_access_token(request.code)
        user_info = await AlipayOAuth.get_user_info(token_data["access_token"])

        alipay_uid = user_info.get("user_id") or token_data.get("user_id")
        if not alipay_uid:
            raise HTTPException(status_code=400, detail="支付宝用户信息缺失")
        nickname = user_info.get("nick_name", "支付宝用户")
        avatar = user_info.get("avatar", "")

        query = select(User).where(User.alipay_user_id == alipay_uid)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            default_org_id = "00000000-0000-0000-0000-000000000001"
            user = User(
                id=str(uuid4()),
                email=f"ali_{alipay_uid[:16]}@alipay.user",
                hashed_password=get_password_hash(secrets.token_urlsafe(32)),
                name=nickname,
                avatar_url=avatar,
                role="member",
                org_id=default_org_id,
                is_active=True,
                email_verified=True,  # 第三方登录视为已验证
                alipay_user_id=alipay_uid,
                login_type="alipay",
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        tokens = create_token_pair(user.id)
        return {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "avatar_url": user.avatar_url,
                "login_type": user.login_type,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"支付宝 OAuth 回调失败: {e}")
        raise HTTPException(status_code=500, detail="支付宝登录失败，请重试") from e


# ==================== 忘记密码 ====================


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    captcha_token: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    captcha_token: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


_email_verify_tokens: dict[str, EmailVerifyTokenData] = (
    {}
)  # key=验证码, value={user_id, email, expires_at}
_oauth_state_tokens: dict[str, OAuthStateTokenData] = {}


def _get_request_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _hash_reset_context(request: Request) -> dict[str, str]:
    ip = _get_request_ip(request)
    user_agent = request.headers.get("user-agent", "")
    return {
        "ip_hash": hashlib.sha256(ip.encode("utf-8")).hexdigest(),
        "ua_hash": hashlib.sha256(user_agent.encode("utf-8")).hexdigest(),
    }


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


@router.post("/forgot-password", summary="忘记密码 - 发送重置链接")
async def forgot_password(
    request: Request,
    req: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(
        rate_limit(limit=5, window=300, endpoint="forgot_password", by_user=False, fail_closed=True)
    ),
) -> dict[str, Any]:
    """
    发送密码重置链接到用户邮箱。
    无论邮箱是否存在都返回成功（防止枚举攻击）。
    """
    await _require_captcha(request, req.captcha_token)

    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    token = None
    if user:
        # 生成高熵重置令牌（32 字符 URL-safe token，15 分钟有效）
        # S-003 修复：从 6 位数字升级为 32 字符随机 token，防暴力枚举
        now = datetime.now(UTC)
        token = secrets.token_urlsafe(24)  # 192 bits entropy
        reset_context = _hash_reset_context(request)
        await db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.consumed_at.is_(None),
            )
            .values(consumed_at=now)
        )
        db.add(
            PasswordResetToken(
                token_hash=_hash_reset_token(token),
                user_id=str(user.id),
                email=user.email,
                bound_email=req.email,  # 绑定请求邮箱，防止 token 被用于其他邮箱
                ip_hash=reset_context["ip_hash"],
                ua_hash=reset_context["ua_hash"],
                channel="email",
                expires_at=now + timedelta(minutes=15),
            )
        )
        logger.info(f"密码重置令牌已生成 (用户: {user.email})")

        # 发送密码重置令牌
        from src.services.email_service import email_service

        await email_service.send_reset_code(user.email, token)
        await db.commit()

    # 始终返回成功（防止邮箱枚举）
    return {
        "message": "如果该邮箱已注册，我们将发送密码重置验证码",
        "expires_in": 900,
        # 开发模式返回验证码，方便调试
        **({"debug_token": token} if settings.DEV_MODE and user else {}),
    }


@router.post("/reset-password", summary="重置密码 - 使用重置令牌")
async def reset_password(
    request: Request,
    req: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(
        rate_limit(limit=5, window=300, endpoint="reset_password", by_user=False, fail_closed=True)
    ),
) -> dict[str, str]:
    """使用高熵重置令牌重置密码"""
    await _require_captcha(request, req.captcha_token)

    token_hash = _hash_reset_token(req.token)
    token_result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    token_record: PasswordResetToken | None = token_result.scalar_one_or_none()
    if not token_record or token_record.consumed_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码无效或已过期")

    now = datetime.now(UTC)
    if now > _ensure_aware(token_record.expires_at):
        token_record.consumed_at = now
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="验证码已过期，请重新获取"
        )

    reset_context = _hash_reset_context(request)
    if (
        token_record.ip_hash != reset_context["ip_hash"]
        or token_record.ua_hash != reset_context["ua_hash"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重置上下文不匹配，请重新获取验证码",
        )

    # 密码强度验证
    validate_password(req.new_password)

    # 更新密码
    user_result = await db.execute(select(User).where(User.id == token_record.user_id))
    user: User | None = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.hashed_password = get_password_hash(req.new_password)
    user.password_changed_at = now
    user.login_attempts = 0  # 重置登录失败计数
    token_record.consumed_at = now
    await db.commit()

    # 审计日志
    try:
        audit = AuditService(db)
        await audit.log(
            action=AuditAction.USER_PASSWORD_CHANGE.value,
            resource_type=ResourceType.USER.value,
            resource_id=str(user.id),
            user=user,
            extra_data={"action": "password_reset"},
        )
    except Exception as e:
        logger.error(f"密码重置审计日志写入失败: {e}")

    logger.info(f"用户 {user.email} 密码重置成功")
    return {"message": "密码重置成功，请使用新密码登录"}


@router.put("/change-password", summary="修改密码 - 需要旧密码")
async def change_password(
    req: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, str]:
    """已登录用户修改密码（需验证旧密码）"""
    from src.core.security import verify_password

    if not verify_password(req.old_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确")

    validate_password(req.new_password)

    if req.old_password == req.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与旧密码相同"
        )

    user.hashed_password = get_password_hash(req.new_password)
    user.password_changed_at = datetime.now(UTC)
    await db.commit()

    logger.info(f"用户 {user.email} 修改密码成功")
    return {"message": "密码修改成功"}
