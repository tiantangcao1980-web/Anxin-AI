# -*- coding: utf-8 -*-
"""
Trace 持久化 Sink（T1 骨架 / 待 H1 接入主路径）

设计要点：
- Fire-and-forget：enqueue() 立即返回，不阻塞主路径
- 批量落盘：worker 每 flush_interval_ms 或满 batch_size 触发
- 队列满降级：丢弃最早 + warning 日志 + sentry 上报
- PII 脱敏：进队列前过 scrub（H1 时接 pii_service）

设计文档：docs/audit/harness/01-trace-persistence-design.md
本文件不导入到主路径，等 H1 时由 trace_context.end_trace() 调用 enqueue()。
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from collections import deque
from collections.abc import Callable
from typing import Any

from loguru import logger

# ===== PII 脱敏（最小可用，H1 接 pii_service 替换） =====

_SCRUBBERS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b\d{17}[\dXx]\b"), "[MASK_ID]"),                      # 身份证
    (re.compile(r"\b1[3-9]\d{9}\b"), "[MASK_PHONE]"),                    # 手机
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[MASK_EMAIL]"),       # 邮箱
    (re.compile(r"\b(?:\d[ -]?){12,18}\d\b"), "[MASK_CARD]"),            # 银行卡
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "[MASK_KEY]"),                  # OpenAI key
    (re.compile(r"(?i)(password[\"':= ]+)(\S+)"), r"\1[MASK_PWD]"),     # 密码
]


def scrub(text: str | None) -> str | None:
    """最小化 PII 脱敏（H1 替换为调用 pii_service.scrub）"""
    if not text:
        return text
    out = text
    for pattern, replacement in _SCRUBBERS:
        out = pattern.sub(replacement, out)
    return out


def scrub_dict(data: dict) -> dict:
    """递归脱敏 dict 值（仅字符串）"""
    if not isinstance(data, dict):
        return data
    out = {}
    for k, v in data.items():
        if isinstance(v, str):
            out[k] = scrub(v)
        elif isinstance(v, dict):
            out[k] = scrub_dict(v)
        elif isinstance(v, list):
            out[k] = [scrub_dict(x) if isinstance(x, dict) else (scrub(x) if isinstance(x, str) else x) for x in v]
        else:
            out[k] = v
    return out


# ===== 失败聚类签名 =====

def cluster_id_for(error_type: str, agent_name: str, tool_name: str, error_msg: str) -> str:
    """生成失败聚类 key"""
    msg = (error_msg or "").lower().splitlines()[0] if error_msg else ""
    # 归一化：截断省略号 / hash / id / 数字
    msg = re.sub(r"\.{3,}", "", msg)                        # 省略号
    msg = re.sub(r"\b[a-f0-9]{4,}\b", "X", msg)             # hash / uuid / 高熵 token
    msg = re.sub(r"\d+", "N", msg)[:200]                    # 数字
    raw = f"{error_type}|{agent_name}|{tool_name}|{msg}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


# ===== Sink 主体 =====

class TraceSink:
    """Trace 持久化 Sink（fire-and-forget）

    用法（H1 时接入）：
        from src.services.trace_sink import trace_sink
        await trace_sink.start()  # 应用启动时
        trace_sink.enqueue(trace_summary)  # end_trace() 中调用
        await trace_sink.stop()  # 应用关闭时
    """

    def __init__(
        self,
        batch_size: int = 50,
        flush_interval_ms: int = 500,
        max_queue: int = 10_000,
        writer: Callable[[list[dict]], Any] | None = None,
    ):
        self.batch_size = batch_size
        self.flush_interval = flush_interval_ms / 1000.0
        self.max_queue = max_queue
        self.writer = writer or self._default_writer
        self._queue: deque[dict] = deque()
        self._worker_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._dropped = 0

    def enqueue(self, trace_summary: dict) -> bool:
        """非阻塞入队。返回 False 表示因满被丢弃。"""
        if len(self._queue) >= self.max_queue:
            self._dropped += 1
            if self._dropped % 100 == 1:
                logger.warning(
                    f"[TraceSink] 队列已满 max={self.max_queue}, 已丢弃 {self._dropped} 条"
                )
            return False

        scrubbed = self._scrub_summary(trace_summary)
        self._queue.append(scrubbed)
        return True

    def _scrub_summary(self, summary: dict) -> dict:
        """脱敏 + 附加聚类签名"""
        scrubbed = scrub_dict(summary)
        # 给每个 error span 加 cluster_id
        for span in scrubbed.get("agent_spans", []) or []:
            if span.get("status") == "error":
                span["cluster_id"] = cluster_id_for(
                    error_type=span.get("error_type", "unknown"),
                    agent_name=span.get("agent", ""),
                    tool_name=span.get("tool", ""),
                    error_msg=span.get("error_msg", ""),
                )
        return scrubbed

    async def start(self):
        """启动后台 worker"""
        if self._worker_task and not self._worker_task.done():
            return
        self._stop_event.clear()
        self._worker_task = asyncio.create_task(self._run())
        logger.info("[TraceSink] worker 已启动")

    async def stop(self):
        """优雅停止"""
        self._stop_event.set()
        if self._worker_task:
            await self._worker_task
            self._worker_task = None
        await self._flush()  # 最后一次冲刷
        logger.info(f"[TraceSink] worker 已停止 (累计丢弃 {self._dropped} 条)")

    async def _run(self):
        """worker 主循环"""
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.flush_interval)
            except TimeoutError:
                pass
            await self._flush()

    async def _flush(self):
        """从 queue 取出 batch 落盘"""
        if not self._queue:
            return
        batch: list[dict] = []
        while self._queue and len(batch) < self.batch_size:
            batch.append(self._queue.popleft())
        if not batch:
            return
        try:
            await self._invoke_writer(batch)
        except Exception as e:
            logger.error(f"[TraceSink] 落盘失败 batch={len(batch)} err={e}")
            # 落盘失败不重新入队（避免雪崩）；依赖 metrics 告警

    async def _invoke_writer(self, batch: list[dict]):
        result = self.writer(batch)
        if asyncio.iscoroutine(result):
            await result

    async def _default_writer(self, batch: list[dict]):
        """T1 stub：仅打印；H1 替换为 SQLAlchemy 写入"""
        logger.debug(f"[TraceSink] (stub) 即将落盘 {len(batch)} 条 trace")

    @property
    def stats(self) -> dict:
        return {
            "queue_size": len(self._queue),
            "max_queue": self.max_queue,
            "dropped": self._dropped,
            "running": self._worker_task is not None and not self._worker_task.done(),
        }


# 全局单例（H1 时由应用启动器调用 .start()）
trace_sink = TraceSink()
