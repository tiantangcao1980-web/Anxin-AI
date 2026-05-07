from types import SimpleNamespace
from typing import Any

import pytest

from src.core import config as config_module
from src.services import vector_store as vector_module
from src.services.agent_rag_service import AgentRAGService
from src.services.legal_corpus_loader import LegalArticle


def test_keyword_search_uses_loaded_corpus_and_formats_articles() -> None:
    original_corpus = AgentRAGService._corpus
    original_initialized = AgentRAGService._initialized
    try:
        AgentRAGService._corpus = [
            LegalArticle(
                law_name="中华人民共和国民法典",
                law_type="law",
                article_number="第585条",
                title="违约金",
                content="约定的违约金过分高于造成的损失的，可以请求适当减少。",
                tags=["违约金", "调整"],
            )
        ]
        AgentRAGService._initialized = True

        context = AgentRAGService._keyword_search(
            "合同违约金是否可以调整？",
            contract_type=None,
            max_articles=3,
            max_context_length=1000,
        )

        assert "中华人民共和国民法典" in context
        assert "第585条" in context
        assert "违约金" in context
    finally:
        AgentRAGService._corpus = original_corpus
        AgentRAGService._initialized = original_initialized


@pytest.mark.asyncio
async def test_vector_search_filters_results_after_semantic_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    monkeypatch.setattr(
        config_module,
        "get_settings",
        lambda: SimpleNamespace(
            QDRANT_COLLECTION_NAME="legal_articles",
            RAG_SCORE_THRESHOLD=0.75,
        ),
    )

    async def fake_semantic_search(
        *,
        collection_name: str,
        query: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        calls.append(
            {
                "collection_name": collection_name,
                "query": query,
                "top_k": top_k,
            }
        )
        return [
            {
                "score": 0.9,
                "payload": {
                    "source": "Civil Code",
                    "content": "High relevance article",
                },
            },
            {
                "score": 0.2,
                "payload": {
                    "source": "Low Source",
                    "content": "Low relevance article",
                },
            },
        ]

    monkeypatch.setattr(vector_module, "semantic_search", fake_semantic_search)

    context = await AgentRAGService._vector_search(
        "违约金",
        contract_type=None,
        max_articles=5,
        max_context_length=1000,
    )

    assert calls == [
        {
            "collection_name": "legal_articles",
            "query": "违约金",
            "top_k": 5,
        }
    ]
    assert "High relevance article" in context
    assert "Low relevance article" not in context
