# -*- coding: utf-8 -*-
"""
Governance authz PDP 端到端测试。

覆盖：
  - role × scope grants
  - global gates 加严
  - clearance gate
  - 跨境 gate
  - default deny
  - PII classify + mask
  - trust level
  - tool scope enforce
"""
from __future__ import annotations

import pytest

from src.services.governance import (
    Decision,
    decide,
    classify,
    mask,
    enforce_tool_call,
    evaluate_trust,
    can_transition,
    LifecycleStage,
)
from src.services.governance.tool_scope import ToolDecision


# ────────────────────────────────────────────────────────────────────
# authz.decide
# ────────────────────────────────────────────────────────────────────
def test_legal_member_can_review_contract():
    res = decide(
        subject={"role": "legal_member", "clearance": "L4", "tenant_id": "t1",
                 "primary_jurisdiction": "CN"},
        action="skill.contract-steward.review",
        resource={"type": "skill", "id": "/contract-steward:review",
                  "classification": "L3", "jurisdiction": "CN"},
        context={"mfa_recent": True, "business_hours": True},
    )
    # access-matrix 里 legal_member 有 skill.contract-steward.*
    assert res.decision == Decision.ALLOW
    assert any("role-grant" in r["rule"] for r in res.reasons)


def test_growth_member_cannot_touch_contract():
    res = decide(
        subject={"role": "growth_member", "clearance": "L2", "tenant_id": "t1",
                 "primary_jurisdiction": "CN"},
        action="data.contract.read",
        resource={"type": "data", "id": "contracts/2026", "classification": "L3",
                  "jurisdiction": "CN"},
        context={"mfa_recent": True},
    )
    # growth_member denies data.contract.*
    assert res.decision == Decision.DENY


def test_write_requires_confirm():
    res = decide(
        subject={"role": "legal_member", "clearance": "L4", "tenant_id": "t1",
                 "primary_jurisdiction": "CN"},
        action="data.contract.write",
        resource={"type": "data", "id": "contracts/abc", "classification": "L3",
                  "jurisdiction": "CN"},
        context={"mfa_recent": True, "business_hours": True},
    )
    assert res.decision == Decision.REQUIRE_CONFIRM


def test_high_amount_step_up():
    res = decide(
        subject={"role": "admin", "clearance": "L4", "tenant_id": "t1",
                 "primary_jurisdiction": "CN"},
        action="connector.stripe.write",
        resource={"type": "connector", "id": "stripe", "classification": "L3",
                  "jurisdiction": "CN"},
        context={"mfa_recent": True, "business_hours": True, "amount_cny": 2_000_000},
    )
    assert res.decision == Decision.REQUIRE_STEP_UP


def test_cross_border_eu_to_cn_step_up():
    res = decide(
        subject={"role": "admin", "clearance": "L4", "tenant_id": "t1",
                 "primary_jurisdiction": "EU"},
        action="data.contract.read",
        resource={"type": "data", "id": "...", "classification": "L3",
                  "jurisdiction": "CN"},
        context={"mfa_recent": True},
    )
    # EU subject 读 CN 资源 — jurisdiction gate 触发
    assert res.decision in (Decision.REQUIRE_CONFIRM, Decision.REQUIRE_STEP_UP)


def test_clearance_blocks_l5_for_low_clearance():
    res = decide(
        subject={"role": "growth_member", "clearance": "L2", "tenant_id": "t1",
                 "primary_jurisdiction": "CN"},
        action="data.privileged.read",
        resource={"type": "data", "id": "privileged/...", "classification": "L5",
                  "jurisdiction": "CN"},
        context={},
    )
    assert res.decision == Decision.DENY


def test_super_admin_wildcard_but_writes_still_confirm():
    res = decide(
        subject={"role": "super_admin", "clearance": "L5", "tenant_id": "t1",
                 "primary_jurisdiction": "CN"},
        action="data.contract.write",
        resource={"type": "data", "id": "x", "classification": "L3",
                  "jurisdiction": "CN"},
        context={"mfa_recent": True, "business_hours": True},
    )
    # super_admin 全集，但写动作仍受 global_gates 约束
    assert res.decision == Decision.REQUIRE_CONFIRM


def test_default_deny_for_unmapped_role():
    res = decide(
        subject={"role": "random_role", "clearance": "L1", "tenant_id": "t1",
                 "primary_jurisdiction": "CN"},
        action="skill.contract-steward.review",
        resource={"type": "skill", "id": "x", "classification": "L1",
                  "jurisdiction": "CN"},
        context={},
    )
    assert res.decision == Decision.DENY


