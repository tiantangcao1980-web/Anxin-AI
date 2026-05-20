"""
Token 用量与费用统计

按 provider 定价计算每次 LLM 调用的费用，
聚合到任务/会话/用户/Agent 维度。
"""

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

# ===== 主流模型定价（$/M tokens, 2026-04 更新）=====
# 来源: OpenAI / Anthropic / DeepSeek 官方定价
PRICING_TABLE: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "o3": {"input": 10.00, "output": 40.00},
    "o3-mini": {"input": 1.10, "output": 4.40},
    "o4-mini": {"input": 1.10, "output": 4.40},
    # Anthropic
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    # DeepSeek
    "deepseek-chat": {"input": 0.27, "output": 1.10},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    # Qwen（通义千问）
    "qwen-plus": {"input": 0.80, "output": 2.00},
    "qwen-turbo": {"input": 0.30, "output": 0.60},
    "qwen-max": {"input": 2.40, "output": 9.60},
    # 本地模型 — 零成本（仅电力）
    "local": {"input": 0.0, "output": 0.0},
}

# 默认定价（未知模型）
DEFAULT_PRICING = {"input": 1.00, "output": 3.00}


@dataclass
class CostRecord:
    """单次 LLM 调用的费用记录"""

    timestamp: float
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    agent_name: str | None = None
    operation: str | None = None
    trace_id: str | None = None
    conversation_id: str | None = None
    user_id: str | None = None


class CostTracker:
    """
    全局费用追踪器

    内存中保留最近 N 条记录，支持多维度聚合。
    生产环境可扩展为写入数据库。
    """

    def __init__(self, max_records: int = 10000):
        self._records: list[CostRecord] = []
        self._max_records = max_records
        # 聚合缓存
        self._by_user: dict[str, float] = defaultdict(float)
        self._by_agent: dict[str, float] = defaultdict(float)
        self._by_model: dict[str, float] = defaultdict(float)
        self._by_conversation: dict[str, float] = defaultdict(float)
        self._total_tokens: int = 0
        self._total_cost: float = 0.0

    def get_pricing(self, model: str) -> dict[str, float]:
        """查找模型定价，支持模糊匹配"""
        if model in PRICING_TABLE:
            return PRICING_TABLE[model]
        # 模糊匹配：gpt-4o-2024xxxx → gpt-4o
        for key in PRICING_TABLE:
            if model.startswith(key):
                return PRICING_TABLE[key]
        # 本地模型检测
        if any(tag in model.lower() for tag in ["qwen2.5", "llama", "glm", "yi-", "local"]):
            return PRICING_TABLE["local"]
        return DEFAULT_PRICING

    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """计算单次调用费用（美元）"""
        pricing = self.get_pricing(model)
        cost = (
            prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]
        ) / 1_000_000
        return round(cost, 8)

    def record(
        self,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        agent_name: str | None = None,
        operation: str | None = None,
        trace_id: str | None = None,
        conversation_id: str | None = None,
        user_id: str | None = None,
    ) -> CostRecord:
        """记录一次 LLM 调用"""
        total = prompt_tokens + completion_tokens
        cost = self.calculate_cost(model, prompt_tokens, completion_tokens)

        record = CostRecord(
            timestamp=time.time(),
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            cost_usd=cost,
            agent_name=agent_name,
            operation=operation,
            trace_id=trace_id,
            conversation_id=conversation_id,
            user_id=user_id,
        )

        self._records.append(record)
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records :]

        # 更新聚合
        self._total_tokens += total
        self._total_cost += cost
        if user_id:
            self._by_user[user_id] += cost
        if agent_name:
            self._by_agent[agent_name] += cost
        self._by_model[model] += cost
        if conversation_id:
            self._by_conversation[str(conversation_id)] += cost

        # 同步更新 trace_context
        from src.harness.trace_context import current_trace

        trace = current_trace()
        if trace:
            trace.record_llm_usage(prompt_tokens, completion_tokens, cost)

        return record

    def get_stats(self) -> dict[str, Any]:
        """获取全局统计"""
        return {
            "total_records": len(self._records),
            "total_tokens": self._total_tokens,
            "total_cost_usd": round(self._total_cost, 4),
            "by_model": dict(self._by_model),
            "by_agent": dict(self._by_agent),
            "top_users": dict(sorted(self._by_user.items(), key=lambda x: x[1], reverse=True)[:10]),
        }

    def get_conversation_cost(self, conversation_id: str) -> dict[str, Any]:
        """获取单个会话的费用明细"""
        conv_records = [r for r in self._records if r.conversation_id == str(conversation_id)]
        total_cost = sum(r.cost_usd for r in conv_records)
        total_tokens = sum(r.total_tokens for r in conv_records)
        return {
            "conversation_id": conversation_id,
            "call_count": len(conv_records),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "by_agent": {
                agent: round(sum(r.cost_usd for r in conv_records if r.agent_name == agent), 6)
                for agent in {r.agent_name for r in conv_records if r.agent_name}
            },
        }

    def get_user_cost(self, user_id: str) -> float:
        """获取用户累计费用"""
        return round(self._by_user.get(user_id, 0.0), 6)


# 全局单例
cost_tracker = CostTracker()
