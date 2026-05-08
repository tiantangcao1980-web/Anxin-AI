from uuid import uuid4

import pytest

from src.models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeType
from src.models.user import Organization
from src.services import knowledge_service as knowledge_service_module
from src.services.citation_tracker import citation_tracker
from src.services.knowledge_service import KnowledgeService
from src.services.pii_service import pii_service
from src.services.rag_service import rag_service
from src.services.reranker_service import RerankResult

SENSITIVE_TEXT = "联系人手机号13812345678，身份证11010119900101123X，邮箱zhang.san@example.com。"


def test_scrub_for_output_masks_phone_id_card_and_email():
    payload = {
        "content": SENSITIVE_TEXT,
        "sources": [{"email": "reviewer@example.com", "phone": "13900001111"}],
    }

    scrubbed = pii_service.scrub_for_output(payload)
    rendered = str(scrubbed)

    assert "13812345678" not in rendered
    assert "11010119900101123X" not in rendered
    assert "zhang.san@example.com" not in rendered
    assert "reviewer@example.com" not in rendered
    assert "13900001111" not in rendered
    assert "138****5678" in rendered
    assert "110101********123X" in rendered
    assert "z***@example.com" in rendered
    assert "r***@example.com" in rendered
    assert "139****1111" in rendered


def test_citation_tracker_masks_pii_in_returned_graph_fields():
    citations = citation_tracker.extract_citations("依据《客户13812345678管理规定》第12条处理。")

    citation_payload = citations[0].to_dict()
    graph = citation_tracker.build_citation_graph(citations)
    rendered = str({"citation": citation_payload, "graph": graph})

    assert "13812345678" not in rendered
    assert "138****5678" in rendered


def test_rag_context_sources_include_clickable_chunk_location_fields():
    context = rag_service.build_context(
        "合同是否成立",
        [
            RerankResult(
                id="civil_code_490",
                content="当事人采用合同书形式订立合同的，自当事人均签名时合同成立。",
                original_score=0.9,
                rerank_score=0.9,
                final_score=0.9,
                metadata={
                    "doc_id": "civil_code_490",
                    "chunk_id": "civil_code_490_0",
                    "title": "《民法典》第490条",
                    "source": "民法典",
                    "source_url": "/knowledge/documents/civil_code_490#civil_code_490_0",
                    "start_index": 12,
                    "end_index": 46,
                },
            )
        ],
    )

    source = context.sources[0]

    assert source["doc_id"] == "civil_code_490"
    assert source["chunk_id"] == "civil_code_490_0"
    assert source["source_url"].endswith("#civil_code_490_0")
    assert source["anchor_text"].startswith("当事人采用合同书形式")
    assert source["chunk_start"] == 12
    assert source["chunk_end"] == 46


async def _create_foreign_org(db_session) -> Organization:
    org = Organization(id=str(uuid4()), name=f"外部组织-{uuid4().hex[:6]}")
    db_session.add(org)
    await db_session.flush()
    return org


def _knowledge_base(
    *,
    name: str,
    org_id: str,
    created_by: str | None = None,
    is_public: bool = False,
    collection: str | None = None,
) -> KnowledgeBase:
    return KnowledgeBase(
        id=str(uuid4()),
        name=name,
        knowledge_type=KnowledgeType.OTHER,
        description=name,
        org_id=org_id,
        created_by=created_by,
        is_public=is_public,
        doc_count=1,
        vector_collection=collection or f"kb_{uuid4().hex[:8]}",
    )


@pytest.mark.asyncio
async def test_search_filters_inaccessible_kbs_before_vector_search_and_redacts(
    db_session,
    monkeypatch,
    test_user,
):
    foreign_org = await _create_foreign_org(db_session)
    allowed_kb = _knowledge_base(
        name="本组织知识库",
        org_id=test_user.org_id,
        created_by=test_user.id,
        collection="kb_allowed",
    )
    foreign_kb = _knowledge_base(
        name="外部私有知识库",
        org_id=foreign_org.id,
        collection="kb_foreign",
    )
    db_session.add_all([allowed_kb, foreign_kb])
    await db_session.flush()

    calls = []

    async def fake_search(collection_name, query, top_k, **kwargs):
        calls.append(collection_name)
        return [
            {
                "id": "doc-allowed",
                "title": "合同联系人13900001111",
                "content": SENSITIVE_TEXT,
                "source": "owner@example.com",
                "score": 0.91,
                "metadata": {"reviewer": "reviewer@example.com"},
            }
        ]

    monkeypatch.setattr(knowledge_service_module.vector_store, "search", fake_search)

    service = KnowledgeService(db_session)
    results = await service.search(
        "劳动合同",
        kb_ids=[allowed_kb.id, foreign_kb.id],
        top_k=5,
        user_id=test_user.id,
        org_id=test_user.org_id,
    )

    assert calls == ["kb_allowed"]
    rendered = str(results)
    assert "doc-allowed" in rendered
    assert "13812345678" not in rendered
    assert "11010119900101123X" not in rendered
    assert "owner@example.com" not in rendered
    assert "reviewer@example.com" not in rendered
    assert "138****5678" in rendered
    assert "110101********123X" in rendered
    assert "o***@example.com" in rendered
    assert "r***@example.com" in rendered


