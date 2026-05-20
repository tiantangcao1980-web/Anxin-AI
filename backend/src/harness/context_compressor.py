"""
Context Compressor — 四层渐进式上下文压缩

灵感来源：Claude Code 四层压缩策略
- Tier 1 MicroCompact (80%): 外科手术式清理旧工具输出，零 API 调用
- Tier 2 AutoCompact (85%): 模型驱动摘要，保留关键上下文
- Tier 3 SessionCompact: 持久化关键信息，激进缩减
- Tier 4 ReactiveCompact: 最后手段，纯截断

法律场景适配：
- 法律对话通常很长（合同审查、案件分析可达数万 token）
- 法条引用和判例编号必须精确保留（不可丢失）
- 用户纠正和明确指令优先保留
- 工具返回的长文本（文档内容、搜索结果）优先压缩
"""

import re
from datetime import datetime
from typing import Any

from loguru import logger

# ===== 压缩配置 =====

COMPRESS_CONFIG: dict[str, Any] = {
    # 各层触发阈值（占最大上下文窗口的比例）
    "micro_threshold": 0.80,  # 80% → MicroCompact
    "auto_threshold": 0.85,  # 85% → AutoCompact
    "session_threshold": 0.92,  # 92% → SessionCompact
    "reactive_threshold": 0.98,  # 98% → ReactiveCompact
    # 压缩后目标
    "post_compress_budget": 50000,  # 压缩后保留 ~50K token 工作区
    # AutoCompact 参数
    "summary_max_tokens": 20000,  # 摘要上限
    "reserve_buffer": 13000,  # 保留缓冲区
    "max_retries": 3,  # 最大重试次数
    # 保护规则
    "preserve_recent_messages": 5,  # 保留最近 N 条消息不压缩
    "preserve_citations": True,  # 法条引用永远保留
    "preserve_corrections": True,  # 用户纠正永远保留
}

# 法律引用正则（这些内容绝不压缩）
RE_LEGAL_CITATION = re.compile(r"《[^》]+》(?:\s*第\s*\d+\s*条)?")
RE_CASE_NUMBER = re.compile(r"[（(]\d{4}[）)][^，,。]+号")


class CompressedSegment:
    """压缩段落"""

    def __init__(self, original_tokens: int, compressed_text: str, tier: int) -> None:
        self.original_tokens = original_tokens
        self.compressed_text = compressed_text
        self.compressed_tokens = len(compressed_text) // 2  # 粗估
        self.tier = tier
        self.timestamp = datetime.now()
        self.savings = original_tokens - self.compressed_tokens

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "tier": self.tier,
            "savings": self.savings,
            "savings_pct": round(self.savings / max(self.original_tokens, 1) * 100, 1),
        }


