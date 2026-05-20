# -*- coding: utf-8 -*-
"""
BasePersonaAgent —— V3 user-facing persona 抽象基类

设计选择（与现有 `BaseLegalAgent` 的关系）：
    - **组合 + 继承** — 继承自 ``BaseLegalAgent``，复用其 LLM 客户端 / 共享
      连接池 / 重试机制 / 流式 chat() / RAG 注入 等基础设施；
    - **不修改** ``agents/base.py``，仅在 persona 子类层加 persona-specific
      字段（display_name / emoji / capabilities / backed_by_skills /
      supported_apps），并提供 ``handle_message()`` 给 API 层统一调用；
    - 子类 **必须** 覆盖 ``persona_id`` / ``display_name`` / ``SYSTEM_PROMPT``，
      可选覆盖 ``handle_message()`` / ``capability_*()`` 业务方法。

PersonaRegistry 在自动加载时只需要 import 子类模块，子类即注册自身。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from src.agents.base import (
    AgentConfig,
    AgentResponse,
    BaseLegalAgent,
)


@dataclass(slots=True)
class PersonaInfo:
    """对外暴露的 persona 元信息（/api/v1/personas 列表用）。"""

    persona_id: str
    display_name: str
    emoji: str
    description: str
    capabilities: List[str] = field(default_factory=list)
    backed_by_skills: List[str] = field(default_factory=list)
    supported_apps: List[str] = field(default_factory=list)
    backed_by_agents: List[str] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "persona_id": self.persona_id,
            "display_name": self.display_name,
            "emoji": self.emoji,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "backed_by_skills": list(self.backed_by_skills),
            "supported_apps": list(self.supported_apps),
            "backed_by_agents": list(self.backed_by_agents),
            "enabled": self.enabled,
        }


class BasePersonaAgent(BaseLegalAgent):
    """V3 user-facing persona 基类。

    子类约定（class attribute）::

        class FooPersona(BasePersonaAgent):
            persona_id = "foo"
            display_name = "Foo 管家"
            emoji = "🤖"
            description = "..."
            backed_by_skills = ["docx", "xlsx"]
            supported_apps = ["feishu"]
            capabilities = ["cap_a", "cap_b"]
            backed_by_agents = ["coordinator"]
            SYSTEM_PROMPT = "你是 ..."

    `__init_subclass__` 自动把子类注册到 ``PersonaRegistry``，无需手动 register。
    """

    # ----- 子类必须覆盖 -----
    persona_id: str = ""
    display_name: str = ""
    emoji: str = "🤖"
    description: str = ""
    SYSTEM_PROMPT: str = ""

    # ----- 子类可选覆盖 -----
    backed_by_skills: List[str] = []
    supported_apps: List[str] = []
    capabilities: List[str] = []
    backed_by_agents: List[str] = []
    enabled: bool = True

    def __init__(
        self,
        *,
        llm_client: Any | None = None,
        llm_callable: Optional[Callable[..., Any]] = None,
        skill_executor: Any | None = None,
        fetch_service: Any | None = None,
        kb_search: Any | None = None,
        **_extra: Any,
    ) -> None:
        """统一构造器。

        所有 persona 子类共享 4 个标准依赖注入 kwargs（`llm_client` /
        `llm_callable` / `skill_executor` / `fetch_service`），加 1 个常用
        `kb_search`。其余子类专用 kwargs 通过 `**_extra` 吸收，避免上层
        签名扩散。这让测试可以稳定地注入 mock：

            agent = MarketResearcherAgent(llm_callable=mock_fn)
            agent = ContentDirectorAgent(llm_client=mock_obj)
        """

        if not self.persona_id:
            raise ValueError(f"{type(self).__name__} 必须定义 persona_id")
        if not self.SYSTEM_PROMPT:
            raise ValueError(f"{type(self).__name__} 必须定义 SYSTEM_PROMPT")

        config = AgentConfig(
            name=self.display_name or self.persona_id,
            role=self.persona_id,
            description=self.description or self.display_name or self.persona_id,
            system_prompt=self.SYSTEM_PROMPT,
            tools=list(self.backed_by_skills),
        )
        super().__init__(config)

        # 标准注入点（生产可缺省，测试可 mock）
        self.llm_client = llm_client
        self.llm_callable = llm_callable
        self.skill_executor = skill_executor
        self.fetch_service = fetch_service
        self.kb_search = kb_search

    # ------------------------------------------------------------------
    # 通用 LLM 适配（子类可覆盖）
    # ------------------------------------------------------------------
    async def run_llm(self, system: str, user: str) -> str:
        """统一 LLM 调用入口。

        优先级：``llm_callable`` (测试)  >  ``llm_client.complete`` (测试 mock)
        >  ``BaseLegalAgent.chat()`` (生产)。
        """

        if self.llm_callable is not None:
            res = self.llm_callable(system, user)
            if hasattr(res, "__await__"):
                return await res  # type: ignore[no-any-return]
            return res  # type: ignore[return-value]

        if self.llm_client is not None and hasattr(self.llm_client, "complete"):
            return await self.llm_client.complete(user, system=system)

        # 退回 BaseLegalAgent.chat（真生产 LLM）
        return await self.chat(message=user)

    async def _call_specialized_governed(
        self,
        agent: "BaseLegalAgent",
        task: Dict[str, Any],
        *,
        action: str,
        classification: str = "L3",
        jurisdiction: str = "CN",
    ) -> "AgentResponse":
        """统一调用底层 specialized agent — 自动走治理 PDP + 审计。

        从 task["context"] 提取 ``user_id / role / tenant_id / clearance / primary_jurisdiction``
        构造 PDP subject；缺字段时降级为 ``subject=None``（行为同直接 .process()）。

        - action: 如 ``"agent.legal_advisor.consult"``
        - classification: 资源数据分级（L1..L5）
        - jurisdiction: 资源法域

        子类调用示例::

            response = await self._call_specialized_governed(
                self._get_advisor(), task,
                action=f"agent.{self.persona_id}.consult",
            )
        """
        ctx = (task.get("context") or {}) if isinstance(task, dict) else {}
        if not ctx.get("user_id"):
            # 缺关键 subject 字段 → 不强加治理（向后兼容）
            return await agent.process(task)

        subject = {
            "id": str(ctx.get("user_id")),
            "role": ctx.get("role") or "viewer",
            "tenant_id": str(ctx.get("tenant_id") or ctx.get("org_id") or "unknown"),
            "clearance": ctx.get("clearance") or "L3",
            "primary_jurisdiction": ctx.get("primary_jurisdiction") or "CN",
        }
        resource = {
            "type": "agent",
            "id": type(agent).__name__,
            "classification": classification,
            "jurisdiction": jurisdiction,
            "version": getattr(agent.config if hasattr(agent, "config") else None, "name", "0.0.0"),
        }
        context_extra = {
            "trace_id": ctx.get("trace_id") or ctx.get("request_id"),
            "mfa_recent": bool(ctx.get("mfa_recent")),
        }
        return await agent.process_governed(
            task, subject=subject, action=action,
            resource=resource, context=context_extra,
        )

    async def _llm(self, prompt: str, system: Optional[str] = None) -> str:
        """`llm_client.complete(prompt, system=...)` 风格的兼容入口。

        ContentDirectorAgent 等 persona 习惯用 ``self._llm(prompt, system=...)``，
        保留为薄封装；缺省走 ``run_llm()``。
        """

        return await self.run_llm(system or self.SYSTEM_PROMPT, prompt)

    # ------------------------------------------------------------------
    # 自动注册 hook
    # ------------------------------------------------------------------
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # 仅注册「叶子」persona（必须显式声明 persona_id）
        if getattr(cls, "persona_id", "") and cls.__name__ != "BasePersonaAgent":
            try:
                from src.agents.personas.registry import PersonaRegistry

                PersonaRegistry.instance().register(cls)
            except Exception as exc:  # pragma: no cover - 防御
                logger.warning(f"自动注册 persona {cls.__name__} 失败: {exc}")

    # ------------------------------------------------------------------
    # 元信息
    # ------------------------------------------------------------------
    @classmethod
    def get_info(cls) -> PersonaInfo:
        return PersonaInfo(
            persona_id=cls.persona_id,
            display_name=cls.display_name,
            emoji=cls.emoji,
            description=cls.description,
            capabilities=list(cls.capabilities),
            backed_by_skills=list(cls.backed_by_skills),
            supported_apps=list(cls.supported_apps),
            backed_by_agents=list(cls.backed_by_agents),
            enabled=cls.enabled,
        )

    @classmethod
    def manifest(cls) -> Dict[str, Any]:
        """V3 merge: 持久化用的 persona manifest（dict 形式，兼容 V3 测试契约）。"""
        return {
            "persona_id": cls.persona_id,
            "display_name": cls.display_name,
            "emoji": cls.emoji,
            "description": cls.description,
            "capabilities": list(cls.capabilities),
            "backed_by_skills": list(cls.backed_by_skills),
            "supported_apps": list(cls.supported_apps),
            "backed_by_agents": list(cls.backed_by_agents),
            "enabled": cls.enabled,
        }

    # ------------------------------------------------------------------
    # 兼容 specialized agent 的 process() 接口（由 coordinator 调用）
    # ------------------------------------------------------------------
    async def process(self, task: Dict[str, Any]) -> AgentResponse:
        """适配 `BaseLegalAgent.process()`，让 persona 也可以被 coordinator 编排。"""
        message = task.get("description") or task.get("message") or ""
        context = task.get("context") or {}
        llm_config = context.get("llm_config")
        history = context.get("history")
        user_id = context.get("user_id")

        content = await self.handle_message(
            message=message,
            user_id=user_id,
            llm_config=llm_config,
            history=history,
            extra=context,
        )
        return AgentResponse(
            agent_name=self.name,
            content=content,
            metadata={
                "persona_id": self.persona_id,
                "capabilities": list(self.capabilities),
            },
        )

    # ------------------------------------------------------------------
    # 主对外接口（API 层调用）
    # ------------------------------------------------------------------
    async def handle_message(
        self,
        message: str,
        user_id: Optional[str] = None,
        llm_config: Optional[Any] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """处理用户消息（默认：直接走 chat）。

        子类如需多轮路由 / capability dispatch / 调用 specialized agent，
        可以覆盖此方法。
        """
        return await self.chat(
            message=message,
            user_id=user_id,
            llm_config=llm_config,
            history=history,
        )
