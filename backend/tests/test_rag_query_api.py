# -*- coding: utf-8 -*-
"""P13-C: rag_query 路由 API 测试。

⚠️ 设计说明：
v3/main 当前主 app 在 P6 fetch / P4 app_authorization 的 import 链上有
**预先存在**的损坏（``TierName`` / ``OAuthError`` 未导出），导致
``src.api.main:app`` 无法启动。
因此本测试用 **隔离 FastAPI app + 路由 mount + dep override** 直接挂载
P13-C 的 router，独立验证 3 endpoint 的契约。

覆盖：

    POST /api/v1/rag/query/multimodal
    POST /api/v1/rag/query/text-only
    GET  /api/v1/rag/query/health
"""

from __future__ import annotations

import sys
import types
import uuid
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")  # type: ignore[misc]
def _compile_jsonb_for_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


# 与 persona 测试相同：在 import 主路由前 stub 掉 fetch（pre-existing 损坏）
if "src.api.routes.fetch" not in sys.modules:
    _fetch_stub = types.ModuleType("src.api.routes.fetch")
    _fetch_stub.router = APIRouter()
    sys.modules["src.api.routes.fetch"] = _fetch_stub


from src.api.routes import rag_query as rag_query_route  # noqa: E402
from src.core.deps import get_current_user_required  # noqa: E402
from src.services.rag.query import (  # noqa: E402
    Modality,
    MultimodalRetriever,
    RetrievedSegment,
    VLMQueryEngine,
)


BASE = "/api/v1/rag/query"


# ============ stubs ============


class StubVectorSearcher:
    def __init__(self, segments):
        self.segments = list(segments)

    async def search(self, *, query, top_k, document_ids):
        return list(self.segments)


class StubVLMClient:
    def __init__(self, *, supports_vision: bool = True):
        self._supports_vision = supports_vision
        self.calls: list[dict] = []

    @property
    def supports_vision(self) -> bool:
        return self._supports_vision

    async def chat_with_vision(self, *, system_prompt, user_text, images, language):
        self.calls.append({"images": images, "language": language})
        return {
            "answer": "合同条款约定金额为 100 元 [seg:t1]，并已盖章 [seg:seal1]",
            "mentioned_segment_ids": ["seal1"],
            "confidence": 0.85,
            "tokens": 1500,
        }


def _build_engine(*, with_vision: bool = True) -> tuple[VLMQueryEngine, StubVLMClient]:
    segs = [
        RetrievedSegment(
            segment_id="t1",
            document_id="docA",
            modality=Modality.TEXT,
            content="合同总价为 100 元",
            score=0.9,
            page=1,
            char_range=(0, 12),
            metadata={"document_name": "合同 A.pdf"},
        ),
        RetrievedSegment(
            segment_id="seal1",
            document_id="docA",
            modality=Modality.SEAL,
            content=b"\x89PNG\r\n\x1a\n",
            score=0.6,
            page=2,
            metadata={"document_name": "合同 A.pdf", "caption": "甲方公章"},
        ),
    ]
    retriever = MultimodalRetriever(vector_searcher=StubVectorSearcher(segs))
    vlm = StubVLMClient(supports_vision=with_vision)
    engine = VLMQueryEngine(retriever=retriever, vlm_client=vlm)
    return engine, vlm


# ============ fixtures ============


@pytest_asyncio.fixture
async def client_factory():
    """返回一个 (engine_setter) → AsyncClient 的工厂，便于每个测试独立注入引擎。"""

    async def _build(engine: VLMQueryEngine | None):
        app = FastAPI()
        app.include_router(rag_query_route.router, prefix="/api/v1/rag/query")

        fake_user = SimpleNamespace(
            id=uuid.uuid4(),
            email="rag@anxin.cn",
            role="user",
            organization_id=None,
        )

        async def _fake_user():
            return fake_user

        app.dependency_overrides[get_current_user_required] = _fake_user
        rag_query_route.set_query_engine(engine)

        transport = ASGITransport(app=app)
        client = AsyncClient(transport=transport, base_url="http://test")
        return app, client

    yield _build
    rag_query_route.set_query_engine(None)


