# -*- coding: utf-8 -*-
"""ContractStewardPersona —— 6 capability 单元测试（P9-C）。

不依赖 DB / 路由层；用 mock specialized agent 注入 persona。

覆盖：
    1. draft_contract  — drafter 注入 / fallback / docx 占位
    2. review_contract — reviewer + checker 协同 / perspective 守卫
    3. identify_risks  — investigator 注入 / 黑名单条款命中
    4. find_template   — 关键词命中 / 类型命中 / 空 query 报错
    5. compare_versions — additions / deletions / modifications / semantic
    6. archive          — 默认保留期 / 自定义保留期 / 合同类型路由
    7. metadata 一致性
"""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.personas.contract_models import (
    ArchiveResult,
    ContractDraft,
    ReviewReport,
    RiskAnalysis,
    Template,
    VersionDiff,
)
from src.agents.personas.contract_steward import ContractStewardPersona


# ---------------------------------------------------------------------------
# 测试夹具
# ---------------------------------------------------------------------------


class _MockDrafter:
    """模拟 DocumentDraftAgent.draft_contract。"""

    def __init__(self, text: str = ""):
        self.text = text or (
            "## 第一条 合同标的\n甲方采购乙方提供的标准化产品。\n"
            "## 第二条 价款与支付\n人民币 100 万元，30/70 分期。\n"
            "## 第三条 违约责任\n违约方支付合同总额 5% 的违约金。\n"
        )
        self.calls: list[dict] = []

    async def draft_contract(self, *, contract_type: str, parties: dict, terms: dict) -> str:
        self.calls.append({"contract_type": contract_type, "parties": parties, "terms": terms})
        return self.text


class _MockReviewer:
    """模拟 ContractReviewAgent.process()。"""

    def __init__(self, meta: dict | None = None, raise_exc: bool = False):
        self.meta = meta or {
            "summary": "整体偏甲方有利，主要风险在违约金过高。",
            "risk_level": "high",
            "risk_score": 0.65,
            "risks": [
                {
                    "title": "违约金条款过高",
                    "level": "high",
                    "description": "违约金 30%，超过《民法典》合理范围。",
                    "suggested_text": "违约金调整为合同总额 5%。",
                    "issue_type": "biased",
                    "clause": "第五条",
                },
            ],
            "missing_clauses": ["不可抗力条款", "保密条款"],
        }
        self.raise_exc = raise_exc
        self.calls: list[dict] = []

    async def process(self, task: dict) -> Any:
        self.calls.append(task)
        if self.raise_exc:
            raise RuntimeError("模拟 LLM 故障")

        class _Resp:
            metadata = self.meta

        return _Resp()


class _MockChecker:
    def __init__(self, meta: dict | None = None):
        self.meta = meta or {
            "quality_score": 0.85,
            "confidence_level": "high",
            "summary": "审查质量验证通过。",
        }

    async def process(self, task: dict) -> Any:
        class _Resp:
            metadata = self.meta

        return _Resp()


class _MockInvestigator:
    def __init__(self, meta: dict | None = None):
        self.meta = meta or {
            "contract_type": "采购合同",
            "missing_elements": ["违约金", "管辖法院"],
            "preliminary_risks": ["主体资格不清", "标的物描述不明"],
            "applicable_laws": ["民法典合同编", "招标投标法"],
        }

    async def process(self, task: dict) -> Any:
        class _Resp:
            metadata = self.meta

        return _Resp()


class _MockDocxSkill:
    def __init__(self):
        self.payloads: list[dict] = []

    async def render_contract(self, payload: dict) -> str:
        self.payloads.append(payload)
        return "/tmp/mock-rendered.docx"


# ---------------------------------------------------------------------------
# 元数据一致性
# ---------------------------------------------------------------------------


