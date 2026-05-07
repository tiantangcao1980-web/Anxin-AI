import pytest

from src.core.config import settings
from src.services import oauth_service
from src.services.oauth_service import AlipayOAuth, WeChatMiniProgramOAuth


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload


class _FakeAsyncClient:
    payload: dict[str, object] = {}
    captured: dict[str, object] = {}

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, url: str, params: dict[str, object] | None = None) -> _FakeResponse:
        self.__class__.captured = {"method": "GET", "url": url, "params": params or {}}
        return _FakeResponse(self.__class__.payload)

    async def post(self, url: str, data: dict[str, object] | None = None) -> _FakeResponse:
        self.__class__.captured = {"method": "POST", "url": url, "data": data or {}}
        return _FakeResponse(self.__class__.payload)


@pytest.fixture(autouse=True)
def fake_httpx_client(monkeypatch):
    _FakeAsyncClient.payload = {}
    _FakeAsyncClient.captured = {}
    monkeypatch.setattr(oauth_service.httpx, "AsyncClient", _FakeAsyncClient)


@pytest.mark.asyncio
async def test_wechat_mini_code2session_requires_openid(monkeypatch) -> None:
    monkeypatch.setattr(settings, "WECHAT_MINI_APP_ID", "mini-app")
    monkeypatch.setattr(settings, "WECHAT_MINI_APP_SECRET", "mini-secret")
    _FakeAsyncClient.payload = {"session_key": "session-only"}

    with pytest.raises(ValueError, match="缺少 openid"):
        await WeChatMiniProgramOAuth.code2session("wx-code")

    assert _FakeAsyncClient.captured["method"] == "GET"
    assert _FakeAsyncClient.captured["url"] == WeChatMiniProgramOAuth.CODE2SESSION_URL


@pytest.mark.asyncio
async def test_alipay_oauth_access_token_returns_provider_payload(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ALIPAY_APP_ID", "ali-app")
    _FakeAsyncClient.payload = {
        "alipay_system_oauth_token_response": {
            "access_token": "token-1",
            "user_id": "ali-user-1",
        }
    }

    result = await AlipayOAuth.get_access_token("auth-code-123")

    assert result == {"access_token": "token-1", "user_id": "ali-user-1"}
    assert _FakeAsyncClient.captured["method"] == "POST"
    assert _FakeAsyncClient.captured["url"] == AlipayOAuth.GATEWAY_URL