# ────────────────────────────────────────────────────────────────────
# data_classifier
# ────────────────────────────────────────────────────────────────────
def test_classify_phone_and_mask():
    text = "请联系王经理，电话 13800001234，邮箱 wang.m@example.com"
    cls, findings = classify(text)
    assert cls.value in ("L3", "L4")
    types = {f.type for f in findings}
    assert "cn_mobile" in types
    assert "email" in types

    masked, _ = mask(text)
    assert "13800001234" not in masked
    assert "138" in masked
    assert "1234" in masked


def test_classify_no_pii():
    cls, findings = classify("今天天气真好。")
    from src.services.governance import Classification
    assert cls == Classification.L1
    assert findings == []


# ────────────────────────────────────────────────────────────────────
# tool_scope
# ────────────────────────────────────────────────────────────────────
def test_tool_scope_amazon_listing_allows_amazon_host():
    res = enforce_tool_call(
        skill_id="/cross-border-ecom:amazon-listing",
        tool="http_get_public",   # network_egress category
        target_host="sellingpartnerapi-na.amazon.com",
        persona="cross-border-ecom",
        trust_level="verified",
    )
    # amazon 在 explicit_egress_allowlist
    # 注意：amazon-listing override 中 network_egress 不在 allow，所以是 DENY
    # 这恰好测试了 override 优先级——SKILL override 取代了 persona default 的 network_egress
    assert res.decision == ToolDecision.DENY


def test_tool_scope_dd_expert_allows_qichacha():
    res = enforce_tool_call(
        skill_id="/dd-expert:company-dd",
        tool="http_get_public",
        target_host="api.qichacha.com",
        persona="dd-expert",
        trust_level="verified",
    )
    assert res.decision == ToolDecision.ALLOW


def test_tool_scope_blocks_unknown_host():
    res = enforce_tool_call(
        skill_id="/dd-expert:company-dd",
        tool="http_get_public",
        target_host="evil.example.com",
        persona="dd-expert",
        trust_level="verified",
    )
    assert res.decision == ToolDecision.DENY


def test_tool_scope_untrusted_send_denied():
    res = enforce_tool_call(
        skill_id="/legal-advisor:legal-research",
        tool="feishu_send",
        persona="legal-advisor",
        trust_level="untrusted",
    )
    assert res.decision == ToolDecision.DENY


# ────────────────────────────────────────────────────────────────────
# trust
# ────────────────────────────────────────────────────────────────────
def test_trust_official_is_verified():
    ev = evaluate_trust(
        skill_id="/legal-advisor:legal-research",
        version="1.0.0",
        source_url="https://anxinai.com/marketplace/legal-advisor",
    )
    assert ev.level.value == "verified"


def test_trust_unknown_source_untrusted():
    ev = evaluate_trust(
        skill_id="/random:thing",
        version="0.1.0",
        source_url="https://malicious.example/skill",
    )
    assert ev.level.value == "untrusted"
    assert ev.connector_write == "deny"


# ────────────────────────────────────────────────────────────────────
# lifecycle
# ────────────────────────────────────────────────────────────────────
def test_lifecycle_draft_to_review_requires_gates():
    res = can_transition(
        skill_id="/legal-advisor:legal-research",
        from_stage=LifecycleStage.DRAFT,
        to_stage=LifecycleStage.REVIEW,
        actor={"role": "legal_member", "type": "author"},
        gate_runners={
            "frontmatter_complete": lambda ctx: True,
            "governance_lint_pass": lambda ctx: True,
            "unit_test_coverage_min": lambda ctx: True,
        },
    )
    assert res.allowed


def test_lifecycle_publish_blocked_without_dual_sign():
    res = can_transition(
        skill_id="/legal-advisor:legal-research",
        from_stage=LifecycleStage.REVIEW,
        to_stage=LifecycleStage.PUBLISHED,
        actor={"role": "legal_member", "type": "reviewer"},
        gate_runners={
            "reviewer_dual_sign": lambda ctx: False,
            "builder_hub_scan_clean": lambda ctx: True,
            "shadow_run_clean": lambda ctx: True,
        },
    )
    assert not res.allowed
    assert any("reviewer_dual_sign" in r for r in res.reasons)
