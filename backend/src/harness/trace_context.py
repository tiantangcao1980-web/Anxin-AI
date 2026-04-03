# -*- coding: utf-8 -*-
"""
全链路请求追踪

为每个用户请求生成 trace_id，贯穿 chat_service → workforce → coordinator → agents → tools，
支持事后回放"一个回答是怎么生成的"。
"""

import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class SpanRecord:
    """单个操作的记录"""
    span_id: str
    parent_span_id: Optional[str]
    operation: str          # 如 "coordinator.analyze", "agent.contract_reviewer.chat"
    agent_name: Optional[str] = None
    tool_name: Optional[str] = None
    start_time: float = 0.0
    end_time: float = 0.0
    status: str = "started"  # started / success / error / timeout
    error_msg: Optional[str] = None
    token_usage: Optional[Dict[str, int]] = None  # {prompt_tokens, completion_tokens, total_tokens}
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def latency_ms(self) -> float:
        if self.end_time and self.start_time:
            return round((self.end_time - self.start_time) * 1000, 2)
        return 0.0


@dataclass
class TraceContext:
    """一次请求的完整追踪上下文"""
    trace_id: str
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    route: Optional[str] = None
    start_time: float = 0.0
    spans: List[SpanRecord] = field(default_factory=list)
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost_usd: float = 0.0
    _current_span_id: Optional[str] = field(default=None, repr=False)

    def start_span(
        self,
        operation: str,
        agent_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        **metadata,
    ) -> str:
        """开始一个新 span，返回 span_id"""
        span_id = uuid.uuid4().hex[:12]
        span = SpanRecord(
            span_id=span_id,
            parent_span_id=parent_span_id or self._current_span_id,
            operation=operation,
            agent_name=agent_name,
            tool_name=tool_name,
            start_time=time.time(),
            metadata=metadata,
        )
        self.spans.append(span)
        self._current_span_id = span_id
        return span_id

    def end_span(
        self,
        span_id: str,
        status: str = "success",
        error_msg: Optional[str] = None,
        token_usage: Optional[Dict[str, int]] = None,
    ):
        """结束一个 span"""
        for span in self.spans:
            if span.span_id == span_id:
                span.end_time = time.time()
                span.status = status
                span.error_msg = error_msg
                if token_usage:
                    span.token_usage = token_usage
                    self.total_prompt_tokens += token_usage.get("prompt_tokens", 0)
                    self.total_completion_tokens += token_usage.get("completion_tokens", 0)
                # 恢复 parent span
                self._current_span_id = span.parent_span_id
                return
        logger.warning(f"TraceContext: span {span_id} not found")

    def record_llm_usage(self, prompt_tokens: int, completion_tokens: int, cost_usd: float = 0.0):
        """快速记录 LLM token 用量（不关联特定 span 时使用）"""
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_cost_usd += cost_usd

    @property
    def total_tokens(self) -> int:
        return self.total_prompt_tokens + self.total_completion_tokens

    @property
    def elapsed_ms(self) -> float:
        if self.start_time:
            return round((time.time() - self.start_time) * 1000, 2)
        return 0.0

    def to_summary(self) -> Dict[str, Any]:
        """生成可存储的摘要"""
        return {
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "route": self.route,
            "elapsed_ms": self.elapsed_ms,
            "span_count": len(self.spans),
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "error_spans": [
                {"operation": s.operation, "error": s.error_msg}
                for s in self.spans if s.status == "error"
            ],
            "agent_spans": [
                {
                    "operation": s.operation,
                    "agent": s.agent_name,
                    "latency_ms": s.latency_ms,
                    "tokens": s.token_usage,
                    "status": s.status,
                }
                for s in self.spans if s.agent_name
            ],
        }


# ===== 全局 ContextVar，线程/协程安全 =====
_trace_var: ContextVar[Optional[TraceContext]] = ContextVar("_trace_var", default=None)


def start_trace(
    user_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> TraceContext:
    """创建并激活一个新的 trace"""
    trace = TraceContext(
        trace_id=uuid.uuid4().hex[:16],
        user_id=user_id,
        conversation_id=conversation_id,
        start_time=time.time(),
    )
    _trace_var.set(trace)
    return trace


def current_trace() -> Optional[TraceContext]:
    """获取当前协程的 trace（可能为 None）"""
    return _trace_var.get()


def end_trace() -> Optional[Dict[str, Any]]:
    """结束当前 trace 并返回摘要"""
    trace = _trace_var.get()
    if trace:
        summary = trace.to_summary()
        _trace_var.set(None)
        logger.info(
            f"[Trace {trace.trace_id}] 完成 | "
            f"{trace.elapsed_ms:.0f}ms | "
            f"{trace.total_tokens} tokens | "
            f"${trace.total_cost_usd:.4f} | "
            f"{len(trace.spans)} spans"
        )
        return summary
    return None
