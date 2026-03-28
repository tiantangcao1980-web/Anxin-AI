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
        # Mock LLM配置
        mock_llm_config.return_value = MagicMock(
            provider="openai",
            model_name="gpt-4o",
            temperature=0.7,
            max_tokens=4096,
            api_key="test-key",
            api_base_url=None,
            source="env"
        )
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
        mock_llm_config.return_value = MagicMock(
            provider="openai",
            model_name="gpt-4o",
            temperature=0.7,
            max_tokens=4096,
            api_key="test-key",
            api_base_url=None,
            source="env"
        )
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
        mock_llm_config.return_value = MagicMock(
            provider="openai",
            model_name="gpt-4o",
            temperature=0.7,
            max_tokens=4096,
            api_key="test-key",
            api_base_url=None,
            source="env"
        )
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
        mock_llm_config.return_value = MagicMock(
            provider="openai",
            model_name="gpt-4o",
            temperature=0.7,
            max_tokens=4096,
            api_key="test-key",
            api_base_url=None,
            source="env"
        )
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
        """测试智能体对话成功"""
        # Mock配置
        mock_llm_config.return_value = MagicMock(
            provider="openai",
            model_name="gpt-4o",
            temperature=0.7,
            max_tokens=4096,
            api_key="test-key",
            api_base_url=None,
            source="env"
        )
        
        # Mock Agent响应
        mock_agent = MagicMock()
        mock_response = MagicMock()
        mock_response.msgs = [MagicMock(content="这是法律咨询的回复")]
        mock_agent.step.return_value = mock_response
        
        mock_model_factory.return_value = MagicMock()
        
        agent = LegalAdvisorAgent()
        agent.agent = mock_agent
        
        response = await agent.chat("请问合同违约应该如何处理？")
        
        assert response == "这是法律咨询的回复"
        mock_agent.step.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.agents.base.get_llm_config_sync')
    @patch('src.agents.base.ModelFactory.create')
    async def test_agent_chat_without_init(self, mock_model_factory, mock_llm_config):
        """测试未初始化的Agent对话"""
        mock_llm_config.return_value = MagicMock(
            provider="openai",
            model_name="gpt-4o",
            temperature=0.7,
            max_tokens=4096,
            api_key="test-key",
            api_base_url=None,
            source="env"
        )
        mock_model_factory.return_value = MagicMock()
        
        agent = LegalAdvisorAgent()
        agent.agent = None  # 模拟未初始化
        
        response = await agent.chat("测试消息")
        
        assert response == "Agent未初始化"
    
    @pytest.mark.asyncio
    @patch('src.agents.base.get_llm_config_sync')
    @patch('src.agents.base.ModelFactory.create')
    async def test_agent_chat_error_handling(self, mock_model_factory, mock_llm_config):
        """测试Agent对话错误处理"""
        mock_llm_config.return_value = MagicMock(
            provider="openai",
            model_name="gpt-4o",
            temperature=0.7,
            max_tokens=4096,
            api_key="test-key",
            api_base_url=None,
            source="env"
        )
        
        mock_agent = MagicMock()
        mock_agent.step.side_effect = Exception("API调用失败")
        
        mock_model_factory.return_value = MagicMock()
        
        agent = LegalAdvisorAgent()
        agent.agent = mock_agent
        
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
        mock_llm_config.return_value = MagicMock(
            provider="openai",
            model_name="gpt-4o",
            temperature=0.7,
            max_tokens=4096,
            api_key="test-key",
            api_base_url=None,
            source="env"
        )
        
        mock_agent = MagicMock()
        mock_response = MagicMock()
        mock_response.msgs = [MagicMock(content="风险评估结果：中等风险")]
        mock_agent.step.return_value = mock_response
        
        mock_model_factory.return_value = MagicMock()
        
        agent = RiskAssessmentAgent()
        agent.agent = mock_agent
        
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
        mock_llm_config.return_value = MagicMock(
            provider="openai",
            model_name="gpt-4o",
            temperature=0.7,
            max_tokens=4096,
            api_key="test-key",
            api_base_url=None,
            source="env"
        )
        
        mock_agent = MagicMock()
        mock_response = MagicMock()
        mock_response.msgs = [MagicMock(content='{"sentiment_type": "negative", "risk_level": "high"}')]
        mock_agent.step.return_value = mock_response
        
        mock_model_factory.return_value = MagicMock()
        
        agent = SentimentAnalysisAgent()
        agent.agent = mock_agent
        
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
        mock_llm_config.return_value = MagicMock(
            provider="openai",
            model_name="gpt-4o",
            temperature=0.7,
            max_tokens=4096,
            api_key="test-key",
            api_base_url=None,
            source="env"
        )
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

