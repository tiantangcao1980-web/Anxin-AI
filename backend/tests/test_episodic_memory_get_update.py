# -*- coding: utf-8 -*-
"""
情景记忆「按 ID 查询 (get)」与「更新反馈 (update_feedback)」的最小单元测试。

外部向量库 (Qdrant) 全部通过内存版 mock 模拟，无需真实连接。
mock 以 episode_id -> payload 的方式存储 add_episode 写入的文档，
并让 search() 在「查询文本恰好等于某条 episode_id」时精确返回该条，
从而验证 get() 的精确 ID 匹配语义。
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.memory import EnhancedEpisodicMemoryService


def _make_stateful_vector_store() -> Mock:
    """创建带内存后端的 mock 向量库，记录 add/search/delete 三个操作。"""
    store: dict[str, dict] = {}

    mock = Mock()
    mock.create_collection = AsyncMock(return_value=True)

    async def fake_add_documents(collection_name, documents):
        for doc in documents:
            episode_id = doc["id"]
            # 模拟真实 search() 返回结构：metadata 里带 episode_id 等字段
            store[episode_id] = dict(doc["metadata"])
        return len(documents)

    async def fake_search(collection_name, query, top_k=5, score_threshold=0.6):
        results = []
        for episode_id, meta in store.items():
            # query 精确等于某条 episode_id 时给最高分，其余给较低分
            score = 0.99 if query == episode_id else 0.7
            results.append({"id": episode_id, "metadata": dict(meta), "score": score})
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[: top_k * 2]

    async def fake_delete_documents(collection_name, doc_ids):
        for doc_id in doc_ids:
            store.pop(doc_id, None)
        return True

    mock.add_documents = AsyncMock(side_effect=fake_add_documents)
    mock.search = AsyncMock(side_effect=fake_search)
    mock.delete_documents = AsyncMock(side_effect=fake_delete_documents)
    mock._store = store  # 暴露给测试断言
    return mock


@pytest.fixture
async def episodic():
    """已初始化、带内存向量库的情景记忆服务。"""
    vector_store = _make_stateful_vector_store()
    service = EnhancedEpisodicMemoryService(vector_store, Mock())
    await service.ensure_initialized()

    # update_feedback -> update -> delete() 内部会 new 一个真实 VectorStoreService，
    # 这里 patch 成 mock，让删除作用在同一内存后端上。
    delete_proxy = Mock()
    delete_proxy.delete_documents = vector_store.delete_documents
    with patch(
        "src.services.vector_store.VectorStoreService", return_value=delete_proxy
    ):
        yield service, vector_store


async def _add_one(service: EnhancedEpisodicMemoryService) -> str:
    episode_id = await service.add_episode(
        session_id="sess-1",
        task_description="审查服务合同",
        task_type="contract_review",
        agents_involved=["ContractAgent"],
        execution_trace={"agent_sequence": ["ContractAgent"]},
        result_summary="发现2处风险",
        user_rating=3,
        user_feedback="还行",
    )
    assert episode_id is not None
    return episode_id


class TestEpisodicGet:
    async def test_get_returns_exact_episode(self, episodic):
        service, _ = episodic
        episode_id = await _add_one(service)

        got = await service.get(episode_id)

        assert got is not None
        assert got["episode_id"] == episode_id
        assert got["task_type"] == "contract_review"

    async def test_get_missing_returns_none(self, episodic):
        service, _ = episodic
        await _add_one(service)

        assert await service.get("does-not-exist") is None

    async def test_get_empty_id_returns_none(self, episodic):
        service, _ = episodic
        assert await service.get("") is None


class TestEpisodicUpdateFeedback:
    async def test_update_feedback_persists_new_rating(self, episodic):
        service, vector_store = episodic
        episode_id = await _add_one(service)

        ok = await service.update_feedback(episode_id, user_rating=5, user_feedback="非常准确")
        assert ok is True

        # 旧 ID 被删除并以新 ID 重新插入；按内容应能查到新评分
        stored = list(vector_store._store.values())
        assert len(stored) == 1
        meta = stored[0]
        assert meta["user_rating"] == 5
        assert meta["user_feedback"] == "非常准确"
        assert meta["is_successful"] is True

    async def test_update_feedback_missing_returns_false(self, episodic):
        service, _ = episodic
        ok = await service.update_feedback("no-such-id", user_rating=5)
        assert ok is False
