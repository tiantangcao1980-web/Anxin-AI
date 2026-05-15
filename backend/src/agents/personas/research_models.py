"""市场研究员（P7-B）输出物的统一数据模型。

设计原则：
    - **可序列化**：所有字段都是 stdlib 基本类型，方便经 Pydantic 镜像后
      送到 API 层（``api/routes/schemas/persona_market.py``）
    - **可累积**：``ResearchStep`` / ``Citation`` 列表式追加，便于 DeepResearch
      多轮循环增量写入
    - **可回放**：``ResearchReport.steps`` 完整保留思维链，前端可在「调研报告
      详情」抽屉里展开成时间轴
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

# ---------------------------------------------------------------------------
# 引文
# ---------------------------------------------------------------------------


@dataclass
class Citation:
    """单条引文 / 证据。

    字段语义：
        - ``source``  —— 来源标识（``fetch:flk_npc_gov`` / ``fetch:web``
          / ``knowledge_base`` / ``oauth:reddit`` 等），用于审计 + 前端
          按来源分组
        - ``url``     —— 原始 URL（fetch 出处 / kb 资源链接）
        - ``title``   —— 页面 / 文档标题
        - ``excerpt`` —— 真实引用片段（**禁止改写**，便于追溯）
        - ``confidence`` —— 0-1，模型对该证据可信度的自评
    """

    source: str
    url: str
    title: str = ""
    excerpt: str = ""
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "url": self.url,
            "title": self.title,
            "excerpt": self.excerpt,
            "confidence": float(self.confidence),
        }


# ---------------------------------------------------------------------------
# 思维链单步
# ---------------------------------------------------------------------------


@dataclass
class ResearchStep:
    """一次「想 → 查 → 综合 → 出新问题」循环。

    DeepResearch 算法以此为最小单元；多个 step 串成一份 ``ResearchReport``
    的思维链。
    """

    step_id: int
    query: str
    rationale: str = ""
    findings: list[Citation] = field(default_factory=list)
    next_questions: list[str] = field(default_factory=list)
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "query": self.query,
            "rationale": self.rationale,
            "findings": [c.to_dict() for c in self.findings],
            "next_questions": list(self.next_questions),
            "duration_ms": int(self.duration_ms),
        }


# ---------------------------------------------------------------------------
# 调研报告
# ---------------------------------------------------------------------------


@dataclass
class ResearchReport:
    """市场研究员对外的最终交付物。

    ``confidence_score`` 由 step 平均 + 引文数加权计算（``compute_confidence``
    辅助函数）。
    """

    question: str
    summary: str = ""
    findings: list[dict[str, Any]] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    steps: list[ResearchStep] = field(default_factory=list)
    confidence_score: float = 0.0
    duration_ms: int = 0
    suggested_actions: list[str] = field(default_factory=list)
    report_id: str = field(default_factory=lambda: uuid4().hex)
    created_ts: float = field(default_factory=time.time)
    persona_id: str = "market_researcher"

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "persona_id": self.persona_id,
            "question": self.question,
            "summary": self.summary,
            "findings": list(self.findings),
            "citations": [c.to_dict() for c in self.citations],
            "steps": [s.to_dict() for s in self.steps],
            "confidence_score": float(self.confidence_score),
            "duration_ms": int(self.duration_ms),
            "suggested_actions": list(self.suggested_actions),
            "created_ts": float(self.created_ts),
        }


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def compute_confidence(steps: list[ResearchStep]) -> float:
    """从思维链反推总体置信度。

    规则：
        - 所有 finding citation 的 confidence 取均值
        - 引文数 < 2 时 × 0.6（情报量不足）
        - 没有任何 finding → 0
    """
    citations: list[Citation] = []
    for s in steps:
        citations.extend(s.findings)
    if not citations:
        return 0.0
    avg = sum(c.confidence for c in citations) / len(citations)
    if len(citations) < 2:
        avg *= 0.6
    return max(0.0, min(1.0, avg))


__all__ = [
    "Citation",
    "ResearchStep",
    "ResearchReport",
    "compute_confidence",
]
