# -*- coding: utf-8 -*-
"""合同管家 7 API endpoint 集成测试（P9-C）。

覆盖：
    POST /api/v1/personas/contract/draft
    POST /api/v1/personas/contract/review
    POST /api/v1/personas/contract/identify-risks
    GET  /api/v1/personas/contract/templates
    POST /api/v1/personas/contract/compare-versions
    POST /api/v1/personas/contract/archive
    GET  /api/v1/personas/contract/archives

策略：
    - 通过 ``app.dependency_overrides`` 注入 mock persona，避免触发真实
      LLM 调用（specialized agent 在 ``__init__`` 时就 load prompt + RAG）。
    - 鉴权一致：所有 POST 至少跑一次 401 守卫。
"""

from __future__ import annotations

# SQLite ↔ JSONB 兼容补丁（与其它 API 测试保持一致）
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler as _SQLiteTC

if not hasattr(_SQLiteTC, "visit_JSONB"):
    def _visit_JSONB(self, type_, **kw):  # noqa: N802
        return self.visit_JSON(type_, **kw)

    _SQLiteTC.visit_JSONB = _visit_JSONB  # type: ignore[attr-defined]


from datetime import datetime
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient

from src.agents.personas.contract_models import (
    ArchiveResult,
    ContractDraft,
    ReviewIssue,
    ReviewReport,
    RiskAnalysis,
    Template,
    VersionDiff,
)
from src.agents.personas.research_models import Citation


PREFIX = "/api/v1/personas/contract"


# ---------------------------------------------------------------------------
# Fake persona — 替代真品，避免触发 LLM
# ---------------------------------------------------------------------------


class _FakePersona:
    """实现 ContractStewardPersona 的 6 大接口，返回固定结构。"""

    persona_id = "contract_steward"
    display_name = "合同管家"

    async def draft_contract(
        self,
        contract_type: str,
        parties: list[dict],
        terms: dict,
        language: str = "zh",
    ) -> ContractDraft:
        return ContractDraft(
            contract_type=contract_type,
            title=f"测试-{contract_type}",
            full_text="第一条 ……\n第二条 ……\n",
            sections=[
                {"title": "第一条 标的", "content": "……", "optional": False},
                {"title": "第二条 价款", "content": "……", "optional": False},
            ],
            suggested_clauses=[{"title": "不可抗力", "rationale": "...", "content": "..."}],
            estimated_word_count=120,
            language=language,
            docx_template_path="/tmp/fake.docx",
        )

    async def review_contract(
        self,
        document_text: str,
        perspective: str = "buyer",
    ) -> ReviewReport:
        return ReviewReport(
            overall_assessment="审查完成。",
            perspective=perspective,
            score=72.5,
            issues=[
                ReviewIssue(
                    clause_text="第五条 违约金",
                    issue_type="biased",
                    severity="high",
                    description="违约金过高。",
                    suggested_revision="调整为 5%。",
                    location={"section": "第五条"},
                )
            ],
            missing_clauses=["不可抗力"],
            redundant_clauses=[],
            recommendation="redline",
        )

    async def identify_risks(self, document_text: str) -> RiskAnalysis:
        is_blacklist = "单方面任意终止" in document_text
        return RiskAnalysis(
            overall_risk_level="critical" if is_blacklist else "medium",
            risks=[{"category": "general", "description": "测试风险", "likelihood": 0.6, "impact": 0.5, "mitigation": "..."}],
            blacklist_clauses=["单方面任意终止"] if is_blacklist else [],
            legal_basis=[Citation(source="legal_kb", url="", title="民法典合同编", excerpt="", confidence=0.7)],
        )

    async def find_template(
        self,
        query: str,
        contract_type: str | None = None,
    ) -> list[Template]:
        # 命中关键词「租赁」时返回一个模板
        if "租" in query or contract_type == "租赁合同":
            return [
                Template(
                    template_id="tpl_rental",
                    name="房屋租赁合同",
                    contract_type="租赁合同",
                    description="标准房屋租赁",
                    use_case="合同",
                    language="zh",
                    word_count=2000,
                    last_used=None,
                    download_url="/api/v1/knowledge/templates/rental-contract",
                ),
            ]
        return []

    async def compare_versions(self, v1_text: str, v2_text: str) -> VersionDiff:
        return VersionDiff(
            v1_summary="v1 共 2 条",
            v2_summary="v2 共 3 条",
            additions=[{"location": "第三条", "text": "新增", "type": "clause_added"}],
            deletions=[],
            modifications=[],
            semantic_changes=["新增第三条"],
        )

    async def archive(
        self,
        contract_id: str,
        metadata: dict,
        retention_period_days: int | None = None,
    ) -> ArchiveResult:
        return ArchiveResult(
            contract_id=contract_id,
            archive_url=f"/api/v1/personas/contract/archives/{contract_id}",
            metadata=dict(metadata or {}),
            archived_at=datetime.utcnow(),
            retention_period_days=retention_period_days or 1825,
        )


