"""
风控评分引擎中间件（Phase 3）

综合所有上游中间件的分析结果，计算最终风险分数：
- PASS (0-29): 正常处理
- CHALLENGE (30-69): 下发 PoW 挑战
- BLOCK (>=70): 直接拒绝

评分维度：
- HMAC 签名 (0-30)
- 客户端情报 (0-25)
- 请求频率 (0-30)
- 行为模式 (0-15)
"""

import hashlib
import secrets
import time
from collections.abc import Awaitable, Callable
from typing import Any, cast

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.core.config import settings

_SKIP_PATHS = frozenset({
    "/health", "/docs", "/redoc", "/openapi.json",
    "/api/v1/auth/security-config",
    "/api/v1/auth/security-challenge",
})


class RiskScoringMiddleware(BaseHTTPMiddleware):
    """风控评分引擎"""

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self._redis: Any | None = None

    async def _get_redis(self) -> Any:
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(  # type: ignore[no-untyped-call]
                settings.REDIS_URL, encoding="utf-8", decode_responses=True
            )
        return self._redis

    def _get_identifier(self, request: Request) -> str:
        """获取请求标识（用于行为分析）"""
        forwarded = request.headers.get("x-forwarded-for")
        ip = forwarded.split(",")[0].strip() if forwarded else (
            request.client.host if request.client else "unknown"
        )
        client_id = request.headers.get("x-client-id", "")
        return f"{ip}:{client_id}" if client_id else ip

    def _score_hmac(self, request: Request) -> int:
        """HMAC 维度评分 (0-30)"""
        result = getattr(request.state, "hmac_result", None)
        if not isinstance(result, dict):
            return 15  # 无 HMAC 结果，中等风险
        if result.get("skipped"):
            return 0
        if result.get("valid"):
            return 0
        reason = result.get("reason", "")
        if reason == "missing_headers":
            return 15
        if reason in ("nonce_replay", "timestamp_expired"):
            return 30  # 重放攻击，最高分
        if reason == "signature_mismatch":
            return 25
        return 10

    def _score_intel(self, request: Request) -> int:
        """客户端情报维度评分 (0-25)"""
        result = getattr(request.state, "intel_result", None)
        if not isinstance(result, dict):
            return 0
        try:
            score = int(result.get("risk_score", 0))
        except (TypeError, ValueError):
            return 0
        return min(max(score, 0), 25)

    async def _score_behavior(self, identifier: str) -> int:
        """行为分析维度评分 (0-15)"""
        try:
            redis_client = await self._get_redis()
            now = time.time()

            # 记录请求时间戳
            key = f"antibot:intervals:{identifier}"
            await redis_client.lpush(key, str(now))
            await redis_client.ltrim(key, 0, 19)  # 保留最近 20 条
            await redis_client.expire(key, 600)

            # 读取间隔列表
            timestamps = await redis_client.lrange(key, 0, 19)
            if len(timestamps) < 5:
                return 0

            # 计算间隔方差
            ts_list = [float(t) for t in timestamps]
            intervals = [ts_list[i] - ts_list[i + 1] for i in range(len(ts_list) - 1)]
            if not intervals:
                return 0

            mean = sum(intervals) / len(intervals)
            variance = sum((x - mean) ** 2 for x in intervals) / len(intervals)

            # 方差极低 = 机器人（人类操作有自然抖动）
            if variance < 0.001 and len(intervals) >= 10:
                return 15
            elif variance < 0.01 and len(intervals) >= 10:
                return 8
            return 0

        except Exception:
            return 0

    async def _issue_challenge(self) -> dict[str, Any]:
        """生成 PoW 挑战"""
        difficulty = getattr(settings, "ANTIBOT_POW_DIFFICULTY", 4)
        challenge_id = f"ch_{secrets.token_hex(12)}"
        data = secrets.token_hex(16)
        expires_at = int(time.time()) + 120

        try:
            redis_client = await self._get_redis()
            key = f"antibot:challenge:{challenge_id}"
            await redis_client.hset(
                key,
                mapping={
                    "data": data,
                    "difficulty": str(difficulty),
                    "expires_at": str(expires_at),
                },
            )
            await redis_client.expire(key, 120)
        except Exception as e:
            logger.warning(f"无法存储 PoW 挑战: {e}")

        return {
            "challenge_id": challenge_id,
            "algorithm": "sha256",
            "prefix": "0" * difficulty,
            "data": data,
            "difficulty": difficulty,
            "expires_at": expires_at,
        }

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in _SKIP_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        try:
            identifier = self._get_identifier(request)

            # 综合评分
            hmac_score = self._score_hmac(request)
            intel_score = self._score_intel(request)
            behavior_score = await self._score_behavior(identifier)
            total_score = hmac_score + intel_score + behavior_score

            challenge_threshold = getattr(settings, "ANTIBOT_CHALLENGE_THRESHOLD", 30)
            block_threshold = getattr(settings, "ANTIBOT_BLOCK_THRESHOLD", 70)

            if total_score >= block_threshold:
                logger.warning(
                    f"风控阻断: score={total_score} "
                    f"(hmac={hmac_score}, intel={intel_score}, behavior={behavior_score}) "
                    f"id={identifier} path={request.url.path}"
                )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "请求被安全策略拦截", "code": "RISK_BLOCKED"},
                    headers={"Retry-After": "60"},
                )

            if total_score >= challenge_threshold and getattr(settings, "ANTIBOT_POW_ENABLED", False):
                # 检查是否已携带有效的挑战解答
                challenge_id = request.headers.get("x-challenge-id")
                challenge_solution = request.headers.get("x-challenge-solution")

                if challenge_id and challenge_solution:
                    # 验证解答
                    try:
                        redis_client = await self._get_redis()
                        ch_key = f"antibot:challenge:{challenge_id}"
                        ch_data = await redis_client.hgetall(ch_key)
                        if isinstance(ch_data, dict) and ch_data:
                            challenge_data = cast(dict[str, Any], ch_data)
                            test_hash = hashlib.sha256(
                                f"{challenge_data['data']}{challenge_solution}".encode()
                            ).hexdigest()
                            if test_hash.startswith("0" * int(challenge_data["difficulty"])):
                                await redis_client.delete(ch_key)
                                # 挑战通过，放行
                                return await call_next(request)
                    except Exception:
                        pass

                # 下发新挑战
                challenge = await self._issue_challenge()
                logger.info(
                    f"风控挑战: score={total_score} id={identifier} path={request.url.path}"
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "需要完成安全验证",
                        "code": "CHALLENGE_REQUIRED",
                        "challenge": challenge,
                    },
                    headers={"X-Challenge-Required": "true"},
                )

            # PASS — 记录评分供审计
            if total_score > 0:
                logger.debug(
                    f"风控通过: score={total_score} "
                    f"(h={hmac_score},i={intel_score},b={behavior_score}) "
                    f"path={request.url.path}"
                )

        except Exception as e:
            logger.debug(f"RiskScoring 中间件异常（已降级放行）: {e}")

        return await call_next(request)
