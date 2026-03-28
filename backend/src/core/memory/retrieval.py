"""
多层记忆检索系统 (Multi-Tier Memory Retrieval)
实现工作记忆 → 情景记忆 → 语义记忆的跨层检索
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
from pydantic import BaseModel

from .semantic_memory import SemanticMemoryService
from .episodic_memory import EnhancedEpisodicMemoryService
from .working_memory import WorkingMemoryService


class MemoryRetrievalResult(BaseModel):
    """记忆检索结果"""
    # 工作记忆 (最快)
    working: Optional[Dict[str, Any]] = None

    # 情景记忆 (中速)
    episodic: List[Dict[str, Any]] = []

    # 语义记忆 (慢速)
    semantic: List[Dict[str, Any]] = []

    # 是否找到足够信息
    is_sufficient: bool = False

    # 元数据
    retrieval_time: float = 0.0
    source_counts: Dict[str, int] = {}


class MultiTierMemoryRetrieval:
    """
    多层记忆检索器

    检索策略:
    1. 优先从工作记忆获取 (会话级上下文)
    2. 从情景记忆获取相关案例 (历史经验)
    3. 从语义记忆获取相关知识 (长期知识)
    4. 跨层融合与排序
    5. 缓存到工作记忆
    """

    def __init__(
        self,
        semantic_memory: SemanticMemoryService,
        episodic_memory: EnhancedEpisodicMemoryService,
        working_memory: WorkingMemoryService
    ):
        self.semantic_memory = semantic_memory
        self.episodic_memory = episodic_memory
        self.working_memory = working_memory

    async def retrieve(
        self,
        query: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> MemoryRetrievalResult:
        """
        跨层检索

        Args:
            query: 查询文本
            session_id: 会话 ID
            context: 上下文信息 (task_type, filters, etc.)

        Returns:
            MemoryRetrievalResult: 检索结果
        """
        start_time = datetime.now()
        result = MemoryRetrievalResult()

        # 1️⃣ 工作记忆层 (最快)
        result.working = await self._retrieve_working(session_id)
        if self._is_sufficient(result.working, query):
            result.is_sufficient = True
            result.source_counts = {"working": 1}
            return result

        # 2️⃣ 情景记忆层 (中速)
        result.episodic = await self._retrieve_episodic(
            query=query,
            context=context or {}
        )

        # 3️⃣ 语义记忆层 (慢速)
        result.semantic = await self._retrieve_semantic(
            query=query,
            context=context or {}
        )

        # 4️⃣ 跨层融合与排序
        result = await self._fuse_and_rank(result, query)

        # 5️⃣ 缓存到工作记忆
        await self._cache_to_working(session_id, result)

        # 6️⃣ 计算统计
        end_time = datetime.now()
        result.retrieval_time = (end_time - start_time).total_seconds()
        result.source_counts = {
            "working": 1 if result.working else 0,
            "episodic": len(result.episodic),
            "semantic": len(result.semantic)
        }

        self._log_retrieval(result, query)

        return result

    async def _retrieve_working(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        从工作记忆检索

        返回整个会话状态
        """
        try:
            session = await self.working_memory.get(session_id)
            if session:
                logger.debug(f"[记忆检索] 工作记忆命中: {session_id}")
            return session
        except Exception as e:
            logger.error(f"[记忆检索] 工作记忆检索失败: {e}")
            return None

    async def _retrieve_episodic(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        从情景记忆检索

        优先返回高分、成功的相关案例
        """
        try:
            task_type = context.get("task_type")

            # 构建过滤器
            filters = {}
            if task_type:
                filters["task_type"] = task_type

            # 优先返回成功案例
            filters["min_rating"] = context.get("min_rating", 3)

            # 执行搜索
            episodes = await self.episodic_memory.search(
                query=query,
                top_k=context.get("episodic_top_k", 3),
                filters=filters
            )

            logger.debug(f"[记忆检索] 情景记忆命中: {len(episodes)} 个案例")
            return episodes

        except Exception as e:
            logger.error(f"[记忆检索] 情景记忆检索失败: {e}")
            return []

    async def _retrieve_semantic(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        从语义记忆检索

        返回相关知识、法规、模板等
        """
        try:
            # 构建过滤器
            filters = {}
            knowledge_types = context.get("knowledge_types", [])
            if knowledge_types:
                filters["knowledge_types"] = knowledge_types

            # 执行搜索
            knowledges = await self.semantic_memory.search(
                query=query,
                top_k=context.get("semantic_top_k", 5),
                filters=filters
            )

            logger.debug(f"[记忆检索] 语义记忆命中: {len(knowledges)} 条知识")
            return knowledges

        except Exception as e:
            logger.error(f"[记忆检索] 语义记忆检索失败: {e}")
            return []

    async def _fuse_and_rank(
        self,
        result: MemoryRetrievalResult,
        query: str
    ) -> MemoryRetrievalResult:
        """
        跨层融合与排序

        策略:
        - 情景记忆: 优先高分成功案例
        - 语义记忆: 综合相似度、访问频率、置信度
        """
        # 情景记忆已在 search 中排序
        # 语义记忆已在 search 中排序
        # 这里可以添加额外的跨层融合逻辑

        # 例如: 如果情景记忆中的案例引用了语义知识,提升该知识的权重
        if result.episodic and result.semantic:
            semantic_ids = {k["knowledge_id"] for k in result.semantic}

            for episode in result.episodic:
                # 假设案例中有关联的知识 ID
                related_ids = episode.get("related_knowledge_ids", [])
                for rid in related_ids:
                    if rid in semantic_ids:
                        # 提升相关知识的权重
                        for k in result.semantic:
                            if k["knowledge_id"] == rid:
                                k["boosted"] = True
                                k["similarity_score"] = min(k["similarity_score"] * 1.2, 1.0)

            # 重新排序语义记忆
            result.semantic.sort(
                key=lambda k: k.get("similarity_score", 0),
                reverse=True
            )

        return result

    async def _cache_to_working(
        self,
        session_id: str,
        result: MemoryRetrievalResult
    ):
        """
        缓存检索结果到工作记忆

        存储检索到的记忆引用,供后续使用
        """
        try:
            # 获取当前会话
            session = await self.working_memory.get(session_id)
            if not session:
                return

            # 缓存记忆引用
            retrieved = {
                "episodic_ids": [e["episode_id"] for e in result.episodic],
                "semantic_ids": [s["knowledge_id"] for s in result.semantic],
                "cached_at": datetime.now().isoformat()
            }

            session["retrieved_memories"] = retrieved
            await self.working_memory.update(session_id, session)

        except Exception as e:
            logger.warning(f"[记忆检索] 缓存到工作记忆失败: {e}")

    def _is_sufficient(
        self,
        working: Optional[Dict[str, Any]],
        query: str
    ) -> bool:
        """
        判断工作记忆是否足够

        检查:
        - 当前上下文是否包含答案
        - 共享变量中是否有相关信息
        """
        if not working:
            return False

        # 检查当前上下文
        current_context = working.get("current_context", {})
        if current_context.get("has_answer"):
            return True

        # 检查共享变量
        shared_vars = working.get("shared_variables", {})
        if any(query.lower() in str(v).lower() for v in shared_vars.values()):
            return True

        return False

    def _log_retrieval(
        self,
        result: MemoryRetrievalResult,
        query: str
    ):
        """记录检索日志"""
        logger.info(
            f"[记忆检索] 查询: {query[:50]}... "
            f"工作: {1 if result.working else 0}, "
            f"情景: {len(result.episodic)}, "
            f"语义: {len(result.semantic)}, "
            f"耗时: {result.retrieval_time:.3f}s"
        )


# 便捷函数
async def retrieve_memories(
    retrieval: MultiTierMemoryRetrieval,
    query: str,
    session_id: str,
    context: Optional[Dict[str, Any]] = None
) -> MemoryRetrievalResult:
    """
    便捷的跨层检索函数

    Args:
        retrieval: 多层记忆检索器实例
        query: 查询文本
        session_id: 会话 ID
        context: 上下文信息

    Returns:
        检索结果
    """
    return await retrieval.retrieve(query, session_id, context)
