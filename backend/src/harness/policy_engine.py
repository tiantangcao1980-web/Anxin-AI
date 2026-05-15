"""
Agent 权限与审批引擎

控制 Agent 能做什么、不能做什么：
1. 工具白名单：每个 Agent 只能调用被授权的工具
2. 操作风险分级：高风险操作需人工审批
3. 数据访问控制：按数据敏感度限制访问
4. 审批门控：与 approval 模块对接
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from src.harness.tool_registry import RiskLevel, tool_registry


class DataClassification(str, Enum):
    """数据敏感等级（与 security_config.py 对齐）"""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SENSITIVE = "sensitive"
    TOP_SECRET = "top_secret"


class PolicyDecision(str, Enum):
    """策略决定"""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class PolicyCheckResult:
    """权限检查结果"""

    decision: PolicyDecision
    reason: str
    tool_name: str | None = None
    agent_name: str | None = None
    required_approver_role: str | None = None  # 需要谁审批
    missing_permissions: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class PolicyContext:
    """
    一次工具调用的组织治理上下文。

    这些字段都是可选的，便于现有调用点逐步接入；只要传入，就按
    fail-closed 解释，避免 agent 在订阅、隐私模式、设备信任或通道策略
    缺失时拿到过宽权限。
    """

    subscription_features: dict[str, Any] | Iterable[str] | None = None
    user_role: str | None = None
    permissions: Iterable[str] | None = None
    privacy_mode: str | None = None
    device_trusted: bool = True
    channel_allowed: bool = True
    approval_state: str | None = None
    approver_role: str | None = None


@dataclass
class AgentPolicy:
    """单个 Agent 的策略配置"""

    agent_name: str
    # 允许的工具列表（None = 遵从 tool_registry 的 allowed_agents）
    allowed_tools: set[str] | None = None
    # 明确禁止的工具
    denied_tools: set[str] = field(default_factory=set)
    # 允许的最高风险等级
    max_risk_level: RiskLevel = RiskLevel.WRITE
    # 允许访问的最高数据敏感度
    max_data_classification: DataClassification = DataClassification.INTERNAL
    # 是否允许对外发送
    can_external_send: bool = False
    # 单次任务最大 token 预算
    max_tokens_per_task: int = 50000
    # 是否需要人工确认才能输出
    output_requires_review: bool = False


_FEATURE_TOOL_ALIASES: dict[str, set[str]] = {
    "legal_knowledge_base": {
        "search_knowledge",
        "search_vector",
        "query_graph",
        "search_case_law",
        "verify_citation",
    },
    "template_marketplace": {"draft_contract", "draft_document"},
    "due_diligence": {"crawl_company_info"},
    "sentiment_monitoring": {"analyze_sentiment"},
    "lawyer_matching": {"generate_legal_opinion"},
}

_APPROVER_ROLES = {
    "super_admin",
    "admin",
    "org_admin",
    "partner",
    "lawyer",
}


def _normalize_string_set(values: Iterable[str] | None) -> set[str] | None:
    if values is None:
        return None
    return {str(value).strip().lower() for value in values if str(value).strip()}


def _active_feature_names(features: dict[str, Any] | Iterable[str] | None) -> set[str] | None:
    if features is None:
        return None
    if isinstance(features, dict):
        active: set[str] = set()
        for key, value in features.items():
            if isinstance(value, bool) and value:
                active.add(key)
            elif isinstance(value, int) and value > 0:
                active.add(key)
            elif isinstance(value, str) and value.strip():
                active.add(key)
            elif isinstance(value, list) and value:
                active.add(key)
        return {item.lower() for item in active}
    return _normalize_string_set(features) or set()


def _feature_allows_tool(tool_name: str, tags: list[str], active_features: set[str]) -> bool:
    if "*" in active_features or "all" in active_features:
        return True

    selectors = {tool_name, f"tool:{tool_name}"}
    for tag in tags:
        selectors.add(tag)
        selectors.add(f"tag:{tag}")
    for feature, tool_names in _FEATURE_TOOL_ALIASES.items():
        if tool_name in tool_names:
            selectors.add(feature)

    return bool(active_features & {selector.lower() for selector in selectors})


def _is_valid_approver(role: str | None) -> bool:
    return (role or "").lower() in _APPROVER_ROLES


class PolicyEngine:
    """
    Agent 权限引擎

    核心逻辑：
    1. 每个 Agent 有默认策略
    2. tool_registry 的 allowed_agents 是第一层过滤
    3. policy_engine 是第二层精细控制
    4. 高风险操作强制需要审批
    """

    def __init__(self) -> None:
        self._policies: dict[str, AgentPolicy] = {}
        self._audit_log: list[dict[str, Any]] = []
        self._max_audit = 3000
        self._register_default_policies()

    def _register_default_policies(self) -> None:
        """注册默认 Agent 策略"""

        # 法律顾问：广泛权限但不可对外发送
        self.set_policy(
            AgentPolicy(
                agent_name="legal_advisor",
                max_risk_level=RiskLevel.WRITE,
                can_external_send=False,
                denied_tools={"create_payment", "send_email"},
            )
        )

        # 合同审查：只做审查不生成新合同
        self.set_policy(
            AgentPolicy(
                agent_name="contract_reviewer",
                max_risk_level=RiskLevel.WRITE,
                denied_tools={"create_payment", "send_email", "crawl_company_info"},
            )
        )

        # 合同管家：合同全生命周期
        self.set_policy(
            AgentPolicy(
                agent_name="contract_steward",
                max_risk_level=RiskLevel.WRITE,
                denied_tools={"create_payment", "send_email"},
            )
        )

        # 尽调专家：需要外部数据采集
        self.set_policy(
            AgentPolicy(
                agent_name="due_diligence",
                max_risk_level=RiskLevel.EXTERNAL_SEND,
                can_external_send=True,
                denied_tools={"create_payment", "send_email"},
            )
        )

        # 证据分析：需要外部数据采集
        self.set_policy(
            AgentPolicy(
                agent_name="evidence_analyst",
                max_risk_level=RiskLevel.EXTERNAL_SEND,
                can_external_send=True,
                denied_tools={"create_payment", "send_email", "draft_contract"},
            )
        )

        # 文书起草：可写但不可执行
        self.set_policy(
            AgentPolicy(
                agent_name="document_drafter",
                max_risk_level=RiskLevel.WRITE,
                denied_tools={"create_payment", "send_email", "crawl_company_info"},
            )
        )

        # 风险评估：只读分析
        self.set_policy(
            AgentPolicy(
                agent_name="risk_assessor",
                max_risk_level=RiskLevel.READ_ONLY,
                denied_tools={"create_payment", "send_email", "draft_contract", "draft_document"},
            )
        )

        # 合规专员：只读分析
        self.set_policy(
            AgentPolicy(
                agent_name="compliance_officer",
                max_risk_level=RiskLevel.READ_ONLY,
                denied_tools={"create_payment", "send_email", "draft_contract"},
            )
        )

        # 法律研究：只读
        self.set_policy(
            AgentPolicy(
                agent_name="legal_researcher",
                max_risk_level=RiskLevel.READ_ONLY,
                denied_tools={"create_payment", "send_email", "draft_contract", "draft_document"},
            )
        )

        # 共识管理：只读
        self.set_policy(
            AgentPolicy(
                agent_name="consensus_manager",
                max_risk_level=RiskLevel.READ_ONLY,
            )
        )

        # 诉讼策略：可写文书
        self.set_policy(
            AgentPolicy(
                agent_name="litigation_strategist",
                max_risk_level=RiskLevel.WRITE,
                denied_tools={"create_payment", "send_email"},
            )
        )

        # 知识产权：只读分析
        self.set_policy(
            AgentPolicy(
                agent_name="ip_specialist",
                max_risk_level=RiskLevel.READ_ONLY,
                denied_tools={"create_payment", "send_email", "draft_contract"},
            )
        )

        # 监管监控：外部访问
        self.set_policy(
            AgentPolicy(
                agent_name="regulatory_monitor",
                max_risk_level=RiskLevel.EXTERNAL_SEND,
                can_external_send=True,
                denied_tools={"create_payment", "send_email", "draft_contract"},
            )
        )

        # 税务/劳动合规：只读
        for name in ("tax_compliance", "labor_compliance"):
            self.set_policy(
                AgentPolicy(
                    agent_name=name,
                    max_risk_level=RiskLevel.READ_ONLY,
                    denied_tools={"create_payment", "send_email", "draft_contract"},
                )
            )

        # 舆情分析：只读
        self.set_policy(
            AgentPolicy(
                agent_name="sentiment_agent",
                max_risk_level=RiskLevel.READ_ONLY,
            )
        )

        # 需求分析：只读
        self.set_policy(
            AgentPolicy(
                agent_name="requirement_analyst",
                max_risk_level=RiskLevel.READ_ONLY,
            )
        )

        # 审查员：只读
        self.set_policy(
            AgentPolicy(
                agent_name="review_checker",
                max_risk_level=RiskLevel.READ_ONLY,
            )
        )

        logger.info(f"[PolicyEngine] 注册 {len(self._policies)} 个 Agent 策略")

    def set_policy(self, policy: AgentPolicy) -> None:
        """设置或更新 Agent 策略"""
        self._policies[policy.agent_name] = policy

    def get_policy(self, agent_name: str) -> AgentPolicy | None:
        """获取 Agent 策略"""
        return self._policies.get(agent_name)

    def check_tool_access(
        self,
        agent_name: str,
        tool_name: str,
        context: PolicyContext | None = None,
    ) -> PolicyCheckResult:
        """
        检查 Agent 是否可以调用指定工具

        三层检查：
        1. tool_registry 的 allowed_agents
        2. policy_engine 的 denied_tools
        3. 风险等级限制
        """
        # 第一层：tool_registry
        tool_def = tool_registry.get(tool_name)
        if not tool_def:
            self._log_audit(agent_name, tool_name, "DENY", "unknown tool")
            return PolicyCheckResult(
                decision=PolicyDecision.DENY,
                reason="工具未注册，已按 fail-closed 拒绝",
                tool_name=tool_name,
                agent_name=agent_name,
            )

        if context and not context.channel_allowed:
            self._log_audit(agent_name, tool_name, "DENY", "channel policy denied")
            return PolicyCheckResult(
                decision=PolicyDecision.DENY,
                reason="当前通道策略不允许 Agent 执行该工具",
                tool_name=tool_name,
                agent_name=agent_name,
            )

        if not tool_registry.is_allowed(tool_name, agent_name):
            self._log_audit(agent_name, tool_name, "DENY", "tool_registry 不允许")
            return PolicyCheckResult(
                decision=PolicyDecision.DENY,
                reason=f"工具 {tool_name} 不在 Agent {agent_name} 的 tool_registry 白名单中",
                tool_name=tool_name,
                agent_name=agent_name,
            )

        # 第二层：policy_engine
        policy = self._policies.get(agent_name)
        if policy:
            if policy.allowed_tools is not None and tool_name not in policy.allowed_tools:
                self._log_audit(agent_name, tool_name, "DENY", "policy allowed_tools")
                return PolicyCheckResult(
                    decision=PolicyDecision.DENY,
                    reason=f"工具 {tool_name} 不在 Agent {agent_name} 的显式允许列表中",
                    tool_name=tool_name,
                    agent_name=agent_name,
                )

            if tool_name in policy.denied_tools:
                self._log_audit(agent_name, tool_name, "DENY", "policy denied_tools")
                return PolicyCheckResult(
                    decision=PolicyDecision.DENY,
                    reason=f"Agent {agent_name} 的策略明确禁止调用 {tool_name}",
                    tool_name=tool_name,
                    agent_name=agent_name,
                )

            if tool_def.risk_level == RiskLevel.EXTERNAL_SEND and not policy.can_external_send:
                self._log_audit(agent_name, tool_name, "DENY", "external send disabled")
                return PolicyCheckResult(
                    decision=PolicyDecision.DENY,
                    reason=f"Agent {agent_name} 不允许对外发送或调用外部数据源",
                    tool_name=tool_name,
                    agent_name=agent_name,
                )

            # 第三层：风险等级
            risk_order = [
                RiskLevel.READ_ONLY,
                RiskLevel.WRITE,
                RiskLevel.EXECUTE,
                RiskLevel.EXTERNAL_SEND,
                RiskLevel.HIGH_RISK,
            ]
            tool_risk_idx = risk_order.index(tool_def.risk_level)
            max_risk_idx = risk_order.index(policy.max_risk_level)

            if tool_risk_idx > max_risk_idx:
                self._log_audit(
                    agent_name,
                    tool_name,
                    "DENY",
                    f"风险等级超限: {tool_def.risk_level.value} > {policy.max_risk_level.value}",
                )
                return PolicyCheckResult(
                    decision=PolicyDecision.DENY,
                    reason=f"工具 {tool_name} 风险等级 {tool_def.risk_level.value} 超过 Agent {agent_name} 允许的 {policy.max_risk_level.value}",
                    tool_name=tool_name,
                    agent_name=agent_name,
                )

        context_result = self._check_context(agent_name, tool_name, context)
        if context_result:
            return context_result

        # 审批门控
        if tool_def.requires_approval:
            if (
                context
                and context.approval_state == "approved"
                and _is_valid_approver(context.approver_role)
            ):
                self._log_audit(agent_name, tool_name, "ALLOW", "approved high-risk tool")
                return PolicyCheckResult(
                    decision=PolicyDecision.ALLOW,
                    reason="已由授权角色审批",
                    tool_name=tool_name,
                    agent_name=agent_name,
                )
            self._log_audit(agent_name, tool_name, "REQUIRE_APPROVAL", "工具要求审批")
            return PolicyCheckResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                reason=f"工具 {tool_name} 需要人工审批后才能执行",
                tool_name=tool_name,
                agent_name=agent_name,
                required_approver_role="lawyer" if "legal" in tool_name else "admin",
            )

        self._log_audit(agent_name, tool_name, "ALLOW", "通过所有检查")
        return PolicyCheckResult(
            decision=PolicyDecision.ALLOW,
            reason="通过",
            tool_name=tool_name,
            agent_name=agent_name,
        )

    def _check_context(
        self,
        agent_name: str,
        tool_name: str,
        context: PolicyContext | None,
    ) -> PolicyCheckResult | None:
        if not context:
            return None

        tool_def = tool_registry.get(tool_name)
        if not tool_def:
            return None

        active_features = _active_feature_names(context.subscription_features)
        if active_features is not None and not _feature_allows_tool(
            tool_def.name, tool_def.tags, active_features
        ):
            self._log_audit(agent_name, tool_name, "DENY", "subscription feature denied")
            return PolicyCheckResult(
                decision=PolicyDecision.DENY,
                reason=f"当前订阅能力不包含工具 {tool_name}",
                tool_name=tool_name,
                agent_name=agent_name,
            )

        permissions = _normalize_string_set(context.permissions)
        if permissions is not None:
            missing = set(tool_def.required_permissions) - permissions
            if missing:
                self._log_audit(agent_name, tool_name, "DENY", "missing permissions")
                return PolicyCheckResult(
                    decision=PolicyDecision.DENY,
                    reason=f"当前角色缺少权限: {', '.join(sorted(missing))}",
                    tool_name=tool_name,
                    agent_name=agent_name,
                    missing_permissions=missing,
                )

        if (context.privacy_mode or "").lower() in {"top_secret", "local_only", "offline"}:
            if (
                tool_def.risk_level in {RiskLevel.EXTERNAL_SEND, RiskLevel.HIGH_RISK}
                or "external" in tool_def.tags
            ):
                self._log_audit(agent_name, tool_name, "DENY", "privacy mode denied")
                return PolicyCheckResult(
                    decision=PolicyDecision.DENY,
                    reason="绝密/本地模式不允许外部发送、高风险或外部数据源工具",
                    tool_name=tool_name,
                    agent_name=agent_name,
                )

        if not context.device_trusted and tool_def.risk_level in {
            RiskLevel.EXECUTE,
            RiskLevel.EXTERNAL_SEND,
            RiskLevel.HIGH_RISK,
        }:
            self._log_audit(agent_name, tool_name, "DENY", "untrusted device")
            return PolicyCheckResult(
                decision=PolicyDecision.DENY,
                reason="未受信设备不允许执行可执行、外部发送或高风险工具",
                tool_name=tool_name,
                agent_name=agent_name,
            )

        return None

    def get_agent_available_tools(
        self,
        agent_name: str,
        context: PolicyContext | None = None,
    ) -> list[str]:
        """获取 Agent 可用的所有工具列表"""
        available = []
        for tool_name in tool_registry._tools:
            result = self.check_tool_access(agent_name, tool_name, context=context)
            if result.decision == PolicyDecision.ALLOW:
                available.append(tool_name)
        return available

    def _log_audit(
        self,
        agent_name: str,
        tool_name: str,
        decision: str,
        reason: str,
    ) -> None:
        """记录审计日志"""
        import time

        self._audit_log.append(
            {
                "timestamp": time.time(),
                "agent": agent_name,
                "tool": tool_name,
                "decision": decision,
                "reason": reason,
            }
        )
        if len(self._audit_log) > self._max_audit:
            self._audit_log = self._audit_log[-self._max_audit :]

    def get_stats(self) -> dict[str, Any]:
        """获取策略统计"""
        from collections import Counter

        decisions = Counter(log["decision"] for log in self._audit_log)
        denied_tools = Counter(log["tool"] for log in self._audit_log if log["decision"] == "DENY")
        return {
            "total_checks": len(self._audit_log),
            "decisions": dict(decisions),
            "top_denied_tools": dict(denied_tools.most_common(10)),
            "agents_with_policies": list(self._policies.keys()),
        }


# 全局单例
policy_engine = PolicyEngine()
