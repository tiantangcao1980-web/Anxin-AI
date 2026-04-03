"""Shared webhook signature and replay protection helpers."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Optional

from loguru import logger

from src.core.config import settings


class WebhookSecurity:
    _seen_signatures: dict[str, float] = {}

    @classmethod
    def _prune(cls) -> None:
        now = time.time()
        expired = [
            key for key, ts in cls._seen_signatures.items()
            if now - ts > settings.WEBHOOK_SIGNATURE_MAX_AGE_SECONDS
        ]
        for key in expired:
            cls._seen_signatures.pop(key, None)

    @classmethod
    def verify(
        cls,
        *,
        scope: str,
        body: bytes,
        signature: Optional[str],
        secret: Optional[str],
        timestamp: Optional[str],
    ) -> bool:
        """Verify HMAC signature with timestamp freshness and simple replay protection."""
        if not secret:
            return not settings.is_production()
        if not signature or not timestamp:
            return False

        try:
            ts_value = int(timestamp)
        except (TypeError, ValueError):
            logger.info(f"{scope} webhook timestamp 非法: {timestamp}")
            return False

        now = int(time.time())
        max_age = settings.WEBHOOK_SIGNATURE_MAX_AGE_SECONDS
        if abs(now - ts_value) > max_age:
            logger.info(f"{scope} webhook timestamp 过期: age={abs(now - ts_value)}")
            return False

        payload = f"{ts_value}.".encode("utf-8") + body
        expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature.strip(), expected):
            return False

        replay_key = hashlib.sha256(f"{scope}:{ts_value}:{signature}".encode("utf-8")).hexdigest()
        cls._prune()
        if replay_key in cls._seen_signatures:
            logger.warning(f"{scope} webhook 检测到重放")
            return False

        cls._seen_signatures[replay_key] = time.time()
        return True
