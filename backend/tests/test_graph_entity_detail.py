import pytest

from src.services.graph_service import GraphService


@pytest.mark.asyncio
async def test_get_entity_detail_falls_back_to_contains_match_when_exact_name_missing(monkeypatch):
    service = GraphService()
    service.graph = object()

    def fake_query_graph(query: str, params=None):
        name = (params or {}).get("name")
        keyword = (params or {}).get("keyword")

        if "RETURN n.name as name, labels(n) as labels, properties(n) as props" in query:
            if name == "知识产权":
                return []
            if name == "知识产权纠纷":
                return [
                    {
                        "name": "知识产权纠纷",
                        "labels": ["案例"],
                        "props": {"来源": "最高法"},
                    }
                ]
            if keyword == "知识产权":
                return [
                    {
                        "name": "知识产权纠纷",
                        "labels": ["案例"],
                        "props": {"来源": "最高法"},
                    }
                ]

        if "MATCH (n)-[r]->(m) WHERE n.name = $name" in query:
            return [
                {
                    "relation": "REFERENCES",
                    "target": "专利法",
                    "target_labels": ["法规"],
                    "rel_props": {},
                }
            ]

        if "MATCH (m)-[r]->(n) WHERE n.name = $name" in query:
            return [
                {
                    "relation": "CITED_BY",
                    "source": "知识产权保护专题",
                    "source_labels": ["文档"],
                    "rel_props": {},
                }
            ]

        return []

    monkeypatch.setattr(service, "query_graph", fake_query_graph)

    detail = await service.get_entity_detail("知识产权")

    assert detail["name"] == "知识产权纠纷"
    assert detail["type"] == "案例"
    assert detail["properties"] == {"来源": "最高法"}
    assert detail["outEdges"] == [{"target": "专利法", "label": "REFERENCES"}]
    assert detail["inEdges"] == [{"source": "知识产权保护专题", "label": "CITED_BY"}]
    assert detail["entity"]["name"] == "知识产权纠纷"


@pytest.mark.asyncio
async def test_get_entity_detail_returns_empty_payload_when_no_match(monkeypatch):
    service = GraphService()
    service.graph = object()

    monkeypatch.setattr(service, "query_graph", lambda query, params=None: [])

    detail = await service.get_entity_detail("知识产权")

    assert detail == {
        "entity": None,
        "incoming_relations": [],
        "outgoing_relations": [],
    }
