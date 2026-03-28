"""
情景记忆服务 (Episodic Memory Service)
负责存储和检索历史案件/任务的处理经验，实现"经验复用"
"""

import uuid
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
from src.services.vector_store import vector_store

class EpisodicMemoryService:
    COLLECTION_NAME = "episodic_memory"

    def __init__(self):
        self.vector_store = vector_store
        self._initialized = False

    async def ensure_initialized(self):
        """确保向量集合存在"""
        if not self._initialized:
            await self.vector_store.create_collection(self.COLLECTION_NAME)
            self._initialized = True

    async def add_memory(
        self,
        task_description: str,
        plan: List[Dict[str, Any]],
        final_result: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        添加一条情景记忆
        """
        await self.ensure_initialized()
        
        if not metadata:
            metadata = {}
            
        memory_id = str(uuid.uuid4())
        
        # 提取结果摘要，避免存储过大
        result_summary = final_result.get("summary", "")
        if not result_summary and "content" in final_result:
            result_summary = final_result["content"][:500] + "..."
            
        # 序列化复杂对象，确保 Qdrant payload 兼容性
        
        payload = {
            "memory_id": memory_id, # 显式存储 ID 到 payload
            "original_task": task_description,
            "plan_json": json.dumps(plan, ensure_ascii=False),
            "result_summary": result_summary,
            "timestamp": datetime.now().isoformat(),
            "type": "case_execution",
            "user_rating": 0, # 默认 0 分
            "user_comment": ""
        }
        
        if user_feedback:
            payload["user_rating"] = user_feedback.get("rating", 0)
            payload["user_comment"] = user_feedback.get("comment", "")
            
        if metadata:
            payload.update(metadata)

        content_to_vectorize = f"Task: {task_description}\nResult: {result_summary}"
        
        document = {
            "id": memory_id,
            "content": content_to_vectorize,
            "metadata": payload
        }
        
        count = await self.vector_store.add_documents(
            self.COLLECTION_NAME, 
            [document]
        )
        
        if count > 0:
            logger.info(f"已保存情景记忆: {memory_id}")
            return memory_id
        return None

    async def retrieve_similar_cases(
        self,
        task_description: str,
        top_k: int = 3,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        检索相似的历史案件
        """
        await self.ensure_initialized()
        
        # 增加过滤条件：优先返回好评（>=4分）的案例
        # 这里先检索所有相似的，然后在内存排序，或者可以在 search 中加 filter
        # 为了通用性，先检索相似度高的，再按评分加权
        
        results = await self.vector_store.search(
            collection_name=self.COLLECTION_NAME,
            query=task_description,
            top_k=top_k * 2, # 多取一些用于重排序
            score_threshold=score_threshold
        )
        
        memories = []
        for res in results:
            meta = res.get("metadata", {})
            
            # 如果评分太低（如 1 分），则过滤掉（负面经验）
            rating = meta.get("user_rating", 0)
            if rating > 0 and rating < 2: 
                continue

            # 尝试解析 plan_json
            plan = []
            try:
                if "plan_json" in meta:
                    plan = json.loads(meta["plan_json"])
            except:
                pass
                
            memories.append({
                "memory_id": meta.get("memory_id"),
                "task": meta.get("original_task"),
                "plan": plan,
                "result_summary": meta.get("result_summary"),
                "timestamp": meta.get("timestamp"),
                "rating": rating,
                "similarity_score": res.get("score")
            })
            
        # 按 (评分 * 相似度) 排序，优先推荐高分且相似的
        memories.sort(key=lambda x: (x["rating"] or 3) * x["similarity_score"], reverse=True)
        
        return memories[:top_k]

    async def update_feedback(self, memory_id: str, rating: int, comment: str = "") -> bool:
        """更新记忆的反馈评分"""
        if not self.vector_store.client:
            return False
            
        try:
            from qdrant_client.models import PointStruct
            # Qdrant 更新 payload 需要知道 point ID (这里是 memory_id 的 md5 int)
            import hashlib
            point_id = int(hashlib.md5(memory_id.encode()).hexdigest()[:8], 16)
            
            # 由于 Qdrant 的 set_payload 是覆盖更新，我们最好先读取再更新，或者只更新特定字段
            # set_payload 是增量更新 (partial update)，所以是安全的
            
            self.vector_store.client.set_payload(
                collection_name=self.COLLECTION_NAME,
                payload={
                    "user_rating": rating,
                    "user_comment": comment,
                    "last_feedback_at": datetime.now().isoformat()
                },
                points=[point_id]
            )
            logger.info(f"已更新记忆反馈: {memory_id}, 评分: {rating}")
            return True
        except Exception as e:
            logger.error(f"更新记忆反馈失败: {e}")
            return False

# 全局实例
episodic_memory = EpisodicMemoryService()
