"""Enterprise agent governance policy regressions."""

from src.harness.policy_engine import AgentPolicy, PolicyContext, PolicyEngine
from src.harness.tool_registry import RiskLevel


def test_available_tools_respect_subscription_permissions_and_privacy_mode():
    engine = PolicyEngine()

    tools = engine.get_agent_available_tools(
        "legal_researcher",
        context=PolicyContext(
            subscription_features={"legal_knowledge_base"},
            permissions={"read:knowledge"},
            privacy_mode="top_secret",
        ),
    )

    assert "search_knowledge" in tools
    assert "web_search" not in tools
    assert "draft_contract" not in tools


def test_available_tools_fail_closed_without_role_permissions():
    engine = PolicyEngine()

    tools = engine.get_agent_available_tools(
        "legal_researcher",
        context=PolicyContext(
            subscription_features={"legal_knowledge_base"},
            permissions=set(),
        ),
    )

    assert "search_knowledge" not in tools


def test_high_risk_tool_visible_only_after_authorized_approval():
    engine = PolicyEngine()
    engine.set_policy(AgentPolicy(
        agent_name="legal_advisor",
        max_risk_level=RiskLevel.HIGH_RISK,
    ))

    base_context = {
        "subscription_features": {"lawyer_matching"},
        "permissions": {"review:contracts", "sign:contracts"},
    }

    before_approval = engine.get_agent_available_tools(
        "legal_advisor",
        context=PolicyContext(**base_context),
    )
    after_approval = engine.get_agent_available_tools(
        "legal_advisor",
        context=PolicyContext(
            **base_context,
            approval_state="approved",
            approver_role="org_admin",
        ),
    )

    assert "generate_legal_opinion" not in before_approval
    assert "generate_legal_opinion" in after_approval


def test_channel_policy_denies_all_agent_tools():
    engine = PolicyEngine()

    tools = engine.get_agent_available_tools(
        "legal_researcher",
        context=PolicyContext(
            subscription_features={"legal_knowledge_base"},
            permissions={"read:knowledge"},
            channel_allowed=False,
        ),
    )

    assert tools == []