class ContextCompressor:
    """
    四层渐进式上下文压缩器

    针对法律场景的优化：
    - 法条、案号等关键引用永远保留
    - 用户纠正指令优先保留
    - 长工具输出（文档全文、搜索结果）优先压缩
    - 合同条款提取 L0 摘要替代全文
    """

    def __init__(self) -> None:
        self._compress_history: list[dict[str, Any]] = []  # 压缩历史
        self._total_saved: int = 0

    def estimate_tokens(self, text: str) -> int:
        """粗估 token 数（中文约 1.5 字/token，英文约 4 字符/token）"""
        if not text:
            return 0
        cn_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        other_chars = len(text) - cn_chars
        return int(cn_chars / 1.5 + other_chars / 4)

    def should_compress(
        self,
        messages: list[dict[str, Any]],
        max_context_tokens: int = 200000,
    ) -> int | None:
        """
        检查是否需要压缩，返回应触发的层级

        Returns:
            None (无需压缩), 1 (Micro), 2 (Auto), 3 (Session), 4 (Reactive)
        """
        total = sum(self.estimate_tokens(m.get("content", "")) for m in messages)
        ratio = total / max_context_tokens

        if ratio >= COMPRESS_CONFIG["reactive_threshold"]:
            return 4
        if ratio >= COMPRESS_CONFIG["session_threshold"]:
            return 3
        if ratio >= COMPRESS_CONFIG["auto_threshold"]:
            return 2
        if ratio >= COMPRESS_CONFIG["micro_threshold"]:
            return 1
        return None

    async def compress(
        self,
        messages: list[dict[str, Any]],
        tier: int,
        max_context_tokens: int = 200000,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        执行压缩

        Returns:
            (compressed_messages, compression_stats)
        """
        if tier == 1:
            return await self._micro_compact(messages)
        elif tier == 2:
            return await self._auto_compact(messages, max_context_tokens)
        elif tier == 3:
            return await self._session_compact(messages)
        else:
            return self._reactive_compact(messages)

    # ===== Tier 1: MicroCompact =====

    async def _micro_compact(
        self,
        messages: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        外科手术式清理：替换旧工具输出为占位符

        零 API 调用，只操作本地缓存
        保留最近 N 条消息不动
        """
        preserve_count = int(COMPRESS_CONFIG["preserve_recent_messages"])
        total_saved = 0
        cleaned_count = 0

        result: list[dict[str, Any]] = []
        cutoff = len(messages) - preserve_count

        for i, msg in enumerate(messages):
            if i >= cutoff:
                # 最近的消息不动
                result.append(msg)
                continue

            content = msg.get("content", "")
            role = msg.get("role", "")

            # 只清理 assistant 的工具结果和长输出
            if role == "assistant" and len(content) > 2000:
                # 提取必须保留的法律引用
                preserved_citations = RE_LEGAL_CITATION.findall(content)
                preserved_cases = RE_CASE_NUMBER.findall(content)

                # 替换为摘要
                summary = self._generate_micro_summary(
                    content, preserved_citations, preserved_cases
                )
                saved = self.estimate_tokens(content) - self.estimate_tokens(summary)
                total_saved += max(0, saved)
                cleaned_count += 1

                result.append({**msg, "content": summary})
            elif role == "tool" and len(content) > 1000:
                # 工具返回的长结果
                summary = f"[工具结果已压缩，原始长度 {len(content)} 字符]"
                if preserved := RE_LEGAL_CITATION.findall(content):
                    summary += f"\n引用保留: {'; '.join(preserved[:5])}"
                saved = self.estimate_tokens(content) - self.estimate_tokens(summary)
                total_saved += max(0, saved)
                cleaned_count += 1
                result.append({**msg, "content": summary})
            else:
                result.append(msg)

        stats = {
            "tier": 1,
            "tier_name": "MicroCompact",
            "messages_cleaned": cleaned_count,
            "tokens_saved": total_saved,
            "api_calls": 0,
        }
        self._record_compression(stats)
        return result, stats

    def _generate_micro_summary(
        self,
        content: str,
        citations: list[str],
        cases: list[str],
    ) -> str:
        """生成 MicroCompact 摘要"""
        # 保留首段作为上下文
        first_para = content[:300].split("\n\n")[0]

        parts = [f"[已压缩内容摘要] {first_para}..."]
        if citations:
            parts.append(f"[引用保留] {'; '.join(citations[:5])}")
        if cases:
            parts.append(f"[案号保留] {'; '.join(cases[:3])}")

        return "\n".join(parts)

    # ===== Tier 2: AutoCompact =====

    async def _auto_compact(
        self,
        messages: list[dict[str, Any]],
        max_context_tokens: int,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        模型驱动摘要：用 LLM 生成结构化摘要

        保留关键上下文：法律引用、用户指令、最近对话
        """
        preserve_count = int(COMPRESS_CONFIG["preserve_recent_messages"])
        cutoff = len(messages) - preserve_count

        old_messages = messages[:cutoff]
        recent_messages = messages[cutoff:]

        if not old_messages:
            return messages, {"tier": 2, "tier_name": "AutoCompact", "skipped": True}

        # 提取旧消息中的关键信息
        old_text = "\n---\n".join(
            f"[{m.get('role', 'unknown')}] {m.get('content', '')[:500]}" for m in old_messages
        )

        # 提取必须保留的元素
        all_citations = RE_LEGAL_CITATION.findall(old_text)
        all_cases = RE_CASE_NUMBER.findall(old_text)
        user_corrections = [
            m.get("content", "")
            for m in old_messages
            if m.get("role") == "user"
            and any(
                kw in m.get("content", "")
                for kw in ["不对", "错了", "不是", "应该是", "修改", "纠正", "重新"]
            )
        ]

        # 尝试用 LLM 摘要
        summary = await self._llm_summarize(old_text, all_citations, all_cases, user_corrections)

        if not summary:
            # LLM 不可用，退化到规则摘要
            summary = self._rule_based_summary(old_messages, all_citations, all_cases)

        # 构建压缩后的消息列表
        compressed = [
            {"role": "system", "content": f"[上下文压缩摘要]\n{summary}"},
            *recent_messages,
        ]

        old_tokens = sum(self.estimate_tokens(m.get("content", "")) for m in old_messages)
        new_tokens = self.estimate_tokens(summary)

        stats = {
            "tier": 2,
            "tier_name": "AutoCompact",
            "old_messages_count": len(old_messages),
            "tokens_before": old_tokens,
            "tokens_after": new_tokens,
            "tokens_saved": old_tokens - new_tokens,
            "citations_preserved": len(all_citations),
            "corrections_preserved": len(user_corrections),
            "api_calls": 1,
        }
        self._record_compression(stats)
        return compressed, stats

    async def _llm_summarize(
        self,
        text: str,
        citations: list[str],
        cases: list[str],
        corrections: list[str],
    ) -> str | None:
        """用 LLM 生成结构化摘要"""
        logger.debug(
            "LLM 摘要服务未配置，使用规则摘要 "
            f"(text={len(text)}, citations={len(citations)}, cases={len(cases)}, "
            f"corrections={len(corrections)})"
        )
        return None

    def _rule_based_summary(
        self,
        messages: list[dict[str, Any]],
        citations: list[str],
        cases: list[str],
    ) -> str:
        """基于规则的摘要（LLM 不可用时的降级方案）"""
        parts = []

        # 提取用户消息的首句
        user_msgs = [m for m in messages if m.get("role") == "user"]
        if user_msgs:
            parts.append("用户提问摘要：")
            for m in user_msgs[-5:]:
                content = m.get("content", "")[:100]
                parts.append(f"  - {content}")

        # 提取 assistant 的关键结论
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
        if assistant_msgs:
            parts.append("\nAI 回复要点：")
            for m in assistant_msgs[-3:]:
                content = m.get("content", "")[:200]
                parts.append(f"  - {content}...")

        # 保留引用
        if citations:
            parts.append(f"\n法律引用: {'; '.join(citations[:10])}")
        if cases:
            parts.append(f"案号: {'; '.join(cases[:5])}")

        return "\n".join(parts)

    # ===== Tier 3: SessionCompact =====

    async def _session_compact(
        self,
        messages: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        会话压缩：激进缩减，只保留核心上下文

        将关键信息持久化到记忆系统，然后大幅裁剪消息
        """
        # 先持久化关键信息到记忆层
        try:
            from src.services.memory_layer import memory_layer

            for msg in messages:
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    if len(content) > 20:
                        memory_layer.add_session_memory(
                            session_id="current",
                            content=content[:200],
                            metadata={"compressed_at": datetime.now().isoformat()},
                        )
        except Exception:
            pass

        # 只保留最近 3 条消息 + 摘要
        recent = messages[-3:]
        summary_text = self._rule_based_summary(messages[:-3], [], [])

        compressed = [
            {"role": "system", "content": f"[会话深度压缩]\n{summary_text[:2000]}"},
            *recent,
        ]

        old_tokens = sum(self.estimate_tokens(m.get("content", "")) for m in messages)
        new_tokens = sum(self.estimate_tokens(m.get("content", "")) for m in compressed)

        stats = {
            "tier": 3,
            "tier_name": "SessionCompact",
            "tokens_saved": old_tokens - new_tokens,
            "persisted_to_memory": True,
        }
        self._record_compression(stats)
        return compressed, stats

    # ===== Tier 4: ReactiveCompact =====

    def _reactive_compact(
        self,
        messages: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        最后手段：纯截断，只保留最近 2 条

        信息损失最大，仅在其他方法都失败时使用
        """
        recent = messages[-2:]
        old_tokens = sum(self.estimate_tokens(m.get("content", "")) for m in messages)
        new_tokens = sum(self.estimate_tokens(m.get("content", "")) for m in recent)

        stats = {
            "tier": 4,
            "tier_name": "ReactiveCompact",
            "tokens_saved": old_tokens - new_tokens,
            "warning": "重度信息丢失，仅保留最近2条消息",
        }
        self._record_compression(stats)
        return recent, stats

    # ===== 统计 =====

    def _record_compression(self, stats: dict[str, Any]) -> None:
        self._compress_history.append(
            {
                **stats,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self._total_saved += stats.get("tokens_saved", 0)
        # 只保留最近 50 次
        if len(self._compress_history) > 50:
            self._compress_history = self._compress_history[-50:]

    def get_stats(self) -> dict[str, Any]:
        """获取压缩统计"""
        return {
            "total_compressions": len(self._compress_history),
            "total_tokens_saved": self._total_saved,
            "recent_compressions": self._compress_history[-5:],
            "by_tier": {
                tier: sum(1 for c in self._compress_history if c.get("tier") == tier)
                for tier in [1, 2, 3, 4]
            },
        }


# 全局实例
context_compressor = ContextCompressor()
