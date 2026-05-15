"""
安全相关：JWT认证、密码加密、Token黑名单、请求频率限制
"""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import bcrypt
from jose import JWTError, jwt
from loguru import logger
from pydantic import BaseModel

from src.core.config import settings


class RateLimitBackendUnavailable(RuntimeError):  # noqa: N818
    """Raised when Redis-backed rate limiting is required but unavailable."""


class TokenPayload(BaseModel):
    """Token载荷"""

    sub: str  # user_id
    exp: datetime
    type: str = "access"
    jti: str | None = None  # JWT ID，用于黑名单


class TokenData(BaseModel):
    """Token数据"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPair(BaseModel):
    """Token对"""

    access_token: str
    refresh_token: str
    access_expires_in: int
    refresh_expires_in: int


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码（直接使用 bcrypt 5.x，避免 passlib 兼容性问题）"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def _generate_jti(user_id: str) -> str:
    """生成JWT ID"""
    import uuid

    return hashlib.sha256(f"{user_id}:{uuid.uuid4()}".encode()).hexdigest()[:32]


def create_access_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    """创建访问Token"""
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    jti = _generate_jti(user_id)

    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "access",
        "jti": jti,
        "iat": datetime.now(UTC),
    }

    return cast(
        str,
        jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        ),
    )


def create_refresh_token(user_id: str, expires_days: int = 7) -> str:
    """创建刷新Token"""
    expire = datetime.now(UTC) + timedelta(days=expires_days)
    jti = _generate_jti(user_id)

    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
        "jti": jti,
        "iat": datetime.now(UTC),
    }

    return cast(
        str,
        jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        ),
    )


def create_token_pair(user_id: str) -> TokenPair:
    """创建访问Token和刷新Token对"""
    access_expires = settings.JWT_EXPIRE_MINUTES
    refresh_expires_days = 7

    access_token = create_access_token(user_id, expires_delta=timedelta(minutes=access_expires))
    refresh_token = create_refresh_token(user_id, expires_days=refresh_expires_days)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_in=access_expires * 60,  # 转为秒
        refresh_expires_in=refresh_expires_days * 24 * 3600,
    )


def decode_token(token: str) -> TokenPayload | None:
    """解码Token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return TokenPayload(**payload)
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> str | None:
    """验证Token并返回user_id"""
    payload = decode_token(token)
    if payload is None:
        return None
    if payload.type != token_type:
        return None
    return payload.sub


def get_token_jti(token: str) -> str | None:
    """获取Token的JTI"""
    payload = decode_token(token)
    if payload is None:
        return None
    return payload.jti


# ========== Token黑名单管理 ==========


