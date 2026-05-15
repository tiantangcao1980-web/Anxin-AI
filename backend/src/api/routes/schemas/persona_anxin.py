"""安心助理 persona 路由的 Pydantic 镜像（P9-A）。

In/Out 对应 ``src.agents.personas.orchestration_models`` 中的数据类。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class ClassifyIntentIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class RouteIn(BaseModel):
    intent: dict[str, Any] = Field(
        ..., description="IntentClassification.to_dict() 的内容"
    )
    context: dict[str, Any] | None = Field(default=None)


class OrchestrateIn(BaseModel):
    plan: dict[str, Any] = Field(..., description="ExecutionPlan.to_dict() 的内容")
    context: dict[str, Any] | None = Field(default=None)


class DecomposeIn(BaseModel):
    task: str = Field(..., min_length=1, max_length=4000)


class GuideIn(BaseModel):
    vague_query: str = Field(..., min_length=1, max_length=4000)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class IntentClassificationOut(BaseModel):
    primary_intent: str
    target_personas: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    entities: dict[str, list[str]] = Field(default_factory=dict)
    classifier: str = "fast_path"


class RoutingDecisionOut(BaseModel):
    primary_persona: str
    supporting_personas: list[str] = Field(default_factory=list)
    execution_mode: str = "sequential"
    rationale: str = ""


class SubTaskOut(BaseModel):
    task_id: str
    description: str
    assigned_persona: str
    depends_on: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_output: str = ""


class ExecutionPlanOut(BaseModel):
    plan_id: str
    user_query: str
    subtasks: list[SubTaskOut] = Field(default_factory=list)
    total_estimated_seconds: int = 0
    execution_mode: str = "sequential"
    created_ts: float = 0.0


class OrchestrationResultOut(BaseModel):
    plan: ExecutionPlanOut
    subtask_results: dict[str, dict[str, Any]] = Field(default_factory=dict)
    final_summary: str = ""
    duration_ms: int = 0
    citations: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "ok"
    failed_subtasks: list[str] = Field(default_factory=list)


class GuidanceResponseOut(BaseModel):
    suggested_personas: list[dict[str, str]] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    quick_actions: list[dict[str, str]] = Field(default_factory=list)
    message: str = ""
