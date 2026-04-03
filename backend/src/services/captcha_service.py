"""CAPTCHA verification service."""

from __future__ import annotations

from typing import Optional

import httpx
from loguru import logger

from src.core.config import settings


class CaptchaService:
    VERIFY_URLS = {
        "turnstile": "https://challenges.cloudflare.com/turnstile/v0/siteverify",
    }

    @staticmethod
    def is_enabled() -> bool:
        provider = (settings.CAPTCHA_PROVIDER or "").lower()
        if provider != "turnstile":
            return False
        return bool(
            settings.CAPTCHA_ENABLED
            and settings.TURNSTILE_SITE_KEY
            and settings.TURNSTILE_SECRET_KEY
        )

    @staticmethod
    def get_public_config() -> dict:
        if not CaptchaService.is_enabled():
            return {
                "captcha_enabled": False,
                "captcha_provider": None,
                "captcha_site_key": None,
            }
        return {
            "captcha_enabled": True,
            "captcha_provider": settings.CAPTCHA_PROVIDER.lower(),
            "captcha_site_key": settings.TURNSTILE_SITE_KEY,
        }

    @staticmethod
    async def verify_token(token: str, remote_ip: Optional[str] = None) -> bool:
        if not CaptchaService.is_enabled():
            return True
        if not token:
            return False

        verify_url = CaptchaService.VERIFY_URLS.get(settings.CAPTCHA_PROVIDER.lower())
        if not verify_url:
            logger.warning(f"不支持的 CAPTCHA 提供商: {settings.CAPTCHA_PROVIDER}")
            return False

        payload = {
            "secret": settings.TURNSTILE_SECRET_KEY,
            "response": token,
        }
        if remote_ip:
            payload["remoteip"] = remote_ip

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(verify_url, data=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.warning(f"CAPTCHA 验证失败: {exc}")
            return False

        success = bool(data.get("success"))
        if not success:
            logger.info(f"CAPTCHA 验证未通过: errors={data.get('error-codes', [])}")
        return success


captcha_service = CaptchaService()
