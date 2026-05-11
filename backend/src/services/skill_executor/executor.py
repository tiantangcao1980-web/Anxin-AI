# -*- coding: utf-8 -*-
"""
SkillExecutor —— 技能执行器（P5-A）

设计要点：
    - **不直接耦合具体 LLM**：通过 ``llm_callable`` 注入。生产默认实现见
      ``_default_llm_call``，会按需 lazy-import 项目内的 ``LLMService`` /
      ``rag_service`` 等模块。测试时直接传 mock callable 即可。
    - **app_authorizations 校验**：若 ``Skill.requires_apps`` 非空，会和
      ``ExecutionContext.app_authorizations`` 取交集；缺权限直接 SKIPPED。
    - **persona 校验**：若 ``Skill.personas`` 非空，需匹配 context.persona。
    - **execute_batch**：基于 ``asyncio.gather`` 并发执行，单条失败不影响其它。
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from src.services.skill_executor.models import (
    ExecutionContext,
    SkillExecutionLog,
    SkillExecutionStatus,
    SkillResult,
)
from src.services.skill_registry import Skill, SkillRegistry

logger = logging.getLogger(__name__)

# LLM callable 协议：接收 system_prompt + user_prompt，返回字符串 / 协程
LLMCallable = Callable[[str, str], "str | Awaitable[str]"]


class SkillNotFoundError(LookupError):
    """注册表里找不到对应 skill。"""


class SkillDisabledError(RuntimeError):
    """skill 被运行时禁用。"""


class SkillExecutor:
    """运行时技能执行器。

    用法::

        executor = SkillExecutor(registry=SkillRegistry.instance())
        ctx = ExecutionContext(user_id="u1", persona="lawyer")
        result = await executor.execute("contract-review", {"file": "..."}, ctx)
    """

    def __init__(
        self,
        registry: SkillRegistry | None = None,
        llm_callable: LLMCallable | None = None,
    ) -> None:
        self.registry = registry or SkillRegistry.instance()
        self.llm_callable: LLMCallable = llm_callable or _default_llm_call
        self._logs: list[SkillExecutionLog] = []  # 进程内简易历史，便于调试

    # ------------------------------------------------------------------
    # 单次执行
    # ------------------------------------------------------------------
    async def execute(
        self,
        skill_name: str,
        payload: dict[str, Any],
        context: ExecutionContext,
    ) -> SkillResult:
        """执行单条 skill。

        异常以 ``SkillResult(status=FAILED)`` 形式返回，不向外抛。
        """
        log = SkillExecutionLog(
            skill_name=skill_name,
            user_id=context.user_id,
            persona=context.persona,
            payload=dict(payload or {}),
            status=SkillExecutionStatus.RUNNING,
        )
        self._logs.append(log)

        skill = self.registry.get(skill_name)
        if skill is None:
            log.mark_failed(f"skill 不存在: {skill_name}")
            return SkillResult(
                skill_name=skill_name,
                status=SkillExecutionStatus.FAILED,
                error=log.error,
            )
        if not skill.enabled:
            log.status = SkillExecutionStatus.SKIPPED
            log.error = "skill 已被禁用"
            return SkillResult(
                skill_name=skill_name,
                status=SkillExecutionStatus.SKIPPED,
                error=log.error,
            )

        # persona 鉴权
        if not skill.supports_persona(context.persona):
            log.status = SkillExecutionStatus.SKIPPED
            log.error = f"persona {context.persona!r} 无权访问该 skill"
            return SkillResult(
                skill_name=skill_name,
                status=SkillExecutionStatus.SKIPPED,
                error=log.error,
            )

        # app 授权鉴权
        missing = [
            app for app in skill.requires_apps if app not in context.app_authorizations
        ]
        if missing:
            log.status = SkillExecutionStatus.SKIPPED
            log.error = f"缺少应用授权: {missing}"
            return SkillResult(
                skill_name=skill_name,
                status=SkillExecutionStatus.SKIPPED,
                error=log.error,
                metadata={"missing_apps": missing},
            )

        # 真正执行
        started = time.perf_counter()
        try:
            system_prompt, user_prompt = self._build_prompt(skill, payload, context)
            output = await _maybe_await(self.llm_callable(system_prompt, user_prompt))
            duration = int((time.perf_counter() - started) * 1000)
            log.mark_success(output)
            return SkillResult(
                skill_name=skill_name,
                status=SkillExecutionStatus.SUCCESS,
                output=output,
                duration_ms=duration,
                metadata={"persona": context.persona, "version": skill.version},
            )
        except Exception as exc:  # 捕获 LLM 调用一切异常
            duration = int((time.perf_counter() - started) * 1000)
            logger.exception("skill 执行失败: %s", skill_name)
            log.mark_failed(str(exc))
            return SkillResult(
                skill_name=skill_name,
                status=SkillExecutionStatus.FAILED,
                error=str(exc),
                duration_ms=duration,
            )

    # ------------------------------------------------------------------
    # 批量执行
    # ------------------------------------------------------------------
    async def execute_batch(
        self,
        items: Iterable[tuple[str, dict[str, Any]]],
        context: ExecutionContext,
        concurrency: int = 4,
    ) -> list[SkillResult]:
        """并发执行多个 skill；单条失败不影响其它，按顺序返回结果。"""
        items_list = list(items)
        if not items_list:
            return []

        semaphore = asyncio.Semaphore(max(1, concurrency))

        async def _run(skill_name: str, payload: dict[str, Any]) -> SkillResult:
            async with semaphore:
                return await self.execute(skill_name, payload, context)

        results = await asyncio.gather(
            *(_run(name, payload) for name, payload in items_list),
            return_exceptions=False,
        )
        return list(results)

    # ------------------------------------------------------------------
    # 调试 / 内省
    # ------------------------------------------------------------------
    @property
    def logs(self) -> list[SkillExecutionLog]:
        """返回当前进程内已执行 log（最大不限，调用方注意清理）。"""
        return list(self._logs)

    def clear_logs(self) -> None:
        self._logs.clear()

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    @staticmethod
    def _build_prompt(
        skill: Skill,
        payload: dict[str, Any],
        context: ExecutionContext,
    ) -> tuple[str, str]:
        """把 skill body + context + payload 拼成 ``(system, user)`` 双段。"""
        system_parts = [
            f"# 技能: {skill.name} (v{skill.version})",
            f"> {skill.description}",
            "",
            skill.body or "(无具体步骤说明)",
            "",
            context.to_prompt_block(),
        ]
        user_parts = ["## 调用参数 (payload)"]
        if not payload:
            user_parts.append("(空)")
        else:
            for k, v in payload.items():
                user_parts.append(f"- **{k}**: {v}")
        return "\n".join(system_parts), "\n".join(user_parts)


async def _maybe_await(value: "str | Awaitable[str]") -> str:
    """允许 ``llm_callable`` 同步或异步返回字符串。"""
    if asyncio.iscoroutine(value) or isinstance(value, asyncio.Future):
        return await value  # type: ignore[no-any-return]
    if hasattr(value, "__await__"):
        return await value  # type: ignore[no-any-return]
    return str(value)


def _default_llm_call(system_prompt: str, user_prompt: str) -> str:
    """缺省 LLM 调用：尝试走 ``rag_service`` 的轻量 chat 客户端。

    设计原则：
        - **lazy import**：避免在没有 LLM 配置的测试环境里炸 ImportError
        - **失败回落**：拿不到客户端时返回 stub，便于本地无 key 调试

    生产部署建议在 app 启动时显式 ``SkillExecutor(llm_callable=my_call)`` 注入。
    """
    try:
        # rag_service 已经持有一个 OpenAI 兼容的客户端
        from src.core.config import settings
        from src.services.rag_service import _build_llm_client  # type: ignore[attr-defined]

        client = _build_llm_client()
    except Exception:
        client = None

    if client is None:
        return (
            "[skill_executor stub] 当前未配置 LLM 客户端。\n"
            f"--- system ---\n{system_prompt}\n\n--- user ---\n{user_prompt}"
        )

    try:
        from src.core.config import settings as _s

        response = client.chat.completions.create(
            model=getattr(_s, "LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        logger.warning("默认 LLM 调用失败: %s", exc)
        return f"[skill_executor stub: llm error] {exc}"
