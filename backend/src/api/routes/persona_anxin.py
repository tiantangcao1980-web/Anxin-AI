"""安心助理（anxin_assistant）persona 路由 —— P9-A。

挂载点（在 ``api/routes/__init__.py`` 用 ``prefix="/personas/anxin"`` 注册）::

    POST  /api/v1/personas/anxin/classify-intent   body: { message }
    POST  /api/v1/personas/anxin/route             body: { intent, context }
    POST  /api/v1/personas/anxin/orchestrate       body: { plan, context }
    POST  /api/v1/personas/anxin/decompose         body: { task }
    POST  /api/v1/personas/anxin/guide             body: { vague_query }

设计说明：
    - **agent 单例**：进程内共用一个 ``AnxinAssistantAgent``。测试可通过
      ``set_agent_for_test()`` 替换。
    - **不持久化**：plan / orchestration result 全部在内存对象层流转。
    - **鉴权**：复用全局 ``get_current_user_required``。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.agents.personas.anxin_assistant import AnxinAssistantAgent
from src.agents.personas.orchestration_models import (
    ExecutionPlan,
    IntentClassification,
    SubTask,
)
from src.api.routes.schemas.persona_anxin import (
    ClassifyIntentIn,
    DecomposeIn,
    ExecutionPlanOut,
    GuidanceResponseOut,
    GuideIn,
    IntentClassificationOut,
    OrchestrateIn,
    OrchestrationResultOut,
    RouteIn,
    RoutingDecisionOut,
    SubTaskOut,
)
from src.core.deps import get_current_user_required
from src.models.user import User

router = APIRouter()


# ---------------------------------------------------------------------------
# 单例 + 测试钩子
# ---------------------------------------------------------------------------


_agent: AnxinAssistantAgent | None = None


def get_anxin_agent() -> AnxinAssistantAgent:
    """获取（懒构造）全局 ``AnxinAssistantAgent``。"""
    global _agent
    if _agent is None:
        _agent = AnxinAssistantAgent()
    return _agent


def set_agent_for_test(agent: AnxinAssistantAgent | None) -> None:
    """单测专用：替换 / 重置全局 agent。"""
    global _agent
    _agent = agent


# ---------------------------------------------------------------------------
# 序列化辅助
# ---------------------------------------------------------------------------


def _ser_plan(p: ExecutionPlan) -> ExecutionPlanOut:
    return ExecutionPlanOut(
        plan_id=p.plan_id,
        user_query=p.user_query,
        subtasks=[SubTaskOut(**st.to_dict()) for st in p.subtasks],
        total_estimated_seconds=p.total_estimated_seconds,
        execution_mode=p.execution_mode,
        created_ts=p.created_ts,
    )


def _plan_from_dict(data: dict) -> ExecutionPlan:
    """从 API 收到的 dict 构造 ExecutionPlan（容错最少必需字段）。"""
    raw_subtasks = data.get("subtasks") or []
    subtasks: list[SubTask] = []
    for raw in raw_subtasks:
        if not isinstance(raw, dict):
            continue
        subtasks.append(
            SubTask(
                task_id=str(raw.get("task_id") or ""),
                description=str(raw.get("description") or ""),
                assigned_persona=str(raw.get("assigned_persona") or "anxin_assistant"),
                depends_on=[str(x) for x in (raw.get("depends_on") or [])],
                inputs=dict(raw.get("inputs") or {}),
                expected_output=str(raw.get("expected_output") or ""),
            )
        )
    return ExecutionPlan(
        plan_id=str(data.get("plan_id") or "plan-from-api"),
        user_query=str(data.get("user_query") or ""),
        subtasks=subtasks,
        total_estimated_seconds=int(data.get("total_estimated_seconds") or 0),
        execution_mode=str(data.get("execution_mode") or "sequential"),
        created_ts=float(data.get("created_ts") or 0.0),
    )


def _intent_from_dict(data: dict) -> IntentClassification:
    return IntentClassification(
        primary_intent=str(data.get("primary_intent") or "anxin_assistant"),
        target_personas=[str(x) for x in (data.get("target_personas") or [])],
        confidence=float(data.get("confidence") or 0.0),
        reasoning=str(data.get("reasoning") or ""),
        entities={
            str(k): [str(x) for x in (v or [])]
            for k, v in (data.get("entities") or {}).items()
        },
        classifier=str(data.get("classifier") or "fast_path"),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/classify-intent",
    response_model=IntentClassificationOut,
    summary="意图分类（fast path + LLM fallback）",
)
async def classify_intent(
    payload: ClassifyIntentIn,
    _user: User = Depends(get_current_user_required),
) -> IntentClassificationOut:
    agent = get_anxin_agent()
    intent = await agent.classify_intent(payload.message)
    return IntentClassificationOut(**intent.to_dict())


@router.post(
    "/route",
    response_model=RoutingDecisionOut,
    summary="路由决策（产生 primary/supporting persona + 执行模式）",
)
async def route_to_persona(
    payload: RouteIn,
    _user: User = Depends(get_current_user_required),
) -> RoutingDecisionOut:
    agent = get_anxin_agent()
    intent = _intent_from_dict(payload.intent)
    decision = await agent.route_to_persona(intent, context=payload.context or {})
    return RoutingDecisionOut(**decision.to_dict())


@router.post(
    "/orchestrate",
    response_model=OrchestrationResultOut,
    summary="执行编排计划（顺序 / 并发 / 分支）",
)
async def orchestrate(
    payload: OrchestrateIn,
    _user: User = Depends(get_current_user_required),
) -> OrchestrationResultOut:
    agent = get_anxin_agent()
    plan = _plan_from_dict(payload.plan)
    result = await agent.orchestrate(plan, context=payload.context or {})
    return OrchestrationResultOut(
        plan=_ser_plan(result.plan),
        subtask_results=result.subtask_results,
        final_summary=result.final_summary,
        duration_ms=result.duration_ms,
        citations=result.citations,
        status=result.status,
        failed_subtasks=list(result.failed_subtasks),
    )


@router.post(
    "/decompose",
    response_model=ExecutionPlanOut,
    summary="把任务拆成子任务依赖图（DAG）",
)
async def decompose(
    payload: DecomposeIn,
    _user: User = Depends(get_current_user_required),
) -> ExecutionPlanOut:
    agent = get_anxin_agent()
    plan = await agent.decompose_task(payload.task)
    return _ser_plan(plan)


@router.post(
    "/guide",
    response_model=GuidanceResponseOut,
    summary="模糊问题引导（推荐 persona + 跟进问题 + 快捷动作）",
)
async def guide(
    payload: GuideIn,
    _user: User = Depends(get_current_user_required),
) -> GuidanceResponseOut:
    agent = get_anxin_agent()
    guidance = await agent.guide_user(payload.vague_query)
    return GuidanceResponseOut(**guidance.to_dict())
