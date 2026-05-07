"""
HMAC 请求签名验证中间件

签名算法:
  payload = timestamp + "\\n" + nonce + "\\n" + method + "\\n" + path + "\\n" + SHA256(body)
  signature = HMAC-SHA256(signing_key, payload)

前端请求头:
  X-Request-Timestamp: Unix 秒
  X-Request-Nonce: 16 字节随机 hex
  X-Request-Signature: Base64(HMAC-SHA256)

防护:
  - 时间偏移 >300s 拒绝（防重放）
  - Redis SETNX nonce 去重（TTL=600s）
  - HMAC 签名校验
"""

import base64
import hashlib
import hmac
import time
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.core.config import settings

# 白名单路径（不需要签名）
_SKIP_PATHS = frozenset({
    "/health", "/docs", "/redoc", "/openapi.json",
    "/api/v1/auth/security-config",
})


class HMACSignatureMiddleware(BaseHTTPMiddleware):
    """HMAC 请求签名验证"""

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self._redis: Any | None = None
        self._redis_warning_logged = False

    async def _get_redis(self) -> Any:
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(  # type: ignore[no-untyped-call]
                settings.REDIS_URL, encoding="utf-8", decode_responses=True
            )
        return self._redis

    async def _check_nonce(self, nonce: str) -> bool:
        """Redis SETNX 检查 nonce 是否已使用，返回 True 表示是新 nonce"""
        try:
            redis_client = await self._get_redis()
            key = f"antibot:nonce:{nonce}"
            ttl = getattr(settings, "ANTIBOT_NONCE_TTL", 600)
            result = await redis_client.set(key, "1", nx=True, ex=ttl)
            return result is not None
        except Exception as e:
            if not self._redis_warning_logged:
                logger.warning(f"HMAC nonce Redis 不可用（已降级）: {e}")
                self._redis_warning_logged = True
            return True  # Redis 故障时降级放行

    async def _get_signing_key(self, request: Request) -> str | None:
        """获取签名密钥：已登录用户用专属 key，否则用公共 key"""
        # 尝试从 JWT 获取 user_id
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from src.core.security import verify_token
                user_id = verify_token(auth_header[7:], "access")
                if user_id:
                    redis_client = await self._get_redis()
                    user_key = await redis_client.get(f"antibot:signing_key:{user_id}")
                    if user_key:
                        return str(user_key)
            except Exception:
                pass

        # 回退到公共签名密钥
        return getattr(settings, "ANTIBOT_PUBLIC_SIGNING_KEY", "") or None

    def _verify_signature(
        self, signing_key: str, timestamp: str, nonce: str,
        method: str, path: str, body: bytes, provided_sig: str,
    ) -> bool:
        """验证 HMAC-SHA256 签名"""
        body_hash = hashlib.sha256(body).hexdigest()
        payload = f"{timestamp}\n{nonce}\n{method}\n{path}\n{body_hash}"
        expected = hmac.new(
            signing_key.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected_b64 = base64.b64encode(expected).decode("utf-8")
        return hmac.compare_digest(expected_b64, provided_sig)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # 跳过白名单路径和 OPTIONS 预检
        if request.url.path in _SKIP_PATHS or request.method == "OPTIONS":
            request.state.hmac_result = {"valid": True, "skipped": True}
            return await call_next(request)

        try:
            timestamp = request.headers.get("x-request-timestamp")
            nonce = request.headers.get("x-request-nonce")
            signature = request.headers.get("x-request-signature")

            # 无签名头 — 标记为 missing
            if timestamp is None or nonce is None or signature is None:
                request.state.hmac_result = {"valid": False, "reason": "missing_headers"}
                if getattr(settings, "ANTIBOT_HMAC_ENFORCE", False):
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "缺少请求签名", "code": "HMAC_MISSING"},
                    )
                return await call_next(request)

            # 1. 时间偏移检查
            drift = getattr(settings, "ANTIBOT_TIMESTAMP_DRIFT", 300)
            try:
                ts = int(timestamp)
            except (ValueError, TypeError):
                request.state.hmac_result = {"valid": False, "reason": "invalid_timestamp"}
                if getattr(settings, "ANTIBOT_HMAC_ENFORCE", False):
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "无效的时间戳", "code": "HMAC_INVALID_TS"},
                    )
                return await call_next(request)

            if abs(time.time() - ts) > drift:
                request.state.hmac_result = {"valid": False, "reason": "timestamp_expired"}
                if getattr(settings, "ANTIBOT_HMAC_ENFORCE", False):
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "请求已过期", "code": "HMAC_EXPIRED"},
                    )
                return await call_next(request)

            # 2. Nonce 去重
            if not await self._check_nonce(nonce):
                request.state.hmac_result = {"valid": False, "reason": "nonce_replay"}
                logger.warning(f"HMAC 重放检测: nonce={nonce[:8]}... path={request.url.path}")
                if getattr(settings, "ANTIBOT_HMAC_ENFORCE", False):
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "请求已被使用", "code": "HMAC_REPLAY"},
                    )
                return await call_next(request)

            # 3. 签名验证
            signing_key = await self._get_signing_key(request)
            if not signing_key:
                request.state.hmac_result = {"valid": False, "reason": "no_signing_key"}
                return await call_next(request)

            body = await request.body()
            valid = self._verify_signature(
                signing_key, timestamp, nonce,
                request.method, request.url.path, body, signature,
            )

            request.state.hmac_result = {
                "valid": valid,
                "reason": None if valid else "signature_mismatch",
            }

            if not valid:
                logger.warning(
                    f"HMAC 签名无效: path={request.url.path} method={request.method}"
                )
                if getattr(settings, "ANTIBOT_HMAC_ENFORCE", False):
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "签名验证失败", "code": "HMAC_INVALID"},
                    )

        except Exception as e:
            logger.debug(f"HMAC 中间件异常（已降级放行）: {e}")
            request.state.hmac_result = {"valid": False, "reason": "error", "degraded": True}

        return await call_next(request)
