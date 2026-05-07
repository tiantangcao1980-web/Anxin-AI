from unittest.mock import AsyncMock, patch

import pytest

from src.core.llm_helper import LLMConfigResult
from src.services.llm_service import LLMService


@pytest.fixture(autouse=True)
def reset_llm_config_cache():
    LLMService.invalidate_default_config_cache()
    yield
    LLMService.invalidate_default_config_cache()


def _make_snapshot(model_name: str = "gpt-4o") -> LLMConfigResult:
    return LLMConfigResult(
        provider="openai",
        api_key="sk-test",
        api_base_url="https://api.openai.com/v1",
        model_name=model_name,
        temperature=0.7,
        max_tokens=4096,
        config_id="cfg-1",
        source="db",
        extra_params={"top_p": 1},
    )


@pytest.mark.asyncio
async def test_get_cached_effective_config_hits_db_once_within_ttl():
    snapshot = _make_snapshot()

    with patch.object(
        LLMService,
        "_load_effective_config_snapshot_from_db",
        new=AsyncMock(return_value=snapshot),
    ) as mock_loader:
        first = await LLMService.get_cached_effective_config("llm")
        second = await LLMService.get_cached_effective_config("llm")

    assert first.model_name == "gpt-4o"
    assert second.model_name == "gpt-4o"
    assert first is not second
    assert mock_loader.await_count == 1


@pytest.mark.asyncio
async def test_get_cached_effective_config_returns_deep_copy():
    snapshot = _make_snapshot()

    with patch.object(
        LLMService,
        "_load_effective_config_snapshot_from_db",
        new=AsyncMock(return_value=snapshot),
    ):
        first = await LLMService.get_cached_effective_config("llm")
        first.extra_params["top_p"] = 0.2
        second = await LLMService.get_cached_effective_config("llm")

    assert second.extra_params["top_p"] == 1


@pytest.mark.asyncio
async def test_invalidate_default_config_cache_forces_reload():
    with patch.object(
        LLMService,
        "_load_effective_config_snapshot_from_db",
        new=AsyncMock(side_effect=[_make_snapshot("gpt-4o"), _make_snapshot("gpt-4.1")]),
    ) as mock_loader:
        first = await LLMService.get_cached_effective_config("llm")
        LLMService.invalidate_default_config_cache("llm")
        second = await LLMService.get_cached_effective_config("llm")

    assert first.model_name == "gpt-4o"
    assert second.model_name == "gpt-4.1"
    assert mock_loader.await_count == 2
