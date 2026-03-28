"""
经验提取器 (Experience Extractor)
从历史案例中学习,提取可重用的模式
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
from pydantic import BaseModel

from src.core.memory.episodic_memory import EnhancedEpisodicMemoryService


class Pattern(BaseModel):
    """经验模式"""
    pattern_id: str
    pattern_type: str  # dag_optimization, reasoning_template, agent_selection, etc.
    task_type: str
    description: str
    confidence: float  # 0-1,基于评分和频率
    data: Dict[str, Any]  # 模式具体数据
    created_at: datetime
    usage_count: int = 0
    success_rate: float = 0.0

    class Config:
        arbitrary_types_allowed = True


class ExperienceExtractor:
    """
    经验提取器

    功能:
    1. 从成功案例中提取 DAG 优化模式
    2. 从失败案例中提取错误模式
    3. 提取 Agent 选择偏好
    4. 提取推理链模板
    """

    def __init__(self, episodic_memory: EnhancedEpisodicMemoryService):
        self.episodic_memory = episodic_memory
        self._patterns: List[Pattern] = []

    async def extract_from_episode(self, episode_id: str) -> List[Pattern]:
        """
        从单个案例中提取可重用的模式

        Args:
            episode_id: 案例 ID

        Returns:
            提取的模式列表
        """
        # 获取案例详情
        episode = await self.episodic_memory.get(episode_id)
        if not episode:
            logger.warning(f"案例不存在: {episode_id}")
            return []

        patterns = []

        # 1. 提取成功模式
        if episode.get("is_successful") and episode.get("user_rating", 0) >= 4:
            patterns.extend(await self._extract_success_patterns(episode))

        # 2. 提取失败模式
        elif not episode.get("is_successful") or episode.get("user_rating", 0) <= 2:
            patterns.extend(await self._extract_failure_patterns(episode))

        # 3. 提取 Agent 协作模式
        patterns.extend(await self._extract_collaboration_patterns(episode))

        # 4. 保存模式
        for pattern in patterns:
            self._patterns.append(pattern)
            logger.debug(f"提取模式: {pattern.pattern_type} - {pattern.description}")

        return patterns

    async def _extract_success_patterns(self, episode: Dict[str, Any]) -> List[Pattern]:
        """
        提取成功模式
        """
        patterns = []

        # DAG 优化模式
        if episode.get("agents_involved"):
            dag_pattern = Pattern(
                pattern_id=f"dag_{episode['task_type']}_{datetime.now().timestamp()}",
                pattern_type="dag_optimization",
                task_type=episode["task_type"],
                description=f"高效的 {episode['task_type']} DAG 配置",
                confidence=min(episode.get("user_rating", 3) / 5, 1.0),
                data={
                    "agents_used": episode.get("agents_involved", []),
                    "execution_time": episode.get("success_metrics", {}).get("execution_time", 0),
                    "agent_sequence": episode.get("execution_trace", {}).get("agent_sequence", []),
                    "parallel_groups": episode.get("execution_trace", {}).get("parallel_groups", []),
                },
                created_at=datetime.now()
            )
            patterns.append(dag_pattern)

        # 推理链模板
        if episode.get("reasoning_chain"):
            reasoning_pattern = Pattern(
                pattern_id=f"reasoning_{episode['task_type']}_{datetime.now().timestamp()}",
                pattern_type="reasoning_template",
                task_type=episode["task_type"],
                description=f"有效的 {episode['task_type']} 推理路径",
                confidence=min(episode.get("user_rating", 3) / 5, 1.0),
                data={
                    "reasoning_steps": episode.get("reasoning_chain", []),
                    "key_decisions": episode.get("execution_trace", {}).get("decisions", []),
                },
                created_at=datetime.now()
            )
            patterns.append(reasoning_pattern)

        return patterns

    async def _extract_failure_patterns(self, episode: Dict[str, Any]) -> List[Pattern]:
        """
        提取失败模式
        """
        patterns = []

        # 失败原因分析
        failure_reason = episode.get("failure_reason") or episode.get("user_feedback", "")

        if failure_reason:
            failure_pattern = Pattern(
                pattern_id=f"failure_{episode['task_type']}_{datetime.now().timestamp()}",
                pattern_type="failure_pattern",
                task_type=episode["task_type"],
                description=f"{episode['task_type']} 失败模式: {failure_reason[:50]}",
                confidence=0.5,  # 失败模式置信度较低
                data={
                    "failure_reason": failure_reason,
                    "agents_used": episode.get("agents_involved", []),
                    "avoid_patterns": [],  # TODO: 提取应避免的模式
                },
                created_at=datetime.now()
            )
            patterns.append(failure_pattern)

        return patterns

    async def _extract_collaboration_patterns(self, episode: Dict[str, Any]) -> List[Pattern]:
        """
        提取 Agent 协作模式
        """
        patterns = []

        agents = episode.get("agents_involved", [])
        if len(agents) > 1:
            collaboration_pattern = Pattern(
                pattern_id=f"collab_{episode['task_type']}_{datetime.now().timestamp()}",
                pattern_type="agent_collaboration",
                task_type=episode["task_type"],
                description=f"{episode['task_type']} 协作模式: {', '.join(agents)}",
                confidence=min(episode.get("user_rating", 3) / 5, 1.0),
                data={
                    "agents": agents,
                    "task_type": episode["task_type"],
                    "success": episode.get("is_successful", False),
                },
                created_at=datetime.now()
            )
            patterns.append(collaboration_pattern)

        return patterns

    async def get_patterns(
        self,
        pattern_type: Optional[str] = None,
        task_type: Optional[str] = None,
        min_confidence: float = 0.5,
        limit: int = 10
    ) -> List[Pattern]:
        """
        获取已提取的模式

        Args:
            pattern_type: 模式类型过滤
            task_type: 任务类型过滤
            min_confidence: 最低置信度
            limit: 返回数量限制

        Returns:
            匹配的模式列表
        """
        patterns = self._patterns

        # 过滤
        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]

        if task_type:
            patterns = [p for p in patterns if p.task_type == task_type]

        patterns = [p for p in patterns if p.confidence >= min_confidence]

        # 排序: 按置信度和使用次数
        patterns.sort(key=lambda p: (p.confidence, p.usage_count), reverse=True)

        return patterns[:limit]

    async def update_pattern_usage(self, pattern_id: str, success: bool):
        """
        更新模式使用统计

        Args:
            pattern_id: 模式 ID
            success: 是否成功
        """
        for pattern in self._patterns:
            if pattern.pattern_id == pattern_id:
                pattern.usage_count += 1
                # 更新成功率 (指数移动平均)
                alpha = 0.1
                pattern.success_rate = (alpha * (1 if success else 0) + (1 - alpha) * pattern.success_rate)
                break

    async def get_pattern_stats(self) -> Dict[str, Any]:
        """
        获取模式统计信息

        Returns:
            统计数据
        """
        pattern_types = {}
        for pattern in self._patterns:
            pt = pattern.pattern_type
            if pt not in pattern_types:
                pattern_types[pt] = {"count": 0, "avg_confidence": 0}
            pattern_types[pt]["count"] += 1

        total = len(self._patterns)
        avg_confidence = sum(p.confidence for p in self._patterns) / total if total > 0 else 0

        return {
            "total_patterns": total,
            "avg_confidence": avg_confidence,
            "by_type": pattern_types,
            "most_used": sorted(self._patterns, key=lambda p: p.usage_count, reverse=True)[:5]
        }
