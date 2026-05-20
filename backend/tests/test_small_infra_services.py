from typing import Any

import pytest

from src.core.privacy import InferenceRequest, SensitivityLevel
from src.services.cache_service import CacheService
from src.services.captcha_service import CaptchaService
from src.services.compute_router_service import ComputeRouterService
from src.services.email_service import EmailService
from src.services.im_hub import IMConnectionManager
from src.services.sms_service import SMSService
from src.services.webhook_idempotency_service import webhook_processing_lock


@pytest.mark.asyncio
async def test_email_service_returns_false_when_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.config import settings

    monkeypatch.setattr(settings, "ALIYUN_ACCESS_KEY_ID", "", raising=False)
    monkeypatch.setattr(settings, "ALIYUN_ACCESS_KEY_SECRET", "", raising=False)
    monkeypatch.setattr(settings, "ALIYUN_EMAIL_ACCOUNT", "", raising=False)
    monkeypatch.setattr(EmailService, "_client", None)

    assert EmailService.is_available() is False
    assert await EmailService.send_verification_code("user@example.com", "123456") is False


@pytest.mark.asyncio
async def test_sms_service_returns_false_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.core.config import settings

    monkeypatch.setattr(settings, "ALIYUN_ACCESS_KEY_ID", "", raising=False)
    monkeypatch.setattr(settings, "ALIYUN_ACCESS_KEY_SECRET", "", raising=False)
    monkeypatch.setattr(settings, "ALIYUN_SMS_SIGN_NAME", "", raising=False)
    monkeypatch.setattr(SMSService, "_client", None)

    assert SMSService.is_available() is False
    assert await SMSService.send_verification_code("13812345678", "123456") is False


@pytest.mark.asyncio
async def test_compute_router_routes_public_hybrid_and_confidential_requests() -> None:
    router = ComputeRouterService()

    public_prompt, public_recovery = await router.route_request(
        InferenceRequest(prompt="公开问题", sensitivity=SensitivityLevel.PUBLIC)
    )
    assert public_prompt == "公开问题"
    assert public_recovery is None

    hybrid_prompt, hybrid_recovery = await router.route_request(
        InferenceRequest(prompt="联系 13812345678", sensitivity=SensitivityLevel.HYBRID)
    )
    assert "[PHONE_1]" in hybrid_prompt
    assert hybrid_recovery == {"[PHONE_1]": "13812345678"}

    local_result, local_recovery = await router.route_request(
        InferenceRequest(prompt="本地处理", sensitivity=SensitivityLevel.CONFIDENTIAL)
    )
    assert "本地安全模式" in local_result
    assert local_recovery is None


def test_captcha_public_config_is_disabled_when_provider_is_unavailable() -> None:
    assert CaptchaService.is_enabled() is False
    assert CaptchaService.get_public_config() == {
        "captcha_enabled": False,
        "captcha_provider": None,
        "captcha_site_key": None,
    }


@pytest.mark.asyncio
async def test_cache_service_get_client_uses_configured_redis_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.config import settings
    from src.services import cache_service as cache_module

    calls: list[dict[str, Any]] = []

    class FakeRedis:
        pass

    def fake_from_url(url: str, **kwargs: Any) -> FakeRedis:
        calls.append({"url": url, **kwargs})
        return FakeRedis()

    monkeypatch.setattr(settings, "REDIS_URL", "redis://unit-test/0", raising=False)
    monkeypatch.setattr(cache_module.redis, "from_url", fake_from_url)

    client = await CacheService().get_client()

    assert isinstance(client, FakeRedis)
    assert calls == [
        {
            "url": "redis://unit-test/0",
            "encoding": "utf-8",
            "decode_responses": True,
        }
    ]


@pytest.mark.asyncio
async def test_webhook_processing_lock_allows_local_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.config import settings

    monkeypatch.setattr(settings, "WEBHOOK_PROCESSING_LOCK_BACKEND", "local", raising=False)

    async with webhook_processing_lock("unit", "event-1"):
        assert True


@pytest.mark.asyncio
async def test_im_manager_removes_disconnected_socket_after_send_failure() -> None:
    class BrokenWebSocket:
        async def send_json(self, message: dict[str, object]) -> None:
            raise RuntimeError("closed")

    manager = IMConnectionManager()
    socket = BrokenWebSocket()
    manager.active_connections["user-1"] = [socket]  # type: ignore[list-item]

    await manager.send_to_user("user-1", {"type": "ping"})

    assert manager.active_connections == {}
