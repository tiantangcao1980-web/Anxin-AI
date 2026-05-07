"""
增强的情景记忆服务 (Enhanced Episodic Memory)
负责存储中期经验：历史案例、用户反馈、执行轨迹
"""

import inspect
import json
import uuid
from datetime import datetime
from typing import Any, cast

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
    TASK_TYPES: dict[str, str] = {
        "contract_review": "合同审查",
        "case_analysis": "案件分析",
        "document_generation": "文档生成",
        "legal_consultation": "法律咨询",
        "due_diligence": "尽职调查",
        "clause_optimization": "条款优化"
    }

    def __init__(self, vector_store: Any = None, db: Any = None) -> None:
        super().__init__()
        self.vector_store = vector_store
        self.db = db

    async def ensure_initialized(self) -> None:
        """确保服务已初始化"""
        if self._initialized or self.vector_store is None:
            return

        result = self.vector_store.create_collection(self.COLLECTION_NAME)
        if inspect.isawaitable(result):
            await result
        self._initialized = True
        self._log_info("情景记忆服务初始化完成")

    async def add(self, data: dict[str, Any]) -> str | None:
        """兼容统一记忆接口，转发到 add_episode。"""
        return await self.add_episode(
            session_id=self._coerce_str(data.get("session_id"), default=str(uuid.uuid4())),
            task_description=self._coerce_str(data.get("task_description")),
            task_type=self._coerce_str(data.get("task_type"), default="legal_consultation"),
            agents_involved=self._coerce_str_list(data.get("agents_involved")),
            execution_trace=self._coerce_dict(data.get("execution_trace")),
            result_summary=self._coerce_str(data.get("result_summary")),
            user_rating=self._coerce_int(data.get("user_rating")),
            user_feedback=self._coerce_str(data.get("user_feedback")),
            metadata=self._coerce_optional_dict(data.get("metadata")),
        )

    async def add_episode(
        self,
        session_id: str,
        task_description: str,
        task_type: str,
        agents_involved: list[str],
        execution_trace: dict[str, Any],
        result_summary: str,
        user_rating: int = 0,
        user_feedback: str = "",
        metadata: dict[str, Any] | None = None
    ) -> str | None:
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
        vector_store = self._require_vector_store()

        episode_id = str(uuid.uuid4())

        # 计算成功指标
        is_successful = user_rating >= 4
        execution_time = metadata.get("execution_time", 0) if metadata else 0

        # 构建存储数据
        payload: dict[str, Any] = {
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
        document: dict[str, Any] = {
            "id": episode_id,
            "content": content_to_vectorize,
            "metadata": payload
        }

        count = await vector_store.add_documents(
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
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
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
        vector_store = self._require_vector_store()

        # 执行向量搜索
        results = await vector_store.search(
            collection_name=self.COLLECTION_NAME,
            query=query,
            top_k=top_k * 2,
            score_threshold=0.6
        )

        # 过滤和排序
        episodes: list[dict[str, Any]] = []
        for res in results:
            raw_meta = res.get("metadata", {})
            meta = raw_meta if isinstance(raw_meta, dict) else {}

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
            execution_trace: dict[str, Any] = {}
            try:
                raw_execution_trace = meta.get("execution_trace")
                if isinstance(raw_execution_trace, str) and raw_execution_trace:
                    parsed_trace = json.loads(raw_execution_trace)
                    if isinstance(parsed_trace, dict):
                        execution_trace = cast(dict[str, Any], parsed_trace)
            except Exception:
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
            episode_id = episode.get("episode_id")
            if isinstance(episode_id, str) and episode_id:
                await self._update_accessed_at(episode_id)

        return episodes[:top_k]

    async def get(self, episode_id: str) -> dict[str, Any] | None:
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

    async def update(self, episode_id: str, updates: dict[str, Any]) -> bool:
        """更新案例 — 删除旧记录后重新插入"""
        await self.ensure_initialized()
        try:
            old = await self.get(episode_id)
            if not old:
                return False
            await self.delete(episode_id)
            merged = {**old, **updates}
            new_id = await self.store(
                task_description=self._coerce_str(merged.get("task_description")),
                result=self._coerce_str(merged.get("result_summary", merged.get("result"))),
                task_type=self._coerce_str(merged.get("task_type"), default="legal_consultation"),
                metadata=merged,
            )
            return new_id is not None
        except Exception as e:
            self._log_warning(f"更新情景记忆失败: {episode_id}, {e}")
            return False

    async def delete(self, episode_id: str) -> bool:
        """删除案例"""
        await self.ensure_initialized()
        try:
            from src.services.vector_store import VectorStoreService
            vs = VectorStoreService()
            await vs.delete_documents(
                collection_name=self.COLLECTION_NAME,
                doc_ids=[episode_id],
            )
            return True
        except Exception as e:
            self._log_warning(f"删除情景记忆失败: {episode_id}, {e}")
            return False

    async def store(
        self,
        *,
        task_description: str,
        result: str,
        task_type: str = "legal_consultation",
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """兼容旧接口，转发到 add_episode。"""
        normalized_metadata = dict(metadata) if metadata else None

        return await self.add_episode(
            session_id=self._coerce_str(
                normalized_metadata.get("session_id") if normalized_metadata else None,
                default=str(uuid.uuid4()),
            ),
            task_description=task_description,
            task_type=task_type,
            agents_involved=self._coerce_str_list(
                normalized_metadata.get("agents_involved") if normalized_metadata else None
            ),
            execution_trace=self._coerce_dict(
                normalized_metadata.get("execution_trace") if normalized_metadata else None
            ),
            result_summary=result,
            user_rating=self._coerce_int(
                normalized_metadata.get("user_rating") if normalized_metadata else None
            ),
            user_feedback=self._coerce_str(
                normalized_metadata.get("user_feedback") if normalized_metadata else None
            ),
            metadata=normalized_metadata,
        )

    async def _update_accessed_at(self, episode_id: str) -> None:
        """更新访问时间（非关键路径）"""
        pass

    async def get_successful_patterns(
        self,
        task_type: str,
        top_k: int = 10
    ) -> list[dict[str, Any]]:
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

    async def get_statistics(self) -> dict[str, Any]:
        """获取情景记忆统计"""
        await self.ensure_initialized()

        return {
            "total_episodes": 0,
            "successful_rate": 0.0,
            "average_rating": 0.0,
            "by_task_type": {}
        }

    def _require_vector_store(self) -> Any:
        if self.vector_store is None:
            raise RuntimeError("Vector store is not configured")
        return self.vector_store

    @staticmethod
    def _coerce_optional_dict(value: Any) -> dict[str, Any] | None:
        return value if isinstance(value, dict) else None

    @staticmethod
    def _coerce_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _coerce_str(value: Any, default: str = "") -> str:
        return value if isinstance(value, str) else default

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        return value if isinstance(value, int) else default

    @staticmethod
    def _coerce_str_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str)]
