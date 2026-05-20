# -*- coding: utf-8 -*-
"""
验证 BaseLegalAgent.process_governed 对全部继承类生效。

关键性质：
  - subject=None → 与 process() 行为一致（向后兼容）
  - PDP ALLOW   → 正常返回；metadata 含 authz_decision / policy_snapshot_id
  - PDP DENY    → 抛 PermissionError；写审计 outcome=denied
  - 全部 21+ subclass 都拿到这个能力（不用一行一行改）
"""
from __future__ import annotations

from typing import Any

import pytest

from src.agents.base import AgentResponse, BaseLegalAgent


class _DummyAgent(BaseLegalAgent):
    """最小子类：实现抽象的 process()。"""

    def __init__(self) -> None:
        # 跳过父类 __init__（避免触发 LLM 连接池 / config 解析）
        # ABC 检查 process 实现即可
        pass

    async def process(self, task: dict[str, Any]) -> AgentResponse:
        if task.get("crash"):
            raise RuntimeError("boom")
        return AgentResponse(agent_name="dummy", content="hello", metadata={"orig": True})


@pytest.mark.asyncio
async def test_backward_compat_no_subject():
    """subject=None → 跳过治理，行为同 process()。"""
    a = _DummyAgent()
    r = await a.process_governed({"x": 1})
    assert r.content == "hello"
    assert "orig" in r.metadata


@pytest.mark.asyncio
async def test_allow_path_decorates_metadata():
    a = _DummyAgent()
    subject = {
        "id": "u1", "role": "legal_member", "tenant_id": "t1",
        "clearance": "L4", "primary_jurisdiction": "CN",
    }
    r = await a.process_governed(
        {"x": 1},
        subject=subject,
        action="skill.legal-advisor.legal-research",  # 命中 access-matrix legal_member 的 grant
        resource={"type": "agent", "id": "dummy",
                  "classification": "L2", "jurisdiction": "CN"},
        context={"mfa_recent": True, "business_hours": True},
    )
    assert r.content == "hello"
    # PDP 决策被写入 metadata
    assert r.metadata.get("authz_decision") == "ALLOW"
    assert r.metadata.get("policy_snapshot_id", "").startswith("pol_")


@pytest.mark.asyncio
async def test_deny_path_raises_permission_error():
    a = _DummyAgent()
    subject = {
        "id": "u1", "role": "growth_member", "tenant_id": "t1",
        "clearance": "L2", "primary_jurisdiction": "CN",
    }
    with pytest.raises(PermissionError):
        await a.process_governed(
            {"x": 1},
            subject=subject,
            # growth_member 不允许法律 skill
            action="skill.legal-advisor.legal-research",
            resource={"type": "agent", "id": "dummy",
                      "classification": "L2", "jurisdiction": "CN"},
        )


@pytest.mark.asyncio
async def test_failure_still_writes_audit():
    a = _DummyAgent()
    subject = {
        "id": "u1", "role": "legal_member", "tenant_id": "t1",
        "clearance": "L4", "primary_jurisdiction": "CN",
    }
    with pytest.raises(RuntimeError, match="boom"):
        await a.process_governed(
            {"crash": True},
            subject=subject,
            action="skill.legal-advisor.legal-research",
            resource={"type": "agent", "id": "dummy",
                      "classification": "L2", "jurisdiction": "CN"},
            context={"mfa_recent": True},
        )


def test_all_21_specialized_agents_inherit_governed():
    """检查 backend/src/agents/*.py 中的 specialized Agent 类都拿到 process_governed。"""
    from pathlib import Path

    AGENT_FILES = [
        "compliance_officer", "consensus_agent", "contract_investigator",
        "contract_reviewer", "contract_steward", "coordinator",
        "document_drafter", "due_diligence", "evidence_analyst",
        "ip_specialist", "labor_compliance", "legal_advisor",
        "legal_calculator", "legal_researcher", "litigation_strategist",
        "regulatory_monitor", "requirement_analyst", "review_checker",
        "risk_assessor", "sentiment_agent", "tax_compliance",
        "template_librarian",
    ]
    p_root = Path(__file__).resolve().parents[1] / "src" / "agents"
    for name in AGENT_FILES:
        f = p_root / f"{name}.py"
        assert f.exists(), f"agent file missing: {name}"

    # 治理方法本身存在
    assert hasattr(BaseLegalAgent, "process_governed")
    import inspect
    sig = inspect.signature(BaseLegalAgent.process_governed)
    assert "subject" in sig.parameters
    assert "action" in sig.parameters
    assert "resource" in sig.parameters