def test_persona_metadata_is_complete():
    p = ContractStewardPersona()
    assert p.persona_id == "contract_steward"
    assert p.display_name == "合同管家"
    assert p.emoji == "📜"
    assert "docx" in p.backed_by_skills
    assert "pdf" in p.backed_by_skills
    assert set(p.supported_apps) == {"fadada", "esign"}
    assert len(p.capabilities) == 6
    for cap in (
        "contract_drafting",
        "contract_review",
        "risk_identification",
        "template_management",
        "version_comparison",
        "archival",
    ):
        assert cap in p.capabilities
    # backed_by_agents 必须列出 6 个 specialized agent
    assert len(p.backed_by_agents) == 6
    assert "contract_reviewer" in p.backed_by_agents
    assert "review_checker" in p.backed_by_agents
    assert "document_drafter" in p.backed_by_agents
    assert "template_librarian" in p.backed_by_agents
    assert "风险优先" in p.SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# 1. draft_contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_draft_contract_with_mock_drafter_and_docx():
    p = ContractStewardPersona()
    drafter = _MockDrafter()
    docx_skill = _MockDocxSkill()
    draft = await p.draft_contract(
        contract_type="采购合同",
        parties=[
            {"role": "甲方", "name": "ACME 制造", "type": "legal_entity"},
            {"role": "乙方", "name": "Beta 供应链"},
        ],
        terms={"金额": "100 万元", "期限": "12 个月"},
        drafter=drafter,
        docx_skill=docx_skill,
    )
    assert isinstance(draft, ContractDraft)
    assert draft.contract_type == "采购合同"
    assert "ACME 制造" in draft.title
    assert draft.docx_template_path == "/tmp/mock-rendered.docx"
    # drafter 应被调用一次
    assert len(drafter.calls) == 1
    # docx skill 收到完整 payload
    assert docx_skill.payloads[0]["contract_type"] == "采购合同"
    # sections 切分有效
    assert len(draft.sections) >= 2
    # suggested_clauses 至少含 2 条通用建议
    titles = {c["title"] for c in draft.suggested_clauses}
    assert "不可抗力" in titles and "保密" in titles


@pytest.mark.asyncio
async def test_draft_contract_falls_back_when_drafter_raises():
    p = ContractStewardPersona()

    class _Boom:
        async def draft_contract(self, **kw):
            raise RuntimeError("LLM down")

    draft = await p.draft_contract(
        contract_type="服务合同",
        parties=[{"role": "甲方", "name": "X 公司"}],
        terms={},
        drafter=_Boom(),
    )
    # fallback 文本仍含合同类型与当事方
    assert "服务合同" in draft.full_text
    assert "X 公司" in draft.full_text
    # docx_template_path 走占位（也可能 None — 取决于 /tmp 是否可写）
    assert draft.docx_template_path is None or draft.docx_template_path.endswith(".docx")


@pytest.mark.asyncio
async def test_draft_contract_validation():
    p = ContractStewardPersona()
    with pytest.raises(ValueError):
        await p.draft_contract(contract_type="", parties=[{"name": "X"}], terms={})
    with pytest.raises(ValueError):
        await p.draft_contract(contract_type="X", parties=[], terms={})


# ---------------------------------------------------------------------------
# 2. review_contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_review_contract_uses_reviewer_and_checker():
    p = ContractStewardPersona()
    rev = _MockReviewer()
    ck = _MockChecker()
    report = await p.review_contract(
        document_text="第一条 ……\n第二条 ……",
        perspective="buyer",
        reviewer=rev,
        checker=ck,
    )
    assert isinstance(report, ReviewReport)
    assert report.perspective == "buyer"
    assert report.recommendation == "redline"  # high risk → redline
    assert len(report.issues) == 1
    assert report.issues[0].severity == "high"
    assert "不可抗力条款" in report.missing_clauses
    # score 由 risk_score 0.65 反推为 35
    assert report.score == pytest.approx(35.0, abs=0.5)
    # reviewer / checker 都被调用
    assert rev.calls and len(rev.calls) == 1


@pytest.mark.asyncio
async def test_review_contract_critical_routes_to_reject():
    p = ContractStewardPersona()
    rev = _MockReviewer(
        meta={
            "summary": "存在严重违法条款。",
            "risk_level": "critical",
            "risk_score": 0.95,
            "risks": [],
            "missing_clauses": [],
        }
    )
    report = await p.review_contract(
        document_text="某合同正文",
        perspective="seller",
        reviewer=rev,
        checker=_MockChecker(),
    )
    assert report.recommendation == "reject"
    assert report.perspective == "seller"


@pytest.mark.asyncio
async def test_review_contract_perspective_validation():
    p = ContractStewardPersona()
    with pytest.raises(ValueError):
        await p.review_contract(
            document_text="x", perspective="enemy", reviewer=_MockReviewer()
        )
    with pytest.raises(ValueError):
        await p.review_contract(
            document_text="", perspective="buyer", reviewer=_MockReviewer()
        )


