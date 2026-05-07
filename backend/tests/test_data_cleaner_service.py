from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from src.services import data_cleaner as data_cleaner_module
from src.services.data_cleaner import DataCleaner


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self) -> dict[str, Any]:
        return self._payload


def _configure_cleaner(
    monkeypatch: pytest.MonkeyPatch,
    *,
    base_url: str,
    response_payload: dict[str, Any],
) -> tuple[DataCleaner, dict[str, Any]]:
    calls: dict[str, Any] = {}

    monkeypatch.setattr(
        data_cleaner_module,
        "get_llm_config_sync",
        lambda namespace: SimpleNamespace(
            model_name="unit-model",
            api_key="unit-key",
            api_base_url=base_url,
        ),
    )

    class FakeAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            calls["client_args"] = args
            calls["client_kwargs"] = kwargs

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: object | None,
        ) -> None:
            return None

        async def post(
            self,
            url: str,
            *,
            headers: dict[str, str],
            json: dict[str, Any],
        ) -> FakeResponse:
            calls["request"] = {
                "url": url,
                "headers": headers,
                "json": json,
            }
            return FakeResponse(response_payload)

    monkeypatch.setattr(data_cleaner_module.httpx, "AsyncClient", FakeAsyncClient)

    return DataCleaner(), calls


@pytest.mark.asyncio
async def test_clean_html_extracts_openai_compatible_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cleaner, calls = _configure_cleaner(
        monkeypatch,
        base_url="https://llm.example/v1",
        response_payload={
            "choices": [
                {
                    "message": {
                        "content": (
                            "analysis: "
                            '{"court_name": "Court A", "parties": ["Alice", "Bob"], '
                            '"amount": "100", "legal_provisions": ["Civil Code"]}'
                            " done"
                        )
                    }
                }
            ]
        },
    )

    result = await cleaner.clean_html("<html><body>case text</body></html>")

    assert result == {
        "court_name": "Court A",
        "parties": ["Alice", "Bob"],
        "amount": "100",
        "legal_provisions": ["Civil Code"],
    }
    assert calls["client_kwargs"] == {"timeout": 60.0}
    assert calls["request"]["url"] == "https://llm.example/v1/chat/completions"
    assert calls["request"]["headers"]["Authorization"] == "Bearer unit-key"
    assert calls["request"]["json"]["model"] == "unit-model"
    assert calls["request"]["json"]["messages"][0]["role"] == "system"


@pytest.mark.asyncio
async def test_clean_html_extracts_local_output_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cleaner, calls = _configure_cleaner(
        monkeypatch,
        base_url="http://localhost:1234/api/v1/chat",
        response_payload={
            "output": [
                {
                    "type": "message",
                    "content": (
                        "{'court_name': 'Local Court', 'parties': ['One'], "
                        "'amount': null, 'legal_provisions': ['Rule A']}"
                    ),
                }
            ]
        },
    )

    result = await cleaner.clean_html("local model case text")

    assert result == {
        "court_name": "Local Court",
        "parties": ["One"],
        "amount": None,
        "legal_provisions": ["Rule A"],
    }
    assert calls["request"]["url"] == "http://localhost:1234/api/v1/chat"
    assert calls["request"]["json"] == {
        "model": "unit-model",
        "input": calls["request"]["json"]["input"],
        "stream": False,
    }
    assert "local model case text" in calls["request"]["json"]["input"]


@pytest.mark.asyncio
async def test_clean_html_returns_empty_when_uninitialized() -> None:
    cleaner = object.__new__(DataCleaner)
    cleaner._url = ""

    assert await cleaner.clean_html("<html></html>") == {}
