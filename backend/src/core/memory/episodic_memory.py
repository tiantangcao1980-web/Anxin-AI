"""
增强的情景记忆服务 (Enhanced Episodic Memory)
负责存储中期经验：历史案例、用户反馈、执行轨迹
"""

import uuid
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from .base import BaseMemoryService


class EnhancedEpisodicMemoryService(BaseMemoryService):
    """
    增强的情景记忆服务

    存储内容:
    - 历史任务执行记录
    - 用户反馈 (评分、评论)
    - Agent 执行轨迹
    - 成功/失败模式

    特性:
    - 支持多 Agent 协作记录
    - 执行轨迹追踪
    - 学习模式提取
    """

    COLLECTION_NAME = "episodic_memory"

    # 任务类型
    TASK_TYPES = {
        "contract_review": "合同审查",
        "case_analysis": "案件分析",
        "document_generation": "文档生成",
        "legal_consultation": "法律咨询",
        "due_diligence": "尽职调查",
        "clause_optimization": "条款优化"
    }

    def __init__(self, vector_store=None, db=None):
        super().__init__()
        self.vector_store = vector_store
        self.db = db

    async def ensure_initialized(self):
        """确保服务已初始化"""
        if not self._initialized and self.vector_store:
            await self.vector_store.create_collection(self.COLLECTION_NAME)
            self._initialized = True
            self._log_info("情景记忆服务初始化完成")

    async def add_episode(
        self,
        session_id: str,
        task_description: str,
        task_type: str,
        agents_involved: List[str],
        execution_trace: Dict[str, Any],
        result_summary: str,
        user_rating: int = 0,
        user_feedback: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        添加情景记忆 (案例)

        Args:
            session_id: 会话 ID
            task_description: 任务描述
            task_type: 任务类型
            agents_involved: 参与的 Agent 列表
            execution_trace: 执行轨迹 (DAG 结构)
            result_summary: 结果摘要
            user_rating: 用户评分 (1-5)
            user_feedback: 用户反馈文本
            metadata: 额外元数据

        Returns:
            episode_id: 案例 ID
        """
        await self.ensure_initialized()

        episode_id = str(uuid.uuid4())

        # 计算成功指标
        is_successful = user_rating >= 4
        execution_time = metadata.get("execution_time", 0) if metadata else 0

        # 构建存储数据
        payload = {
            "episode_id": episode_id,
            "session_id": session_id,
            "task_description": task_description,
            "task_type": task_type,
            "agents_involved": agents_involved,
            "execution_trace": json.dumps(execution_trace, ensure_ascii=False),
            "reasoning_chain": metadata.get("reasoning_chain", []) if metadata else [],
            "result_summary": result_summary,
            "user_rating": user_rating,
            "user_feedback": user_feedback,
            "success_metrics": {
                "is_successful": is_successful,
                "execution_time": execution_time,
                "agent_count": len(agents_involved),
                "timestamp": datetime.now().isoformat()
            },
            "is_successful": is_successful,
            "learned_patterns": [],  # 后续由经验提取器填充
            "created_at": datetime.now().isoformat(),
            "accessed_at": datetime.now().isoformat()
        }

        # 添加到向量存储
        content_to_vectorize = f"Task: {task_description}\nResult: {result_summary}"
        document = {
            "id": episode_id,
            "content": content_to_vectorize,
            "metadata": payload
        }

        count = await self.vector_store.add_documents(
            self.COLLECTION_NAME,
            [document]
        )

        if count > 0:
            self._log_info(
                f"已添加情景记忆: {episode_id} "
                f"(评分: {user_rating}, 成功: {is_successful})"
            )
            return episode_id

        return None

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索情景记忆

        Args:
            query: 查询文本
            top_k: 返回数量
            filters: 过滤条件 (task_type, is_successful, min_rating)

        Returns:
            匹配的案例列表
        """
        await self.ensure_initialized()

        # 执行向量搜索
        results = await self.vector_store.search(
            collection_name=self.COLLECTION_NAME,
            query=query,
            top_k=top_k * 2,
            score_threshold=0.6
        )

        # 过滤和排序
        episodes = []
        for res in results:
            meta = res.get("metadata", {})

            # 应用过滤器
            if filters:
                # 任务类型过滤
                if filters.get("task_type") and meta.get("task_type") != filters.get("task_type"):
                    continue

                # 成功状态过滤
                if "is_successful" in filters and meta.get("is_successful") != filters["is_successful"]:
                    continue

                # 最低评分过滤
                min_rating = filters.get("min_rating", 0)
                if meta.get("user_rating", 0) < min_rating:
                    continue

            # 解析执行轨迹
            execution_trace = {}
            try:
                if "execution_trace" in meta and meta["execution_trace"]:
                    execution_trace = json.loads(meta["execution_trace"])
            except:
                pass

            episodes.append({
                "episode_id": meta.get("episode_id"),
                "session_id": meta.get("session_id"),
                "task_description": meta.get("task_description"),
                "task_type": meta.get("task_type"),
                "agents_involved": meta.get("agents_involved", []),
                "execution_trace": execution_trace,
                "reasoning_chain": meta.get("reasoning_chain", []),
                "result_summary": meta.get("result_summary"),
                "user_rating": meta.get("user_rating", 0),
                "user_feedback": meta.get("user_feedback", ""),
                "success_metrics": meta.get("success_metrics", {}),
                "is_successful": meta.get("is_successful", False),
                "similarity_score": res.get("score")
            })

        # 重排序: 优先高分、高相似度的成功案例
        episodes.sort(
            key=lambda e: (
                e["similarity_score"] * 0.5 +
                (e["user_rating"] / 5) * 0.3 +
                (1 if e["is_successful"] else 0) * 0.2
            ),
            reverse=True
        )

        # 更新访问时间
        for episode in episodes[:top_k]:
            await self._update_accessed_at(episode["episode_id"])

        return episodes[:top_k]

    async def get(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """获取单个案例"""
        await self.ensure_initialized()

        # TODO: 实现按 ID 查询
        results = await self.search(query=episode_id, top_k=1)
        return results[0] if results else None

    async def update_feedback(
        self,
        episode_id: str,
        user_rating: int,
        user_feedback: str = ""
    ) -> bool:
        """
        更新用户反馈

        Args:
            episode_id: 案例 ID
            user_rating: 评分 (1-5)
            user_feedback: 反馈文本

        Returns:
            是否更新成功
        """
        await self.ensure_initialized()

        # TODO: 实现更新逻辑
        self._log_info(
            f"更新反馈: {episode_id}, "
            f"评分: {user_rating}, 反馈: {user_feedback[:50]}..."
        )
        return True

    async def update(self, episode_id: str, updates: Dict[str, Any]) -> bool:
        """更新案例"""
        await self.ensure_initialized()
        # TODO: 实现更新逻辑
        return False

    async def delete(self, episode_id: str) -> bool:
        """删除案例"""
        await self.ensure_initialized()
        # TODO: 实现删除逻辑
        return False

    async def _update_accessed_at(self, episode_id: str):
        """更新访问时间"""
        # TODO: 异步更新访问时间
        pass

    async def get_successful_patterns(
        self,
        task_type: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取特定任务类型的成功模式
        """
        results = await self.search(
            query=task_type,
            top_k=top_k,
            filters={
                "task_type": task_type,
                "is_successful": True,
                "min_rating": 4
            }
        )
        return results

    async def get_statistics(self) -> Dict[str, Any]:
        """获取情景记忆统计"""
        await self.ensure_initialized()

        return {
            "total_episodes": 0,
            "successful_rate": 0.0,
            "average_rating": 0.0,
            "by_task_type": {}
        }
