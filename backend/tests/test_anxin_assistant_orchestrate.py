# -*- coding: utf-8 -*-
"""P9-A: AnxinAssistantAgent.orchestrate 三种执行模式测试。

覆盖：
    - sequential : 上下游 t1 → t2 输出对接
    - parallel   : 多 persona 并发，gather 后聚合
    - branching  : 条件 task 选中 1 个分支，其余 skipped
    - 降级        : persona 未注册 → 单 subtask failed，partial
                  : 全部 subtask failed → status=failed，建议转人工
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.personas import AnxinAssistantAgent, PersonaRegistry
from src.agents.personas.base_persona import BasePersonaAgent
from src.agents.personas.orchestration_models import (
    ExecutionPlan,
    SubTask,
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
# Stub persona —— 注册到 registry 以模拟 P9-B/C/D/E
# ------------------------------------------------------------------
def _make_stub_persona(pid: str, display: str, response_text: str):
    """动态生成 BasePersonaAgent 子类（自动 __init_subclass__ 注册）。"""
    cls = type(
        f"Stub_{pid}",
        (BasePersonaAgent,),
        {
            "persona_id": pid,
            "display_name": display,
            "emoji": "🧪",
            "description": f"stub for {pid}",
            "SYSTEM_PROMPT": f"stub for {pid}",
            "capabilities": [],
            "backed_by_skills": [],
            "supported_apps": [],
            "_stub_resp": response_text,
        },
    )

    # 动态附加 handle_message
    async def _handle(self, message, user_id=None, llm_config=None, history=None, extra=None):
        return f"[{self.persona_id}] {self._stub_resp} | input={message[:40]}"

    cls.handle_message = _handle
    return cls


def _ensure_stub(pid: str, display: str = "", text: str = "ok") -> None:
    """注册 stub persona class（已注册不重复创建）。"""
    if PersonaRegistry.instance().has(pid):
        return
    cls = _make_stub_persona(pid, display or pid, text)
    # __init_subclass__ 已自动注册；但 reset_instance 后需 re-import 才能命中
    PersonaRegistry.instance().register(cls)
    # 用 patch 让实例化时不去找 LLM
    PersonaRegistry.instance()._instances[pid] = cls.__new__(cls)
    inst = PersonaRegistry.instance()._instances[pid]
    inst._stub_resp = text  # type: ignore[attr-defined]
    inst.persona_id = pid  # type: ignore[attr-defined]
    inst.name = display or pid  # type: ignore[attr-defined]


# ------------------------------------------------------------------
class TestSequential:
    @pytest.mark.asyncio
    async def test_sequential_two_steps_pass_output(self, agent):
        _ensure_stub("contract_steward", "合同管家", "已起草合同 v1")
        _ensure_stub("operations_manager", "流程管家", "已发审批")

        plan = ExecutionPlan.new(
            user_query="起草采购合同并发审批",
            subtasks=[
                SubTask(
                    task_id="s1",
                    description="起草采购合同",
                    assigned_persona="contract_steward",
                    depends_on=[],
                    inputs={"task": "起草采购合同"},
                    expected_output="合同草稿",
                ),
                SubTask(
                    task_id="s2",
                    description="发审批",
                    assigned_persona="operations_manager",
                    depends_on=["s1"],
                    inputs={"task": "发审批"},
                    expected_output="审批已发起",
                ),
            ],
            execution_mode="sequential",
        )
        # mock 自身 _summarize 直接返回固定文本，避免依赖 chat
        with patch.object(
            agent,
            "_summarize",
            new=AsyncMock(return_value="# 总结\n所有步骤完成"),
        ):
            result = await agent.orchestrate(plan)

        assert result.status == "ok"
        assert result.subtask_results["s1"]["status"] == "ok"
        assert result.subtask_results["s2"]["status"] == "ok"
        # 第二步收到的 message 必须包含第一步输出
        assert "已起草合同 v1" in result.subtask_results["s2"]["output"]
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_sequential_first_fails_aborts(self, agent):
        # 不注册 contract_steward → 触发 KeyError 降级
        plan = ExecutionPlan.new(
            user_query="起草采购合同并发审批",
            subtasks=[
                SubTask(
                    task_id="s1",
                    description="起草采购合同",
                    assigned_persona="contract_steward",
                    depends_on=[],
                    inputs={"task": "起草"},
                ),
                SubTask(
                    task_id="s2",
                    description="发审批",
                    assigned_persona="operations_manager",
                    depends_on=["s1"],
                    inputs={"task": "发审批"},
                ),
            ],
            execution_mode="sequential",
        )
        with patch.object(agent, "_summarize", new=AsyncMock(return_value="x")):
            result = await agent.orchestrate(plan)

        assert "s1" in result.failed_subtasks
        assert result.subtask_results["s1"]["status"] == "failed"
        # s2 因 s1 失败被中止 → 没有进入 results
        assert "s2" not in result.subtask_results
        assert result.status in ("partial", "failed")


# ------------------------------------------------------------------
class TestParallel:
    @pytest.mark.asyncio
    async def test_parallel_aggregates(self, agent):
        _ensure_stub("market_researcher", "市场研究员", "调研结果 A")
        _ensure_stub("ecommerce_assistant", "跨境电商助手", "议价方案 B")

        plan = ExecutionPlan.new(
            user_query="调研某公司 并 准备议价方案",
            subtasks=[
                SubTask(
                    task_id="p1",
                    description="调研",
                    assigned_persona="market_researcher",
                    depends_on=[],
                    inputs={"task": "调研某公司"},
                ),
                SubTask(
                    task_id="p2",
                    description="议价",
                    assigned_persona="ecommerce_assistant",
                    depends_on=[],
                    inputs={"task": "准备议价方案"},
                ),
            ],
            execution_mode="parallel",
        )
        with patch.object(agent, "_summarize", new=AsyncMock(return_value="# 汇总")):
            result = await agent.orchestrate(plan)

        assert result.status == "ok"
        assert result.subtask_results["p1"]["status"] == "ok"
        assert result.subtask_results["p2"]["status"] == "ok"
        assert "调研结果 A" in result.subtask_results["p1"]["output"]
        assert "议价方案 B" in result.subtask_results["p2"]["output"]

    @pytest.mark.asyncio
    async def test_parallel_partial_failure(self, agent):
        _ensure_stub("market_researcher", "市场研究员", "调研 OK")
        # 不注册 ecommerce_assistant，模拟单边降级

        plan = ExecutionPlan.new(
            user_query="调研 + 议价",
            subtasks=[
                SubTask(
                    task_id="p1",
                    description="调研",
                    assigned_persona="market_researcher",
                    depends_on=[],
                    inputs={"task": "调研"},
                ),
                SubTask(
                    task_id="p2",
                    description="议价",
                    assigned_persona="ecommerce_assistant",
                    depends_on=[],
                    inputs={"task": "议价"},
                ),
            ],
            execution_mode="parallel",
        )
        with patch.object(agent, "_summarize", new=AsyncMock(return_value="x")):
            result = await agent.orchestrate(plan)
        assert result.status == "partial"
        assert "p2" in result.failed_subtasks
        assert result.subtask_results["p1"]["status"] == "ok"
        assert result.subtask_results["p2"]["status"] == "failed"


# ------------------------------------------------------------------
class TestBranching:
    @pytest.mark.asyncio
    async def test_branching_picks_one(self, agent):
        _ensure_stub("market_researcher", "市场研究员", "走 A")
        _ensure_stub("ecommerce_assistant", "跨境电商助手", "走 B")

        # 让条件判定（assigned=anxin_assistant）返回选中 market_researcher 的 JSON
        cond_json = (
            '```json\n{"chosen_branch":"market_researcher","reason":"是大公司"}\n```'
        )
        with patch.object(agent, "chat", new=AsyncMock(return_value=cond_json)), patch.object(
            agent, "_summarize", new=AsyncMock(return_value="# 总结")
        ):
            plan = ExecutionPlan.new(
                user_query="如果是大公司就调研，否则议价",
                subtasks=[
                    SubTask(
                        task_id="cond",
                        description="判定",
                        assigned_persona="anxin_assistant",
                        depends_on=[],
                        inputs={"task": "如果是大公司..."},
                    ),
                    SubTask(
                        task_id="b1",
                        description="A 分支",
                        assigned_persona="market_researcher",
                        depends_on=["cond"],
                        inputs={"task": "调研"},
                    ),
                    SubTask(
                        task_id="b2",
                        description="B 分支",
                        assigned_persona="ecommerce_assistant",
                        depends_on=["cond"],
                        inputs={"task": "议价"},
                    ),
                ],
                execution_mode="branching",
            )
            result = await agent.orchestrate(plan)

        assert result.subtask_results["cond"]["status"] == "ok"
        assert result.subtask_results["b1"]["status"] == "ok"
        assert result.subtask_results["b2"]["status"] == "skipped"
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_branching_cond_fails_skips_all(self, agent):
        _ensure_stub("market_researcher", "市场研究员", "走 A")

        # 条件判定 chat 抛错
        with patch.object(
            agent, "chat", new=AsyncMock(side_effect=RuntimeError("cond err"))
        ), patch.object(agent, "_summarize", new=AsyncMock(return_value="x")):
            plan = ExecutionPlan.new(
                user_query="如果...",
                subtasks=[
                    SubTask(
                        task_id="cond",
                        description="判定",
                        assigned_persona="anxin_assistant",
                        depends_on=[],
                        inputs={"task": "x"},
                    ),
                    SubTask(
                        task_id="b1",
                        description="分支 A",
                        assigned_persona="market_researcher",
                        depends_on=["cond"],
                        inputs={"task": "x"},
                    ),
                ],
                execution_mode="branching",
            )
            result = await agent.orchestrate(plan)

        assert result.subtask_results["cond"]["status"] == "failed"
        assert result.subtask_results["b1"]["status"] == "skipped"
        assert result.status == "failed"


# ------------------------------------------------------------------
class TestEmptyPlan:
    @pytest.mark.asyncio
    async def test_empty_plan(self, agent):
        plan = ExecutionPlan.new(user_query="x", subtasks=[], execution_mode="sequential")
        result = await agent.orchestrate(plan)
        assert result.status == "ok"
        assert result.subtask_results == {}
        assert result.failed_subtasks == []


# ------------------------------------------------------------------
class TestRoutingDecision:
    @pytest.mark.asyncio
    async def test_route_decision_default_sequential_single(self, agent):
        from src.agents.personas.orchestration_models import IntentClassification

        intent = IntentClassification(
            primary_intent="contract_steward",
            target_personas=["contract_steward"],
            confidence=0.8,
        )
        decision = await agent.route_to_persona(intent, context={"user_message": "起草合同"})
        assert decision.primary_persona == "contract_steward"
        assert decision.execution_mode == "sequential"

    @pytest.mark.asyncio
    async def test_route_decision_parallel_default_for_multi(self, agent):
        from src.agents.personas.orchestration_models import IntentClassification

        intent = IntentClassification(
            primary_intent="market_researcher",
            target_personas=["market_researcher", "ecommerce_assistant"],
            confidence=0.8,
        )
        decision = await agent.route_to_persona(intent, context={"user_message": "调研 同时 议价"})
        assert decision.execution_mode == "parallel"
        assert "ecommerce_assistant" in decision.supporting_personas

    @pytest.mark.asyncio
    async def test_route_decision_branching_on_if(self, agent):
        from src.agents.personas.orchestration_models import IntentClassification

        intent = IntentClassification(
            primary_intent="market_researcher",
            target_personas=["market_researcher", "ecommerce_assistant"],
            confidence=0.8,
        )
        decision = await agent.route_to_persona(
            intent, context={"user_message": "如果是大公司就调研否则议价"}
        )
        assert decision.execution_mode == "branching"
