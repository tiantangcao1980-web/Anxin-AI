"""尽调专家（due_diligence_expert）persona 的数据模型。

设计原则：
    - 仅 dataclass，不依赖 ORM / FastAPI / 持久层；API 层用独立 Pydantic
      schema 镜像（``api/routes/schemas/persona_dd.py``）
    - ``Citation`` 直接复用 ``research_models.Citation``，避免 schema 漂移；
      尽调结论的可追溯性与 P7-B 市场研究员保持一致
    - 所有 dict / list 默认值统一用 ``field(default_factory=...)``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from src.agents.personas.research_models import Citation

# ---------------------------------------------------------------------------
# 公司基础工商信息
# ---------------------------------------------------------------------------


@dataclass
class CompanyBasicInfo:
    """工商公开数据 + 信用中国「主体登记」字段映射。"""

    name: str
    legal_representative: str
    registered_capital: float          # 单位：万元
    establishment_date: date
    business_scope: str
    industry: str
    address: str
    unified_credit_code: str           # 18 位 USCC
    status: str                        # "存续" / "注销" / "吊销" / "迁出" / "停业"


# ---------------------------------------------------------------------------
# 诉讼记录
# ---------------------------------------------------------------------------


@dataclass
class LitigationRecord:
    """单条诉讼/仲裁记录。

    ``role`` 取值：
        - "plaintiff"    — 原告（主动起诉，正向信号）
        - "defendant"    — 被告（被起诉，负向信号）
        - "third_party"  — 第三人 / 仲裁参与方
    """

    case_number: str
    case_type: str
    court: str
    role: str
    amount_disputed: float | None = None
    judgment_date: date | None = None
    judgment_summary: str = ""
    full_text_url: str = ""


# ---------------------------------------------------------------------------
# 信用瑕疵
# ---------------------------------------------------------------------------


@dataclass
class CreditFlag:
    """信用瑕疵旗标（来源信用中国 / 税务局公告 / 法院失信名单）。

    ``flag_type`` 常见取值：
        - "tax_default"             税务违法/欠税
        - "court_default"           失信被执行人
        - "administrative_penalty"  行政处罚
        - "abnormal_operation"      经营异常
        - "consumption_restriction" 限制高消费
    ``severity`` ∈ {"low", "medium", "high", "critical"}。
    """

    flag_type: str
    description: str
    issued_date: date
    issuing_authority: str
    severity: str = "medium"


# ---------------------------------------------------------------------------
# 尽调主报告
# ---------------------------------------------------------------------------


@dataclass
class DueDiligenceReport:
    """完整尽调报告（公司 / 项目 / 人物三态共用）。"""

    target: str
    target_type: str                   # "company" / "person" / "project"
    investigation_depth: str           # "quick" / "standard" / "deep"
    basic_info: CompanyBasicInfo | None = None
    shareholders: list[dict[str, Any]] = field(default_factory=list)
    key_personnel: list[dict[str, Any]] = field(default_factory=list)
    litigation_records: list[LitigationRecord] = field(default_factory=list)
    credit_flags: list[CreditFlag] = field(default_factory=list)
    intellectual_properties: list[dict[str, Any]] = field(default_factory=list)
    public_news_count: int = 0
    overall_risk_level: str = "unknown"   # low / medium / high / critical / unknown
    summary: str = ""
    recommendations: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)
    citations: list[Citation] = field(default_factory=list)
    report_id: str = ""                # 由调用方/服务层填写，用于缓存键


# ---------------------------------------------------------------------------
# 证据分析结果
# ---------------------------------------------------------------------------


@dataclass
class EvidenceAnalysis:
    """文档可信度 + 是否支持给定主张的分析结果。

    ``authenticity_score`` ∈ [0,1]：
        - 1.0  无任何造假指标
        - 0.5  存在中等可疑信号
        - 0.0  明显伪造（章/抬头/落款不一致 等）
    """

    document_summary: str
    claim: str
    supports_claim: bool
    confidence: float                  # 0-1
    supporting_excerpts: list[str] = field(default_factory=list)
    contradicting_excerpts: list[str] = field(default_factory=list)
    inconsistencies: list[str] = field(default_factory=list)
    authenticity_score: float = 0.5    # 0-1, 文档真实性
    forgery_indicators: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 舆情报告
# ---------------------------------------------------------------------------


@dataclass
class SentimentReport:
    """指定主体在指定时间段的多源舆情聚合。"""

    target: str
    period_start: date
    period_end: date
    overall_sentiment: str             # positive / neutral / negative / mixed
    sentiment_score: float             # -1 到 +1
    volume: int = 0                    # 提及次数
    by_source: dict[str, dict[str, Any]] = field(default_factory=dict)
    top_topics: list[dict[str, Any]] = field(default_factory=list)
    notable_events: list[dict[str, Any]] = field(default_factory=list)
    trend: str = "stable"              # improving / stable / deteriorating


# ---------------------------------------------------------------------------
# 关系图谱
# ---------------------------------------------------------------------------


@dataclass
class RelationshipNode:
    id: str
    name: str
    type: str                          # person / company / asset
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class RelationshipEdge:
    """有向边：from_id ─relationship→ to_id。

    ``relationship`` 常见取值：
        - "owns"            股东 → 企业
        - "controls"        实控人 → 企业
        - "invests_in"      投资关系
        - "supplies"        供货关系
        - "litigates_with"  涉诉关系（双向，但保留有向以便区分原/被）
        - "managed_by"      高管任职
    """

    from_id: str
    to_id: str
    relationship: str
    confidence: float = 0.8
    source: str = ""                   # 数据出处（"qichacha" / "litigation" / ...）


@dataclass
class RelationshipGraph:
    """实体关系图。``risk_paths`` 记录由风险等级跳转的高风险传导链。"""

    root_entity: str
    nodes: list[RelationshipNode] = field(default_factory=list)
    edges: list[RelationshipEdge] = field(default_factory=list)
    depth: int = 0
    risk_paths: list[list[str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 风险分级
# ---------------------------------------------------------------------------


@dataclass
class RiskGrade:
    """综合风险等级（参考标普 / 穆迪信用等级体系）。"""

    grade: str                         # AAA / AA / A / BBB / BB / B / C / D
    score: float                       # 0-100，越高越好
    breakdown: dict[str, float] = field(default_factory=dict)
    rationale: str = ""
    red_flags: list[str] = field(default_factory=list)
    recommended_action: str = "monitor"  # trust / verify_more / monitor / avoid


__all__ = [
    "CompanyBasicInfo",
    "LitigationRecord",
    "CreditFlag",
    "DueDiligenceReport",
    "EvidenceAnalysis",
    "SentimentReport",
    "RelationshipNode",
    "RelationshipEdge",
    "RelationshipGraph",
    "RiskGrade",
]
