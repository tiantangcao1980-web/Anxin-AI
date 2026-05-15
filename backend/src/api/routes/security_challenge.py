"""
安全挑战 API

- GET  /auth/security-config   — 前端获取安全配置（公共签名密钥、功能开关）
- POST /auth/security-challenge — PoW 挑战验证（Phase 3）
"""

import hashlib
from typing import Any, cast

from fastapi import APIRouter, HTTPException, status
from loguru import logger
from pydantic import BaseModel

from src.core.config import settings

router = APIRouter()


# ============ 安全配置端点 ============


class SecurityConfigResponse(BaseModel):
    hmac_enabled: bool = False
    hmac_enforce: bool = False
    public_signing_key: str | None = None
    fingerprint_enabled: bool = False
    pow_enabled: bool = False
    pow_difficulty: int = 4


@router.get("/security-config", response_model=SecurityConfigResponse)
async def get_security_config() -> SecurityConfigResponse:
    """返回前端需要的安全功能配置"""
    return SecurityConfigResponse(
        hmac_enabled=getattr(settings, "ANTIBOT_HMAC_ENABLED", False),
        hmac_enforce=getattr(settings, "ANTIBOT_HMAC_ENFORCE", False),
        public_signing_key=getattr(settings, "ANTIBOT_PUBLIC_SIGNING_KEY", None),
        fingerprint_enabled=getattr(settings, "ANTIBOT_FINGERPRINT_ENABLED", False),
        pow_enabled=getattr(settings, "ANTIBOT_POW_ENABLED", False),
        pow_difficulty=getattr(settings, "ANTIBOT_POW_DIFFICULTY", 4),
    )


# ============ PoW 挑战端点（Phase 3） ============


class ChallengeRequest(BaseModel):
    challenge_id: str
    nonce: int


class ChallengeResponse(BaseModel):
    valid: bool
    message: str = ""


@router.post("/security-challenge", response_model=ChallengeResponse)
async def verify_challenge(req: ChallengeRequest) -> ChallengeResponse:
    """验证 PoW 挑战解答"""
    try:
        import redis.asyncio as aioredis

        redis_from_url = cast(Any, aioredis.from_url)
        redis_client = redis_from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        key = f"antibot:challenge:{req.challenge_id}"
        challenge_data = await redis_client.hgetall(key)

        if not challenge_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="挑战不存在或已过期",
            )

        # 验证 PoW
        data = challenge_data["data"]
        difficulty = int(challenge_data["difficulty"])
        test_hash = hashlib.sha256(f"{data}{req.nonce}".encode()).hexdigest()
        prefix = "0" * difficulty

        if test_hash.startswith(prefix):
            # 验证通过，删除挑战（一次性）
            await redis_client.delete(key)
            return ChallengeResponse(valid=True, message="验证通过")
        else:
            return ChallengeResponse(valid=False, message="解答不正确")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PoW 验证异常: {e}")
        # 降级放行
        return ChallengeResponse(valid=True, message="验证服务暂时不可用，已放行")
