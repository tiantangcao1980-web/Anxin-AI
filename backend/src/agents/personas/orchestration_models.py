"""
orchestration_models —— P9-A 安心助理 persona 编排相关数据类

包含：
    - IntentClassification : LLM / fast-path 路由的意图分类输出
    - RoutingDecision      : 综合 IntentClassification 后的执行决策
    - SubTask              : 拆解后的子任务（含依赖图）
    - ExecutionPlan        : 一次会话中需要跑的所有 SubTask 编排
    - OrchestrationResult  : 编排执行的最终结果（含每个 subtask 输出 + 总结）
    - GuidanceResponse     : 模糊问题时返回给用户的引导响应

设计选择：
    - **dataclass + slots** —— 避免 pydantic 依赖渗透到 agents 层；API 层另行
      在 ``schemas/persona_anxin.py`` 中维护 pydantic 镜像，二者通过 to_dict()
      / from_dict() 衔接。
    - **不直接依赖 sqlalchemy / DB Model** —— P9-A 不落库，仅内存对象；
      后续 P9-A.1 若要持久化，可在 services 层加 mapper。
    - **顺序/并发/分支** 三种 execution_mode 文案统一，在 orchestrate() 中识别。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# 意图分类
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class IntentClassification:
    """单次用户消息的意图分类结果。

    与「路由」分离 —— 同一份分类可被不同 routing 策略消费。
    """

    primary_intent: str  # e.g. "legal_consult" / "contract_review" / "market_research"
    target_personas: list[str] = field(default_factory=list)  # 推荐 persona_id（按相关性降序）
    confidence: float = 0.0  # 0~1
    reasoning: str = ""
    entities: dict[str, list[str]] = field(default_factory=dict)
    classifier: str = "fast_path"  # "fast_path" / "llm" / "hybrid"

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_intent": self.primary_intent,
            "target_personas": list(self.target_personas),
            "confidence": float(self.confidence),
            "reasoning": self.reasoning,
            "entities": {k: list(v) for k, v in self.entities.items()},
            "classifier": self.classifier,
        }


# ---------------------------------------------------------------------------
# 路由决策
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RoutingDecision:
    """根据 IntentClassification 决定真正的执行流程。"""

    primary_persona: str
    supporting_personas: list[str] = field(default_factory=list)
    execution_mode: str = "sequential"  # "sequential" / "parallel" / "branching"
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_persona": self.primary_persona,
            "supporting_personas": list(self.supporting_personas),
            "execution_mode": self.execution_mode,
            "rationale": self.rationale,
        }


# ---------------------------------------------------------------------------
# 子任务 / 执行计划
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SubTask:
    """单个 persona 上的子任务。"""

    task_id: str
    description: str
    assigned_persona: str
    depends_on: list[str] = field(default_factory=list)  # 其它 task_id
    inputs: dict[str, Any] = field(default_factory=dict)
    expected_output: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "assigned_persona": self.assigned_persona,
            "depends_on": list(self.depends_on),
            "inputs": dict(self.inputs),
            "expected_output": self.expected_output,
        }


@dataclass(slots=True)
class ExecutionPlan:
    """一次编排的全量计划。"""

    plan_id: str
    user_query: str
    subtasks: list[SubTask] = field(default_factory=list)
    total_estimated_seconds: int = 0
    execution_mode: str = "sequential"
    created_ts: float = field(default_factory=lambda: time.time())

    @classmethod
    def new(
        cls,
        user_query: str,
        subtasks: list[SubTask] | None = None,
        execution_mode: str = "sequential",
        total_estimated_seconds: int = 0,
    ) -> ExecutionPlan:
        return cls(
            plan_id=f"plan-{uuid.uuid4().hex[:12]}",
            user_query=user_query,
            subtasks=list(subtasks or []),
            execution_mode=execution_mode,
            total_estimated_seconds=total_estimated_seconds,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "user_query": self.user_query,
            "subtasks": [t.to_dict() for t in self.subtasks],
            "total_estimated_seconds": int(self.total_estimated_seconds),
            "execution_mode": self.execution_mode,
            "created_ts": float(self.created_ts),
        }


# ---------------------------------------------------------------------------
# 编排结果
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class OrchestrationResult:
    """orchestrate() 的最终输出。"""

    plan: ExecutionPlan
    subtask_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    final_summary: str = ""
    duration_ms: int = 0
    citations: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"  # ok / partial / failed
    failed_subtasks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan.to_dict(),
            "subtask_results": {k: dict(v) for k, v in self.subtask_results.items()},
            "final_summary": self.final_summary,
            "duration_ms": int(self.duration_ms),
            "citations": [dict(c) for c in self.citations],
            "status": self.status,
            "failed_subtasks": list(self.failed_subtasks),
        }


# ---------------------------------------------------------------------------
# 模糊问题引导
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class GuidanceResponse:
    """用户问题模糊时，安心助理给出的引导建议。"""

    suggested_personas: list[dict[str, str]] = field(default_factory=list)
    # 每项: { persona_id, display_name, reason, sample_question }
    follow_up_questions: list[str] = field(default_factory=list)
    quick_actions: list[dict[str, str]] = field(default_factory=list)
    # 每项: { label, persona_id, action }
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "suggested_personas": [dict(p) for p in self.suggested_personas],
            "follow_up_questions": list(self.follow_up_questions),
            "quick_actions": [dict(q) for q in self.quick_actions],
            "message": self.message,
        }
