from __future__ import annotations

from typing import Any

import pytest

from src.services import web_search_service as web_search_module
from src.services.web_search_service import WebSearchService


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


@pytest.mark.asyncio
async def test_duckduckgo_search_maps_abstract_and_related_topics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    class FakeAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            calls.append({"client_args": args, "client_kwargs": kwargs})

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: object | None,
        ) -> None:
            return None

        async def get(
            self,
            url: str,
            *,
            params: dict[str, str | int],
            headers: dict[str, str],
        ) -> FakeResponse:
            calls.append({"url": url, "params": params, "headers": headers})
            return FakeResponse(
                {
                    "Heading": "Contract dispute",
                    "Abstract": "Contract case summary",
                    "AbstractURL": "https://example.com/abstract",
                    "RelatedTopics": [
                        {
                            "Text": "Related legal topic",
                            "FirstURL": "https://example.com/topic",
                        },
                        {"Name": "ignored"},
                    ],
                }
            )

    monkeypatch.setattr(web_search_module.httpx, "AsyncClient", FakeAsyncClient)

    results = await WebSearchService()._search_duckduckgo(
        "contract dispute",
        max_results=5,
        search_depth="basic",
        time_range=None,
    )

    assert results == [
        {
            "title": "Contract dispute",
            "snippet": "Contract case summary",
            "url": "https://example.com/abstract",
            "relevance": 0.7,
            "source": "duckduckgo",
        },
        {
            "title": "Related legal topic",
            "snippet": "Related legal topic",
            "url": "https://example.com/topic",
            "relevance": 0.5,
            "source": "duckduckgo",
        },
    ]
    assert calls[0]["client_kwargs"] == {"timeout": 10.0, "follow_redirects": True}
    assert calls[1]["url"] == "https://api.duckduckgo.com/"
    assert calls[1]["params"] == {
        "q": "contract dispute",
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1,
    }
