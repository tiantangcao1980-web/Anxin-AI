"""
性能基准测试
测试系统各组件的响应时间、吞吐量和资源使用
"""

import asyncio
import time
import pytest
from typing import List
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from src.core.memory import (
    SemanticMemoryService,
    EnhancedEpisodicMemoryService,
    WorkingMemoryService,
    MultiTierMemoryRetrieval
)
from src.core.evolution import (
    FeedbackPipeline,
    ExperienceExtractor,
    PolicyOptimizer
)
from src.services.cache_service import CacheService


# ========== 性能指标 ==========


class PerformanceMetrics:
    """性能指标收集器"""

    def __init__(self, name: str):
        self.name = name
        self.durations: List[float] = []
        self.success_count = 0
        self.error_count = 0

    def record(self, duration: float, success: bool = True):
        """记录一次操作"""
        self.durations.append(duration)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1

    def get_stats(self) -> dict:
        """获取统计信息"""
        if not self.durations:
            return {
                "name": self.name,
                "count": 0,
                "avg": 0,
                "min": 0,
                "max": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0,
                "success_rate": 0
            }

        sorted_durations = sorted(self.durations)
        count = len(self.durations)

        return {
            "name": self.name,
            "count": count,
            "avg": sum(self.durations) / count,
            "min": sorted_durations[0],
            "max": sorted_durations[-1],
            "p50": sorted_durations[int(count * 0.5)],
            "p95": sorted_durations[int(count * 0.95)],
            "p99": sorted_durations[int(count * 0.99)],
            "success_rate": self.success_count / count if count > 0 else 0
        }