class TokenBlacklist:
    """
    Token黑名单管理
    使用Redis存储已失效的Token JTI
    """

    KEY_PREFIX = "legal_agent:token:blacklist"

    def __init__(self) -> None:
        self._redis: Any | None = None
        self._redis_warning_logged = False
        self._local_blacklist: dict[str, datetime] = {}

    def _prune_local_blacklist(self) -> None:
        now = datetime.now(UTC)
        expired = [jti for jti, exp in self._local_blacklist.items() if exp <= now]
        for jti in expired:
            self._local_blacklist.pop(jti, None)

    def _store_local_blacklist(self, jti: str, exp: datetime) -> None:
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)
        self._prune_local_blacklist()
        self._local_blacklist[jti] = exp

    def _log_redis_fallback(self, action: str, error: Exception) -> None:
        """Redis 不可用时记录一次警告，后续降级为调试日志，避免刷屏。"""
        message = f"{action}: {error}"
        if self._redis_warning_logged:
            logger.debug(message)
            return
        logger.warning(message)
        self._redis_warning_logged = True

    async def _get_redis(self) -> Any:
        """获取Redis客户端"""
        if self._redis is None:
            import redis.asyncio as redis

            self._redis = redis.from_url(  # type: ignore[no-untyped-call]
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    def _make_key(self, jti: str) -> str:
        """生成黑名单Key"""
        return f"{self.KEY_PREFIX}:{jti}"

    async def add_to_blacklist(self, token: str, reason: str = "logout") -> bool:
        """
        将Token加入黑名单

        Args:
            token: JWT Token
            reason: 加入黑名单的原因

        Returns:
            是否成功
        """
        payload: TokenPayload | None = None
        exp = datetime.now(UTC)
        try:
            payload = decode_token(token)
            if payload is None:
                return False

            jti = payload.jti
            if not jti:
                # 兼容没有jti的旧Token
                jti = hashlib.sha256(token.encode()).hexdigest()[:32]

            # 计算剩余过期时间
            now = datetime.now(UTC)
            exp = payload.exp
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=UTC)

            ttl = int((exp - now).total_seconds())
            if ttl <= 0:
                # Token已过期，无需加入黑名单
                return True

            redis_client = await self._get_redis()
            key = self._make_key(jti)

            # 存储黑名单记录
            await redis_client.set(key, reason, ex=ttl)

            logger.info(f"Token已加入黑名单: jti={jti[:8]}..., reason={reason}")
            return True

        except Exception as e:
            logger.error(f"添加Token到黑名单失败: {e}")
            if payload is not None:
                jti = payload.jti or hashlib.sha256(token.encode()).hexdigest()[:32]
                self._store_local_blacklist(jti, exp)
                logger.warning(f"Redis不可用，Token已写入本地黑名单回退: jti={jti[:8]}...")
                return True
            return False

    async def is_blacklisted(self, token: str, fail_closed: bool = False) -> bool:
        """
        检查Token是否在黑名单中

        Args:
            token: JWT Token
            fail_closed: Redis 故障时是否拒绝请求（用于 refresh token 等敏感链路）

        Returns:
            是否在黑名单中
        """
        jti = None
        try:
            payload = decode_token(token)
            if payload is None:
                return True  # 无效Token视为已黑名单

            jti = payload.jti
            if not jti:
                jti = hashlib.sha256(token.encode()).hexdigest()[:32]

            redis_client = await self._get_redis()
            key = self._make_key(jti)

            return int(await redis_client.exists(key)) > 0

        except Exception as e:
            self._log_redis_fallback("检查Token黑名单失败", e)
            if fail_closed:
                logger.warning("Redis 不可用且处于 fail-closed 模式，拒绝敏感操作")
                return True  # 敏感链路：Redis 故障时视为已撤销
            # 普通链路：降级为本地黑名单
            self._prune_local_blacklist()
            return (jti in self._local_blacklist) if jti else True

    async def revoke_all_user_tokens(self, user_id: str) -> bool:
        """
        撤销用户所有Token（通过用户级别的黑名单标记）

        注意：这需要在验证Token时同时检查用户级别的撤销标记
        """
        try:
            redis_client = await self._get_redis()
            key = f"{self.KEY_PREFIX}:user:{user_id}"

            # 设置用户级别的撤销时间戳
            await redis_client.set(key, datetime.now(UTC).isoformat(), ex=7 * 24 * 3600)  # 7天

            logger.info(f"已撤销用户所有Token: user_id={user_id}")
            return True

        except Exception as e:
            logger.error(f"撤销用户Token失败: {e}")
            return False

    async def close(self) -> None:
        """关闭Redis连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None


# 全局Token黑名单实例
_token_blacklist: TokenBlacklist | None = None


def get_token_blacklist() -> TokenBlacklist:
    """获取Token黑名单单例"""
    global _token_blacklist
    if _token_blacklist is None:
        _token_blacklist = TokenBlacklist()
    return _token_blacklist


async def refresh_access_token(refresh_token: str) -> TokenPair | None:
    """
    使用刷新Token获取新的Token对

    Args:
        refresh_token: 刷新Token

    Returns:
        新的Token对，失败返回None
    """
    # 验证刷新Token
    user_id = verify_token(refresh_token, token_type="refresh")
    if not user_id:
        logger.warning("刷新Token无效")
        return None

    # 检查是否在黑名单中 — refresh 链路使用 fail-closed
    blacklist = get_token_blacklist()
    if await blacklist.is_blacklisted(refresh_token, fail_closed=True):
        logger.warning(f"刷新Token已被撤销或 Redis 不可用(fail-closed): user_id={user_id}")
        return None

    # 将旧的刷新Token加入黑名单
    await blacklist.add_to_blacklist(refresh_token, reason="token_refresh")

    # 创建新的Token对
    return create_token_pair(user_id)


async def revoke_token(token: str, reason: str = "logout") -> bool:
    """
    撤销Token

    Args:
        token: 要撤销的Token
        reason: 撤销原因

    Returns:
        是否成功
    """
    blacklist = get_token_blacklist()
    return await blacklist.add_to_blacklist(token, reason)


async def verify_token_with_blacklist(token: str, token_type: str = "access") -> str | None:
    """
    验证Token（包含黑名单检查）

    Args:
        token: JWT Token
        token_type: Token类型

    Returns:
        用户ID，验证失败返回None
    """
    # 基本验证
    user_id = verify_token(token, token_type)
    if not user_id:
        return None

    # 黑名单检查
    blacklist = get_token_blacklist()
    if await blacklist.is_blacklisted(token):
        logger.warning(f"Token已被撤销: user_id={user_id}")
        return None

    return user_id


# ========== 请求频率限制 ==========


class RateLimiter:
    """
    请求频率限制器
    使用Redis实现滑动窗口限流
    """

    KEY_PREFIX = "legal_agent:rate_limit"

    # 默认限制配置
    DEFAULT_LIMIT = 60  # 每分钟60次请求
    DEFAULT_WINDOW = 60  # 窗口大小（秒）

    def __init__(self) -> None:
        self._redis: Any | None = None
        self._redis_warning_logged = False
        self._memory_windows: dict[str, list[float]] = {}

    def _log_redis_fallback(self, action: str, error: Exception) -> None:
        """限流 Redis 不可用时只在首次输出警告，后续使用调试日志。"""
        message = f"{action}: {error}"
        if self._redis_warning_logged:
            logger.debug(message)
            return
        logger.warning(message)
        self._redis_warning_logged = True

    async def _get_redis(self) -> Any:
        """获取Redis客户端"""
        if self._redis is None:
            import redis.asyncio as redis

            self._redis = redis.from_url(  # type: ignore[no-untyped-call]
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    def _make_key(self, identifier: str, endpoint: str = "global") -> str:
        """生成限流Key"""
        return f"{self.KEY_PREFIX}:{endpoint}:{identifier}"

    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str = "global",
        limit: int = DEFAULT_LIMIT,
        window: int = DEFAULT_WINDOW,
        fail_closed: bool = False,
    ) -> tuple[bool, int, int]:
        """
        检查并更新请求频率

        Args:
            identifier: 标识符（如用户ID、IP地址）
            endpoint: 端点标识
            limit: 限制次数
            window: 时间窗口（秒）

        Returns:
            (是否允许, 当前请求数, 剩余配额)
        """
        try:
            redis_client = await self._get_redis()
            key = self._make_key(identifier, endpoint)
            now = datetime.now(UTC).timestamp()
            window_start = now - window

            # 使用Lua脚本实现原子操作
            lua_script = """
            local key = KEYS[1]
            local now = tonumber(ARGV[1])
            local window_start = tonumber(ARGV[2])
            local limit = tonumber(ARGV[3])
            local window = tonumber(ARGV[4])
            
            -- 移除过期的记录
            redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
            
            -- 获取当前请求数
            local current = redis.call('ZCARD', key)
            
            if current < limit then
                -- 添加当前请求
                redis.call('ZADD', key, now, now)
                redis.call('EXPIRE', key, window)
                return {1, current + 1, limit - current - 1}
            else
                return {0, current, 0}
            end
            """

            result = await redis_client.eval(
                lua_script,
                1,
                key,
                str(now),
                str(window_start),
                str(limit),
                str(window),
            )

            result_values = cast(list[Any], result)
            allowed = bool(result_values[0])
            current = int(result_values[1])
            remaining = int(result_values[2])

            if not allowed:
                logger.warning(f"请求频率超限: {identifier} -> {endpoint}")

            return allowed, current, remaining

        except Exception as e:
            if fail_closed:
                logger.error(f"频率限制检查失败且处于 fail-closed 模式: {e}")
                raise RateLimitBackendUnavailable(str(e)) from e

            self._log_redis_fallback("频率限制检查失败，已降级为本地内存限流", e)
            key = self._make_key(identifier, endpoint)
            now = datetime.now(UTC).timestamp()
            window_start = now - window
            timestamps = [ts for ts in self._memory_windows.get(key, []) if ts > window_start]
            current = len(timestamps)
            if current < limit:
                timestamps.append(now)
                self._memory_windows[key] = timestamps
                return True, current + 1, limit - current - 1
            self._memory_windows[key] = timestamps
            return False, current, 0

    async def get_usage(
        self,
        identifier: str,
        endpoint: str = "global",
        window: int = DEFAULT_WINDOW,
    ) -> int:
        """
        获取当前使用量

        Args:
            identifier: 标识符
            endpoint: 端点标识
            window: 时间窗口（秒）

        Returns:
            当前请求数
        """
        try:
            redis_client = await self._get_redis()
            key = self._make_key(identifier, endpoint)
            now = datetime.now(UTC).timestamp()
            window_start = now - window

            # 移除过期记录并获取计数
            await redis_client.zremrangebyscore(key, "-inf", window_start)
            return int(await redis_client.zcard(key))

        except Exception as e:
            self._log_redis_fallback("获取限流使用量失败，已降级为本地内存统计", e)
            key = self._make_key(identifier, endpoint)
            now = datetime.now(UTC).timestamp()
            window_start = now - window
            timestamps = [ts for ts in self._memory_windows.get(key, []) if ts > window_start]
            self._memory_windows[key] = timestamps
            return len(timestamps)

    async def reset(self, identifier: str, endpoint: str = "global") -> bool:
        """
        重置限流计数

        Args:
            identifier: 标识符
            endpoint: 端点标识

        Returns:
            是否成功
        """
        try:
            redis_client = await self._get_redis()
            key = self._make_key(identifier, endpoint)
            await redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"重置限流失败: {e}")
            key = self._make_key(identifier, endpoint)
            self._memory_windows.pop(key, None)
            return True

    async def close(self) -> None:
        """关闭Redis连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None


# 全局频率限制器实例
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """获取频率限制器单例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


# ========== 便捷的限流配置 ==========


class RateLimitConfig:
    """预定义的限流配置"""

    # 通用API限制
    API_DEFAULT = {"limit": 60, "window": 60}  # 60次/分钟

    # 认证相关限制（更严格）
    AUTH_LOGIN = {"limit": 10, "window": 60}  # 10次/分钟
    AUTH_REGISTER = {"limit": 5, "window": 300}  # 5次/5分钟
    AUTH_PASSWORD_RESET = {"limit": 3, "window": 300}  # 3次/5分钟

    # 搜索限制
    SEARCH = {"limit": 30, "window": 60}  # 30次/分钟

    # 文件上传限制
    UPLOAD = {"limit": 20, "window": 60}  # 20次/分钟

    # AI对话限制
    CHAT = {"limit": 30, "window": 60}  # 30次/分钟
    CHAT_STREAM = {"limit": 20, "window": 60}  # 20次/分钟
