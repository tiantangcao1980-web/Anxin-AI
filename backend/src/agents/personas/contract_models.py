"""合同管家 persona —— 数据模型（P9-C）。

本模块为 ``ContractStewardPersona`` 6 大能力（起草 / 审查 / 风险 / 模板 /
对比 / 归档）提供强类型出参契约。

设计取舍
--------
- **dataclass 而非 pydantic**：persona 内部能力契约保持轻量；API 层走
  ``api/routes/schemas/persona_contract.py`` 的 pydantic 镜像。
- **`severity` / `recommendation` 用字符串枚举值**：避免和上游 21 个
  specialized agent 已经使用的字符串风格不一致；测试可直接断言字面值。
- **`Citation` 复用 ``research_models.Citation``**：法律条文引用本质和
  市场研究引文同构（来源 + URL + 摘要 + 置信度），统一一个类型方便前端
  下钻溯源组件复用。
- **金额 / 评分用 float，非 Decimal**：合同管家不直接做出纳，金额是
  「条款描述」级别；JSON 序列化也无 decimal 痛。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.agents.personas.research_models import Citation

# ---------------------------------------------------------------------------
# 1. 起草
# ---------------------------------------------------------------------------


@dataclass
class ContractDraft:
    """合同起草输出。

    - ``contract_type``：归一后的合同类型（``"采购合同"`` / ``"NDA"`` 等）。
    - ``sections``：分节结构 ``[{title, content, optional}]``，前端按章节渲染。
    - ``suggested_clauses``：可选追加条款（如「不可抗力」「数据保护」），
      包含 ``{title, rationale, content}``，让用户决定是否插入。
    - ``estimated_word_count``：正文实际字数（不含模板占位符）。
    - ``docx_template_path``：与 P5-B docx skill 对接 —— ``draft_contract``
      渲染完成后可写入临时 .docx，路径回填此字段；未渲染时为 ``None``。
    """

    contract_type: str
    title: str
    full_text: str
    sections: list[dict] = field(default_factory=list)
    suggested_clauses: list[dict] = field(default_factory=list)
    estimated_word_count: int = 0
    language: str = "zh"
    docx_template_path: str | None = None


# ---------------------------------------------------------------------------
# 2. 审查
# ---------------------------------------------------------------------------


@dataclass
class ReviewIssue:
    """单条审查问题。

    - ``issue_type`` ∈ ``{"missing", "ambiguous", "biased", "illegal"}``：
      missing = 缺失关键条款；ambiguous = 用语模糊；biased = 单方面有利；
      illegal = 触犯强制性规定。
    - ``severity`` ∈ ``{"critical", "high", "medium", "low"}``。
    - ``location``：``{section, page?, paragraph?}``，前端用于跳转高亮。
    """

    clause_text: str
    issue_type: str
    severity: str
    description: str
    suggested_revision: str
    location: dict = field(default_factory=dict)


@dataclass
class ReviewReport:
    """合同审查总报告。

    - ``perspective`` ∈ ``{"buyer", "seller", "neutral"}``：审查立场，决定
      「单方面有利」类问题的判定方向。
    - ``score``：0-100，越高越对己方（``perspective``）有利。
    - ``recommendation`` ∈ ``{"sign_as_is", "negotiate", "redline", "reject"}``：
      具体动作建议，前端按此分流到「直接签 / 拉清单谈 / 红线版改 / 拒绝」。
    """

    overall_assessment: str
    perspective: str
    score: float
    issues: list[ReviewIssue] = field(default_factory=list)
    missing_clauses: list[str] = field(default_factory=list)
    redundant_clauses: list[str] = field(default_factory=list)
    recommendation: str = "negotiate"


# ---------------------------------------------------------------------------
# 3. 风险识别
# ---------------------------------------------------------------------------


@dataclass
class RiskAnalysis:
    """合同风险全景分析。

    - ``overall_risk_level`` ∈ ``{"low", "medium", "high", "critical"}``。
    - ``risks``：每项形如 ``{category, description, likelihood, impact,
      mitigation}``；likelihood / impact 都是 0-1 浮点。
    - ``blacklist_clauses``：触发禁用条款的原文片段列表 —— 比如「保证最低
      销售额」「单方面任意终止」等业内黑名单条款。
    - ``legal_basis``：每条风险背后的法条引用，前端用于「点风险看法条」。
    """

    overall_risk_level: str
    risks: list[dict] = field(default_factory=list)
    blacklist_clauses: list[str] = field(default_factory=list)
    legal_basis: list[Citation] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 4. 模板检索
# ---------------------------------------------------------------------------


@dataclass
class Template:
    """模板库单条记录。

    与 ``backend/src/agents/template_librarian.py::TEMPLATE_CATALOG`` 一一
    对应，但额外补充了 ``last_used`` 与 ``download_url``，让前端可以做
    「最近使用」与「直接下载」两种快捷入口。
    """

    template_id: str
    name: str
    contract_type: str
    description: str
    use_case: str = ""
    language: str = "zh"
    word_count: int = 0
    last_used: datetime | None = None
    download_url: str = ""


# ---------------------------------------------------------------------------
# 5. 版本对比
# ---------------------------------------------------------------------------


@dataclass
class VersionDiff:
    """两版合同对比结果。

    - ``additions`` / ``deletions`` / ``modifications`` 都是带定位信息的
      列表，方便前端渲染左右对照视图。
    - ``semantic_changes``：语义级关键变化（不是逐字 diff，而是 LLM 概括
      出的「权利义务变化」），用自然语言数组返回。
    """

    v1_summary: str
    v2_summary: str
    additions: list[dict] = field(default_factory=list)
    deletions: list[dict] = field(default_factory=list)
    modifications: list[dict] = field(default_factory=list)
    semantic_changes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 6. 归档
# ---------------------------------------------------------------------------


@dataclass
class ArchiveResult:
    """归档动作返回结果。

    - ``archive_url``：归档后的访问 URL（OSS / 本地路径），前端做「查看
      归档版」按钮的目标。
    - ``retention_period_days``：保留天数；不同合同类型法定保留期不同
      （税务凭证 10 年、合规审计 5 年等），由调用方传入或采用默认 1825 天
      （5 年，覆盖大多数民商事追诉期）。
    """

    contract_id: str
    archive_url: str
    metadata: dict = field(default_factory=dict)
    archived_at: datetime = field(default_factory=datetime.utcnow)
    retention_period_days: int = 1825


__all__ = [
    "ContractDraft",
    "ReviewIssue",
    "ReviewReport",
    "RiskAnalysis",
    "Template",
    "VersionDiff",
    "ArchiveResult",
    "Citation",
]
