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
from typing import Any, Dict, List, Optional

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

    def __init__(self) -> None:
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
