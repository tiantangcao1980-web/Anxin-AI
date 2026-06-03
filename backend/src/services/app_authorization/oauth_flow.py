"""
OAuthFlowService — 通用 OAuth 2.0 授权码流程编排（P4-A）

5 个公开方法
------------
- ``start``       : 生成 state + 缓存 + 返回 authorize_url
- ``callback``    : 校验 state + 用 code 换 token + 加密入库 + 返回 AppAuthorization
- ``refresh``     : 用 refresh_token 续期 + 更新 token 行
- ``disconnect``  : 调 provider.revoke + 标记 status=revoked
- ``list_for_user``: 列出某用户的所有授权（API 路由用）

state 缓存策略
--------------
- 优先 Redis（``settings.REDIS_URL``），降级到本地内存（仅本地开发 / 测试）；
- TTL = 600s（OAuth state 寿命短，防止 CSRF）；
- key 形如 ``oauth:state:{provider_id}:{state}`` → value = user_id。

错误体系
--------
- ``OAuthStateError``     : state 不匹配 / 已过期
- ``OAuthProviderError``  : provider 拒绝 / 非 2xx 响应
- ``OAuthNotFoundError``  : authorization_id 不存在
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.app_authorization.base import (
    BaseOAuthProvider,
    OAuthTokenBundle,
)
from src.services.app_authorization.models import (
    AppAuthorization,
    AppAuthorizationStatus,
    AppToken,
)
from src.services.app_authorization.registry import OAuthProviderRegistry
from src.services.app_authorization.token_store import TokenStore


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------
class OAuthFlowError(Exception):
    """OAuth flow 通用基类。"""


class OAuthStateError(OAuthFlowError):
    """state 校验失败 / 已过期。"""


class OAuthProviderError(OAuthFlowError):
    """provider 调用失败（封装上游 4xx/5xx）。"""


class OAuthConfigError(OAuthFlowError):
    """provider 凭据（client_id / client_secret）未配置。

    诚实化保障：未配置时不得静默生成带空 ``client_id=`` 的"假绿"授权 URL，
    也不得用空凭据去换 token，而应明确报错告知"该应用尚未配置"。
    """


class OAuthNotFoundError(OAuthFlowError):
    """AppAuthorization 不存在。"""


# ---------------------------------------------------------------------------
# state 缓存（Redis 优先 + 本地内存降级）
# ---------------------------------------------------------------------------
class _StateCache:
    """OAuth state 缓存：Redis 优先，失败降级到内存（仅当前进程）。

    内存模式不支持 TTL 精确过期，但通过 lazy expire（取出时检查）实现。
    """

    STATE_TTL_SECONDS = 600  # 10 分钟

    def __init__(self) -> None:
        self._memory: dict[str, tuple[str, float]] = {}
        self._redis: Any = None  # 类型: redis.asyncio.Redis | None
        self._redis_ready: bool = False

    async def _ensure_redis(self) -> Any | None:
        if self._redis is not None or self._redis_ready:
            return self._redis
        try:
            import redis.asyncio as aioredis  # noqa: WPS433

            from src.core.config import settings

            self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            # ping 一次确认可用
            await self._redis.ping()
        except Exception:
            self._redis = None
        self._redis_ready = True
        return self._redis

    @staticmethod
    def _key(provider_id: str, state: str) -> str:
        return f"oauth:state:{provider_id}:{state}"

    async def put(self, provider_id: str, state: str, user_id: str) -> None:
        redis = await self._ensure_redis()
        if redis is not None:
            try:
                await redis.set(
                    self._key(provider_id, state),
                    user_id,
                    ex=self.STATE_TTL_SECONDS,
                )
                return
            except Exception:
                pass  # 退化到内存
        # 内存降级（带 deadline timestamp）
        import time

        self._memory[self._key(provider_id, state)] = (
            user_id,
            time.time() + self.STATE_TTL_SECONDS,
        )

    async def pop(self, provider_id: str, state: str) -> str | None:
        """取出并删除（一次性使用）。"""
        key = self._key(provider_id, state)
        redis = await self._ensure_redis()
        if redis is not None:
            try:
                val = await redis.get(key)
                if val is not None:
                    await redis.delete(key)
                    return val
            except Exception:
                pass
        # 内存
        import time

        item = self._memory.pop(key, None)
        if item is None:
            return None
        user_id, deadline = item
        if time.time() > deadline:
            return None
        return user_id


# 进程级单例（轻量，避免每次 new 一个 Redis client）
_state_cache: _StateCache | None = None


def _get_state_cache() -> _StateCache:
    global _state_cache
    if _state_cache is None:
        _state_cache = _StateCache()
    return _state_cache


# ---------------------------------------------------------------------------
# 主服务
# ---------------------------------------------------------------------------
class OAuthFlowService:
    """通用 OAuth 2.0 流程编排（无状态：每个请求 new 一次）。"""

    def __init__(
        self,
        db: AsyncSession,
        *,
        registry: OAuthProviderRegistry | None = None,
        token_store: TokenStore | None = None,
        state_cache: _StateCache | None = None,
    ) -> None:
        self.db = db
        self.registry = registry or OAuthProviderRegistry.default()
        self._token_store_lazy = token_store
        self._state_cache = state_cache or _get_state_cache()

    @property
    def token_store(self) -> TokenStore:
        """惰性构造 TokenStore（避免无 KEY 环境下 import 即崩）。"""
        if self._token_store_lazy is None:
            self._token_store_lazy = TokenStore.from_settings()
        return self._token_store_lazy

    # ------------------------------------------------------------------
    # 1) start
    # ------------------------------------------------------------------
    async def start(
        self,
        provider_id: str,
        user_id: str,
        *,
        redirect_uri: str | None = None,
        scopes: list[str] | None = None,
    ) -> dict[str, str]:
        """生成授权 URL。

        返回 ``{"authorize_url": "...", "state": "..."}``。
        """
        provider = self._build_provider(provider_id)
        self._require_configured(provider_id, provider)
        state = secrets.token_urlsafe(32)
        await self._state_cache.put(provider_id, state, user_id)

        callback_url = redirect_uri or self._default_redirect_uri(provider_id)
        url = await provider.authorize_url(
            state=state,
            redirect_uri=callback_url,
            scopes=scopes,
        )
        return {"authorize_url": url, "state": state}

    # ------------------------------------------------------------------
    # 2) callback
    # ------------------------------------------------------------------
    async def callback(
        self,
        provider_id: str,
        state: str,
        code: str,
        *,
        redirect_uri: str | None = None,
    ) -> AppAuthorization:
        """处理 OAuth 回调：校验 state → 换 token → 加密入库。

        若该 user × provider 已有授权记录，则更新 token；否则创建。
        """
        user_id = await self._state_cache.pop(provider_id, state)
        if user_id is None:
            raise OAuthStateError(f"OAuth state 校验失败或已过期 (provider={provider_id})")

        provider = self._build_provider(provider_id)
        self._require_configured(provider_id, provider)
        callback_url = redirect_uri or self._default_redirect_uri(provider_id)

        try:
            bundle = await provider.exchange_code(code=code, redirect_uri=callback_url)
        except Exception as e:
            raise OAuthProviderError(f"provider {provider_id} exchange_code 失败: {e}") from e

        return await self._upsert_authorization(
            user_id=user_id,
            provider_id=provider_id,
            bundle=bundle,
        )

    # ------------------------------------------------------------------
    # 3) refresh
    # ------------------------------------------------------------------
    async def refresh(self, authorization_id: str) -> AppAuthorization:
        """用 refresh_token 续期；失败时把 status 置为 expired/error。"""
        auth = await self._load_authorization(authorization_id)
        token_row = await self._load_token_row(auth.id)
        if token_row is None or token_row.encrypted_refresh_token is None:
            auth.status = AppAuthorizationStatus.EXPIRED
            auth.error_message = "无 refresh_token，无法续期"
            await self.db.flush()
            raise OAuthProviderError("当前授权无 refresh_token，无法续期")

        try:
            refresh_plain = self.token_store.decrypt(token_row.encrypted_refresh_token)
        except Exception as e:
            auth.status = AppAuthorizationStatus.ERROR
            auth.error_message = f"refresh_token 解密失败: {e}"
            await self.db.flush()
            raise OAuthProviderError(str(e)) from e

        provider = self._build_provider(auth.provider_id)
        try:
            bundle = await provider.refresh_token(refresh_plain)
        except Exception as e:
            auth.status = AppAuthorizationStatus.EXPIRED
            auth.error_message = f"refresh 失败: {e}"
            await self.db.flush()
            raise OAuthProviderError(str(e)) from e

        # 更新 token 行
        token_row.encrypted_access_token = self.token_store.encrypt(bundle.access_token)
        if bundle.refresh_token:
            token_row.encrypted_refresh_token = self.token_store.encrypt(bundle.refresh_token)
        token_row.token_type = bundle.token_type or "Bearer"
        token_row.expires_at = bundle.expires_at

        auth.status = AppAuthorizationStatus.CONNECTED
        auth.error_message = None
        auth.last_refresh_at = datetime.now(UTC)
        if bundle.scopes:
            auth.scopes = bundle.scopes

        await self.db.flush()
        # 防止 onupdate=func.now() 导致 updated_at 被标为 expired —— 显式刷新一次
        await self.db.refresh(auth)
        return auth

    # ------------------------------------------------------------------
    # 4) disconnect
    # ------------------------------------------------------------------
    async def disconnect(self, authorization_id: str) -> AppAuthorization:
        """断开连接：调 provider.revoke + 标 status=revoked。"""
        auth = await self._load_authorization(authorization_id)
        token_row = await self._load_token_row(auth.id)

        # 尝试调 revoke（失败不阻止本地清理）
        if token_row is not None:
            try:
                access_plain = self.token_store.decrypt(token_row.encrypted_access_token)
                provider = self._build_provider(auth.provider_id)
                await provider.revoke(access_plain)
            except Exception:
                # revoke 失败不致命：远端可能已经过期
                pass

        auth.status = AppAuthorizationStatus.REVOKED
        await self.db.flush()
        await self.db.refresh(auth)
        return auth

    # ------------------------------------------------------------------
    # 5) 列表查询（API 用）
    # ------------------------------------------------------------------
    async def list_for_user(self, user_id: str) -> list[AppAuthorization]:
        """列出某用户的所有授权（按创建时间倒序）。"""
        stmt = (
            select(AppAuthorization)
            .where(AppAuthorization.user_id == user_id)
            .order_by(AppAuthorization.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _build_provider(self, provider_id: str) -> BaseOAuthProvider:
        try:
            return self.registry.build(provider_id)
        except KeyError as e:
            raise OAuthProviderError(str(e)) from e

    @staticmethod
    def _require_configured(provider_id: str, provider: BaseOAuthProvider) -> None:
        """fail-fast：provider 未配置 client_id/client_secret 时明确报错。

        防止"未配置却静默假成功"——避免生成带空 ``client_id=`` 的死链接，或用
        空凭据去换 token（必失败但报错语义模糊）。
        """
        client_id = getattr(provider, "client_id", None)
        client_secret = getattr(provider, "client_secret", None)
        missing: list[str] = []
        if not client_id:
            missing.append("client_id")
        if not client_secret:
            missing.append("client_secret")
        if missing:
            raise OAuthConfigError(
                f"应用 '{provider_id}' 尚未配置凭据（缺少 {', '.join(missing)}），"
                "请在后台 / 环境变量中填入对应的 client_id / client_secret 后再发起授权。"
            )

    def _default_redirect_uri(self, provider_id: str) -> str:
        from src.core.config import settings

        base = (settings.APP_AUTH_REDIRECT_BASE_URL or "").rstrip("/")
        return f"{base}/api/v1/app-authorizations/{provider_id}/callback"

    async def _load_authorization(self, authorization_id: str) -> AppAuthorization:
        stmt = select(AppAuthorization).where(AppAuthorization.id == authorization_id)
        result = await self.db.execute(stmt)
        auth = result.scalar_one_or_none()
        if auth is None:
            raise OAuthNotFoundError(f"AppAuthorization {authorization_id} 不存在")
        return auth

    async def _load_token_row(self, authorization_id: str) -> AppToken | None:
        stmt = select(AppToken).where(AppToken.authorization_id == authorization_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _upsert_authorization(
        self,
        *,
        user_id: str,
        provider_id: str,
        bundle: OAuthTokenBundle,
    ) -> AppAuthorization:
        """创建或更新授权 + token 行。"""
        # 找现有（未 revoked 的优先；若全 revoked 则也复用第一条）
        stmt = (
            select(AppAuthorization)
            .where(
                AppAuthorization.user_id == user_id,
                AppAuthorization.provider_id == provider_id,
            )
            .order_by(AppAuthorization.created_at.desc())
        )
        result = await self.db.execute(stmt)
        auth = result.scalar_one_or_none()

        now = datetime.now(UTC)

        if auth is None:
            auth = AppAuthorization(
                id=str(uuid4()),
                user_id=user_id,
                provider_id=provider_id,
                status=AppAuthorizationStatus.CONNECTED,
                scopes=bundle.scopes or [],
                connected_at=now,
                last_refresh_at=None,
                error_message=None,
            )
            self.db.add(auth)
            await self.db.flush()
        else:
            auth.status = AppAuthorizationStatus.CONNECTED
            auth.scopes = bundle.scopes or auth.scopes
            auth.error_message = None
            if auth.connected_at is None:
                auth.connected_at = now

        token_row = await self._load_token_row(auth.id)
        encrypted_access = self.token_store.encrypt(bundle.access_token)
        encrypted_refresh = self.token_store.encrypt_optional(bundle.refresh_token)

        if token_row is None:
            token_row = AppToken(
                id=str(uuid4()),
                authorization_id=auth.id,
                encrypted_access_token=encrypted_access,
                encrypted_refresh_token=encrypted_refresh,
                token_type=bundle.token_type or "Bearer",
                expires_at=bundle.expires_at,
            )
            self.db.add(token_row)
        else:
            token_row.encrypted_access_token = encrypted_access
            if encrypted_refresh is not None:
                token_row.encrypted_refresh_token = encrypted_refresh
            token_row.token_type = bundle.token_type or "Bearer"
            token_row.expires_at = bundle.expires_at

        await self.db.flush()
        # 防止 onupdate=func.now() 触发懒加载（API 路由在 async 上下文外读字段时会 MissingGreenlet）
        await self.db.refresh(auth)
        return auth


__all__ = [
    "OAuthFlowService",
    "OAuthFlowError",
    "OAuthStateError",
    "OAuthProviderError",
    "OAuthNotFoundError",
]
