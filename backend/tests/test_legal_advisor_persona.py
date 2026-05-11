# -*- coding: utf-8 -*-
"""P9-B: LegalAdvisorPersona 单元测试

策略：
    - 全部 mock 5 个 specialized agent 的 ``process()`` / ``search_laws()``
      返回，避免真正调用 LLM；
    - 验证：
        1. 元信息字段完整 + 自动注册到 PersonaRegistry
        2. handle_message 路由 capability hint
        3. consult / research_law / assess_risk / review_compliance /
           get_regulatory_updates 5 个能力的封装行为
        4. JSON 解析容错（缺 JSON 块、无效 JSON、字段缺失都不应崩溃）
        5. disclaimer 强制注入
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.base import AgentResponse
from src.agents.personas import LegalAdvisorPersona, PersonaRegistry
from src.agents.personas.legal_models import (
    DEFAULT_DISCLAIMER,
    Citation,
    LawSearchQuery,
)


@pytest.fixture(autouse=True)
def _reset_registry():
    PersonaRegistry.reset_instance()
    yield
    PersonaRegistry.reset_instance()


@pytest.fixture
def agent():
    """构造 agent + 5 个 mock specialized agent，规避 LLM 真初始化。"""
    advisor = AsyncMock()
    researcher = AsyncMock()
    risk = AsyncMock()
    compliance = AsyncMock()
    monitor = AsyncMock()

    with patch("src.agents.base.get_llm_config_sync", return_value=None):
        instance = LegalAdvisorPersona(
            advisor=advisor,
            researcher=researcher,
            risk=risk,
            compliance=compliance,
            monitor=monitor,
        )
    return instance


# ------------------------------------------------------------------
class TestMetadata:
    def test_persona_metadata(self, agent):
        info = agent.get_info()
        assert info.persona_id == "legal_advisor"
        assert info.display_name == "法律顾问"
        assert info.emoji == "⚖️"
        assert "legal_consultation" in info.capabilities
        assert "law_research" in info.capabilities
        assert "risk_assessment" in info.capabilities
        assert "compliance_review" in info.capabilities
        assert "regulation_monitoring" in info.capabilities

    def test_skills_and_apps(self, agent):
        info = agent.get_info()
        assert set(info.backed_by_skills) == {"docx", "pdf"}
        assert set(info.supported_apps) == {"pkulaw", "wkinfo"}

    def test_backed_by_5_specialized_agents(self, agent):
        info = agent.get_info()
        assert set(info.backed_by_agents) == {
            "legal_advisor",
            "legal_researcher",
            "risk_assessor",
            "compliance_officer",
            "regulatory_monitor",
        }

    def test_system_prompt_minimum_length_and_boundaries(self):
        prompt = LegalAdvisorPersona.SYSTEM_PROMPT
        assert len(prompt) >= 200
        # 边界声明：persona 间互不越权
        assert "operations_manager" in prompt
        assert "trade_officer" in prompt
        # 必须强调免责
        assert "不构成正式法律意见" in prompt

    def test_autoregistered(self):
        # 强制重新 autoload 确认 persona 仍在
        PersonaRegistry.instance().autoload("src.agents.personas")
        assert PersonaRegistry.instance().has("legal_advisor")


# ------------------------------------------------------------------
class TestHandleMessageRouting:
    @pytest.mark.asyncio
    async def test_handle_message_passes_consultation_hint(self, agent):
        with patch.object(agent, "chat", new=AsyncMock(return_value="ok")) as mock_chat:
            await agent.handle_message(message="请问劳动合同到期不续签需要赔偿吗")
            kwargs = mock_chat.call_args.kwargs
            override = kwargs.get("system_prompt_override")
            assert override is not None
            assert "legal_consultation" in override

    @pytest.mark.asyncio
    async def test_handle_message_passes_compliance_hint(self, agent):
        with patch.object(agent, "chat", new=AsyncMock(return_value="ok")) as mock_chat:
            await agent.handle_message(message="帮我做一次 GDPR 合规审查")
            kwargs = mock_chat.call_args.kwargs
            override = kwargs.get("system_prompt_override")
            assert override is not None
            assert "compliance_review" in override

    @pytest.mark.asyncio
    async def test_handle_message_passes_risk_hint(self, agent):
        with patch.object(agent, "chat", new=AsyncMock(return_value="ok")) as mock_chat:
            await agent.handle_message(message="评估这个项目的法律风险")
            kwargs = mock_chat.call_args.kwargs
            override = kwargs.get("system_prompt_override")
            assert override is not None
            assert "risk_assessment" in override

    @pytest.mark.asyncio
    async def test_handle_message_passes_monitoring_hint(self, agent):
        with patch.object(agent, "chat", new=AsyncMock(return_value="ok")) as mock_chat:
            await agent.handle_message(message="最近劳动法有什么新出台的政策")
            kwargs = mock_chat.call_args.kwargs
            override = kwargs.get("system_prompt_override")
            assert override is not None
            assert "regulation_monitoring" in override

    @pytest.mark.asyncio
    async def test_handle_message_no_keyword_no_override(self, agent):
        with patch.object(agent, "chat", new=AsyncMock(return_value="ok")) as mock_chat:
            await agent.handle_message(message="你好啊")
            kwargs = mock_chat.call_args.kwargs
            assert kwargs.get("system_prompt_override") is None

    def test_guess_capability_keywords(self):
        guess = LegalAdvisorPersona._guess_capability
        assert guess("我想做合规审查") == "compliance_review"
        assert guess("帮我评估法律风险") == "risk_assessment"
        assert guess("最近有哪些新法规") == "regulation_monitoring"
        assert guess("帮我做法规检索") == "law_research"
        assert guess("公司不发工资该怎么办") == "legal_consultation"
        assert guess("") is None


# ------------------------------------------------------------------
class TestConsult:
    @pytest.mark.asyncio
    async def test_consult_parses_json_payload(self, agent):
        fake = (
            "劳动合同到期不续签，根据《劳动合同法》第46条，需要支付经济补偿。\n\n"
            "```json\n"
            '{"legal_basis":[{"source":"law:劳动合同法","article":"第46条",'
            '"title":"劳动合同法","excerpt":"用人单位应当向劳动者支付经济补偿","confidence":0.9}],'
            '"related_topics":["经济补偿","劳动合同终止"],'
            '"suggested_actions":["保留劳动合同原件","计算工龄"],'
            '"confidence":0.85}\n'
            "```\n"
        )
        agent._core_advisor.process.return_value = AgentResponse(
            agent_name="法律顾问Agent",
            content=fake,
        )
        result = await agent.consult(
            "劳动合同到期不续签需要赔偿吗",
            context={"role": "员工"},
        )
        assert result.question == "劳动合同到期不续签需要赔偿吗"
        assert result.persona_id == "legal_advisor"
        assert result.disclaimer == DEFAULT_DISCLAIMER
        assert result.confidence == pytest.approx(0.85)
        assert len(result.legal_basis) == 1
        assert result.legal_basis[0].article == "第46条"
        assert "经济补偿" in result.related_topics
        assert any("劳动合同原件" in a for a in result.suggested_actions)

    @pytest.mark.asyncio
    async def test_consult_falls_back_to_text_extraction(self, agent):
        # 没有 JSON 块时，应从纯文本里抽 《XX》第Y条
        fake = "根据《民法典》第577条，违约方应承担继续履行的义务。"
        agent._core_advisor.process.return_value = AgentResponse(
            agent_name="法律顾问Agent",
            content=fake,
        )
        result = await agent.consult("违约怎么办")
        assert result.disclaimer == DEFAULT_DISCLAIMER
        assert len(result.legal_basis) >= 1
        assert any("民法典" in c.title for c in result.legal_basis)

    @pytest.mark.asyncio
    async def test_consult_empty_question_raises(self, agent):
        with pytest.raises(ValueError):
            await agent.consult("")

    @pytest.mark.asyncio
    async def test_consult_specialized_failure_returns_disclaimer(self, agent):
        # specialized agent 抛异常时，consult 应返回空答案 + 仍带 disclaimer
        agent._core_advisor.process.side_effect = RuntimeError("LLM down")
        result = await agent.consult("xxx")
        assert result.answer == ""
        assert result.disclaimer == DEFAULT_DISCLAIMER


# ------------------------------------------------------------------
class TestResearchLaw:
    @pytest.mark.asyncio
    async def test_research_law_extracts_citations(self, agent):
        fake_text = (
            "《个人信息保护法》第13条规定...；又见《数据安全法》第21条；"
            "（2024）京01民终123号判决"
        )
        agent._researcher.search_laws.return_value = {
            "keywords": ["个人信息保护"],
            "results": fake_text,
            "agent": "法规研究Agent",
        }
        query = LawSearchQuery(
            keyword="个人信息保护",
            law_type="law",
            jurisdiction="national",
            limit=5,
        )
        result = await agent.research_law(query)
        assert result.persona_id == "legal_advisor"
        assert result.query.keyword == "个人信息保护"
        assert result.summary == fake_text
        assert result.total_found >= 2  # 至少抽到 2 条法条
        # 验证传入 specialized agent 的 keywords 包含 jurisdiction / law_type
        agent._researcher.search_laws.assert_awaited_once()
        call_kw = agent._researcher.search_laws.call_args
        # search_laws(keywords) -> positional
        passed = call_kw.args[0] if call_kw.args else call_kw.kwargs.get("keywords")
        assert "个人信息保护" in passed
        assert "national" in passed

    @pytest.mark.asyncio
    async def test_research_law_respects_limit(self, agent):
        # 制造 3 条法条 + 1 个案号
        text = "《A法》第1条；《B法》第2条；《C法》第3条；（2024）X 1 号"
        agent._researcher.search_laws.return_value = {"results": text}
        query = LawSearchQuery(keyword="kw", limit=2)
        result = await agent.research_law(query)
        assert len(result.citations) <= 2

    @pytest.mark.asyncio
    async def test_research_law_empty_keyword_raises(self, agent):
        with pytest.raises(ValueError):
            await agent.research_law(LawSearchQuery(keyword=""))


# ------------------------------------------------------------------
class TestAssessRisk:
    @pytest.mark.asyncio
    async def test_assess_risk_parses_payload(self, agent):
        fake = (
            "## 风险评估\n本项目存在多处合规风险\n\n"
            "```json\n"
            '{"risk_level":"high","risk_factors":['
            '{"factor":"个人信息处理未取得明示同意","severity":"high",'
            '"likelihood":"high","description":"违反PIPL第13条"}],'
            '"mitigation_suggestions":["增加授权弹窗","建立DSAR流程"],'
            '"regulatory_basis":[{"source":"law:个人信息保护法","article":"第13条",'
            '"title":"个人信息保护法","confidence":0.9}]}\n'
            "```\n"
        )
        agent._risk.process.return_value = AgentResponse(
            agent_name="风险评估Agent",
            content=fake,
        )
        report = await agent.assess_risk("用户画像产品上线", jurisdiction="中国大陆")
        assert report.persona_id == "legal_advisor"
        assert report.scenario == "用户画像产品上线"
        assert report.risk_level == "high"
        assert report.jurisdiction == "中国大陆"
        assert len(report.risk_factors) == 1
        assert report.risk_factors[0].severity == "high"
        assert "增加授权弹窗" in report.mitigation_suggestions
        assert len(report.regulatory_basis) == 1

    @pytest.mark.asyncio
    async def test_assess_risk_fallback_text_level(self, agent):
        agent._risk.process.return_value = AgentResponse(
            agent_name="风险评估Agent",
            content="此项目极高风险，必须立即整改。",
        )
        report = await agent.assess_risk("xxx")
        assert report.risk_level == "critical"

    @pytest.mark.asyncio
    async def test_assess_risk_empty_scenario_raises(self, agent):
        with pytest.raises(ValueError):
            await agent.assess_risk("")


# ------------------------------------------------------------------
class TestReviewCompliance:
    @pytest.mark.asyncio
    async def test_review_compliance_parses_issues(self, agent):
        fake = (
            "整体合规评估：partial\n\n"
            "```json\n"
            '{"overall_compliance":"partial","score":72.5,'
            '"issues":[{"clause":"第3条 用户协议","regulation":"PIPL 第14条",'
            '"severity":"high","suggestion":"增加单独同意弹窗"},'
            '{"clause":"第7条 数据共享","regulation":"PIPL 第23条",'
            '"severity":"medium","suggestion":"列明接收方"}]}\n'
            "```\n"
        )
        agent._compliance.process.return_value = AgentResponse(
            agent_name="合规审核Agent",
            content=fake,
        )
        report = await agent.review_compliance(
            document_text="用户协议全文……" * 50,
            regulation_set="PIPL",
        )
        assert report.persona_id == "legal_advisor"
        assert report.regulation_set == "PIPL"
        assert report.overall_compliance == "partial"
        assert report.score == pytest.approx(72.5)
        assert len(report.issues) == 2
        assert report.issues[0].severity == "high"
        # 文档摘要必须截断到 200 + …
        assert report.document_summary.endswith("…")

    @pytest.mark.asyncio
    async def test_review_compliance_empty_doc_raises(self, agent):
        with pytest.raises(ValueError):
            await agent.review_compliance("", "PIPL")

    @pytest.mark.asyncio
    async def test_review_compliance_empty_regulation_raises(self, agent):
        with pytest.raises(ValueError):
            await agent.review_compliance("doc text", "")

    @pytest.mark.asyncio
    async def test_review_compliance_text_fallback(self, agent):
        agent._compliance.process.return_value = AgentResponse(
            agent_name="合规审核Agent",
            content="经审查，文档严重不合规。",
        )
        report = await agent.review_compliance("text", "GDPR")
        assert report.overall_compliance == "non-compliant"


# ------------------------------------------------------------------
class TestRegulatoryUpdates:
    @pytest.mark.asyncio
    async def test_get_regulatory_updates_parses_list(self, agent):
        fake = (
            "## 最新法规速递\n\n"
            "```json\n"
            '{"updates":[{"title":"《劳动合同法》修订草案",'
            '"issuing_authority":"全国人大常委会","issued_date":"2026-04-01",'
            '"effective_date":"2026-07-01","summary":"加强劳动者权益保护",'
            '"impact_assessment":"用人单位需调整试用期条款",'
            '"affected_domains":["劳动关系","试用期"],'
            '"full_text_url":"https://example.com/law/2026/04/01"}]}\n'
            "```\n"
        )
        agent._monitor.process.return_value = AgentResponse(
            agent_name="监管监测Agent",
            content=fake,
        )
        updates = await agent.get_regulatory_updates("劳动法", since_days=60)
        assert len(updates) == 1
        u = updates[0]
        assert u.title == "《劳动合同法》修订草案"
        assert u.issued_date == "2026-04-01"
        assert u.effective_date == "2026-07-01"
        assert "劳动关系" in u.affected_domains

    @pytest.mark.asyncio
    async def test_get_regulatory_updates_passes_domain_to_specialized(self, agent):
        agent._monitor.process.return_value = AgentResponse(
            agent_name="监管监测Agent",
            content="```json\n{\"updates\":[]}\n```",
        )
        await agent.get_regulatory_updates("数据合规", since_days=30)
        agent._monitor.process.assert_awaited_once()
        task = agent._monitor.process.call_args.args[0]
        assert task["industry"] == "数据合规"
        assert task["context"]["since_days"] == 30

    @pytest.mark.asyncio
    async def test_get_regulatory_updates_empty_when_no_json(self, agent):
        agent._monitor.process.return_value = AgentResponse(
            agent_name="监管监测Agent",
            content="纯文本，没有JSON",
        )
        updates = await agent.get_regulatory_updates("劳动法")
        assert updates == []

    @pytest.mark.asyncio
    async def test_get_regulatory_updates_empty_domain_raises(self, agent):
        with pytest.raises(ValueError):
            await agent.get_regulatory_updates("")

    @pytest.mark.asyncio
    async def test_get_regulatory_updates_invalid_since_days_raises(self, agent):
        with pytest.raises(ValueError):
            await agent.get_regulatory_updates("劳动法", since_days=0)
