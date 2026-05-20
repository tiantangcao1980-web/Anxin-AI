"""
Token 用量与费用统计

按 provider 定价计算每次 LLM 调用的费用，
聚合到任务/会话/用户/Agent 维度。

T6 (2026-05-14):
  - 本地 LLM API 不返 usage 时按 char/4 估算, 避免静默丢失
  - 用户级 token 累计 (_by_user_tokens), 为配额阻断打底
  - check_user_quota() / QuotaExceededError, 调用端可在 LLM 调用前做门禁
"""

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any


class QuotaExceededError(RuntimeError):
    """用户超出订阅 token 配额, 主路径应短路并返回友好提示。"""

    def __init__(self, user_id: str, used: int, quota: int):
        self.user_id = user_id
        self.used = used
        self.quota = quota
        super().__init__(
            f"用户 {user_id} 已用 {used} tokens, 超出订阅配额 {quota}; 请升级套餐或等待下个计费周期"
        )


# 本地 / 自托管 provider 列表 (无 usage 字段时按字符估算)
LOCAL_PROVIDERS = frozenset({"local", "ollama", "lm_studio", "lmstudio", "vllm"})


def estimate_tokens_from_text(text: str) -> int:
    """简易 token 估算: 4 字符 = 1 token (英文均值, 中文偏保守)。

    仅在 LLM API 不返 usage 字段时使用 (典型: 自托管 Ollama / LM Studio)。
    避免静默丢失成本与配额计数。
    """
    if not text:
        return 0
    return max(1, len(text) // 4)

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
        self._by_user_tokens: dict[str, int] = defaultdict(int)  # T6: 配额按 tokens 计
        self._by_agent: dict[str, float] = defaultdict(float)
        self._by_model: dict[str, float] = defaultdict(float)
        self._by_conversation: dict[str, float] = defaultdict(float)
        self._total_tokens: int = 0
        self._total_cost: float = 0.0
        # I4 (2026-05-14): 可选 Redis 后端
        # 设 COST_TRACKER_REDIS_URL=redis://... 启用; 每次 record() 同步增量到 Redis,
        # 把数据丢失窗口从 5 分钟 (E2 snapshot 周期) 进一步降到秒级.
        # 多节点部署时, 各节点 record 自动汇总到同一 Redis key.
        # 失败 → 静默降级到纯内存模式, 不阻断主路径.
        self._redis_init_attempted = False
        self._redis_client: Any = None

    def _get_redis_client(self) -> Any | None:
        """惰性初始化 Redis 客户端 (类似 utils/rate_limit_burst._get_redis_client)。"""
        if self._redis_init_attempted:
            return self._redis_client
        self._redis_init_attempted = True

        import os
        url = os.environ.get("COST_TRACKER_REDIS_URL", "").strip()
        if not url:
            return None
        try:
            import redis
            client = redis.from_url(url, decode_responses=True)
            client.ping()
            self._redis_client = client
            return client
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).warning(
                "cost_tracker: Redis 后端初始化失败, 退回内存模式: %s", exc
            )
            self._redis_client = None
            return None

    def _redis_incr_user(self, user_id: str, tokens: int, cost: float) -> None:
        """I4: 把单次 record 的 (tokens, cost) 同步 ZINCRBY 到 Redis。"""
        client = self._get_redis_client()
        if client is None:
            return
        try:
            # ZINCRBY 同时维护按 user 排序的 leaderboard, 也可用于全局 ranking
            client.zincrby("cost:by_user_tokens", tokens, user_id)
            client.zincrby("cost:by_user_cost", round(cost, 6), user_id)
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).debug(
                "cost_tracker: Redis incr 失败 (不阻断): %s", exc
            )

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
            self._by_user_tokens[user_id] += total
        if agent_name:
            self._by_agent[agent_name] += cost
        self._by_model[model] += cost
        if conversation_id:
            self._by_conversation[str(conversation_id)] += cost

        # I4 (2026-05-14): Redis 增量 (启用时), 把丢失窗口从 5min → 秒级
        if user_id:
            self._redis_incr_user(user_id, total, cost)

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

    def get_user_tokens(self, user_id: str) -> int:
        """T6: 获取用户累计 token 用量, 用于配额扣减。"""
        return self._by_user_tokens.get(user_id, 0)

    def reset_user_tokens(self, user_id: str) -> None:
        """新计费周期开始时清零用户用量 (subscription_service 周期切换时调用)。"""
        self._by_user_tokens.pop(user_id, None)
        self._by_user.pop(user_id, None)

    def check_user_quota(
        self,
        user_id: str,
        quota_tokens: int,
        *,
        upcoming_tokens: int = 0,
    ) -> tuple[bool, int, int]:
        """检查用户是否还在配额内。

        Args:
            user_id: 用户 ID
            quota_tokens: 订阅 token 配额 (0 = 不限)
            upcoming_tokens: 即将消耗的 token 估值 (含本次请求 prompt + 预留 completion)

        Returns:
            (allowed, used, remaining)。allowed=False 时调用端应短路。

        典型用法:
            allowed, used, remaining = cost_tracker.check_user_quota(uid, plan.ai_quota,
                upcoming_tokens=estimate_tokens_from_text(prompt) + 1024)
            if not allowed:
                raise QuotaExceededError(uid, used, plan.ai_quota)
        """
        if quota_tokens <= 0:
            return True, self.get_user_tokens(user_id), 0
        used = self.get_user_tokens(user_id)
        projected = used + max(0, upcoming_tokens)
        remaining = max(0, quota_tokens - projected)
        allowed = projected <= quota_tokens
        return allowed, used, remaining

    # ===== A4 (2026-05-14): DB 持久化层 =====
    # cost_tracker 主路径仍是内存累计 (低延迟), DB 仅作 snapshot / restore /
    # 周期归档. 三个钩子:
    #   snapshot_to_db(db, *, period_start, period_end): 周期性把内存累计落库
    #   restore_from_db(db): 应用启动时把活跃周期数据 (archived=False) 读回内存
    #   archive_and_reset_user(db, user_id, *, new_period): 周期切换时把当前
    #       行 archived=True, 然后清零内存与启用新周期

    async def snapshot_to_db(
        self,
        db: Any,
        *,
        period_start: Any,
        period_end: Any,
    ) -> int:
        """把当前内存累计落库 (upsert 单一活跃行 archived=False)。返回处理的 user 数。"""
        from decimal import Decimal

        from sqlalchemy import select

        from src.models.user_token_usage import UserTokenUsage

        processed = 0
        # 取所有有累计的 user_id (token 或 cost)
        all_users = set(self._by_user_tokens.keys()) | set(self._by_user.keys())
        for user_id in all_users:
            tokens = self._by_user_tokens.get(user_id, 0)
            cost = self._by_user.get(user_id, 0.0)
            # 找 archived=False 的行 (当前周期)
            result = await db.execute(
                select(UserTokenUsage).where(
                    UserTokenUsage.user_id == user_id,
                    UserTokenUsage.archived.is_(False),
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                row = UserTokenUsage(
                    user_id=user_id,
                    period_start=period_start,
                    period_end=period_end,
                    tokens_used=tokens,
                    cost_usd=Decimal(str(round(cost, 6))),
                    call_count=sum(1 for r in self._records if r.user_id == user_id),
                    archived=False,
                )
                db.add(row)
            else:
                row.tokens_used = tokens
                row.cost_usd = Decimal(str(round(cost, 6)))
                row.call_count = sum(1 for r in self._records if r.user_id == user_id)
                # 不动 period 区间 — snapshot 只更新累计值
            processed += 1
        await db.flush()
        return processed

    async def restore_from_db(self, db: Any) -> int:
        """应用启动时把 archived=False 的行读回内存。返回 restore 的 user 数。"""
        from sqlalchemy import select

        from src.models.user_token_usage import UserTokenUsage

        result = await db.execute(
            select(UserTokenUsage).where(UserTokenUsage.archived.is_(False))
        )
        rows = result.scalars().all()
        for row in rows:
            self._by_user_tokens[row.user_id] = int(row.tokens_used or 0)
            self._by_user[row.user_id] = float(row.cost_usd or 0)
        return len(rows)

    async def archive_and_reset_user(
        self,
        db: Any,
        user_id: str,
        *,
        new_period_start: Any = None,
        new_period_end: Any = None,
    ) -> dict[str, Any]:
        """周期切换: 把当前活跃行 archived=True, 内存清零, 可选立即开新周期行。

        Returns: {"archived_tokens": int, "archived_cost": float, "new_period_started": bool}
        """
        from decimal import Decimal

        from sqlalchemy import select

        from src.models.user_token_usage import UserTokenUsage

        # 找当前活跃行
        result = await db.execute(
            select(UserTokenUsage).where(
                UserTokenUsage.user_id == user_id,
                UserTokenUsage.archived.is_(False),
            )
        )
        row = result.scalar_one_or_none()
        archived_tokens = 0
        archived_cost = 0.0
        if row is not None:
            # 同步内存最新值再 archive (避免 in-flight 调用丢失)
            row.tokens_used = self._by_user_tokens.get(user_id, row.tokens_used)
            row.cost_usd = Decimal(str(round(self._by_user.get(user_id, float(row.cost_usd or 0)), 6)))
            row.archived = True
            archived_tokens = row.tokens_used or 0
            archived_cost = float(row.cost_usd or 0)

        # 清零内存
        self.reset_user_tokens(user_id)

        # 可选: 立即创建新周期活跃行 (跳过则等下次 snapshot 自动 upsert)
        new_started = False
        if new_period_start and new_period_end:
            new_row = UserTokenUsage(
                user_id=user_id,
                period_start=new_period_start,
                period_end=new_period_end,
                tokens_used=0,
                cost_usd=Decimal("0"),
                call_count=0,
                archived=False,
            )
            db.add(new_row)
            new_started = True

        await db.flush()
        return {
            "archived_tokens": archived_tokens,
            "archived_cost": archived_cost,
            "new_period_started": new_started,
        }

    def record_with_estimate(
        self,
        *,
        model: str,
        provider: str,
        prompt_text: str = "",
        completion_text: str = "",
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        agent_name: str | None = None,
        operation: str | None = None,
        trace_id: str | None = None,
        conversation_id: str | None = None,
        user_id: str | None = None,
    ) -> CostRecord:
        """T6: 当 LLM API 不返 usage 时, 按字符估算并记录。

        优先用 prompt_tokens / completion_tokens (LLM API 返回的真值);
        缺失时用 prompt_text / completion_text 估算; 都缺失则按 0 记。
        """
        pt = prompt_tokens if prompt_tokens is not None else estimate_tokens_from_text(prompt_text)
        ct = (
            completion_tokens
            if completion_tokens is not None
            else estimate_tokens_from_text(completion_text)
        )
        return self.record(
            model=model,
            provider=provider,
            prompt_tokens=pt,
            completion_tokens=ct,
            agent_name=agent_name,
            operation=operation,
            trace_id=trace_id,
            conversation_id=conversation_id,
            user_id=user_id,
        )


# 全局单例
cost_tracker = CostTracker()
