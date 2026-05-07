import base64
import hashlib
import json
from urllib.parse import urlparse

import pytest

from src.core.config import settings
from src.services import esign_service
from src.services.esign_service import (
    ESignBaoProvider,
    ESignProviderConfigError,
    FaDaDaProvider,
    FlowStatus,
    MockESignProvider,
    SignerInfo,
    SignType,
    get_esign_provider,
    reset_esign_provider,
)


class _FakeResponse:
    def __init__(self, payload=None, *, status_code=200, content: bytes | None = None):
        self._payload = payload if payload is not None else {}
        self.status_code = status_code
        self.content = content if content is not None else json.dumps(self._payload).encode("utf-8")
        self.text = self.content.decode("utf-8", errors="replace")
        self.headers = {}

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def reset_provider_cache():
    reset_esign_provider()
    yield
    reset_esign_provider()


def test_esign_provider_factory_rejects_mock_in_commercial_environment(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.delenv("ESIGN_PROVIDER", raising=False)

    with pytest.raises(ESignProviderConfigError, match="真实 ESIGN_PROVIDER"):
        get_esign_provider()


def test_esign_provider_factory_rejects_unknown_provider(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setenv("ESIGN_PROVIDER", "typo_provider")

    with pytest.raises(ESignProviderConfigError, match="未知电子签章渠道"):
        get_esign_provider()


def test_esign_provider_factory_allows_mock_in_development(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.delenv("ESIGN_PROVIDER", raising=False)

    assert isinstance(get_esign_provider(), MockESignProvider)


@pytest.mark.asyncio
async def test_esignbao_provider_uses_signed_official_headers(monkeypatch):
    calls = []

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def request(self, method, url, content=None, headers=None):
            calls.append({"method": method, "url": url, "content": content or b"", "headers": headers or {}})
            path = urlparse(url).path
            if path == "/api/v2/signflows/createFlowOneStep":
                return _FakeResponse({"code": 0, "data": {"flowId": "flow-1"}})
            if path == "/v1/signflows/flow-1/start":
                return _FakeResponse({"code": 0, "data": {}})
            if path == "/v1/signflows/flow-1/executeUrl":
                return _FakeResponse({"code": 0, "data": {"url": "https://esign.example/sign"}})
            if path == "/v1/signflows/flow-1":
                return _FakeResponse(
                    {
                        "code": 0,
                        "data": {
                            "flowId": "flow-1",
                            "thirdOrderNo": "contract-1",
                            "flowStatus": "completed",
                            "signers": [{"accountId": "signer-1", "signerName": "张三", "signStatus": "2"}],
                        },
                    }
                )
            if path == "/v1/signflows/flow-1/documents":
                return _FakeResponse({"code": 0, "data": {"downloadUrl": "https://esign.example/download.pdf"}})
            if path == "/v1/signflows/flow-1/revoke":
                return _FakeResponse({"code": 0, "data": {}})
            raise AssertionError(f"unexpected e签宝 URL: {url}")

        async def get(self, url):
            assert url == "https://esign.example/download.pdf"
            return _FakeResponse(content=b"%PDF signed")

    monkeypatch.setattr(esign_service.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(settings, "ESIGN_BAO_APP_ID", "esign-app")
    monkeypatch.setattr(settings, "ESIGN_BAO_APP_SECRET", "esign-secret")
    monkeypatch.setattr(settings, "ESIGN_BAO_API_URL", "https://smlopenapi.esign.cn")

    provider = ESignBaoProvider()
    result = await provider.create_sign_flow(
        contract_id="contract-1",
        title="测试合同",
        signers=[SignerInfo(signer_id="signer-1", name="张三", mobile="13800000000")],
        document_url="file-1",
    )
    status = await provider.get_flow_status("flow-1")
    content = await provider.download_signed_doc("flow-1")
    cancelled = await provider.cancel_flow("flow-1", "撤销")

    assert result.flow_id == "flow-1"
    assert result.sign_urls == {"signer-1": "https://esign.example/sign"}
    assert status.status == FlowStatus.COMPLETED
    assert status.signers_status[0].status.value == "signed"
    assert content == b"%PDF signed"
    assert cancelled is True

    create_call = calls[0]
    assert create_call["method"] == "POST"
    assert create_call["url"] == "https://smlopenapi.esign.cn/api/v2/signflows/createFlowOneStep"
    assert create_call["headers"]["X-Tsign-Open-App-Id"] == "esign-app"
    assert create_call["headers"]["X-Tsign-Open-Auth-Mode"] == "Signature"
    assert create_call["headers"]["X-Tsign-Open-Ca-Signature"]
    assert create_call["headers"]["Content-MD5"] == base64.b64encode(
        hashlib.md5(create_call["content"]).digest()
    ).decode("ascii")
    sign_url_call = next(call for call in calls if "/executeUrl" in call["url"])
    assert "accountId=signer-1" in sign_url_call["url"]
    assert sign_url_call["headers"]["Content-MD5"] == ""


@pytest.mark.asyncio
async def test_fadada_provider_uses_fasc_v51_signed_form_calls(monkeypatch):
    calls = []

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, data=None, headers=None):
            calls.append({"url": url, "data": data, "headers": headers or {}})
            path = urlparse(url).path
            if path.endswith("/service/get-access-token"):
                return _FakeResponse({"code": "100000", "data": {"accessToken": "access-1"}})
            if path.endswith("/sign-task/create"):
                return _FakeResponse({"code": "100000", "data": {"signTaskId": "task-1"}})
            if path.endswith("/sign-task/actor/get-url"):
                return _FakeResponse({"code": "100000", "data": {"actorSignTaskUrl": "https://fadada.example/sign"}})
            if path.endswith("/sign-task/app/get-detail"):
                return _FakeResponse(
                    {
                        "code": "100000",
                        "data": {
                            "signTaskId": "task-1",
                            "transReferenceId": "contract-1",
                            "signTaskStatus": "completed",
                            "actors": [
                                {
                                    "actor": {"actorId": "actor-1", "actorType": "person", "actorName": "李四"},
                                    "actorSignStatus": "signed",
                                }
                            ],
                        },
                    }
                )
            if path.endswith("/sign-task/owner/get-download-url"):
                return _FakeResponse({"code": "100000", "data": {"downloadUrl": "https://fadada.example/file.pdf"}})
            if path.endswith("/sign-task/cancel"):
                return _FakeResponse({"code": "100000", "data": {}})
            raise AssertionError(f"unexpected 法大大 URL: {url}")

        async def get(self, url):
            assert url == "https://fadada.example/file.pdf"
            return _FakeResponse(content=b"%PDF fadada")

    monkeypatch.setattr(esign_service.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(settings, "FADADA_APP_ID", "fadada-app")
    monkeypatch.setattr(settings, "FADADA_APP_SECRET", "fadada-secret")
    monkeypatch.setattr(settings, "FADADA_API_URL", "https://api.fadada.com/api/v5")
    monkeypatch.setattr(settings, "FADADA_ACCESS_TOKEN", None)

    provider = FaDaDaProvider()
    result = await provider.create_sign_flow(
        contract_id="contract-1",
        title="法大大测试合同",
        signers=[SignerInfo(signer_id="actor-1", name="李四", sign_type=SignType.PERSONAL)],
        document_url="doc-1",
    )
    status = await provider.get_flow_status("task-1")
    content = await provider.download_signed_doc("task-1")
    cancelled = await provider.cancel_flow("task-1", "撤销")

    assert result.flow_id == "task-1"
    assert result.sign_urls == {"actor-1": "https://fadada.example/sign"}
    assert status.status == FlowStatus.COMPLETED
    assert status.signers_status[0].status.value == "signed"
    assert content == b"%PDF fadada"
    assert cancelled is True

    token_call = calls[0]
    assert token_call["headers"]["X-FASC-Grant-Type"] == "client_credential"
    assert token_call["headers"]["X-FASC-Sign-Type"] == "HMAC-SHA256"
    assert len(token_call["headers"]["X-FASC-Sign"]) == 64
    create_call = next(call for call in calls if call["url"].endswith("/sign-task/create"))
    assert create_call["headers"]["X-FASC-AccessToken"] == "access-1"
    assert "bizContent" not in create_call["headers"]
    posted_body = json.loads(create_call["data"]["bizContent"])
    assert posted_body["signTaskSubject"] == "法大大测试合同"
    assert posted_body["transReferenceId"] == "contract-1"
