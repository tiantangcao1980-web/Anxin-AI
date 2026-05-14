"""
统一上下文装配引擎

整合已有的 context_compressor + memory_layer + experience_engine，
提供统一的上下文装配接口。

职责：
1. 从多来源收集上下文（历史消息、记忆、经验、文档）
2. 按优先级和 token 预算裁剪
3. 自动压缩（对接 context_compressor）
4. 跨会话 artifact handoff
"""

from typing import Any

from loguru import logger


class ContextEngine:
    """
    统一上下文装配引擎

    将散落在 chat_service 中的上下文装配逻辑集中管理。
    """

    def __init__(
        self,
        max_context_tokens: int = 200000,
        memory_budget_tokens: int = 600,
        experience_budget_tokens: int = 300,
    ):
        self.max_context_tokens = max_context_tokens
        self.memory_budget_tokens = memory_budget_tokens
        self.experience_budget_tokens = experience_budget_tokens

    async def assemble(
        self,
        messages: list[dict[str, Any]],
        user_id: str | None = None,
        session_id: str | None = None,
        query: str = "",
        include_memory: bool = True,
        include_experience: bool = True,
    ) -> list[dict[str, Any]]:
        """
        装配完整上下文

        流程：
        1. 压缩历史消息（如需要）
        2. 注入用户画像 + 记忆
        3. 注入经验上下文
        4. 返回装配好的消息列表

        Args:
            messages: 原始历史消息
            user_id: 用户 ID
            session_id: 会话 ID
            query: 当前查询（用于相关性匹配）
            include_memory: 是否注入记忆
            include_experience: 是否注入经验

        Returns:
            装配好的消息列表
        """
        result_messages = list(messages)

        # Step 1: 上下文压缩
        result_messages = await self._maybe_compress(result_messages)

        # Step 2: 记忆注入
        if include_memory and user_id:
            result_messages = await self._inject_memory(
                result_messages, user_id, session_id, query,
            )

        # Step 3: 经验注入
        if include_experience and user_id:
            result_messages = await self._inject_experience(
                result_messages, user_id, query,
            )

        return result_messages

    async def _maybe_compress(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """检查并执行上下文压缩"""
        try:
            from src.harness.context_compressor import context_compressor

            tier = context_compressor.should_compress(
                messages, max_context_tokens=self.max_context_tokens,
            )
            if tier is not None:
                logger.info(f"[ContextEngine] 触发 Tier {tier} 压缩（{len(messages)} 条消息）")
                compressed, stats = await context_compressor.compress(
                    messages, tier=tier, max_context_tokens=self.max_context_tokens,
                )
                logger.info(
                    f"[ContextEngine] 压缩完成 | "
                    f"节省 {stats.get('saved_tokens', '?')} tokens"
                )
                return compressed
        except Exception as e:
            logger.debug(f"[ContextEngine] 压缩跳过: {e}")

        return messages

    async def _inject_memory(
        self,
        messages: list[dict[str, Any]],
        user_id: str,
        session_id: str | None,
        query: str,
    ) -> list[dict[str, Any]]:
        """注入用户画像和记忆上下文"""
        try:
            from src.services.memory_layer import memory_layer

            enriched = await memory_layer.build_enriched_context(
                user_id=user_id,
                session_id=session_id or "",
                query=query,
                max_tokens=self.memory_budget_tokens,
            )
            if enriched:
                messages = [
                    {"role": "system", "content": enriched},
                    *messages,
                ]

            # 缓冲消息到记忆层
            await memory_layer.buffer_message(user_id, {"role": "user", "content": query})
        except Exception as e:
            logger.debug(f"[ContextEngine] 记忆注入跳过: {e}")

        return messages

    async def _inject_experience(
        self,
        messages: list[dict[str, Any]],
        user_id: str,
        query: str,
    ) -> list[dict[str, Any]]:
        """注入经验上下文"""
        try:
            from src.services.experience_engine import experience_engine

            exp_context = experience_engine.build_experience_context(
                user_id, query, max_tokens=self.experience_budget_tokens,
            )
            if exp_context:
                messages = [
                    {"role": "system", "content": exp_context},
                    *messages,
                ]
        except Exception as e:
            logger.debug(f"[ContextEngine] 经验注入跳过: {e}")

        return messages

    def should_compress(
        self,
        messages: list[dict[str, Any]],
        max_context_tokens: int | None = None,
    ) -> int | None:
        """委托 context_compressor: 判定是否需要压缩, 返回 tier 或 None。

        T3 收口入口: chat_service / due_diligence 之前直接 import
        context_compressor, 改为通过 context_engine 集中调用。
        """
        from src.harness.context_compressor import context_compressor

        budget = max_context_tokens if max_context_tokens is not None else self.max_context_tokens
        return context_compressor.should_compress(messages, max_context_tokens=budget)

    async def compress(
        self,
        messages: list[dict[str, Any]],
        tier: int,
        max_context_tokens: int | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """委托 context_compressor.compress, 返回 (压缩后消息, 统计)。"""
        from src.harness.context_compressor import context_compressor

        budget = max_context_tokens if max_context_tokens is not None else self.max_context_tokens
        return await context_compressor.compress(
            messages, tier=tier, max_context_tokens=budget,
        )

    def get_stats(self) -> dict[str, Any]:
        """委托 context_compressor.get_stats。"""
        from src.harness.context_compressor import context_compressor

        return context_compressor.get_stats()

    async def handoff_artifacts(
        self,
        source_session_id: str,
        target_session_id: str,
        artifact_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        跨会话 artifact 交接

        将一个会话的中间结论（摘要、引用、风险标记）
        传递到另一个会话。用于多端同步场景。

        Args:
            source_session_id: 源会话
            target_session_id: 目标会话
            artifact_types: 要交接的类型（summary, citations, risk_marks）
        """
        artifact_types = artifact_types or ["summary", "citations"]
        transferred = {}

        try:
            from src.services.memory_layer import memory_layer

            for art_type in artifact_types:
                data = await memory_layer.get_session_artifact(
                    source_session_id, art_type,
                )
                if data:
                    await memory_layer.set_session_artifact(
                        target_session_id, art_type, data,
                    )
                    transferred[art_type] = True

            logger.info(
                f"[ContextEngine] Artifact handoff: "
                f"{source_session_id} → {target_session_id} | "
                f"types={list(transferred.keys())}"
            )
        except Exception as e:
            logger.debug(f"[ContextEngine] Artifact handoff 跳过: {e}")

        return {"transferred": transferred}


# 全局单例
context_engine = ContextEngine()
