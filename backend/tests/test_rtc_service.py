import pytest

from src.core.config import settings
from src.services.rtc_service import RTCService


@pytest.mark.asyncio
async def test_rtc_service_is_unavailable_without_livekit_config(monkeypatch):
    monkeypatch.setattr(settings, "LIVEKIT_URL", "")
    monkeypatch.setattr(settings, "LIVEKIT_API_KEY", "")
    monkeypatch.setattr(settings, "LIVEKIT_API_SECRET", "")
    RTCService._api = None

    assert RTCService.is_available() is False
    assert RTCService.generate_token("room", "user", "User") is None
    assert await RTCService.create_room("room") is None
    assert await RTCService.delete_room("room") is False
    assert await RTCService.list_rooms() == []
