"""
语义记忆服务 (Semantic Memory)
负责存储长期知识：法规、概念、模板等
"""

import uuid
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from .base import BaseMemoryService


class SemanticMemoryService(BaseMemoryService):
    """
    语义记忆服务

    存储内容:
    - 法律知识 (法规条文、判例)
    - 合同模板
    - 专业概念
    - 行业知识

    存储: Qdrant (向量) + PostgreSQL (结构化)
    """

    COLLECTION_NAME = "semantic_memory"

    # 知识类型
    KNOWLEDGE_TYPES = {
        "statute": "法规条文",
        "case": "判例摘要",
        "template": "合同模板",
        "concept": "法律概念",
        "clause": "条款模板",
        "faq": "常见问题"
    }

    def __init__(self, vector_store=None, db=None):
        super().__init__()
        self.vector_store = vector_store
        self.db = db

    async def ensure_initialized(self):
        """确保向量集合和数据库表存在"""
        if not self._initialized and self.vector_store:
            await self.vector_store.create_collection(self.COLLECTION_NAME)
            self._initialized = True
            self._log_info("语义记忆服务初始化完成")

    async def add_knowledge(
        self,
        knowledge_type: str,
        content: str,
        title: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        添加知识到语义记忆

        Args:
            knowledge_type: 知识类型 (statute/case/template/concept/clause/faq)
            content: 知识内容
            title: 知识标题
            metadata: 额外元数据

        Returns:
            knowledge_id: 知识 ID
        """
        await self.ensure_initialized()

        if knowledge_type not in self.KNOWLEDGE_TYPES:
            self._log_warning(f"未知的知识类型: {knowledge_type}")
            return None

        knowledge_id = str(uuid.uuid4())

        # 构建存储数据
        payload = {
            "knowledge_id": knowledge_id,
            "knowledge_type": knowledge_type,
            "title": title,
            "content": content,
            "related_concepts": metadata.get("related_concepts", []) if metadata else [],
            "confidence_score": metadata.get("confidence", 1.0) if metadata else 1.0,
            "access_count": 0,
            "source": metadata.get("source", "") if metadata else "",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        # 添加到向量存储
        content_to_vectorize = f"{title}\n{content}"
        document = {
            "id": knowledge_id,
            "content": content_to_vectorize,
            "metadata": payload
        }

        count = await self.vector_store.add_documents(
            self.COLLECTION_NAME,
            [document]
        )

        if count > 0:
            self._log_info(f"已添加语义知识: {knowledge_id} ({knowledge_type})")
            return knowledge_id

        return None

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索语义记忆

        Args:
            query: 查询文本
            top_k: 返回数量
            filters: 过滤条件 (如 knowledge_type)

        Returns:
            匹配的知识列表
        """
        await self.ensure_initialized()

        # 执行向量搜索
        results = await self.vector_store.search(
            collection_name=self.COLLECTION_NAME,
            query=query,
            top_k=top_k * 2,  # 多取一些用于重排序
            score_threshold=0.6
        )

        # 过滤和排序
        memories = []
        for res in results:
            meta = res.get("metadata", {})

            # 应用过滤器
            if filters:
                knowledge_type = filters.get("knowledge_type")
                if knowledge_type and meta.get("knowledge_type") != knowledge_type:
                    continue

            memories.append({
                "knowledge_id": meta.get("knowledge_id"),
                "knowledge_type": meta.get("knowledge_type"),
                "title": meta.get("title"),
                "content": meta.get("content"),
                "related_concepts": meta.get("related_concepts", []),
                "confidence_score": meta.get("confidence_score", 1.0),
                "access_count": meta.get("access_count", 0),
                "similarity_score": res.get("score")
            })

        # 重排序: 综合考虑相似度、访问频率、置信度
        memories.sort(
            key=lambda m: (
                m["similarity_score"] * 0.6 +
                m["confidence_score"] * 0.3 +
                min(m["access_count"] / 100, 0.1)
            ),
            reverse=True
        )

        # 更新访问计数
        for memory in memories[:top_k]:
            await self._increment_access_count(memory["knowledge_id"])

        return memories[:top_k]

    async def get(self, knowledge_id: str) -> Optional[Dict[str, Any]]:
        """获取单个知识"""
        # TODO: 从数据库获取完整记录
        await self.ensure_initialized()

        results = await self.vector_store.search(
            collection_name=self.COLLECTION_NAME,
            query=knowledge_id,  # 简化实现,实际应该用 ID 查询
            top_k=1
        )

        if results:
            return results[0].get("metadata")
        return None

    async def update(self, knowledge_id: str, updates: Dict[str, Any]) -> bool:
        """更新知识"""
        await self.ensure_initialized()
        # TODO: 实现更新逻辑
        self._log_warning(f"更新语义知识暂未实现: {knowledge_id}")
        return False

    async def delete(self, knowledge_id: str) -> bool:
        """删除知识"""
        await self.ensure_initialized()
        # TODO: 实现删除逻辑
        self._log_warning(f"删除语义知识暂未实现: {knowledge_id}")
        return False

    async def _increment_access_count(self, knowledge_id: str):
        """增加访问计数"""
        # TODO: 异步更新访问计数
        pass

    async def get_related_concepts(
        self,
        concept: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取相关概念 (用于知识图谱关联)
        """
        results = await self.search(
            query=concept,
            top_k=top_k,
            filters={"knowledge_type": "concept"}
        )
        return results

    async def get_statistics(self) -> Dict[str, Any]:
        """获取语义记忆统计信息"""
        await self.ensure_initialized()

        # TODO: 从数据库获取统计
        return {
            "total_knowledge": 0,
            "by_type": {k: 0 for k in self.KNOWLEDGE_TYPES.keys()},
            "total_accesses": 0
        }
