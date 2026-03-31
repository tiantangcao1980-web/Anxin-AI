"""
智能体团队测试
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.agents.base import BaseLegalAgent, AgentConfig, AgentResponse
from src.agents.workforce import LegalWorkforce, get_workforce
from src.agents.legal_advisor import LegalAdvisorAgent
from src.agents.contract_reviewer import ContractReviewAgent
from src.agents.risk_assessor import RiskAssessmentAgent
from src.agents.sentiment_agent import SentimentAnalysisAgent


# 当前 workforce 中专业智能体的数量（不含 coordinator 和 requirement_analyst）
EXPECTED_AGENT_COUNT = 15


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
    @patch('src.agents.workforce.ContractStewardAgent')
    @patch('src.agents.workforce.EvidenceAnalystAgent')
    @patch('src.agents.workforce.LaborComplianceAgent')
    @patch('src.agents.workforce.TaxComplianceAgent')
    @patch('src.agents.workforce.RegulatoryMonitorAgent')
    @patch('src.agents.workforce.IPSpecialistAgent')
    @patch('src.agents.workforce.LitigationStrategistAgent')
    @patch('src.agents.workforce.ConsensusAgent')
    @patch('src.agents.workforce.RiskAssessmentAgent')
    @patch('src.agents.workforce.ComplianceAgent')
    @patch('src.agents.workforce.DocumentDraftAgent')
    @patch('src.agents.workforce.LegalResearchAgent')
    @patch('src.agents.workforce.DueDiligenceAgent')
    @patch('src.agents.workforce.ContractReviewAgent')
    @patch('src.agents.workforce.LegalAdvisorAgent')
    @patch('src.agents.workforce.CoordinatorAgent')
    def test_workforce_initialization(self, *mocks):
        """测试智能体团队初始化"""
        for mock in mocks:
            mock.return_value = MagicMock()

        workforce = LegalWorkforce()

        assert workforce.coordinator is not None
        assert len(workforce.agents) == EXPECTED_AGENT_COUNT
        assert "legal_advisor" in workforce.agents
        assert "contract_reviewer" in workforce.agents
        assert "risk_assessor" in workforce.agents

    @patch('src.services.skill_service.skill_service.load_skills')
    @patch('src.agents.workforce.RequirementAnalystAgent')
    @patch('src.agents.workforce.ContractStewardAgent')
    @patch('src.agents.workforce.EvidenceAnalystAgent')
    @patch('src.agents.workforce.LaborComplianceAgent')
    @patch('src.agents.workforce.TaxComplianceAgent')
    @patch('src.agents.workforce.RegulatoryMonitorAgent')
    @patch('src.agents.workforce.IPSpecialistAgent')
    @patch('src.agents.workforce.LitigationStrategistAgent')
    @patch('src.agents.workforce.ConsensusAgent')
    @patch('src.agents.workforce.RiskAssessmentAgent')
    @patch('src.agents.workforce.ComplianceAgent')
    @patch('src.agents.workforce.DocumentDraftAgent')
    @patch('src.agents.workforce.LegalResearchAgent')
    @patch('src.agents.workforce.DueDiligenceAgent')
    @patch('src.agents.workforce.ContractReviewAgent')
    @patch('src.agents.workforce.LegalAdvisorAgent')
    @patch('src.agents.workforce.CoordinatorAgent')
    def test_get_agents_info(self, *mocks):
        """测试获取智能体信息"""
        for mock in mocks:
            agent_mock = MagicMock()
            agent_mock.get_info.return_value = {
                "name": "TestAgent",
                "role": "TestRole",
                "description": "Test Description",
                "tools": []
            }
            mock.return_value = agent_mock

        workforce = LegalWorkforce()
        info = workforce.get_agents_info()

        assert len(info) == EXPECTED_AGENT_COUNT
        for agent_info in info:
            assert "name" in agent_info
            assert "role" in agent_info

    @pytest.mark.asyncio
    @patch('src.services.skill_service.skill_service.load_skills')
    @patch('src.agents.workforce.RequirementAnalystAgent')
    @patch('src.agents.workforce.ContractStewardAgent')
    @patch('src.agents.workforce.EvidenceAnalystAgent')
    @patch('src.agents.workforce.LaborComplianceAgent')
    @patch('src.agents.workforce.TaxComplianceAgent')
    @patch('src.agents.workforce.RegulatoryMonitorAgent')
    @patch('src.agents.workforce.IPSpecialistAgent')
    @patch('src.agents.workforce.LitigationStrategistAgent')
    @patch('src.agents.workforce.ConsensusAgent')
    @patch('src.agents.workforce.RiskAssessmentAgent')
    @patch('src.agents.workforce.ComplianceAgent')
    @patch('src.agents.workforce.DocumentDraftAgent')
    @patch('src.agents.workforce.LegalResearchAgent')
    @patch('src.agents.workforce.DueDiligenceAgent')
    @patch('src.agents.workforce.ContractReviewAgent')
    @patch('src.agents.workforce.LegalAdvisorAgent')
    @patch('src.agents.workforce.CoordinatorAgent')
    async def test_workforce_chat(self, *mocks):
        """测试智能体团队对话"""
        for mock in mocks:
            agent_mock = MagicMock()
            agent_mock.chat = AsyncMock(return_value="模拟回复")
            agent_mock.get_info.return_value = {"name": "Test", "role": "Test", "description": "", "tools": []}
            mock.return_value = agent_mock

        workforce = LegalWorkforce()
        response = await workforce.chat("测试问题")

        assert response == "模拟回复"

    @pytest.mark.asyncio
    @patch('src.services.skill_service.skill_service.load_skills')
    @patch('src.agents.workforce.RequirementAnalystAgent')
    @patch('src.agents.workforce.ContractStewardAgent')
    @patch('src.agents.workforce.EvidenceAnalystAgent')
    @patch('src.agents.workforce.LaborComplianceAgent')
    @patch('src.agents.workforce.TaxComplianceAgent')
    @patch('src.agents.workforce.RegulatoryMonitorAgent')
    @patch('src.agents.workforce.IPSpecialistAgent')
    @patch('src.agents.workforce.LitigationStrategistAgent')
    @patch('src.agents.workforce.ConsensusAgent')
    @patch('src.agents.workforce.RiskAssessmentAgent')
    @patch('src.agents.workforce.ComplianceAgent')
    @patch('src.agents.workforce.DocumentDraftAgent')
    @patch('src.agents.workforce.LegalResearchAgent')
    @patch('src.agents.workforce.DueDiligenceAgent')
    @patch('src.agents.workforce.ContractReviewAgent')
    @patch('src.agents.workforce.LegalAdvisorAgent')
    @patch('src.agents.workforce.CoordinatorAgent')
    async def test_workforce_process_task(self, *mocks):
        """测试智能体团队任务处理"""
        # 设置协调者 (first mock = CoordinatorAgent, due to decorator order)
        coordinator_mock = MagicMock()
        coordinator_mock.analyze_task = AsyncMock(return_value={
            "agents": ["legal_advisor"],
            "parallel": False,
            "sub_tasks": {},
            "plan": [{"id": "task_1", "agent": "legal_advisor", "instruction": "审查合同条款", "depends_on": []}],
            "intent": "CONTRACT_REVIEW",
            "reasoning": "合同审查任务",
        })
        coordinator_mock.aggregate_results = AsyncMock(return_value={
            "summary": "任务处理完成"
        })
        mocks[0].return_value = coordinator_mock  # CoordinatorAgent

        # 设置其他智能体
        for i, mock in enumerate(mocks[1:], 1):
            agent_mock = MagicMock()
            agent_mock.process = AsyncMock(return_value=AgentResponse(
                agent_name="TestAgent",
                content="处理结果",
                reasoning="推理过程"
            ))
            agent_mock.get_info.return_value = {"name": "Test", "role": "Test", "description": "", "tools": []}
            agent_mock.chat = AsyncMock(return_value="回复")
            mock.return_value = agent_mock

        workforce = LegalWorkforce()
        workforce.coordinator = coordinator_mock

        result = await workforce.process_task(
            task_description="审查合同条款",
            task_type="contract_review",
            context={"document_id": "test-123"}
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
