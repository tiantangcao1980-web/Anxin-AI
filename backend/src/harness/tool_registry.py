"""
工具注册中心

将散落在各 Agent prompt 中的工具调用统一注册，实现：
1. 统一 schema（输入/输出/风险标签/权限）
2. 调用统计（成功率/延迟/频率）
3. 失败回退策略
4. Agent 工具白名单查询
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger


class RiskLevel(str, Enum):
    """工具风险等级"""

    READ_ONLY = "read_only"  # 只读：知识检索、数据查询
    WRITE = "write"  # 可写：草稿生成、文件创建
    EXECUTE = "execute"  # 可执行：脚本运行、命令执行
    EXTERNAL_SEND = "external_send"  # 对外发送：邮件、消息、API调用
    HIGH_RISK = "high_risk"  # 高风险：支付、删除、正式文件签发


@dataclass
class ToolDefinition:
    """工具定义"""

    name: str  # 唯一标识，如 "search_knowledge"
    display_name: str  # 显示名称，如 "知识库检索"
    description: str  # 功能描述
    risk_level: RiskLevel  # 风险等级
    service_module: str  # 所在服务模块，如 "src.services.knowledge_service"
    method_name: str  # 方法名，如 "search"
    input_schema: dict[str, Any] | None = None  # 输入参数 schema
    output_schema: dict[str, Any] | None = None  # 输出格式 schema
    allowed_agents: set[str] | None = None  # 允许调用的 Agent 列表（None=全部可用）
    required_permissions: set[str] = field(default_factory=set)  # 用户权限要求（可选）
    requires_approval: bool = False  # 是否需要人工审批
    timeout_seconds: int = 30  # 超时时间
    retry_count: int = 1  # 重试次数
    fallback_tool: str | None = None  # 失败时回退到的工具
    tags: list[str] = field(default_factory=list)  # 标签分类


@dataclass
class ToolCallRecord:
    """工具调用记录"""

    tool_name: str
    agent_name: str
    timestamp: float
    latency_ms: float
    success: bool
    error_msg: str | None = None


class ToolRegistry:
    """
    工具注册中心

    管理所有 Agent 可调用的工具/服务，支持：
    - 注册与查询
    - 权限校验
    - 调用统计
    - 失败回退
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._call_history: list[ToolCallRecord] = []
        self._call_counts: dict[str, int] = defaultdict(int)
        self._success_counts: dict[str, int] = defaultdict(int)
        self._total_latency: dict[str, float] = defaultdict(float)
        self._max_history = 5000
        self._register_builtin_tools()

    def _register_builtin_tools(self) -> None:
        """注册内置工具集"""
        builtin_tools = [
            # ===== 知识检索类（只读）=====
            ToolDefinition(
                name="search_knowledge",
                display_name="知识库检索",
                description="从法律知识库中检索相关法条、案例、法规",
                risk_level=RiskLevel.READ_ONLY,
                service_module="src.services.knowledge_service",
                method_name="search",
                required_permissions={"read:knowledge"},
                tags=["knowledge", "search", "rag"],
            ),
            ToolDefinition(
                name="search_vector",
                display_name="向量语义检索",
                description="使用向量相似度检索法律文档",
                risk_level=RiskLevel.READ_ONLY,
                service_module="src.services.vector_store",
                method_name="search",
                required_permissions={"read:knowledge"},
                tags=["knowledge", "search", "vector"],
            ),
            ToolDefinition(
                name="query_graph",
                display_name="知识图谱查询",
                description="从 Neo4j 知识图谱中查询实体和关系",
                risk_level=RiskLevel.READ_ONLY,
                service_module="src.services.graph_service",
                method_name="query",
                required_permissions={"read:knowledge"},
                tags=["knowledge", "graph"],
            ),
            ToolDefinition(
                name="search_case_law",
                display_name="案例检索",
                description="检索裁判文书和典型案例",
                risk_level=RiskLevel.READ_ONLY,
                service_module="src.services.legal_rag",
                method_name="search_cases",
                required_permissions={"read:knowledge"},
                tags=["knowledge", "search", "case"],
            ),
            # ===== 文档处理类（可写）=====
            ToolDefinition(
                name="draft_contract",
                display_name="合同草稿生成",
                description="根据需求生成合同草稿",
                risk_level=RiskLevel.WRITE,
                service_module="src.services.template_engine",
                method_name="generate_contract",
                allowed_agents={
                    "document_drafter",
                    "contract_reviewer",
                    "contract_steward",
                    "legal_advisor",
                },
                required_permissions={"write:contracts"},
                tags=["document", "contract", "generate"],
            ),
            ToolDefinition(
                name="draft_document",
                display_name="法律文书生成",
                description="生成法律文书（起诉状、答辩状、协议等）",
                risk_level=RiskLevel.WRITE,
                service_module="src.services.template_engine",
                method_name="generate_document",
                allowed_agents={"document_drafter", "legal_advisor", "litigation_strategist"},
                required_permissions={"write:documents"},
                tags=["document", "generate"],
            ),
            ToolDefinition(
                name="validate_document",
                display_name="文档质量校验",
                description="对生成的法律文档进行结构和内容校验",
                risk_level=RiskLevel.READ_ONLY,
                service_module="src.services.document_validator",
                method_name="validate",
                required_permissions={"read:documents"},
                tags=["document", "validate"],
            ),
            # ===== 分析类（只读）=====
            ToolDefinition(
                name="analyze_risk",
                display_name="风险分析",
                description="分析合同或案件的法律风险",
                risk_level=RiskLevel.READ_ONLY,
                service_module="src.services.compliance_service",
                method_name="analyze_risk",
                allowed_agents={
                    "risk_assessor",
                    "compliance_officer",
                    "contract_reviewer",
                    "legal_advisor",
                },
                required_permissions={"review:contracts"},
                tags=["analysis", "risk"],
            ),
            ToolDefinition(
                name="analyze_sentiment",
                display_name="舆情分析",
                description="分析企业相关舆情和公众情绪",
                risk_level=RiskLevel.READ_ONLY,
                service_module="src.services.sentiment_service",
                method_name="analyze",
                allowed_agents={"sentiment_agent", "due_diligence", "regulatory_monitor"},
                required_permissions={"view:analytics"},
                tags=["analysis", "sentiment"],
            ),
            ToolDefinition(
                name="verify_citation",
                display_name="引文核查",
                description="验证法条和案例引用的真实性",
                risk_level=RiskLevel.READ_ONLY,
                service_module="src.services.citation_tracker",
                method_name="verify_citations",
                required_permissions={"read:knowledge"},
                tags=["validate", "citation"],
            ),
            # ===== 数据采集类（外部访问）=====
            ToolDefinition(
                name="crawl_company_info",
                display_name="企业信息采集",
                description="从天眼查/企查查等平台采集企业工商信息",
                risk_level=RiskLevel.EXTERNAL_SEND,
                service_module="src.services.crawler_service",
                method_name="crawl_company",
                allowed_agents={"due_diligence", "evidence_analyst"},
                required_permissions={"read:assets"},
                timeout_seconds=60,
                tags=["external", "crawl", "company"],
            ),
            ToolDefinition(
                name="web_search",
                display_name="互联网检索",
                description="搜索互联网获取公开法律信息",
                risk_level=RiskLevel.EXTERNAL_SEND,
                service_module="src.services.crawler_service",
                method_name="web_search",
                required_permissions={"read:knowledge"},
                timeout_seconds=30,
                tags=["external", "search", "web"],
            ),
            # ===== 高风险操作类 =====
            ToolDefinition(
                name="send_email",
                display_name="发送邮件",
                description="向客户或律师发送邮件通知",
                risk_level=RiskLevel.HIGH_RISK,
                service_module="src.services.email_service",
                method_name="send",
                required_permissions={"manage:system"},
                requires_approval=True,
                allowed_agents=set(),  # 默认禁止所有 Agent 直接调用
                tags=["external", "email", "high_risk"],
            ),
            ToolDefinition(
                name="create_payment",
                display_name="创建支付",
                description="创建支付订单",
                risk_level=RiskLevel.HIGH_RISK,
                service_module="src.services.payment_service",
                method_name="create_order",
                required_permissions={"manage:payments"},
                requires_approval=True,
                allowed_agents=set(),  # 禁止 Agent 直接调用
                tags=["payment", "high_risk"],
            ),
            ToolDefinition(
                name="generate_legal_opinion",
                display_name="生成正式法律意见",
                description="生成正式法律意见书（需律师审批）",
                risk_level=RiskLevel.HIGH_RISK,
                service_module="src.services.report_engine",
                method_name="generate_opinion",
                required_permissions={"review:contracts", "sign:contracts"},
                requires_approval=True,
                allowed_agents={"legal_advisor", "litigation_strategist"},
                tags=["document", "opinion", "high_risk"],
            ),
        ]

        for tool in builtin_tools:
            self.register(tool)

        logger.info(f"[ToolRegistry] 注册 {len(self._tools)} 个内置工具")

    def register(self, tool: ToolDefinition) -> None:
        """注册工具"""
        self._tools[tool.name] = tool

    def get(self, tool_name: str) -> ToolDefinition | None:
        """获取工具定义"""
        return self._tools.get(tool_name)

    def list_tools(
        self,
        risk_level: RiskLevel | None = None,
        tag: str | None = None,
        agent_name: str | None = None,
    ) -> list[ToolDefinition]:
        """列出工具（支持过滤）"""
        tools = list(self._tools.values())

        if risk_level:
            tools = [t for t in tools if t.risk_level == risk_level]

        if tag:
            tools = [t for t in tools if tag in t.tags]

        if agent_name:
            tools = [t for t in tools if t.allowed_agents is None or agent_name in t.allowed_agents]

        return tools

    def is_allowed(self, tool_name: str, agent_name: str) -> bool:
        """检查 Agent 是否有权限调用此工具"""
        tool = self._tools.get(tool_name)
        if not tool:
            return False
        if tool.allowed_agents is None:
            return True  # None 表示所有 Agent 可用
        return agent_name in tool.allowed_agents

    def record_call(
        self,
        tool_name: str,
        agent_name: str,
        latency_ms: float,
        success: bool,
        error_msg: str | None = None,
    ) -> None:
        """记录工具调用"""
        record = ToolCallRecord(
            tool_name=tool_name,
            agent_name=agent_name,
            timestamp=time.time(),
            latency_ms=latency_ms,
            success=success,
            error_msg=error_msg,
        )
        self._call_history.append(record)
        if len(self._call_history) > self._max_history:
            self._call_history = self._call_history[-self._max_history :]

        self._call_counts[tool_name] += 1
        if success:
            self._success_counts[tool_name] += 1
        self._total_latency[tool_name] += latency_ms

    def get_tool_stats(self, tool_name: str | None = None) -> dict[str, Any]:
        """获取工具调用统计"""
        if tool_name:
            total = self._call_counts.get(tool_name, 0)
            success = self._success_counts.get(tool_name, 0)
            avg_latency = self._total_latency.get(tool_name, 0) / total if total > 0 else 0
            return {
                "tool": tool_name,
                "total_calls": total,
                "success_rate": round(success / total, 3) if total > 0 else 0,
                "avg_latency_ms": round(avg_latency, 2),
            }

        # 全局统计
        stats: dict[str, dict[str, int | float]] = {}
        for name in self._tools:
            total = self._call_counts.get(name, 0)
            if total == 0:
                continue
            success = self._success_counts.get(name, 0)
            avg_latency = self._total_latency.get(name, 0) / total
            stats[name] = {
                "total_calls": total,
                "success_rate": round(success / total, 3),
                "avg_latency_ms": round(avg_latency, 2),
            }
        return stats

    def get_summary(self) -> dict[str, Any]:
        """获取注册中心摘要"""
        by_risk: defaultdict[str, int] = defaultdict(int)
        for t in self._tools.values():
            by_risk[t.risk_level.value] += 1
        return {
            "total_tools": len(self._tools),
            "by_risk_level": dict(by_risk),
            "requires_approval": [t.name for t in self._tools.values() if t.requires_approval],
            "total_calls": sum(self._call_counts.values()),
        }


# 全局单例
tool_registry = ToolRegistry()
