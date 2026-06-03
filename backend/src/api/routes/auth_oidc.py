# -*- coding: utf-8 -*-
"""
/api/v1/auth/oidc/* —— OIDC / OpenID Connect 单点登录

设计见 deploy/enterprise-onprem/SSO_SAML.md + backend/src/core/oidc.py。

流程（推荐 Authorization Code Flow 由前端完成）：
    1. 前端用 OIDC 客户端拿到 ``id_token``（一般是 Hosted Login UI 回调）
    2. 前端 POST /api/v1/auth/oidc/callback  body: { id_token }
    3. 后端验签 + 校验 iss/aud/exp，提取 sub / email
    4. 在本地 users 表里 upsert（按 email 匹配；首次创建 login_type=oidc）
    5. 返回本地 access_token + refresh_token

权限**不取自 IdP**；本地 role_bindings 决定。这里只确认"你是谁"。
"""

from __future__ import annotations

import logging
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.oidc import OidcConfig, OidcError, OidcUnavailable, OidcVerifier
from src.core.security import create_token_pair
from src.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


class OidcCallbackBody(BaseModel):
    id_token: str = Field(..., min_length=20)
    # 可选：前端额外携带 provider 名称（多 IdP 部署用），后端按名匹配 settings
    provider: str | None = None


class OidcLoginOut(BaseModel):
    access_token: str
    refresh_token: str
    access_expires_in: int
    refresh_expires_in: int
    user_id: str
    is_new_user: bool


# ---------------------------------------------------------------------------
# 配置加载（懒）
# ---------------------------------------------------------------------------


def _load_default_config() -> OidcConfig:
    """从环境变量加载默认 IdP 配置。

    必需：``OIDC_ISSUER`` + ``OIDC_CLIENT_ID``
    可选：``OIDC_AUDIENCE`` + ``OIDC_JWKS_URI`` + ``OIDC_ALGS``
    """
    issuer = os.environ.get("OIDC_ISSUER", "").strip()
    client_id = os.environ.get("OIDC_CLIENT_ID", "").strip()
    if not issuer or not client_id:
        raise OidcUnavailable(
            "缺少 OIDC_ISSUER 或 OIDC_CLIENT_ID 环境变量"
        )
    algs = os.environ.get("OIDC_ALGS", "RS256")
    return OidcConfig(
        issuer=issuer,
        client_id=client_id,
        audience_override=os.environ.get("OIDC_AUDIENCE") or None,
        jwks_uri=os.environ.get("OIDC_JWKS_URI") or None,
        allowed_algorithms=tuple(a.strip() for a in algs.split(",") if a.strip()),
    )


# 模块级 verifier 缓存（每进程一份）
_verifier_cache: dict[str, OidcVerifier] = {}


def _verifier_for(provider: str | None) -> OidcVerifier:
    key = provider or "default"
    if key in _verifier_cache:
        return _verifier_cache[key]
    # 仅 default IdP 走环境变量；多 IdP 留给后续 settings 注入
    if provider and provider != "default":
        raise OidcUnavailable(f"未配置 provider={provider!r}")
    cfg = _load_default_config()
    v = OidcVerifier(cfg)
    _verifier_cache[key] = v
    return v


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------


@router.post(
    "/callback",
    response_model=OidcLoginOut,
)
async def oidc_callback(
    body: OidcCallbackBody,
    db: AsyncSession = Depends(get_db),
) -> OidcLoginOut:
    """前端完成 OIDC 授权码流程后，把 id_token 提交到这里换本地 token。"""
    try:
        verifier = _verifier_for(body.provider)
    except OidcUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    try:
        claims = await verifier.verify_id_token(body.id_token)
    except OidcError as exc:
        logger.warning("OIDC 校验失败: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"OIDC 校验失败: {exc}",
        ) from exc
    except OidcUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OIDC 暂不可用: {exc}",
        ) from exc

    email = claims.get("email") or claims.get("preferred_username") or claims.get("upn")
    if not email or not isinstance(email, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="id_token 缺少 email/preferred_username/upn —— 无法映射到本地用户",
        )
    email = email.strip().lower()
    sub = claims["sub"]
    name = claims.get("name") or claims.get("given_name") or email.split("@")[0]

    # 本地 upsert
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    is_new_user = False
    if user is None:
        user = User(
            id=str(uuid4()),
            email=email,
            name=name,
            hashed_password="!oidc!",  # OIDC 用户不走本地密码
            login_type="oidc",
            is_active=True,
        )
        if hasattr(user, "external_id"):
            user.external_id = sub
        db.add(user)
        is_new_user = True
        await db.flush()
    else:
        # 已存在：刷新登录方式 + 复活
        if not user.is_active:
            user.is_active = True
        if user.login_type != "oidc":
            user.login_type = "oidc"
        await db.flush()

    await db.commit()

    pair = create_token_pair(user.id)
    return OidcLoginOut(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        access_expires_in=pair.access_expires_in,
        refresh_expires_in=pair.refresh_expires_in,
        user_id=user.id,
        is_new_user=is_new_user,
    )


@router.get("/metadata")
async def oidc_metadata() -> dict:
    """暴露当前进程的 OIDC 配置元数据（不含 secret），便于前端构造 redirect URL。"""
    try:
        cfg = _load_default_config()
    except OidcUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return {
        "provider": "default",
        "issuer": cfg.issuer,
        "client_id": cfg.client_id,
        "allowed_algorithms": list(cfg.allowed_algorithms),
    }
