# -*- coding: utf-8 -*-
"""
客户端情报中间件（Phase 2）

分析浏览器指纹和 Bot 信号，检测异常模式：
- 同一指纹出现在过多不同 IP（代理池爬虫）
- 同一 IP 出现过多不同指纹（轮换指纹的爬虫）
- webdriver=true 等自动化工具信号
"""

import base64
import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from loguru import logger

from src.core.config import settings


class ClientIntelMiddleware(BaseHTTPMiddleware):
    """客户端情报采集与异常检测"""

    def __init__(self, app):
        super().__init__(app)
        self._redis = None
        self._redis_warning_logged = False

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                settings.REDIS_URL, encoding="utf-8", decode_responses=True
            )
        return self._redis

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        risk_score = 0
        reasons = []

        try:
            client_id = request.headers.get("x-client-id")
            bot_signals_raw = request.headers.get("x-bot-signals")
            client_ip = self._get_client_ip(request)

            # 1. 解析 Bot 信号
            if bot_signals_raw:
                try:
                    signals = json.loads(base64.b64decode(bot_signals_raw))
                    if signals.get("webdriver"):
                        risk_score += 20
                        reasons.append("webdriver_detected")
                    if signals.get("headlessChrome"):
                        risk_score += 10
                        reasons.append("headless_chrome")
                    if signals.get("noPlugins") and signals.get("noLanguages"):
                        risk_score += 10
                        reasons.append("no_plugins_no_languages")
                except Exception:
                    pass  # 无法解析，不加分

            # 2. 缺少客户端标识 — 可能是非浏览器请求
            if not client_id and not bot_signals_raw:
                risk_score += 5
                reasons.append("no_client_headers")

            # 3. 指纹-IP 关联分析
            if client_id:
                try:
                    redis_client = await self._get_redis()
                    max_ips = getattr(settings, "ANTIBOT_MAX_IPS_PER_FP", 5)
                    max_fps = getattr(settings, "ANTIBOT_MAX_FPS_PER_IP", 10)

                    # 记录指纹对应的 IP
                    fp_ip_key = f"antibot:fp:{client_id}:ips"
                    await redis_client.sadd(fp_ip_key, client_ip)
                    await redis_client.expire(fp_ip_key, 86400)
                    ip_count = await redis_client.scard(fp_ip_key)

                    if ip_count > max_ips:
                        risk_score += 15
                        reasons.append(f"fp_too_many_ips({ip_count})")

                    # 记录 IP 对应的指纹
                    ip_fp_key = f"antibot:ip:{client_ip}:fps"
                    await redis_client.sadd(ip_fp_key, client_id)
                    await redis_client.expire(ip_fp_key, 86400)
                    fp_count = await redis_client.scard(ip_fp_key)

                    if fp_count > max_fps:
                        risk_score += 15
                        reasons.append(f"ip_too_many_fps({fp_count})")

                except Exception as e:
                    if not self._redis_warning_logged:
                        logger.warning(f"ClientIntel Redis 不可用: {e}")
                        self._redis_warning_logged = True

            request.state.intel_result = {
                "risk_score": risk_score,
                "reasons": reasons,
                "client_id": client_id,
                "has_bot_signals": bot_signals_raw is not None,
            }

        except Exception as e:
            logger.debug(f"ClientIntel 中间件异常（已降级）: {e}")
            request.state.intel_result = {
                "risk_score": 0, "reasons": [], "degraded": True
            }

        return await call_next(request)