@pytest_asyncio.fixture(autouse=True)
async def _override_persona():
    """对所有用例自动替换为 _FakePersona。"""
    from src.api.main import app
    from src.api.routes.persona_contract import _get_persona

    fake = _FakePersona()
    app.dependency_overrides[_get_persona] = lambda: fake
    yield
    app.dependency_overrides.pop(_get_persona, None)


# ---------------------------------------------------------------------------
# 1. draft
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_draft_endpoint(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/draft",
        json={
            "contract_type": "采购合同",
            "parties": [
                {"role": "甲方", "name": "ACME"},
                {"role": "乙方", "name": "Beta"},
            ],
            "terms": {"金额": "100 万"},
            "language": "zh",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["contract_type"] == "采购合同"
    assert body["docx_template_path"] == "/tmp/fake.docx"
    assert len(body["sections"]) == 2


@pytest.mark.asyncio
async def test_draft_requires_auth(client: AsyncClient) -> None:
    r = await client.post(
        f"{PREFIX}/draft",
        json={"contract_type": "采购合同", "parties": [{"name": "X"}], "terms": {}},
    )
    assert r.status_code in {401, 403}


# ---------------------------------------------------------------------------
# 2. review
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_review_endpoint(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/review",
        json={"document_text": "第一条 ……", "perspective": "buyer"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["perspective"] == "buyer"
    assert body["recommendation"] == "redline"
    assert body["issues"][0]["severity"] == "high"


@pytest.mark.asyncio
async def test_review_invalid_perspective_returns_422(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/review",
        json={"document_text": "x", "perspective": "enemy"},
    )
    assert r.status_code in {400, 422}


# ---------------------------------------------------------------------------
# 3. identify-risks
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_identify_risks_blacklist_critical(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/identify-risks",
        json={"document_text": "甲方有权单方面任意终止本合同。"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["overall_risk_level"] == "critical"
    assert "单方面任意终止" in body["blacklist_clauses"]


@pytest.mark.asyncio
async def test_identify_risks_normal_text(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/identify-risks",
        json={"document_text": "正常合同正文，无敏感条款。"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["overall_risk_level"] == "medium"
    assert body["legal_basis"][0]["title"] == "民法典合同编"


# ---------------------------------------------------------------------------
# 4. templates
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_templates_search(auth_client: AsyncClient) -> None:
    r = await auth_client.get(f"{PREFIX}/templates?q=租赁")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 1
    assert body["items"][0]["contract_type"] == "租赁合同"


@pytest.mark.asyncio
async def test_templates_requires_auth(client: AsyncClient) -> None:
    r = await client.get(f"{PREFIX}/templates?q=租赁")
    assert r.status_code in {401, 403}


# ---------------------------------------------------------------------------
# 5. compare-versions
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_compare_versions_endpoint(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/compare-versions",
        json={"v1_text": "第一条 X\n第二条 Y", "v2_text": "第一条 X\n第二条 Y\n第三条 Z"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["additions"]
    assert "新增" in body["semantic_changes"][0]


# ---------------------------------------------------------------------------
# 6. archive + 7. archives list
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_archive_then_list(auth_client: AsyncClient) -> None:
    # 6: 归档
    r1 = await auth_client.post(
        f"{PREFIX}/archive",
        json={
            "contract_id": "C-API-001",
            "metadata": {"contract_type": "采购合同", "parties": ["ACME", "Beta"]},
            "retention_period_days": 1825,
        },
    )
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    assert body1["contract_id"] == "C-API-001"
    assert body1["retention_period_days"] == 1825

    # 7: 列表（应至少包含刚才的归档）
    r2 = await auth_client.get(f"{PREFIX}/archives")
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert body2["total"] >= 1
    assert any(it["contract_id"] == "C-API-001" for it in body2["items"])


@pytest.mark.asyncio
async def test_archives_filter_by_party(auth_client: AsyncClient) -> None:
    # 先归档一个带 ACME 的
    await auth_client.post(
        f"{PREFIX}/archive",
        json={
            "contract_id": "C-API-PARTY-1",
            "metadata": {"contract_type": "采购合同", "parties": ["ACME", "Gamma"]},
        },
    )
    # 再归档一个无关的
    await auth_client.post(
        f"{PREFIX}/archive",
        json={
            "contract_id": "C-API-PARTY-2",
            "metadata": {"contract_type": "服务合同", "parties": ["Delta", "Epsilon"]},
        },
    )

    r = await auth_client.get(f"{PREFIX}/archives?party=ACME")
    assert r.status_code == 200
    body = r.json()
    ids = {it["contract_id"] for it in body["items"]}
    assert "C-API-PARTY-1" in ids
    # ACME 过滤不应命中 PARTY-2
    assert "C-API-PARTY-2" not in ids


@pytest.mark.asyncio
async def test_archive_requires_auth(client: AsyncClient) -> None:
    r = await client.post(
        f"{PREFIX}/archive",
        json={"contract_id": "X", "metadata": {}},
    )
    assert r.status_code in {401, 403}
