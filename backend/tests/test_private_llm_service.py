import httpx

from src.services.private_llm_service import PrivateLLMService


def test_private_llm_extracts_models_from_known_provider_responses():
    ollama = httpx.Response(200, json={"models": [{"name": "qwen2.5"}]})
    openai_compatible = httpx.Response(200, json={"data": [{"id": "local-model"}]})

    assert PrivateLLMService._extract_models("ollama", ollama) == ["qwen2.5"]
    assert PrivateLLMService._extract_models("lmstudio", openai_compatible) == ["local-model"]


def test_private_llm_recommendations_and_unknown_guide_are_structured():
    service = PrivateLLMService()

    recommendations = service.get_recommended_models()
    guide = service.get_deployment_guide("unknown")

    assert recommendations[0]["provider"] == "ollama"
    assert guide["provider"] == "unknown"
    assert guide["steps"] == []
    assert "不支持的提供商" in guide["error"]
