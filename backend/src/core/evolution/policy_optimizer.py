"""
策略优化器 (Policy Optimizer)
基于历史经验优化 Agent 选择和 DAG 结构
"""

from collections import Counter
from datetime import datetime
from typing import Any, cast

from loguru import logger
from pydantic import BaseModel

from src.core.evolution.experience_extractor import ExperienceExtractor


class DAGStructure(BaseModel):
    """DAG 结构定义"""

    agents: list[str]
    dependencies: dict[str, list[str]]  # agent_id -> 依赖列表
    parallel_groups: list[list[str]]  # 可并行的 Agent 组
    estimated_duration: float = 0.0
    confidence: float = 0.0


class PolicyOptimizer:
    """
    策略优化器

    功能:
    1. 基于历史成功案例优化 Agent 选择
    2. 优化 DAG 执行结构
    3. 动态调整参数
    """

    def __init__(
        self,
        episodic_memory: Any | None = None,
        experience_extractor: Any | None = None,
        db: Any = None,
        vector_store: Any = None,
    ):
        if experience_extractor is not None and not isinstance(
            experience_extractor, ExperienceExtractor
        ):
            # 兼容旧签名：PolicyOptimizer(db, vector_store)
            db, vector_store, episodic_memory, experience_extractor = (
                episodic_memory,
                experience_extractor,
                None,
                None,
            )

        self.episodic_memory = episodic_memory
        self.experience_extractor = experience_extractor or ExperienceExtractor(
            episodic_memory=episodic_memory,
            db=db,
            vector_store=vector_store,
        )
        self.db = db
        self.vector_store = vector_store
        self._optimization_cache: dict[str, Any] = {}

    async def optimize_agent_selection(
        self, task_description: str, task_type: str, current_agents: list[str] | None = None
    ) -> list[str]:
        """
        优化 Agent 选择

        Args:
            task_description: 任务描述
            task_type: 任务类型
            current_agents: 当前考虑的 Agent 列表

        Returns:
            优化后的 Agent 列表
        """
        # 1. 检查缓存
        cache_key = f"agent_selection:{task_type}"
        if cache_key in self._optimization_cache:
            cached = self._optimization_cache[cache_key]
            if datetime.now().timestamp() - cached["timestamp"] < 3600:  # 1小时缓存
                logger.info(f"使用缓存的 Agent 选择: {cached['agents']}")
                return cast(list[str], cached["agents"])

        # 2. 检索相关成功案例
        if self.episodic_memory is not None:
            successful_episodes = await self.episodic_memory.search(
                query=task_description,
                top_k=10,
                filters={"task_type": task_type, "is_successful": True, "min_rating": 4},
            )
        elif self.vector_store is not None and hasattr(self.vector_store, "search"):
            successful_episodes = await self.vector_store.search(task_description)
        else:
            successful_episodes = []

        if not successful_episodes:
            # 无历史经验,使用默认策略
            default_agents = self._get_default_agents(task_type)
            logger.info(f"使用默认 Agent 选择: {default_agents}")
            return default_agents

        # 3. 统计最常用的 Agent 组合
        agent_combinations: Counter[tuple[str, ...]] = Counter()
        for episode in successful_episodes:
            agents = episode.get("agents_involved", [])
            if agents:
                # 计算组合评分 (考虑评分)
                agents_tuple = tuple(sorted(agents))
                score = episode.get("user_rating", 3)
                agent_combinations[agents_tuple] += score

        # 4. 选择最佳组合
        if agent_combinations:
            best_tuple = agent_combinations.most_common(1)[0][0]
            best_agents = list(best_tuple)

            # 结合当前可用的 Agent
            if current_agents:
                # 取交集
                best_agents = [a for a in best_agents if a in current_agents]

            logger.info(
                f"策略优化: 为 {task_type} 选择 Agent {best_agents} "
                f"(基于 {len(successful_episodes)} 个成功案例)"
            )

            # 5. 缓存结果
            self._optimization_cache[cache_key] = {
                "agents": best_agents,
                "timestamp": datetime.now().timestamp(),
            }

            return best_agents

        # 降级到默认策略
        default_agents = self._get_default_agents(task_type)
        return default_agents

    async def optimize_dag_structure(
        self, task_description: str, task_type: str, agents: list[str]
    ) -> DAGStructure:
        """
        优化 DAG 执行结构

        Args:
            task_description: 任务描述
            task_type: 任务类型
            agents: 可用的 Agent 列表

        Returns:
            优化后的 DAG 结构
        """
        # 1. 从经验提取器检索 DAG 优化模式
        patterns = await self.experience_extractor.get_patterns(
            pattern_type="dag_optimization", task_type=task_type, min_confidence=0.6, limit=5
        )

        if patterns:
            # 使用最佳模式
            best_pattern = patterns[0]
            dag_data = best_pattern.data

            logger.info(f"使用优化的 DAG 结构: {best_pattern.pattern_id}")

            return DAGStructure(
                agents=dag_data.get("agents_used", agents),
                dependencies={},  # TODO: 从模式中提取依赖
                parallel_groups=dag_data.get("parallel_groups", []),
                estimated_duration=dag_data.get("execution_time", 0),
                confidence=best_pattern.confidence,
            )

        # 2. 从成功案例中学习
        if self.episodic_memory is not None:
            successful_episodes = await self.episodic_memory.search(
                query=task_description,
                top_k=5,
                filters={"task_type": task_type, "is_successful": True, "min_rating": 4},
            )
        else:
            successful_episodes = []

        if successful_episodes:
            # 分析最成功的案例
            best_episode = max(
                successful_episodes, key=lambda e: e.get("success_metrics", {}).get("efficiency", 0)
            )

            logger.info(f"基于最佳案例构建 DAG: {best_episode['episode_id']}")

            return self._build_dag_from_episode(best_episode, agents)

        # 3. 降级到默认 DAG
        return self._default_dag(agents)

    async def optimize_parameters(
        self, task_type: str, agent_name: str, current_params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        优化 Agent 参数

        Args:
            task_type: 任务类型
            agent_name: Agent 名称
            current_params: 当前参数

        Returns:
            优化后的参数
        """
        # TODO: 从历史案例中学习最佳参数
        # 这里使用规则引擎
        optimized = current_params.copy()

        # 常见优化规则
        if agent_name == "ContractAgent":
            if task_type == "contract_review":
                optimized["temperature"] = 0.3  # 降低随机性
                optimized["top_p"] = 0.9
        elif agent_name == "CreativeAgent":
            optimized["temperature"] = 0.8  # 提高创造性
            optimized["top_p"] = 0.95

        return optimized

    def _get_default_agents(self, task_type: str) -> list[str]:
        """
        获取默认 Agent 配置

        Args:
            task_type: 任务类型

        Returns:
            默认 Agent 列表
        """
        # 默认 Agent 配置映射
        default_agents = {
            "contract_review": ["ContractAgent", "RiskAgent"],
            "case_analysis": ["CaseAgent", "SearchAgent"],
            "document_generation": ["DocumentAgent", "ReviewAgent"],
            "legal_consultation": ["ConsultationAgent"],
            "due_diligence": ["DueDiligenceAgent", "RiskAgent", "SearchAgent"],
            "clause_optimization": ["ClauseAgent", "ContractAgent"],
        }

        return default_agents.get(task_type, ["ConsultationAgent"])

    def _default_dag(self, agents: list[str]) -> DAGStructure:
        """
        创建默认 DAG 结构

        Args:
            agents: Agent 列表

        Returns:
            默认 DAG 结构
        """
        # 默认串行执行
        return DAGStructure(
            agents=agents,
            dependencies={agents[i]: agents[:i] for i in range(1, len(agents))},
            parallel_groups=[],
            estimated_duration=len(agents) * 30,  # 假设每个 Agent 30秒
            confidence=0.5,
        )

    def _build_dag_from_episode(
        self, episode: dict[str, Any], available_agents: list[str]
    ) -> DAGStructure:
        """
        从历史案例构建 DAG

        Args:
            episode: 历史案例
            available_agents: 可用的 Agent

        Returns:
            DAG 结构
        """
        # 提取执行轨迹
        trace = episode.get("execution_trace", {})

        # Agent 序列
        agent_sequence = trace.get("agent_sequence", [])
        if not agent_sequence:
            agent_sequence = episode.get("agents_involved", [])

        # 并行组
        parallel_groups = trace.get("parallel_groups", [])

        # 构建依赖
        dependencies = {}
        if agent_sequence:
            for i in range(1, len(agent_sequence)):
                dependencies[agent_sequence[i]] = agent_sequence[:i]

        return DAGStructure(
            agents=agent_sequence,
            dependencies=dependencies,
            parallel_groups=parallel_groups,
            estimated_duration=episode.get("success_metrics", {}).get("execution_time", 0),
            confidence=0.7,  # 基于历史数据
        )

    async def get_optimization_stats(self) -> dict[str, Any]:
        """
        获取优化统计信息

        Returns:
            统计数据
        """
        pattern_stats = await self.experience_extractor.get_pattern_stats()

        return {
            "cache_size": len(self._optimization_cache),
            "pattern_stats": pattern_stats,
            "last_optimization": datetime.now().isoformat(),
        }

    def _rank_combinations(self, combinations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """兼容旧测试：按评分、成功率、耗时综合排序。"""
        return sorted(
            combinations,
            key=lambda item: (
                item.get("avg_rating", 0),
                item.get("success_rate", 0),
                -item.get("avg_duration", 0),
            ),
            reverse=True,
        )