# ============ tests ============


@pytest.mark.asyncio
async def test_multimodal_endpoint_returns_answer_with_visual_grounding(client_factory):
    engine, vlm = _build_engine(with_vision=True)
    app, client = await client_factory(engine)
    try:
        async with client:
            res = await client.post(
                f"{BASE}/multimodal",
                json={
                    "query": "合同上的公章是否清晰",
                    "top_k": 5,
                    "enable_vlm": True,
                },
            )
        assert res.status_code == 200, res.text
        data = res.json()
        assert "公章" in data["answer"] or "盖章" in data["answer"]
        assert data["vlm_used"] is True
        # visual_grounding 命中 seal1
        ids = [vg["segment_id"] for vg in data["visual_grounding"]]
        assert ids == ["seal1"]
        # citations 至少 2 条
        assert len(data["citations"]) >= 2
        # confidence ∈ [0, 1]
        assert 0.0 <= data["confidence"] <= 1.0
        # vlm 真的被调
        assert len(vlm.calls) == 1
        # 图被序列化为 base64
        assert any("base64" in img for img in vlm.calls[0]["images"])
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_text_only_endpoint_skips_vlm(client_factory):
    engine, vlm = _build_engine(with_vision=True)
    app, client = await client_factory(engine)
    try:
        async with client:
            res = await client.post(
                f"{BASE}/text-only",
                json={"query": "合同总价是多少", "top_k": 5, "enable_vlm": True},
            )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["vlm_used"] is False
        # text-only 路径下 vlm 不应被调用
        assert vlm.calls == []
        # 仍有 citations
        assert len(data["citations"]) >= 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_when_engine_missing(client_factory):
    app, client = await client_factory(None)  # 不注入
    try:
        async with client:
            res = await client.get(f"{BASE}/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "unavailable"
        assert data["vlm_available"] is False
        assert any("未注入" in n for n in data["notes"])
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_with_vision_capable_engine(client_factory):
    engine, _ = _build_engine(with_vision=True)
    app, client = await client_factory(engine)
    try:
        async with client:
            res = await client.get(f"{BASE}/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["vlm_available"] is True
        assert data["vlm_supports_vision"] is True
        assert "vector_searcher" in data["retriever"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_degraded_without_vision(client_factory):
    engine, _ = _build_engine(with_vision=False)
    app, client = await client_factory(engine)
    try:
        async with client:
            res = await client.get(f"{BASE}/health")
        data = res.json()
        assert data["status"] == "degraded"
        assert data["vlm_supports_vision"] is False
        assert any("不支持 vision" in n for n in data["notes"])
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_multimodal_503_when_engine_missing(client_factory):
    app, client = await client_factory(None)
    try:
        async with client:
            res = await client.post(
                f"{BASE}/multimodal",
                json={"query": "test", "top_k": 5},
            )
        assert res.status_code == 503
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_multimodal_validation_rejects_empty_query(client_factory):
    engine, _ = _build_engine(with_vision=True)
    app, client = await client_factory(engine)
    try:
        async with client:
            res = await client.post(
                f"{BASE}/multimodal",
                json={"query": "", "top_k": 5},
            )
        assert res.status_code == 422  # pydantic validation
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_multimodal_modality_weights_passthrough(client_factory):
    """显式 modality_weights 不应让请求 500，且最终 citations 反映重排。"""
    engine, _ = _build_engine(with_vision=True)
    app, client = await client_factory(engine)
    try:
        async with client:
            res = await client.post(
                f"{BASE}/multimodal",
                json={
                    "query": "合同条款 + 印鉴",
                    "top_k": 5,
                    "modality_weights": {"seal": 1.5, "text": 0.1},
                    "enable_vlm": False,  # 走文本降级，便于稳定断言
                },
            )
        assert res.status_code == 200, res.text
        data = res.json()
        # seal 权重最高 → 排第一
        assert data["citations"][0]["modality"] == "seal"
    finally:
        app.dependency_overrides.clear()
