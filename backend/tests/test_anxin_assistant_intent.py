"""P9-A: AnxinAssistantAgent.classify_intent 单元测试。

覆盖：
    1. fast path 单 persona 命中
    2. fast path 多 persona 命中（按 hit_count 排序）
    3. fast path 未命中 → 触发 LLM fallback
    4. LLM fallback 返回合法 JSON → 走 `llm` classifier
    5. LLM fallback 返回非法 JSON → 回到入口 persona
    6. 实体抽取（公司、文档类型）
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.personas import AnxinAssistantAgent, PersonaRegistry


@pytest.fixture(autouse=True)
def _reset_registry():
    PersonaRegistry.reset_instance()
    yield
    PersonaRegistry.reset_instance()


@pytest.fixture
def agent():
    """规避 LLM 真初始化。"""
    with patch("src.agents.base.get_llm_config_sync", return_value=None):
        return AnxinAssistantAgent()


# ------------------------------------------------------------------
class TestMetadata:
    def test_persona_metadata(self, agent):
        info = agent.get_info()
        assert info.persona_id == "anxin_assistant"
        assert info.display_name == "安心助理"
        assert info.emoji == "🤖"
        assert "intent_routing" in info.capabilities
        assert "multi_persona_orchestration" in info.capabilities
        assert "task_decomposition" in info.capabilities
        assert "context_memory" in info.capabilities
        assert "user_guidance" in info.capabilities
        assert info.supported_apps == []
        assert set(info.backed_by_skills) == {"docx", "xlsx", "pptx", "pdf"}

    def test_system_prompt_minimum_length_and_persona_list(self):
        prompt = AnxinAssistantAgent.SYSTEM_PROMPT
        assert len(prompt) >= 200
        # 必须列出 9 个非自身 persona
        for pid in [
            "legal_advisor",
            "contract_steward",
            "due_diligence_expert",
            "tax_finance_advisor",
            "operations_manager",
            "market_researcher",
            "lead_hunter",
            "content_director",
            "ecommerce_assistant",
        ]:
            assert pid in prompt, f"SYSTEM_PROMPT 缺少 persona: {pid}"

    def test_autoregistered(self):
        PersonaRegistry.instance().autoload("src.agents.personas")
        assert PersonaRegistry.instance().has("anxin_assistant")


# ------------------------------------------------------------------
class TestFastPath:
    @pytest.mark.asyncio
    async def test_single_keyword_hit(self, agent):
        intent = await agent.classify_intent("我要起草一份采购合同")
        assert intent.classifier == "fast_path"
        assert intent.primary_intent == "contract_steward"
        assert "contract_steward" in intent.target_personas
        assert intent.confidence >= 0.6

    @pytest.mark.asyncio
    async def test_multi_persona_hits_ranked(self, agent):
        # 同时命中 contract_steward + due_diligence_expert
        intent = await agent.classify_intent("帮我起草合同 并对供应商做尽调")
        assert intent.classifier == "fast_path"
        assert "contract_steward" in intent.target_personas
        assert "due_diligence_expert" in intent.target_personas

    @pytest.mark.asyncio
    async def test_ecommerce_keyword(self, agent):
        intent = await agent.classify_intent("Shopify 选品建议")
        assert intent.classifier == "fast_path"
        assert intent.primary_intent == "ecommerce_assistant"

    @pytest.mark.asyncio
    async def test_operations_keyword(self, agent):
        intent = await agent.classify_intent("把上周的会议纪要整理成待办")
        assert intent.classifier == "fast_path"
        # 命中两个：meeting_minutes、todo → 都属 operations_manager
        assert intent.primary_intent == "operations_manager"

    def test_extract_entities_company(self, agent):
        ents = agent._extract_entities_lite("调研一下《华为科技》和《X 集团》")
        assert "company" in ents
        assert "华为科技" in ents["company"]

    def test_extract_entities_document_type(self, agent):
        ents = agent._extract_entities_lite("帮我写一份NDA和周报")
        assert "document_type" in ents
        assert "NDA" in ents["document_type"]
        assert "周报" in ents["document_type"]


# ------------------------------------------------------------------
class TestLLMFallback:
    @pytest.mark.asyncio
    async def test_no_keyword_triggers_llm(self, agent):
        fake_llm_resp = (
            '```json\n{"primary_intent":"market_researcher",'
            '"target_personas":["market_researcher"],'
            '"confidence":0.7,"reasoning":"用户问竞争对手"}\n```'
        )
        with patch.object(agent, "chat", new=AsyncMock(return_value=fake_llm_resp)):
            intent = await agent.classify_intent("帮我看下这个赛道里都有谁")
        assert intent.classifier == "llm"
        assert intent.primary_intent == "market_researcher"
        assert intent.confidence == 0.7

    @pytest.mark.asyncio
    async def test_llm_invalid_json_fallback_to_entry(self, agent):
        with patch.object(agent, "chat", new=AsyncMock(return_value="嗯不是 JSON")):
            intent = await agent.classify_intent("这是个完全开放的问题哦")
        assert intent.classifier == "llm"
        assert intent.primary_intent == "anxin_assistant"
        assert intent.confidence == 0.0

    @pytest.mark.asyncio
    async def test_llm_unknown_persona_fallback(self, agent):
        bad = (
            '```json\n{"primary_intent":"non_exist",'
            '"target_personas":["non_exist","still_bad"],'
            '"confidence":0.9,"reasoning":"x"}\n```'
        )
        with patch.object(agent, "chat", new=AsyncMock(return_value=bad)):
            intent = await agent.classify_intent("这是个完全开放的问题")
        # 全部不合法 → fallback 到 anxin_assistant
        assert intent.target_personas == ["anxin_assistant"]
        assert intent.primary_intent == "anxin_assistant"

    @pytest.mark.asyncio
    async def test_llm_chat_exception_returns_entry(self, agent):
        with patch.object(agent, "chat", new=AsyncMock(side_effect=RuntimeError("LLM down"))):
            intent = await agent.classify_intent("一个完全开放的问题")
        assert intent.primary_intent == "anxin_assistant"
        assert intent.confidence == 0.0
        assert "LLM down" in intent.reasoning


# ------------------------------------------------------------------
class TestEmptyMessage:
    @pytest.mark.asyncio
    async def test_empty_message(self, agent):
        intent = await agent.classify_intent("")
        assert intent.primary_intent == "anxin_assistant"
        assert intent.confidence == 0.0