def measure_performance(metrics: PerformanceMetrics):
    """性能测量装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                metrics.record(duration, success=True)
                return result
            except Exception as e:
                duration = time.time() - start
                metrics.record(duration, success=False)
                raise e
        return wrapper
    return decorator


# ========== 缓存性能测试 ==========


@pytest.mark.asyncio
class TestCachePerformance:
    """缓存性能测试"""

    @pytest.fixture
    async def cache_service(self):
        """创建缓存服务"""
        cache = CacheService(enable_l1=True, enable_l2=False)  # 禁用L2避免依赖
        return cache

    async def test_cache_write_performance(self, cache_service):
        """测试缓存写入性能"""
        metrics = PerformanceMetrics("cache_write")

        # 执行100次写入
        for i in range(100):
            @measure_performance(metrics)
            async def write_op():
                await cache_service.set(
                    "test",
                    f"key-{i}",
                    {"data": f"value-{i}"},
                    ttl=60
                )
            await write_op()

        stats = metrics.get_stats()
        print(f"\n📊 缓存写入性能:")
        print(f"  平均: {stats['avg']*1000:.2f}ms")
        print(f"  P95: {stats['p95']*1000:.2f}ms")
        print(f"  P99: {stats['p99']*1000:.2f}ms")

        # 断言：本地开发机上的内存缓存写入应保持在 10ms 以内
        assert stats['avg'] < 0.01
        print("  ✅ 写入性能测试通过")

    async def test_cache_read_performance(self, cache_service):
        """测试缓存读取性能"""
        # 先写入一些数据
        for i in range(100):
            await cache_service.set("test", f"key-{i}", {"data": f"value-{i}"})

        metrics = PerformanceMetrics("cache_read")

        # 执行100次读取
        for i in range(100):
            @measure_performance(metrics)
            async def read_op():
                await cache_service.get("test", f"key-{i}")
            await read_op()

        stats = metrics.get_stats()
        print(f"\n📊 缓存读取性能:")
        print(f"  平均: {stats['avg']*1000:.2f}ms")
        print(f"  P95: {stats['p95']*1000:.2f}ms")
        print(f"  P99: {stats['p99']*1000:.2f}ms")

        # 断言：本地开发机上的 L1 读取应保持在 5ms 以内
        assert stats['avg'] < 0.005
        print("  ✅ 读取性能测试通过")


# ========== 记忆系统性能测试 ==========


@pytest.mark.asyncio
class TestMemoryPerformance:
    """记忆系统性能测试"""

    async def test_semantic_memory_add_performance(self):
        """测试语义记忆添加性能"""
        mock_vector_store = Mock()
        mock_vector_store.add_documents = AsyncMock(return_value=100)

        semantic = SemanticMemoryService(mock_vector_store, Mock())

        metrics = PerformanceMetrics("semantic_add")

        # 添加100条知识
        for i in range(100):
            @measure_performance(metrics)
            async def add_op():
                await semantic.add_knowledge(
                    knowledge_type="statute",
                    title=f"测试法律条文 {i}",
                    content=f"这是第 {i} 条测试法律内容"
                )
            await add_op()

        stats = metrics.get_stats()
        print(f"\n📊 语义记忆添加性能:")
        print(f"  平均: {stats['avg']*1000:.2f}ms")
        print(f"  P95: {stats['p95']*1000:.2f}ms")

        # 断言：平均添加时间应该 < 100ms
        assert stats['avg'] < 0.1
        print("  ✅ 语义记忆添加性能测试通过")

    async def test_episodic_memory_add_performance(self):
        """测试情景记忆添加性能"""
        mock_vector_store = Mock()
        mock_vector_store.add_documents = AsyncMock(return_value=1)

        episodic = EnhancedEpisodicMemoryService(mock_vector_store, Mock())

        metrics = PerformanceMetrics("episodic_add")

        # 添加100条情景
        for i in range(100):
            @measure_performance(metrics)
            async def add_op():
                await episodic.add_episode(
                    session_id=f"session-{i}",
                    task_description=f"测试任务 {i}",
                    task_type="test",
                    agents_involved=["TestAgent"],
                    execution_trace={"agent_sequence": ["TestAgent"]},
                    result_summary="测试结果",
                    user_rating=5
                )
            await add_op()

        stats = metrics.get_stats()
        print(f"\n📊 情景记忆添加性能:")
        print(f"  平均: {stats['avg']*1000:.2f}ms")
        print(f"  P95: {stats['p95']*1000:.2f}ms")

        # 断言：平均添加时间应该 < 150ms
        assert stats['avg'] < 0.15
        print("  ✅ 情景记忆添加性能测试通过")

    async def test_multi_tier_retrieval_performance(self):
        """测试跨层检索性能"""
        mock_vector_store = Mock()
        mock_vector_store.search = AsyncMock(return_value=[])

        mock_db = Mock()

        semantic = SemanticMemoryService(mock_vector_store, mock_db)
        episodic = EnhancedEpisodicMemoryService(mock_vector_store, mock_db)
        working = WorkingMemoryService(redis_url="redis://localhost:6379/1")

        retrieval = MultiTierMemoryRetrieval(
            semantic_memory=semantic,
            episodic_memory=episodic,
            working_memory=working
        )

        metrics = PerformanceMetrics("multi_tier_retrieval")

        # 执行100次检索
        for i in range(100):
            @measure_performance(metrics)
            async def retrieve_op():
                await retrieval.retrieve(
                    query=f"测试查询 {i}",
                    session_id=f"session-{i}",
                    context={"task_type": "test"}
                )
            await retrieve_op()

        stats = metrics.get_stats()
        print(f"\n📊 跨层检索性能:")
        print(f"  平均: {stats['avg']*1000:.2f}ms")
        print(f"  P95: {stats['p95']*1000:.2f}ms")
        print(f"  P99: {stats['p99']*1000:.2f}ms")

        # 断言：平均检索时间应该 < 200ms
        assert stats['avg'] < 0.2
        print("  ✅ 跨层检索性能测试通过")


# ========== 进化系统性能测试 ==========


@pytest.mark.asyncio
class TestEvolutionPerformance:
    """进化系统性能测试"""

    async def test_feedback_submit_performance(self):
        """测试反馈提交性能"""
        mock_db = Mock()
        mock_episodic = Mock()
        mock_episodic.update_rating = AsyncMock(return_value=True)

        feedback_pipeline = FeedbackPipeline(mock_db, mock_episodic)

        metrics = PerformanceMetrics("feedback_submit")

        # 提交100条反馈
        for i in range(100):
            @measure_performance(metrics)
            async def submit_op():
                from src.core.evolution import UserFeedback
                feedback = UserFeedback(
                    episode_id=f"episode-{i}",
                    rating=5,
                    comment="测试反馈"
                )
                await feedback_pipeline.submit_feedback(feedback)
            await submit_op()

        stats = metrics.get_stats()
        print(f"\n📊 反馈提交性能:")
        print(f"  平均: {stats['avg']*1000:.2f}ms")
        print(f"  P95: {stats['p95']*1000:.2f}ms")

        # 断言：平均提交时间应该 < 50ms
        assert stats['avg'] < 0.05
        print("  ✅ 反馈提交性能测试通过")

    async def test_pattern_extraction_performance(self):
        """测试模式提取性能"""
        mock_db = Mock()
        mock_vector_store = Mock()

        extractor = ExperienceExtractor(mock_db, mock_vector_store)

        # Mock 数据库查询
        mock_db.query = Mock()
        mock_db.filter = Mock()
        mock_db.all = Mock(
            return_value=[
                {
                    "episode_id": f"ep-{i}",
                    "task_type": "test",
                    "agents_involved": ["AgentA", "AgentB"],
                    "execution_trace": {"agent_sequence": ["AgentA", "AgentB"]},
                    "user_rating": 5
                }
                for i in range(50)
            ]
        )

        metrics = PerformanceMetrics("pattern_extraction")

        # 提取50次
        for _ in range(50):
            @measure_performance(metrics)
            async def extract_op():
                await extractor.extract_from_success_cases(
                    task_type="test",
                    min_rating=4
                )
            await extract_op()

        stats = metrics.get_stats()
        print(f"\n📊 模式提取性能:")
        print(f"  平均: {stats['avg']*1000:.2f}ms")
        print(f"  P95: {stats['p95']*1000:.2f}ms")

        # 断言：平均提取时间应该 < 100ms
        assert stats['avg'] < 0.1
        print("  ✅ 模式提取性能测试通过")

    async def test_policy_optimization_performance(self):
        """测试策略优化性能"""
        mock_db = Mock()
        mock_vector_store = Mock()
        mock_vector_store.search = AsyncMock(
            return_value=[
                {
                    "agents_involved": ["AgentA", "AgentB"],
                    "user_rating": 5,
                    "similarity_score": 0.9
                }
            ]
        )

        optimizer = PolicyOptimizer(mock_db, mock_vector_store)

        metrics = PerformanceMetrics("policy_optimization")

        # 优化50次
        for i in range(50):
            @measure_performance(metrics)
            async def optimize_op():
                await optimizer.optimize_agent_selection(
                    task_description=f"测试任务 {i}",
                    task_type="test"
                )
            await optimize_op()

        stats = metrics.get_stats()
        print(f"\n📊 策略优化性能:")
        print(f"  平均: {stats['avg']*1000:.2f}ms")
        print(f"  P95: {stats['p95']*1000:.2f}ms")

        # 断言：平均优化时间应该 < 150ms
        assert stats['avg'] < 0.15
        print("  ✅ 策略优化性能测试通过")


# ========== 压力测试 ==========


@pytest.mark.asyncio
class TestStress:
    """压力测试"""

    async def test_concurrent_memory_operations(self):
        """测试并发记忆操作"""
        mock_vector_store = Mock()
        mock_vector_store.add_documents = AsyncMock(return_value=1)

        episodic = EnhancedEpisodicMemoryService(mock_vector_store, Mock())

        metrics = PerformanceMetrics("concurrent_operations")

        # 并发添加1000条情景
        tasks = []
        for i in range(1000):
            @measure_performance(metrics)
            async def add_op(idx=i):
                await episodic.add_episode(
                    session_id=f"session-{idx}",
                    task_description=f"测试任务 {idx}",
                    task_type="stress_test",
                    agents_involved=["TestAgent"],
                    execution_trace={"agent_sequence": ["TestAgent"]},
                    result_summary="测试结果",
                    user_rating=5
                )
            tasks.append(add_op())

        start = time.time()
        await asyncio.gather(*tasks)
        total_time = time.time() - start

        stats = metrics.get_stats()
        print(f"\n📊 并发操作压力测试:")
        print(f"  总耗时: {total_time:.2f}s")
        print(f"  吞吐量: {1000/total_time:.2f} ops/s")
        print(f"  平均响应: {stats['avg']*1000:.2f}ms")

        # 断言：吞吐量应该 > 100 ops/s
        assert 1000 / total_time > 100
        print("  ✅ 并发操作压力测试通过")


# 运行基准测试
async def run_benchmarks():
    """运行所有基准测试"""
    print("=" * 60)
    print("🚀 开始性能基准测试")
    print("=" * 60)

    # 这里可以运行各类测试
    print("\n📋 测试列表:")
    print("  1. 缓存性能测试")
    print("  2. 记忆系统性能测试")
    print("  3. 进化系统性能测试")
    print("  4. 压力测试")

    print("\n" + "=" * 60)
    print("✅ 基准测试配置完成")
    print("  使用 pytest 运行完整测试:")
    print("  pytest tests/test_performance_benchmark.py -v")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
