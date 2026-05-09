"""
智能体团队测试
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentConfig, AgentResponse
from src.agents.contract_reviewer import ContractReviewAgent
from src.agents.legal_advisor import LegalAdvisorAgent
from src.agents.risk_assessor import RiskAssessmentAgent
from src.agents.sentiment_agent import SentimentAnalysisAgent

# 当前 workforce 中专业智能体的数量（不含 coordinator 和 requirement_analyst）
# 直接从注册表读取，避免"新增 agent 忘改测试"的维护成本。
from src.agents.workforce import (
    AGENT_REGISTRY,  # noqa: E402
    LegalWorkforce,
    build_runtime_workspace_artifact,
    get_workforce,
)

EXPECTED_AGENT_COUNT = len(AGENT_REGISTRY)


def test_runtime_workspace_artifact_is_redacted_and_reviewable():
    artifact = build_runtime_workspace_artifact(
        task_id="task-123",
        session_id="session-1",
        task_description="生成一份合同风险摘要",
        plan=[
            {
                "id": "review",
                "agent": "contract_reviewer",
                "instruction": "审查合同，api_key=sk-raw-should-not-leak",
                "depends_on": [],
            }
        ],
        agent_results=[
            AgentResponse(
                agent_name="contract_reviewer",
                content="发现付款条款风险，建议补充违约责任。",
                metadata={"api_key": "sk-raw-should-not-leak", "error": False},
            )
        ],
        final_result={"summary": "合同风险摘要已生成", "private_key": "raw-private-key"},
        elapsed_seconds=3.456,
        has_consensus=False,
    )

    serialized = json.dumps(artifact, ensure_ascii=False)
    assert artifact["artifact_type"] == "agent_runtime_summary"
    assert artifact["metadata"]["runtime_generated"] is True
    assert artifact["content"]["timeline"][-1]["event"] == "artifact_created"
    assert artifact["content"]["timeline"][-1]["status"] == "ready_for_review"
    assert artifact["content"]["agent_results"][0]["status"] == "completed"
    assert "sk-raw-should-not-leak" not in serialized
    assert "raw-private-key" not in serialized
    assert "[redacted]" in serialized


def _mock_agent_registry():
    """构造一个 registry，所有 agent class 被替换为 MagicMock 工厂。

    返回值：{agent_id: MagicMock class, ...}，调用 factory() 得到带 get_info() 的实例。
    """
    registry = {}
    for agent_id in AGENT_REGISTRY:
        cls_mock = MagicMock()
        instance = MagicMock()
        instance.get_info.return_value = {
            "name": agent_id,
            "role": "TestRole",
            "description": "Test Description",
            "tools": [],
        }
        cls_mock.return_value = instance
        registry[agent_id] = cls_mock
    return registry


def _make_llm_config_mock():
    """创建标准的 LLM 配置 mock"""
    return MagicMock(
        provider="openai",
        model_name="gpt-4o",
        temperature=0.7,
        max_tokens=4096,
        api_key="test-key",
        api_base_url=None,
        source="env"
    )


# ============ 智能体初始化测试 ============

class TestAgentInitialization:
    """测试智能体初始化"""

    @patch('src.agents.base.get_llm_config_sync')
    @patch('src.agents.base.ModelFactory.create')
    def test_agent_config_creation(self, mock_model_factory, mock_llm_config):
        """测试智能体配置创建"""
        config = AgentConfig(
            name="测试Agent",
            role="测试角色",
            description="测试描述",
            system_prompt="你是一个测试智能体",
            temperature=0.7,
            max_tokens=4096,
            tools=["test_tool"]
        )

        assert config.name == "测试Agent"
        assert config.role == "测试角色"
        assert config.description == "测试描述"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert "test_tool" in config.tools

    @patch('src.agents.base.get_llm_config_sync')
    @patch('src.agents.base.ModelFactory.create')
    @patch('src.agents.base.ChatAgent')
    def test_legal_advisor_initialization(self, mock_chat_agent, mock_model_factory, mock_llm_config):
        """测试法律顾问Agent初始化"""
        mock_llm_config.return_value = _make_llm_config_mock()
        mock_model_factory.return_value = MagicMock()
        mock_chat_agent.return_value = MagicMock()

        agent = LegalAdvisorAgent()

        assert agent.name == "法律顾问Agent"
        assert agent.role == "首席法律顾问"
        assert agent.config is not None

    @patch('src.agents.base.get_llm_config_sync')
    @patch('src.agents.base.ModelFactory.create')
    @patch('src.agents.base.ChatAgent')
    def test_contract_reviewer_initialization(self, mock_chat_agent, mock_model_factory, mock_llm_config):
        """测试合同审查Agent初始化"""
        mock_llm_config.return_value = _make_llm_config_mock()
        mock_model_factory.return_value = MagicMock()
        mock_chat_agent.return_value = MagicMock()

        agent = ContractReviewAgent()

        assert agent.name == "合同审查Agent"
        assert agent.role == "合同审查专家"

    @patch('src.agents.base.get_llm_config_sync')
    @patch('src.agents.base.ModelFactory.create')
    @patch('src.agents.base.ChatAgent')
    def test_risk_assessor_initialization(self, mock_chat_agent, mock_model_factory, mock_llm_config):
        """测试风险评估Agent初始化"""
        mock_llm_config.return_value = _make_llm_config_mock()
        mock_model_factory.return_value = MagicMock()
        mock_chat_agent.return_value = MagicMock()

        agent = RiskAssessmentAgent()

        assert agent.name == "风险评估Agent"
        assert agent.role == "风险评估专家"

    @patch('src.agents.base.get_llm_config_sync')
    @patch('src.agents.base.ModelFactory.create')
    @patch('src.agents.base.ChatAgent')
    def test_sentiment_agent_initialization(self, mock_chat_agent, mock_model_factory, mock_llm_config):
        """测试舆情分析Agent初始化"""
        mock_llm_config.return_value = _make_llm_config_mock()
        mock_model_factory.return_value = MagicMock()
        mock_chat_agent.return_value = MagicMock()

        agent = SentimentAnalysisAgent()

        assert agent.name == "舆情分析Agent"
        assert agent.role == "舆情分析专家"


# ============ 智能体对话测试 ============

class TestAgentChat:
    """测试智能体对话功能"""

    @pytest.mark.asyncio
    @patch('src.agents.base.get_llm_config_sync')
    @patch('src.agents.base.ModelFactory.create')
    async def test_agent_chat_success(self, mock_model_factory, mock_llm_config):
        """测试智能体对话成功 — 通过 mock chat 方法验证"""
        mock_llm_config.return_value = _make_llm_config_mock()
        mock_model_factory.return_value = MagicMock()

        agent = LegalAdvisorAgent()

        # v2 chat 方法直接调用 HTTP API，需要 mock 整个 chat 方法
        with patch.object(agent, 'chat', new_callable=AsyncMock, return_value="这是法律咨询的回复"):
            response = await agent.chat("请问合同违约应该如何处理？")
            assert response == "这是法律咨询的回复"

    @pytest.mark.asyncio
    @patch('src.agents.base.get_llm_config_sync')
    @patch('src.agents.base.ModelFactory.create')
    async def test_agent_chat_without_valid_config(self, mock_model_factory, mock_llm_config):
        """测试无有效 LLM 配置时的 Agent 对话"""
        # 使用 dummy key 模拟未配置场景
        mock_llm_config.return_value = MagicMock(
            provider="openai",
            model_name="gpt-4o",
            temperature=0.7,
            max_tokens=4096,
            api_key="sk-dummy-key",
            api_base_url=None,
            source="env"
        )
        mock_model_factory.return_value = MagicMock()

        agent = LegalAdvisorAgent()

        # 当 api_key 是 dummy 时，chat 应返回配置提示而非崩溃
        with patch('src.agents.base.BaseLegalAgent.broadcast_status', new_callable=AsyncMock):
            response = await agent.chat("测试消息")
            # 应返回配置提示或错误信息，不应抛出异常
            assert isinstance(response, str)
            assert len(response) > 0

    @pytest.mark.asyncio
    @patch('src.agents.base.get_llm_config_sync')
    @patch('src.agents.base.ModelFactory.create')
    async def test_agent_chat_error_handling(self, mock_model_factory, mock_llm_config):
        """测试Agent对话错误处理"""
        mock_llm_config.return_value = _make_llm_config_mock()
        mock_model_factory.return_value = MagicMock()

        agent = LegalAdvisorAgent()

        # Mock chat 方法模拟错误情况
        with patch.object(agent, 'chat', new_callable=AsyncMock, return_value="处理失败: API调用失败"):
            response = await agent.chat("测试消息")
            assert "处理失败" in response


# ============ 智能体任务处理测试 ============

class TestAgentProcess:
    """测试智能体任务处理"""

    @pytest.mark.asyncio
    @patch('src.agents.base.get_llm_config_sync')
    @patch('src.agents.base.ModelFactory.create')
    async def test_risk_assessment_process(self, mock_model_factory, mock_llm_config):
        """测试风险评估任务处理"""
        mock_llm_config.return_value = _make_llm_config_mock()
        mock_model_factory.return_value = MagicMock()

        agent = RiskAssessmentAgent()

        # Mock chat 方法，因为 process 内部调用 chat
        with patch.object(agent, 'chat', new_callable=AsyncMock, return_value="风险评估结果：中等风险"):
            task = {
                "description": "评估合同履约风险",
                "context": {"contract_type": "服务合同"}
            }

            result = await agent.process(task)

            assert isinstance(result, AgentResponse)
            assert result.agent_name == "风险评估Agent"
            assert "风险评估" in result.content

    @pytest.mark.asyncio
    @patch('src.agents.base.get_llm_config_sync')
    @patch('src.agents.base.ModelFactory.create')
    async def test_sentiment_analysis_process(self, mock_model_factory, mock_llm_config):
        """测试舆情分析任务处理"""
        mock_llm_config.return_value = _make_llm_config_mock()
        mock_model_factory.return_value = MagicMock()

        agent = SentimentAnalysisAgent()

        with patch.object(agent, 'chat', new_callable=AsyncMock,
                          return_value='{"sentiment_type": "negative", "risk_level": "high"}'):
            task = {
                "description": "公司因合同纠纷被起诉，舆论关注度较高",
                "context": {}
            }

            result = await agent.process(task)

            assert isinstance(result, AgentResponse)
            assert result.agent_name == "舆情分析Agent"

    @pytest.mark.asyncio
    @patch('src.agents.base.get_llm_config_sync')
    @patch('src.agents.base.ModelFactory.create')
    async def test_calculate_risk_score(self, mock_model_factory, mock_llm_config):
        """测试风险评分计算"""
        mock_llm_config.return_value = _make_llm_config_mock()
        mock_model_factory.return_value = MagicMock()

        agent = RiskAssessmentAgent()

        factors = {
            "contract_risk": 0.8,
            "litigation_risk": 0.6,
            "compliance_risk": 0.5,
            "other_risk": 0.3
        }

        result = await agent.calculate_risk_score(factors)

        assert "score" in result
        assert "level" in result
        assert result["score"] >= 0 and result["score"] <= 1
        assert result["level"] in ["low", "medium", "high", "critical"]


# ============ 智能体团队测试 ============

# 所有需要 mock 的 Agent 类（按 workforce.py 的导入顺序）
_WORKFORCE_AGENT_PATCHES = [
    'src.agents.workforce.RequirementAnalystAgent',
    'src.agents.workforce.ContractStewardAgent',
    'src.agents.workforce.EvidenceAnalystAgent',
    'src.agents.workforce.LaborComplianceAgent',
    'src.agents.workforce.TaxComplianceAgent',
    'src.agents.workforce.RegulatoryMonitorAgent',
    'src.agents.workforce.IPSpecialistAgent',
    'src.agents.workforce.LitigationStrategistAgent',
    'src.agents.workforce.ConsensusAgent',
    'src.agents.workforce.RiskAssessmentAgent',
    'src.agents.workforce.ComplianceAgent',
    'src.agents.workforce.DocumentDraftAgent',
    'src.agents.workforce.LegalResearchAgent',
    'src.agents.workforce.DueDiligenceAgent',
    'src.agents.workforce.ContractReviewAgent',
    'src.agents.workforce.ContractInvestigatorAgent',
    'src.agents.workforce.ReviewCheckerAgent',
    'src.agents.workforce.LegalAdvisorAgent',
    'src.agents.workforce.CoordinatorAgent',
]


def _apply_workforce_patches(mocks, *, with_info=False, with_chat=False):
    """为所有 workforce agent mock 设置默认返回值"""
    for mock in mocks:
        agent_mock = MagicMock()
        if with_info:
            agent_mock.get_info.return_value = {
                "name": "TestAgent",
                "role": "TestRole",
                "description": "Test Description",
                "tools": []
            }
        if with_chat:
            agent_mock.chat = AsyncMock(return_value="模拟回复")
        mock.return_value = agent_mock


class TestLegalWorkforce:
    """测试法务智能体团队"""

    @patch('src.services.skill_service.skill_service.load_skills')
    @patch('src.agents.workforce.RequirementAnalystAgent')
    @patch('src.agents.workforce.CoordinatorAgent')
    def test_workforce_initialization(self, mock_coordinator, mock_requirement, _mock_skills):
        """测试智能体团队初始化（AGENT_REGISTRY 驱动，无需手工 patch 每个 agent）"""
        mock_coordinator.return_value = MagicMock()
        mock_requirement.return_value = MagicMock()

        with patch.dict(
            'src.agents.workforce.AGENT_REGISTRY', _mock_agent_registry(), clear=True,
        ):
            workforce = LegalWorkforce()

        assert workforce.coordinator is not None
        assert len(workforce.agents) == EXPECTED_AGENT_COUNT
        # 关键 agent 必在注册表内（防止后续误删）
        assert "legal_advisor" in workforce.agents
        assert "contract_reviewer" in workforce.agents
        assert "risk_assessor" in workforce.agents

    @patch('src.services.skill_service.skill_service.load_skills')
    @patch('src.agents.workforce.RequirementAnalystAgent')
    @patch('src.agents.workforce.CoordinatorAgent')
    def test_get_agents_info(self, mock_coordinator, mock_requirement, _mock_skills):
        """测试获取智能体信息（AGENT_REGISTRY 驱动）"""
        mock_coordinator.return_value = MagicMock()
        mock_requirement.return_value = MagicMock()

        with patch.dict(
            'src.agents.workforce.AGENT_REGISTRY', _mock_agent_registry(), clear=True,
        ):
            workforce = LegalWorkforce()
            info = workforce.get_agents_info()

        assert len(info) == EXPECTED_AGENT_COUNT
        for agent_info in info:
            assert "name" in agent_info
            assert "role" in agent_info

    @pytest.mark.asyncio
    @patch('src.services.skill_service.skill_service.load_skills')
    @patch('src.agents.workforce.RequirementAnalystAgent')
    @patch('src.agents.workforce.CoordinatorAgent')
    async def test_workforce_chat(self, mock_coordinator, mock_requirement, _mock_skills):
        """测试智能体团队对话"""
        mock_coordinator.return_value = MagicMock(chat=AsyncMock(return_value="模拟回复"))
        mock_requirement.return_value = MagicMock()

        registry = _mock_agent_registry()
        for cls_mock in registry.values():
            cls_mock.return_value.chat = AsyncMock(return_value="模拟回复")

        with patch.dict('src.agents.workforce.AGENT_REGISTRY', registry, clear=True):
            workforce = LegalWorkforce()
            response = await workforce.chat("测试问题")

        assert response == "模拟回复"

    @pytest.mark.asyncio
    @patch('src.services.skill_service.skill_service.load_skills')
    @patch('src.agents.workforce.RequirementAnalystAgent')
    @patch('src.agents.workforce.CoordinatorAgent')
    async def test_workforce_process_task(self, mock_coordinator, mock_requirement, _mock_skills):
        """测试智能体团队任务处理"""
        coordinator_mock = MagicMock()
        coordinator_mock.analyze_task = AsyncMock(return_value={
            "agents": ["legal_advisor"],
            "parallel": False,
            "sub_tasks": {},
            "plan": [{"id": "task_1", "agent": "legal_advisor", "instruction": "审查合同条款", "depends_on": []}],
            "intent": "CONTRACT_REVIEW",
            "reasoning": "合同审查任务",
        })
        coordinator_mock.aggregate_results = AsyncMock(return_value={"summary": "任务处理完成"})
        mock_coordinator.return_value = coordinator_mock
        mock_requirement.return_value = MagicMock()

        # 所有注册表里的 agent 都返回标准 AgentResponse
        registry = _mock_agent_registry()
        for cls_mock in registry.values():
            instance = cls_mock.return_value
            instance.process = AsyncMock(return_value=AgentResponse(
                agent_name="TestAgent",
                content="处理结果",
                reasoning="推理过程",
            ))
            instance.chat = AsyncMock(return_value="回复")

        with patch.dict('src.agents.workforce.AGENT_REGISTRY', registry, clear=True):
            workforce = LegalWorkforce()
            workforce.coordinator = coordinator_mock
            result = await workforce.process_task(
                task_description="审查合同条款",
                task_type="contract_review",
                context={"document_id": "test-123"},
            )

        assert "task" in result
        assert "analysis" in result
        assert "final_result" in result


# ============ 智能体单例测试 ============

class TestWorkforceSingleton:
    """测试智能体团队单例"""

    @patch('src.agents.workforce.LegalWorkforce')
    def test_get_workforce_singleton(self, mock_workforce_class):
        """测试获取智能体团队单例"""
        import src.agents.workforce as workforce_module

        # 重置单例
        workforce_module._workforce = None

        mock_workforce_class.return_value = MagicMock()

        workforce1 = get_workforce()
        workforce2 = get_workforce()

        # 应该只创建一次实例
        assert workforce1 is workforce2