# ---------------------------------------------------------------------------
# 3. identify_risks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_identify_risks_with_investigator():
    p = ContractStewardPersona()
    inv = _MockInvestigator()
    text = "正文……不含黑名单关键词……"
    analysis = await p.identify_risks(text, investigator=inv)
    assert isinstance(analysis, RiskAnalysis)
    # missing_elements=2 → high；preliminary_risks 2 条 → 已加入 risks
    assert analysis.overall_risk_level in {"medium", "high"}
    assert len(analysis.risks) >= 2
    # legal_basis 来自 applicable_laws
    titles = [c.title for c in analysis.legal_basis]
    assert "民法典合同编" in titles


@pytest.mark.asyncio
async def test_identify_risks_blacklist_forces_critical():
    p = ContractStewardPersona()
    text = (
        "甲方有权单方面任意终止本合同。乙方应保证最低销售额每年不低于 1000 万。"
    )
    analysis = await p.identify_risks(text, investigator=_MockInvestigator(meta={}))
    assert analysis.overall_risk_level == "critical"
    assert "保证最低销售额" in analysis.blacklist_clauses
    assert "单方面任意终止" in analysis.blacklist_clauses


@pytest.mark.asyncio
async def test_identify_risks_empty_text_rejected():
    p = ContractStewardPersona()
    with pytest.raises(ValueError):
        await p.identify_risks("", investigator=_MockInvestigator())


# ---------------------------------------------------------------------------
# 4. find_template
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_template_keyword_match():
    p = ContractStewardPersona()
    items = await p.find_template("租赁")
    assert any(isinstance(it, Template) for it in items)
    assert any("租赁" in it.name or "租" in it.contract_type for it in items)


@pytest.mark.asyncio
async def test_find_template_with_type_filter():
    p = ContractStewardPersona()
    items = await p.find_template("nda", contract_type="保密协议")
    assert items
    assert any("NDA" in it.name or "保密" in it.contract_type for it in items)


@pytest.mark.asyncio
async def test_find_template_empty_query_rejected():
    p = ContractStewardPersona()
    with pytest.raises(ValueError):
        await p.find_template("")


# ---------------------------------------------------------------------------
# 5. compare_versions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_versions_detects_addition_and_modification():
    p = ContractStewardPersona()
    v1 = "第一条 标的\n采购 A 类产品。\n第二条 价款\n100 万元。\n"
    v2 = (
        "第一条 标的\n采购 A 类产品。\n"
        "第二条 价款\n120 万元。\n"
        "第三条 违约金\n违约方支付 10% 违约金。\n"
    )
    diff = await p.compare_versions(v1, v2)
    assert isinstance(diff, VersionDiff)
    # v2 有新增第三条
    assert len(diff.additions) >= 1
    # 第二条内容不同 → modifications
    assert any("价款" in m.get("location", "") for m in diff.modifications)
    # semantic_changes 必非空
    assert diff.semantic_changes


@pytest.mark.asyncio
async def test_compare_versions_validation():
    p = ContractStewardPersona()
    with pytest.raises(ValueError):
        await p.compare_versions(None, "x")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 6. archive
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_archive_default_retention_for_general_contract():
    p = ContractStewardPersona()
    res = await p.archive(
        contract_id="C-001",
        metadata={"contract_type": "采购合同", "parties": ["A", "B"]},
    )
    assert isinstance(res, ArchiveResult)
    assert res.retention_period_days == 1825  # 5 年默认
    assert res.archive_url.startswith("/api/v1/personas/contract/archives/")
    assert res.metadata.get("contract_type") == "采购合同"


@pytest.mark.asyncio
async def test_archive_labor_contract_uses_long_retention():
    p = ContractStewardPersona()
    res = await p.archive(contract_id="L-001", metadata={"contract_type": "劳动合同"})
    assert res.retention_period_days == 7300


@pytest.mark.asyncio
async def test_archive_tax_invoice_uses_10_years():
    p = ContractStewardPersona()
    res = await p.archive(contract_id="T-001", metadata={"contract_type": "税务发票合同"})
    assert res.retention_period_days == 3650


@pytest.mark.asyncio
async def test_archive_custom_retention_overrides_default():
    p = ContractStewardPersona()
    res = await p.archive(
        contract_id="X-1",
        metadata={"contract_type": "采购合同"},
        retention_period_days=3650,
    )
    assert res.retention_period_days == 3650


@pytest.mark.asyncio
async def test_archive_validation():
    p = ContractStewardPersona()
    with pytest.raises(ValueError):
        await p.archive(contract_id="", metadata={})
