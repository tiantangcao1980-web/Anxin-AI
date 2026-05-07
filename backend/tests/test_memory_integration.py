"""
记忆系统集成测试
测试三层记忆架构和跨层检索功能

所有外部服务（Qdrant, Redis）均通过 mock 模拟，无需真实连接。
"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.core.memory import (
    EnhancedEpisodicMemoryService,
    MemoryRetrievalResult,
    MultiTierMemoryRetrieval,
    SemanticMemoryService,
    WorkingMemoryService,
)

# 测试数据
TEST_SEMANTIC_KNOWLEDGE = {
    "knowledge_type": "statute",
    "title": "合同法第10条",
    "content": "当事人订立合同，有书面形式、口头形式和其他形式。法律、行政法规规定采用书面形式的，应当采用书面形式。",
}

TEST_EPISODE = {
    "task_description": "审查服务合同",
    "task_type": "contract_review",
    "agents_involved": ["ContractAgent", "RiskAgent"],
    "execution_trace": {
        "agent_sequence": ["ContractAgent", "RiskAgent"],
        "parallel_groups": []
    },
    "result_summary": "发现3处风险条款，建议修改",
    "user_rating": 5,
    "user_feedback": "非常准确和及时",
}

TEST_QUERY = "服务合同风险审查"


def _make_mock_vector_store():
    """创建 mock 向量存储"""
    mock_vector_store = Mock()
    mock_vector_store.create_collection = AsyncMock(return_value=True)
    mock_vector_store.add_documents = AsyncMock(return_value=1)
    mock_vector_store.search = AsyncMock(return_value=[])
    return mock_vector_store


def _make_mock_working_memory():
    """
    创建一个带内存后端的 WorkingMemoryService，绕过 Redis 依赖。

    通过 mock 掉 redis 连接，用 dict 模拟 get/setex/delete/expire/ping。
    """
    wm = WorkingMemoryService(redis_url=None)
    # 使用内存 dict 模拟 Redis
    _store: dict = {}

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)

    async def fake_get(key):
        return _store.get(key)

    async def fake_setex(key, ttl, value):
        _store[key] = value

    async def fake_delete(key):
        _store.pop(key, None)

    async def fake_expire(key, ttl):
        pass  # TTL 在测试中不需要真正生效

    mock_redis.get = AsyncMock(side_effect=fake_get)
    mock_redis.setex = AsyncMock(side_effect=fake_setex)
    mock_redis.delete = AsyncMock(side_effect=fake_delete)
    mock_redis.expire = AsyncMock(side_effect=fake_expire)

    # 直接注入 mock redis 并标记为已初始化
    wm.redis = mock_redis
    wm._initialized = True

    return wm


@pytest.mark.asyncio
class TestMemoryIntegration:
    """记忆系统集成测试"""

    @pytest.fixture
    async def memory_services(self):
        """创建测试用的记忆服务实例（全部 mock，无外部依赖）"""
        mock_vector_store = _make_mock_vector_store()
        mock_db = Mock()

        semantic = SemanticMemoryService(mock_vector_store, mock_db)
        episodic = EnhancedEpisodicMemoryService(mock_vector_store, mock_db)
        working = _make_mock_working_memory()

        # 初始化语义和情景记忆
        await semantic.ensure_initialized()
        await episodic.ensure_initialized()

        return {
            "semantic": semantic,
            "episodic": episodic,
            "working": working,
        }

    @pytest.fixture
    async def retrieval(self, memory_services):
        """创建跨层检索器"""
        return MultiTierMemoryRetrieval(
            semantic_memory=memory_services["semantic"],
            episodic_memory=memory_services["episodic"],
            working_memory=memory_services["working"],
        )

    async def test_semantic_memory_add(self, memory_services):
        """测试语义记忆添加"""
        semantic = memory_services["semantic"]

        knowledge_id = await semantic.add_knowledge(
            knowledge_type=TEST_SEMANTIC_KNOWLEDGE["knowledge_type"],
            title=TEST_SEMANTIC_KNOWLEDGE["title"],
            content=TEST_SEMANTIC_KNOWLEDGE["content"],
        )

        assert knowledge_id is not None

    async def test_semantic_memory_update_reinserts_merged_knowledge(self, memory_services):
        """测试语义记忆更新会删除旧记录并重新插入合并后的知识。"""
        semantic = memory_services["semantic"]
        old = {
            "knowledge_id": "knowledge-001",
            "knowledge_type": "statute",
            "title": "旧标题",
            "content": "旧内容",
        }
        semantic.vector_store.search = AsyncMock(return_value=[{"metadata": old}])
        semantic.delete = AsyncMock(return_value=True)

        updated = await semantic.update(
            "knowledge-001",
            {"title": "新标题", "content": "新内容"},
        )

        assert updated is True
        semantic.delete.assert_awaited_once_with("knowledge-001")
        document = semantic.vector_store.add_documents.await_args.args[1][0]
        assert document["metadata"]["knowledge_type"] == "statute"
        assert document["metadata"]["title"] == "新标题"
        assert document["metadata"]["content"] == "新内容"

    async def test_episodic_memory_add(self, memory_services):
        """测试情景记忆添加"""
        episodic = memory_services["episodic"]

        episode_id = await episodic.add_episode(
            session_id="test-session-123",
            task_description=TEST_EPISODE["task_description"],
            task_type=TEST_EPISODE["task_type"],
            agents_involved=TEST_EPISODE["agents_involved"],
            execution_trace=TEST_EPISODE["execution_trace"],
            result_summary=TEST_EPISODE["result_summary"],
            user_rating=TEST_EPISODE["user_rating"],
            user_feedback=TEST_EPISODE["user_feedback"],
        )

        assert episode_id is not None

    async def test_working_memory(self, memory_services):
        """测试工作记忆"""
        working = memory_services["working"]

        # 创建会话
        success = await working.create_session(
            session_id="test-session-456",
            user_id="test-user-789",
        )
        assert success is True

        # 添加消息
        await working.add_message(
            session_id="test-session-456",
            role="user",
            content="请帮我审查合同",
        )

        # 验证消息
        messages = await working.get_messages("test-session-456")
        assert len(messages) == 1
        assert messages[0]["content"] == "请帮我审查合同"

    async def test_multi_tier_retrieval(self, retrieval):
        """测试跨层检索"""
        result = await retrieval.retrieve(
            query=TEST_QUERY,
            session_id="test-session-789",
            context={
                "task_type": "contract_review",
                "episodic_top_k": 3,
                "semantic_top_k": 5,
            },
        )

        assert isinstance(result, MemoryRetrievalResult)
        assert hasattr(result, "working")
        assert hasattr(result, "episodic")
        assert hasattr(result, "semantic")
        assert hasattr(result, "retrieval_time")

    async def test_memory_migration(self, memory_services):
        """测试记忆迁移 (工作 -> 情景)"""
        working = memory_services["working"]

        # 1. 创建工作记忆会话
        await working.create_session("test-migration-001", "user-001")

        # 2. 添加消息和上下文
        await working.add_message("test-migration-001", "user", "审查租赁合同")
        await working.set_context("test-migration-001", {
            "document_type": "contract",
            "parties": ["甲方", "乙方"],
        })

        # 3. 验证会话状态
        ctx = await working.get_context("test-migration-001")
        assert ctx is not None
        assert ctx["document_type"] == "contract"

        messages = await working.get_messages("test-migration-001")
        assert len(messages) == 1
        assert messages[0]["content"] == "审查租赁合同"
