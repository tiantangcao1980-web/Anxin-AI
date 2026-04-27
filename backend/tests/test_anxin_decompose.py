# -*- coding: utf-8 -*-
"""P9-A: AnxinAssistantAgent.decompose_task / guide_user 测试。

覆盖：
    - decompose 三种 mode 产出 SubTask 依赖图正确
    - decompose 至少 1 个 subtask
    - decompose 在 sequential 模式下 depends_on 链
    - decompose 在 branching 模式下首个 subtask = anxin_assistant 条件判定
    - guide_user fast path 命中
    - guide_user 完全模糊回退到通用建议
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.agents.personas import AnxinAssistantAgent, PersonaRegistry
from src.agents.personas.orchestration_models import (
    IntentClassification,
    RoutingDecision,
)


@pytest.fixture(autouse=True)
def _reset_registry():
    PersonaRegistry.reset_instance()
    yield
    PersonaRegistry.reset_instance()


@pytest.fixture
def agent():
    with patch("src.agents.base.get_llm_config_sync", return_value=None):
        return AnxinAssistantAgent()


# ------------------------------------------------------------------
class TestDecompose:
    @pytest.mark.asyncio
    async def test_sequential_chain(self, agent):
        decision = RoutingDecision(
            primary_persona="contract_steward",
            supporting_personas=["operations_manager"],
            execution_mode="sequential",
        )
        plan = await agent.decompose_task("起草合同 然后 发审批", decision=decision)
        assert plan.execution_mode == "sequential"
        assert len(plan.subtasks) == 2
        # 链式 depends_on
        assert plan.subtasks[0].depends_on == []
        assert plan.subtasks[1].depends_on == [plan.subtasks[0].task_id]
        assert plan.subtasks[0].assigned_persona == "contract_steward"
        assert plan.subtasks[1].assigned_persona == "operations_manager"
        assert plan.user_query.startswith("起草合同")
        assert plan.total_estimated_seconds >= 15

    @pytest.mark.asyncio
    async def test_parallel_independent(self, agent):
        decision = RoutingDecision(
            primary_persona="market_researcher",
            supporting_personas=["ecommerce_assistant"],
            execution_mode="parallel",
        )
        plan = await agent.decompose_task("调研 同时 议价", decision=decision)
        assert plan.execution_mode == "parallel"
        assert len(plan.subtasks) == 2
        for st in plan.subtasks:
            assert st.depends_on == []

    @pytest.mark.asyncio
    async def test_branching_first_is_anxin(self, agent):
        decision = RoutingDecision(
            primary_persona="market_researcher",
            supporting_personas=["ecommerce_assistant"],
            execution_mode="branching",
        )
        plan = await agent.decompose_task("如果是大公司就调研否则议价", decision=decision)
        assert plan.execution_mode == "branching"
        # 首个子任务应是 anxin_assistant 做条件判定
        assert plan.subtasks[0].assigned_persona == "anxin_assistant"
        assert plan.subtasks[0].depends_on == []
        cond_id = plan.subtasks[0].task_id
        # 后续每个分支都依赖 cond
        for st in plan.subtasks[1:]:
            assert st.depends_on == [cond_id]

    @pytest.mark.asyncio
    async def test_decompose_dedup_personas(self, agent):
        # 故意制造重复 persona
        decision = RoutingDecision(
            primary_persona="contract_steward",
            supporting_personas=["contract_steward", "operations_manager"],
            execution_mode="parallel",
        )
        plan = await agent.decompose_task("x", decision=decision)
        personas = [st.assigned_persona for st in plan.subtasks]
        # contract_steward 不应出现两次
        assert personas.count("contract_steward") == 1
        assert "operations_manager" in personas

    @pytest.mark.asyncio
    async def test_decompose_uses_intent_when_no_decision(self, agent):
        """当 decision=None 且 intent 命中 fast-path 关键词时，应自动 route 一次。"""
        plan = await agent.decompose_task("帮我起草合同 并对供应商做尽调")
        assert len(plan.subtasks) >= 2
        assigned = {st.assigned_persona for st in plan.subtasks}
        assert "contract_steward" in assigned
        assert "due_diligence_expert" in assigned

    @pytest.mark.asyncio
    async def test_decompose_at_least_one_subtask(self, agent):
        # 即使 intent 完全空，也兜底产出 anxin_assistant 1 个 subtask
        decision = RoutingDecision(
            primary_persona="",
            supporting_personas=[],
            execution_mode="sequential",
        )
        plan = await agent.decompose_task("hi", decision=decision)
        assert len(plan.subtasks) >= 1
        assert plan.subtasks[0].assigned_persona == "anxin_assistant"


# ------------------------------------------------------------------
class TestGuideUser:
    @pytest.mark.asyncio
    async def test_guide_with_fast_path_hit(self, agent):
        guide = await agent.guide_user("帮我看看合同问题")
        # 至少推荐 contract_steward
        ids = [s["persona_id"] for s in guide.suggested_personas]
        assert "contract_steward" in ids
        assert guide.follow_up_questions
        assert guide.quick_actions
        assert guide.message

    @pytest.mark.asyncio
    async def test_guide_full_vague_returns_generic_three(self, agent):
        guide = await agent.guide_user("我有点焦虑")
        assert len(guide.suggested_personas) == 3
        # 含 sample_question
        for s in guide.suggested_personas:
            assert s["display_name"]
            assert s["reason"]

    @pytest.mark.asyncio
    async def test_guide_quick_actions_link_to_personas(self, agent):
        guide = await agent.guide_user("帮我做一个调研")
        ids = {s["persona_id"] for s in guide.suggested_personas}
        action_ids = {q["persona_id"] for q in guide.quick_actions}
        assert ids == action_ids
        assert all(q["action"] == "open_persona" for q in guide.quick_actions)


# ------------------------------------------------------------------
class TestIntentClassificationDataclass:
    def test_intent_to_dict_roundtrip(self):
        intent = IntentClassification(
            primary_intent="legal_advisor",
            target_personas=["legal_advisor"],
            confidence=0.8,
            reasoning="x",
            entities={"company": ["A"]},
            classifier="fast_path",
        )
        d = intent.to_dict()
        assert d["primary_intent"] == "legal_advisor"
        assert d["confidence"] == 0.8
        assert d["entities"] == {"company": ["A"]}