@pytest.mark.asyncio
async def test_search_without_kb_ids_uses_accessible_kbs_not_global_collection(
    db_session,
    monkeypatch,
    test_user,
):
    allowed_kb = _knowledge_base(
        name="默认可访问知识库",
        org_id=test_user.org_id,
        created_by=test_user.id,
        collection="kb_default_allowed",
    )
    db_session.add(allowed_kb)
    await db_session.flush()

    calls = []

    async def fake_search(collection_name, query, top_k, **kwargs):
        calls.append(collection_name)
        return [{"id": "doc-default", "title": "默认", "content": "ok", "score": 0.8}]

    monkeypatch.setattr(knowledge_service_module.vector_store, "search", fake_search)

    service = KnowledgeService(db_session)
    results = await service.search(
        "默认检索",
        kb_ids=None,
        top_k=5,
        user_id=test_user.id,
        org_id=test_user.org_id,
    )

    assert calls == ["kb_default_allowed"]
    assert results[0]["id"] == "doc-default"


@pytest.mark.asyncio
async def test_hybrid_keyword_search_filters_to_accessible_kbs_and_redacts(
    db_session,
    monkeypatch,
    test_user,
):
    foreign_org = await _create_foreign_org(db_session)
    allowed_kb = _knowledge_base(
        name="可访问关键词库",
        org_id=test_user.org_id,
        created_by=test_user.id,
        collection="kb_keyword_allowed",
    )
    foreign_kb = _knowledge_base(
        name="外部关键词库",
        org_id=foreign_org.id,
        collection="kb_keyword_foreign",
    )
    allowed_doc = KnowledgeDocument(
        id=str(uuid4()),
        knowledge_base_id=allowed_kb.id,
        title="劳动合同联系人13812345678",
        content=f"劳动合同关键词。{SENSITIVE_TEXT}",
        source="allowed@example.com",
        is_processed=True,
    )
    foreign_doc = KnowledgeDocument(
        id=str(uuid4()),
        knowledge_base_id=foreign_kb.id,
        title="劳动合同外部文件",
        content="劳动合同关键词。外部组织专属内容。",
        source="foreign@example.com",
        is_processed=True,
    )
    db_session.add_all([allowed_kb, foreign_kb, allowed_doc, foreign_doc])
    await db_session.flush()

    async def fake_search(*args, **kwargs):
        return []

    monkeypatch.setattr(knowledge_service_module.vector_store, "search", fake_search)

    service = KnowledgeService(db_session)
    results = await service.hybrid_search(
        "劳动合同",
        kb_ids=None,
        top_k=5,
        user_id=test_user.id,
        org_id=test_user.org_id,
    )

    rendered = str(results)
    assert str(allowed_doc.id) in rendered
    assert str(foreign_doc.id) not in rendered
    assert "外部组织专属内容" not in rendered
    assert "13812345678" not in rendered
    assert "allowed@example.com" not in rendered
    assert "138****5678" in rendered
    assert "a***@example.com" in rendered


@pytest.mark.asyncio
async def test_rag_query_filters_collections_and_redacts_nested_response(
    db_session,
    monkeypatch,
    test_user,
):
    foreign_org = await _create_foreign_org(db_session)
    allowed_kb = _knowledge_base(
        name="RAG 可访问库",
        org_id=test_user.org_id,
        created_by=test_user.id,
        collection="kb_rag_allowed",
    )
    foreign_kb = _knowledge_base(
        name="RAG 外部库",
        org_id=foreign_org.id,
        collection="kb_rag_foreign",
    )
    db_session.add_all([allowed_kb, foreign_kb])
    await db_session.flush()

    calls = []

    class FakeRAGResponse:
        def to_dict(self):
            return {
                "answer": f"建议联系：{SENSITIVE_TEXT}",
                "sources": [
                    {
                        "id": "chunk-1",
                        "title": "来源联系人13900001111",
                        "content_snippet": SENSITIVE_TEXT,
                        "source": "source@example.com",
                    }
                ],
                "confidence": 0.82,
            }

    async def fake_rag_query(query, collection_names, system_prompt=None, **kwargs):
        calls.append(collection_names)
        return FakeRAGResponse()

    monkeypatch.setattr(knowledge_service_module.rag_service, "query", fake_rag_query)

    service = KnowledgeService(db_session)
    result = await service.rag_query(
        "劳动合同",
        kb_ids=[allowed_kb.id, foreign_kb.id],
        user_id=test_user.id,
        org_id=test_user.org_id,
    )

    assert calls == [["kb_rag_allowed"]]
    rendered = str(result)
    assert "13812345678" not in rendered
    assert "11010119900101123X" not in rendered
    assert "zhang.san@example.com" not in rendered
    assert "source@example.com" not in rendered
    assert "13900001111" not in rendered
    assert "138****5678" in rendered
    assert "110101********123X" in rendered
    assert "z***@example.com" in rendered
    assert "s***@example.com" in rendered
    assert "139****1111" in rendered
