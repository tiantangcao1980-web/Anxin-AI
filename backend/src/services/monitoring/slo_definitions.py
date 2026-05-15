"""
SLO 定义（P19-A）

5 个核心业务域 SLO，对应 prometheus 业务 metric 用于：
1. Grafana SLO dashboard（错误预算 + 燃烧率）
2. Alertmanager 告警规则（fast burn / slow burn）
3. 月度复盘 — error budget 剩余量

字段含义：
- p99_latency_seconds  延迟 SLO（基于 anxin_http_request_duration_seconds）
- error_rate           错误率 SLO（5xx / 总请求；oauth/webhook 看 result label）
- availability         月度可用性 SLO（用于 burn rate 公式）
- window_days          统计窗口（默认 30 天滚动）
- endpoint_pattern     prometheus label_re 表达式（哪些 endpoint 算入此 SLO）
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SLO:
    name: str                       # 唯一标识（auth/chat/tasks/fetch/oauth）
    description: str                # 中文描述
    p99_latency_seconds: float      # 延迟 SLO（p99）
    error_rate: float               # 错误率 SLO（0~1）
    availability: float             # 月度可用性 SLO（0~1）
    window_days: int = 30
    endpoint_pattern: str = ""      # prometheus label re，匹配 anxin_http_request_duration_seconds
    notes: str = ""                 # 额外说明
    fast_burn_alert_hours: float = 1.0  # fast burn 告警窗口（消耗 2% 预算/h 触发）
    slow_burn_alert_hours: float = 6.0  # slow burn 告警窗口（消耗 5% 预算/6h 触发）

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def error_budget_per_window(self, total_requests: int) -> float:
        """根据总请求数计算 error budget（次数）。"""
        return max(0.0, total_requests * (1.0 - self.availability))


# ===== 5 个核心 SLO =====
SLO_AUTH = SLO(
    name="auth",
    description="登录 / 注册 / Token 刷新等认证类 API",
    p99_latency_seconds=0.5,
    error_rate=0.001,
    availability=0.999,
    endpoint_pattern=r"/api/v1/auth/.*",
    notes="认证是用户进入系统的第一站，SLO 收紧到 99.9% 与 0.1% 错误率",
)

SLO_CHAT = SLO(
    name="chat",
    description="AI 对话端点（流式 / 非流式 / persona 路由）",
    p99_latency_seconds=3.0,
    error_rate=0.01,
    availability=0.995,
    endpoint_pattern=r"/api/v1/(chat|personas/.*)",
    notes="LLM 调用受上游 OpenAI/Anthropic 限制，SLO 适度放宽至 99.5% 与 1%",
)

SLO_TASKS = SLO(
    name="tasks",
    description="任务列表 / 详情 / 创建 / 状态更新（同步轻量 API）",
    p99_latency_seconds=0.1,
    error_rate=0.005,
    availability=0.999,
    endpoint_pattern=r"/api/v1/(tasks|agent-tasks)/.*",
    notes="任务相关 API 应低延迟，p99 100ms",
)

SLO_FETCH = SLO(
    name="fetch",
    description="统一抓取栈（L1 静态 / L2 crawl4ai / L3 HeadlessX / L4 SearXNG）",
    p99_latency_seconds=30.0,
    error_rate=0.05,
    availability=0.99,
    endpoint_pattern=r"/api/v1/fetch/.*",
    notes="外部依赖密集，SLO 放宽至 99% / 5% 错误率",
)

SLO_OAUTH = SLO(
    name="oauth",
    description="OAuth 回调（微信 / 支付宝 / 钉钉 / Notion / Shopify）",
    p99_latency_seconds=2.0,
    error_rate=0.005,
    availability=0.999,
    endpoint_pattern=r"/api/v1/(oauth|app-authorizations)/.*",
    notes="OAuth callback 失败直接影响第三方集成上线率",
)


# ===== 汇总（导入入口） =====
SLO_LIST: list[SLO] = [SLO_AUTH, SLO_CHAT, SLO_TASKS, SLO_FETCH, SLO_OAUTH]
SLO_MATRIX: dict[str, SLO] = {s.name: s for s in SLO_LIST}


def list_slos() -> list[dict[str, object]]:
    """返回所有 SLO 的字典形态（admin dashboard 用）。"""
    return [s.to_dict() for s in SLO_LIST]


def slo_for_endpoint(endpoint: str) -> SLO | None:
    """根据 endpoint 查匹配的 SLO（首个命中）。"""
    import re

    for s in SLO_LIST:
        if s.endpoint_pattern and re.match(s.endpoint_pattern, endpoint):
            return s
    return None
