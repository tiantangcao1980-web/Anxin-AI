import base64
import json

import pytest
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Message, Receive, Scope, Send

from src.middleware.client_intel import ClientIntelMiddleware


async def _empty_app(scope: Scope, receive: Receive, send: Send) -> None:
    return None


def _request(headers: dict[str, str] | None = None) -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": raw_headers,
        "client": ("203.0.113.9", 12345),
    }

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive=receive)


async def _ok_response(request: Request) -> Response:
    return Response("ok")


@pytest.mark.asyncio
async def test_client_intel_marks_requests_without_browser_headers() -> None:
    middleware = ClientIntelMiddleware(_empty_app)
    request = _request()

    response = await middleware.dispatch(request, _ok_response)

    assert response.status_code == 200
    assert request.state.intel_result == {
        "risk_score": 5,
        "reasons": ["no_client_headers"],
        "client_id": None,
        "has_bot_signals": False,
    }


@pytest.mark.asyncio
async def test_client_intel_scores_bot_signals_without_redis() -> None:
    middleware = ClientIntelMiddleware(_empty_app)
    signals = base64.b64encode(
        json.dumps(
            {
                "webdriver": True,
                "headlessChrome": True,
                "noPlugins": True,
                "noLanguages": True,
            }
        ).encode("utf-8")
    ).decode("ascii")
    request = _request({"x-bot-signals": signals})

    response = await middleware.dispatch(request, _ok_response)

    assert response.status_code == 200
    assert request.state.intel_result == {
        "risk_score": 40,
        "reasons": [
            "webdriver_detected",
            "headless_chrome",
            "no_plugins_no_languages",
        ],
        "client_id": None,
        "has_bot_signals": True,
    }
