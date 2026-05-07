from typing import Any

import pytest

from src.services import graph_service as graph_module
from src.services import vector_store as vector_module
from src.services.citation_tracker import Citation, CitationTracker


@pytest.mark.asyncio
async def test_verify_citations_searches_configured_vector_collection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    class FakeVectorStore:
        is_available = True

        async def search(
            self,
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
            return [{"score": 0.82}]

    monkeypatch.setattr(vector_module, "vector_store", FakeVectorStore())

    citations = [
        Citation(
            text="《中华人民共和国民法典》第585条",
            source_type="law",
            source_name="中华人民共和国民法典",
            article="585",
        )
    ]

    verified = await CitationTracker().verify_citations(citations)

    assert calls == [
        {
            "collection_name": "legal_knowledge",
            "query": "《中华人民共和国民法典》第585条",
            "top_k": 1,
        }
    ]
    assert verified[0].verified is True
    assert verified[0].confidence == 0.82


@pytest.mark.asyncio
async def test_sink_to_knowledge_graph_creates_entities_and_relations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    class FakeGraphService:
        async def create_entity(
            self,
            *,
            name: str,
            entity_type: str,
            properties: dict[str, Any],
        ) -> dict[str, Any]:
            calls.append(
                {
                    "kind": "entity",
                    "name": name,
                    "entity_type": entity_type,
                    "properties": properties,
                }
            )
            return {"success": True}

        async def create_relation(
            self,
            subject: str,
            predicate: str,
            obj: str,
            properties: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            calls.append(
                {
                    "kind": "relation",
                    "subject": subject,
                    "predicate": predicate,
                    "obj": obj,
                    "properties": properties,
                }
            )
            return {"success": True}

    monkeypatch.setattr(graph_module, "graph_service", FakeGraphService())

    sunk = await CitationTracker()._sink_to_knowledge_graph(
        [
            Citation("《民法典》第585条", "law", "民法典", article="585", verified=True),
            Citation("《劳动合同法》第10条", "law", "劳动合同法", article="10"),
        ]
    )

    assert sunk == 2
    assert [call["kind"] for call in calls] == ["entity", "entity", "relation"]
    assert calls[-1]["kind"] == "relation"
    assert calls[-1]["predicate"] == "CITED_WITH"
    assert calls[-1]["properties"] is None
    assert {calls[-1]["subject"], calls[-1]["obj"]} == {"民法典", "劳动合同法"}