class TestLegalWorkforce:
    """测试法务智能体团队"""
    
    @patch('src.agents.workforce.LegalAdvisorAgent')
    @patch('src.agents.workforce.ContractReviewAgent')
    @patch('src.agents.workforce.DueDiligenceAgent')
    @patch('src.agents.workforce.LegalResearchAgent')
    @patch('src.agents.workforce.DocumentDraftAgent')
    @patch('src.agents.workforce.ComplianceAgent')
    @patch('src.agents.workforce.RiskAssessmentAgent')
    @patch('src.agents.workforce.ConsensusAgent')
    @patch('src.agents.workforce.CoordinatorAgent')
    def test_workforce_initialization(self, *mocks):
        """测试智能体团队初始化"""
        # 设置所有mock返回MagicMock实例
        for mock in mocks:
            mock.return_value = MagicMock()
        
        workforce = LegalWorkforce()
        
        assert workforce.coordinator is not None
        assert len(workforce.agents) == 8
        assert "legal_advisor" in workforce.agents
        assert "contract_reviewer" in workforce.agents
        assert "risk_assessor" in workforce.agents
    
    @patch('src.agents.workforce.LegalAdvisorAgent')
    @patch('src.agents.workforce.ContractReviewAgent')
    @patch('src.agents.workforce.DueDiligenceAgent')
    @patch('src.agents.workforce.LegalResearchAgent')
    @patch('src.agents.workforce.DocumentDraftAgent')
    @patch('src.agents.workforce.ComplianceAgent')
    @patch('src.agents.workforce.RiskAssessmentAgent')
    @patch('src.agents.workforce.ConsensusAgent')
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
        
        assert len(info) == 8
        for agent_info in info:
            assert "name" in agent_info
            assert "role" in agent_info
    
    @pytest.mark.asyncio
    @patch('src.agents.workforce.LegalAdvisorAgent')
    @patch('src.agents.workforce.ContractReviewAgent')
    @patch('src.agents.workforce.DueDiligenceAgent')
    @patch('src.agents.workforce.LegalResearchAgent')
    @patch('src.agents.workforce.DocumentDraftAgent')
    @patch('src.agents.workforce.ComplianceAgent')
    @patch('src.agents.workforce.RiskAssessmentAgent')
    @patch('src.agents.workforce.ConsensusAgent')
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
    @patch('src.agents.workforce.LegalAdvisorAgent')
    @patch('src.agents.workforce.ContractReviewAgent')
    @patch('src.agents.workforce.DueDiligenceAgent')
    @patch('src.agents.workforce.LegalResearchAgent')
    @patch('src.agents.workforce.DocumentDraftAgent')
    @patch('src.agents.workforce.ComplianceAgent')
    @patch('src.agents.workforce.RiskAssessmentAgent')
    @patch('src.agents.workforce.ConsensusAgent')
    @patch('src.agents.workforce.CoordinatorAgent')
    async def test_workforce_process_task(self, *mocks):
        """测试智能体团队任务处理"""
        # 设置协调者
        coordinator_mock = MagicMock()
        coordinator_mock.analyze_task = AsyncMock(return_value={
            "agents": ["legal_advisor"],
            "parallel": False,
            "sub_tasks": {}
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
