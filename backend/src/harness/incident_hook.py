# -*- coding: utf-8 -*-
"""
Incident Hook 辅助函数 — E1 (2026-05-14)

CREAO Slice 1 的 3 个失败信号 hook (output_validator / agent_forum /
episodic_memory_service) 在 T5 落地时, __init__ 接受可选 incident_collector
参数, 但生产环境从未注入 (因为这 3 个都是模块级单例, 没有 db 句柄)。

本模块提供一个零依赖的 fire-and-forget helper:
  - 自动用 get_db_context 开 db
  - 自动用 pii_service 单例
  - 自动 catch 所有异常 (hook 自身故障绝不影响主路径)

使用方式 (3 个 hook 内部):
  from src.harness.incident_hook import collect_incident_safely

  await collect_incident_safely(
      source=IncidentSource.OUTPUT_VALIDATOR,
      title=...,
      payload=...,
      severity=...,
      ...
  )
"""

from __future__ import annotations

from typing import Any

from loguru import logger


async def collect_incident_safely(
    *,
    source: Any,
    title: str,
    payload: dict[str, Any],
    severity: Any,
    agent_name: str | None = None,
    route: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    trace_id: str | None = None,
    fingerprint_keys: list[str] | None = None,
) -> None:
    """开自己的 db context + 写 incident; 任何异常都吞掉, 永不影响主路径。

    生产环境的 3 个 CREAO hook (output_validator / agent_forum /
    episodic_memory) 应优先调用 self.incident_collector (如果 caller
    传入了), 否则 fallback 到本函数。
    """
    try:
        from src.core.database import get_db_context
        from src.harness.incident_collector import IncidentCollector
        from src.services.pii_service import pii_service

        # G1 (2026-05-14): 自动从 current_trace() 注入 trace_id, 让 Slice 3 builder
        # 能把 incident 关联回完整 trace 链。caller 显式传入时优先 caller 值。
        if trace_id is None:
            try:
                from src.harness.trace_context import current_trace
                t = current_trace()
                if t is not None:
                    trace_id = t.trace_id
            except Exception:
                pass  # trace context 不可用时静默跳过

        async with get_db_context() as db:
            collector = IncidentCollector(db, pii_service)
            await collector.collect(
                source=source,
                title=title,
                payload=payload,
                severity=severity,
                agent_name=agent_name,
                route=route,
                user_id=user_id,
                session_id=session_id,
                trace_id=trace_id,
                fingerprint_keys=fingerprint_keys,
            )
    except Exception as exc:
        # hook 自身故障绝不能让业务主流程挂掉; warn-level 足够追踪
        logger.warning(f"[IncidentHook] collect_incident_safely 跳过: {exc}")
