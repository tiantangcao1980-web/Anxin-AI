# -*- coding: utf-8 -*-
"""LeadScoring 5 因子算法边界测试 (P7-C)。

覆盖：
    1. 权重总和 = 1.0 → 全 1 输入 ⇒ score 1.0
    2. 全 0 输入 ⇒ score 0.0
    3. 越界裁剪 ([-3, 99] → [0, 1])
    4. 决策人 / 行业匹配的真实 lead 路径
    5. score_breakdown 之和 ≈ score
"""

from __future__ import annotations

import math

import pytest

from src.agents.personas.lead_hunter import LeadScoring
from src.agents.personas.sales_models import Contact, Lead, LeadDiscoveryCriteria


def test_weights_sum_to_one():
    assert math.isclose(sum(LeadScoring.WEIGHTS.values()), 1.0, abs_tol=1e-9)


def test_score_all_max_is_one():
    score, breakdown = LeadScoring.score(
        icp_fit=1.0,
        recent_funding_news=1.0,
        competitor_overlap=1.0,
        response_rate_history=1.0,
        decision_maker_in_contacts=1.0,
    )
    assert math.isclose(score, 1.0, abs_tol=1e-6)
    # breakdown 各因子 = 该因子权重
    for k, w in LeadScoring.WEIGHTS.items():
        assert math.isclose(breakdown[k], w, abs_tol=1e-9)


def test_score_all_min_is_zero():
    score, _ = LeadScoring.score(
        icp_fit=0,
        recent_funding_news=0,
        competitor_overlap=0,
        response_rate_history=0,
        decision_maker_in_contacts=0,
    )
    assert score == 0.0


def test_score_clamps_out_of_range_inputs():
    score, _ = LeadScoring.score(
        icp_fit=99,
        recent_funding_news=-3,
        competitor_overlap=0.5,
        response_rate_history=0.5,
        decision_maker_in_contacts=0.5,
    )
    # icp 被裁到 1.0 (×0.30) + 其他 3 个 0.5 (×0.5*0.5) ≈ 0.30 + 0.25
    assert 0.0 <= score <= 1.0
    expected = 0.30 + 0 + 0.5 * 0.20 + 0.5 * 0.15 + 0.5 * 0.15
    assert math.isclose(score, expected, abs_tol=1e-6)


def test_score_breakdown_sum_equals_score():
    score, breakdown = LeadScoring.score(
        icp_fit=0.7,
        recent_funding_news=0.4,
        competitor_overlap=0.3,
        response_rate_history=0.6,
        decision_maker_in_contacts=1.0,
    )
    assert math.isclose(score, sum(breakdown.values()), abs_tol=1e-6)


def test_score_lead_uses_industry_exact_match():
    lead = Lead(
        id="x",
        company_name="X",
        industry="新能源汽车配件",
        country="中国",
        contacts=[Contact(name="Z", title="采购总监")],
        tags=["funded"],
    )
    crit = LeadDiscoveryCriteria(industry="新能源汽车配件")
    LeadScoring.score_lead(lead, criteria=crit, signals={})
    # 预期组成：icp 1.0 (0.30) + funding 0.8 (tag bonus, 0.16) + dm 1.0 (0.15) = 0.61
    assert math.isclose(lead.score, 0.30 + 0.8 * 0.20 + 0.15, abs_tol=1e-6)
    assert lead.score_breakdown["icp_fit"] > 0


def test_score_lead_no_decision_maker_drops_dm_factor():
    lead = Lead(
        id="x",
        company_name="X",
        industry="新能源",
        country="CN",
        contacts=[Contact(name="A", title="工程师")],
    )
    crit = LeadDiscoveryCriteria(industry="新能源")
    LeadScoring.score_lead(lead, criteria=crit, signals={})
    assert lead.score_breakdown["decision_maker_in_contacts"] == 0.0


def test_score_lead_competitor_tag_bonus():
    lead = Lead(
        id="x",
        company_name="X",
        industry="新能源",
        country="CN",
        contacts=[],
        tags=["uses-bosch"],
    )
    crit = LeadDiscoveryCriteria(industry="新能源")
    LeadScoring.score_lead(lead, criteria=crit, signals={})
    # competitor_overlap 应被 tag 触发到 ≥ 0.7 × 0.20 = 0.14
    assert lead.score_breakdown["competitor_overlap"] >= 0.14 - 1e-6


def test_score_lead_industry_mismatch_low_icp():
    lead = Lead(
        id="x",
        company_name="X",
        industry="餐饮",
        country="CN",
        contacts=[],
    )
    crit = LeadDiscoveryCriteria(industry="新能源")
    LeadScoring.score_lead(lead, criteria=crit, signals={})
    # 不匹配 → icp = 0.2 → 贡献 0.06
    assert math.isclose(lead.score_breakdown["icp_fit"], 0.06, abs_tol=1e-6)
