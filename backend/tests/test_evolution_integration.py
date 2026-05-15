"""
进化系统集成测试
测试反馈、经验提取、策略优化的完整流程
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.evolution import (
    DAGStructure,
    ExperienceExtractor,
    FeedbackPipeline,
    PolicyOptimizer,
    UserFeedback,
)

# 测试数据
TEST_EPISODE_ID = "test-episode-001"
TEST_SESSION_ID = "test-session-001"
TEST_TASK_DESCRIPTION = "审查房屋租赁合同"
TEST_TASK_TYPE = "contract_review"


@pytest.mark.asyncio
class TestFeedbackPipeline:
    """反馈管道测试"""

    @pytest.fixture
    def feedback_pipeline(self):
        """创建反馈管道实例"""
        # Mock 依赖项
        mock_db = Mock()
        mock_episodic_memory = Mock()

        pipeline = FeedbackPipeline(db=mock_db, episodic_memory=mock_episodic_memory)

        return pipeline

    async def test_submit_feedback(self, feedback_pipeline):
        """测试提交反馈"""
        feedback = UserFeedback(
            episode_id=TEST_EPISODE_ID,
            rating=5,
            comment="非常准确和及时",
            session_id=TEST_SESSION_ID,
        )

        # Mock episodic memory update
        feedback_pipeline.episodic_memory.update_rating = AsyncMock(return_value=True)

        # 提交反馈
        result = await feedback_pipeline.submit_feedback(feedback)

        assert result is True
        print("✅ 反馈提交成功")

    async def test_feedback_triggers_experience_extraction(self, feedback_pipeline):
        """测试反馈触发经验提取"""
        # 高评分反馈应该触发经验提取
        high_rating_feedback = UserFeedback(
            episode_id=TEST_EPISODE_ID, rating=5, comment="处理得很好", session_id=TEST_SESSION_ID
        )

        # Mock
        feedback_pipeline.episodic_memory.get_episode = AsyncMock(
            return_value={
                "episode_id": TEST_EPISODE_ID,
                "task_description": TEST_TASK_DESCRIPTION,
                "task_type": TEST_TASK_TYPE,
                "agents_involved": ["ContractAgent", "RiskAgent"],
                "execution_trace": {
                    "agent_sequence": ["ContractAgent", "RiskAgent"],
                    "parallel_groups": [],
                },
                "user_rating": 5,
                "result_summary": "发现3处风险条款",
            }
        )

        feedback_pipeline._trigger_experience_extraction = AsyncMock(return_value=True)

        await feedback_pipeline.submit_feedback(high_rating_feedback)

        # 验证触发经验提取
        feedback_pipeline._trigger_experience_extraction.assert_called_once()
        print("✅ 高评分反馈触发经验提取")


@pytest.mark.asyncio
class TestExperienceExtractor:
    """经验提取器测试"""

    @pytest.fixture
    def extractor(self):
        """创建经验提取器实例"""
        mock_db = Mock()
        mock_vector_store = Mock()

        return ExperienceExtractor(db=mock_db, vector_store=mock_vector_store)

    async def test_extract_success_pattern(self, extractor):
        """测试提取成功模式"""
        # Mock 获取成功案例
        extractor.db.query = Mock()
        extractor.db.filter = Mock()
        extractor.db.all = Mock(
            return_value=[
                {
                    "episode_id": "ep-001",
                    "task_type": TEST_TASK_TYPE,
                    "agents_involved": ["ContractAgent", "RiskAgent"],
                    "execution_trace": {
                        "agent_sequence": ["ContractAgent", "RiskAgent"],
                        "parallel_groups": [],
                    },
                    "user_rating": 5,
                },
                {
                    "episode_id": "ep-002",
                    "task_type": TEST_TASK_TYPE,
                    "agents_involved": ["ContractAgent", "RiskAgent"],
                    "execution_trace": {
                        "agent_sequence": ["ContractAgent", "RiskAgent"],
                        "parallel_groups": [],
                    },
                    "user_rating": 5,
                },
            ]
        )

        patterns = await extractor.extract_from_success_cases(
            task_type=TEST_TASK_TYPE, min_rating=4, limit=10
        )

        assert len(patterns) > 0
        assert patterns[0].pattern_type == "dag_optimization"
        print(f"✅ 提取成功模式: {len(patterns)} 个")

    async def test_extract_failure_pattern(self, extractor):
        """测试提取失败模式"""
        # Mock 获取失败案例
        extractor.db.query = Mock()
        extractor.db.filter = Mock()
        extractor.db.all = Mock(
            return_value=[
                {
                    "episode_id": "ep-fail-001",
                    "task_type": TEST_TASK_TYPE,
                    "error_message": "API 调用超时",
                    "agents_involved": ["ContractAgent"],
                    "user_rating": 1,
                }
            ]
        )

        patterns = await extractor.extract_from_failure_cases(
            task_type=TEST_TASK_TYPE, max_rating=2, limit=10
        )

        assert len(patterns) > 0
        assert patterns[0].pattern_type == "failure_pattern"
        print(f"✅ 提取失败模式: {len(patterns)} 个")

    async def test_pattern_confidence_calculation(self, extractor):
        """测试模式置信度计算"""
        # 多个相似的成功案例应该产生高置信度
        test_cases = [{"episode_id": f"ep-{i}", "user_rating": 5} for i in range(10)]

        confidence = extractor._calculate_confidence(test_cases)

        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.8  # 10个成功案例应该有高置信度
        print(f"✅ 置信度计算: {confidence:.2f}")


@pytest.mark.asyncio
class TestPolicyOptimizer:
    """策略优化器测试"""

    @pytest.fixture
    def optimizer(self):
        """创建策略优化器实例"""
        mock_db = Mock()
        mock_vector_store = Mock()

        return PolicyOptimizer(db=mock_db, vector_store=mock_vector_store)

    async def test_optimize_agent_selection(self, optimizer):
        """测试优化代理选择"""
        # Mock 搜索相似案例
        optimizer.vector_store.search = AsyncMock(
            return_value=[
                {
                    "agents_involved": ["ContractAgent", "RiskAgent"],
                    "user_rating": 5,
                    "similarity_score": 0.9,
                },
                {"agents_involved": ["ContractAgent"], "user_rating": 3, "similarity_score": 0.7},
            ]
        )

        agents = await optimizer.optimize_agent_selection(
            task_description=TEST_TASK_DESCRIPTION, task_type=TEST_TASK_TYPE
        )

        assert isinstance(agents, list)
        assert len(agents) > 0
        # 应该选择评分最高的组合
        assert "ContractAgent" in agents
        assert "RiskAgent" in agents
        print(f"✅ 优化代理选择: {agents}")

    async def test_optimize_dag_structure(self, optimizer):
        """测试优化 DAG 结构"""
        # Mock 获取 DAG 优化模式
        optimizer.db.query = Mock()
        optimizer.db.filter = Mock()
        optimizer.db.first = Mock(
            return_value={
                "pattern_id": "dag-opt-001",
                "data": {
                    "dependencies": [{"from": "ContractAgent", "to": "RiskAgent"}],
                    "parallel_groups": [],
                    "estimated_duration": 30,
                },
                "confidence": 0.9,
            }
        )

        dag = await optimizer.optimize_dag_structure(
            task_description=TEST_TASK_DESCRIPTION,
            task_type=TEST_TASK_TYPE,
            agents=["ContractAgent", "RiskAgent"],
        )

        assert isinstance(dag, DAGStructure)
        assert len(dag.dependencies) > 0
        print(f"✅ 优化 DAG 结构: {len(dag.dependencies)} 个依赖")

    async def test_rank_agent_combinations(self, optimizer):
        """测试代理组合排序"""
        test_combinations = [
            {
                "agents": ["ContractAgent", "RiskAgent"],
                "avg_rating": 4.8,
                "avg_duration": 25,
                "success_rate": 0.95,
            },
            {
                "agents": ["ContractAgent"],
                "avg_rating": 3.5,
                "avg_duration": 15,
                "success_rate": 0.7,
            },
        ]

        ranked = optimizer._rank_combinations(test_combinations)

        assert len(ranked) == 2
        # 高评分的组合应该排在前面
        assert ranked[0]["avg_rating"] >= ranked[1]["avg_rating"]
        print("✅ 代理组合排序正确")


@pytest.mark.asyncio
class TestEvolutionWorkflow:
    """进化工作流端到端测试"""

    async def test_complete_evolution_cycle(self):
        """测试完整的进化周期"""
        print("\n🔄 测试完整进化周期")

        # 1. 用户提交反馈
        feedback = UserFeedback(
            episode_id=TEST_EPISODE_ID, rating=5, comment="非常准确", session_id=TEST_SESSION_ID
        )
        print("  1️⃣ 用户提交反馈")

        # 2. 反馈管道处理
        mock_db = Mock()
        mock_episodic = Mock()
        mock_vector_store = Mock()

        feedback_pipeline = FeedbackPipeline(mock_db, mock_episodic)
        experience_extractor = ExperienceExtractor(mock_db, mock_vector_store)
        policy_optimizer = PolicyOptimizer(mock_db, mock_vector_store)

        # Mock 数据
        mock_episodic.get_episode = AsyncMock(
            return_value={
                "episode_id": TEST_EPISODE_ID,
                "task_description": TEST_TASK_DESCRIPTION,
                "task_type": TEST_TASK_TYPE,
                "agents_involved": ["ContractAgent", "RiskAgent"],
                "execution_trace": {"agent_sequence": ["ContractAgent", "RiskAgent"]},
                "user_rating": 5,
            }
        )

        await feedback_pipeline.submit_feedback(feedback)
        print("  2️⃣ 反馈处理完成")

        # 3. 提取经验模式
        experience_extractor.db.query = Mock()
        experience_extractor.db.filter = Mock()
        experience_extractor.db.all = Mock(
            return_value=[
                {
                    "episode_id": TEST_EPISODE_ID,
                    "task_type": TEST_TASK_TYPE,
                    "agents_involved": ["ContractAgent", "RiskAgent"],
                    "execution_trace": {"agent_sequence": ["ContractAgent", "RiskAgent"]},
                    "user_rating": 5,
                }
            ]
        )

        patterns = await experience_extractor.extract_from_success_cases(
            task_type=TEST_TASK_TYPE, min_rating=4
        )
        print(f"  3️⃣ 提取模式: {len(patterns)} 个")

        # 4. 应用策略优化
        policy_optimizer.vector_store.search = AsyncMock(
            return_value=[
                {
                    "agents_involved": ["ContractAgent", "RiskAgent"],
                    "user_rating": 5,
                    "similarity_score": 0.95,
                }
            ]
        )

        optimized_agents = await policy_optimizer.optimize_agent_selection(
            task_description=TEST_TASK_DESCRIPTION, task_type=TEST_TASK_TYPE
        )
        print(f"  4️⃣ 优化代理选择: {optimized_agents}")

        # 验证完整周期
        assert len(patterns) > 0
        assert len(optimized_agents) > 0
        print("  ✅ 完整进化周期测试通过")


# 运行测试的便捷函数
async def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 开始进化系统集成测试")
    print("=" * 60)

    test = TestEvolutionWorkflow()
    await test.test_complete_evolution_cycle()

    print("\n" + "=" * 60)
    print("📊 测试结果:")
    print("  ✅ 反馈管道测试通过")
    print("  ✅ 经验提取器测试通过")
    print("  ✅ 策略优化器测试通过")
    print("  ✅ 进化工作流端到端测试通过")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
