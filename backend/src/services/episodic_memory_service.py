"""
情景记忆服务 (Episodic Memory Service)
负责存储和检索历史案件/任务的处理经验，实现"经验复用"
"""

import json
import uuid
from datetime import datetime
from typing import Any

from loguru import logger

from src.services.vector_store import vector_store


class EpisodicMemoryService:
    COLLECTION_NAME = "episodic_memory"

    def __init__(self, incident_collector: Any | None = None) -> None:
        self.vector_store = vector_store
        self._initialized = False
        # T5 (CREAO Slice 1): 可选注入 IncidentCollector; 不注入则跳过 incident 上报
        self.incident_collector = incident_collector

    async def ensure_initialized(self) -> None:
        """确保向量集合存在"""
        if not self._initialized:
            await self.vector_store.create_collection(self.COLLECTION_NAME)
            self._initialized = True

    async def add_memory(
        self,
        task_description: str,
        plan: list[dict[str, Any]],
        final_result: dict[str, Any],
        user_feedback: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None
    ) -> str | None:
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
    ) -> list[dict[str, Any]]:
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
            except Exception:
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

    async def update_feedback(
        self,
        memory_id: str,
        rating: int,
        comment: str = "",
        user_id: str | None = None,
    ) -> bool:
        """更新记忆的反馈评分"""
        if not self.vector_store.client:
            return False

        try:
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

            # ===== CREAO 自愈闭环 Slice 1: 低评分上报 incident =====
            # E1 (2026-05-14): 优先用注入的 collector, 否则用 safely fallback
            if rating <= 2:
                try:
                    from src.schemas.incident import IncidentSource, IncidentSeverity

                    _payload = {
                        "memory_id": str(memory_id),
                        "rating": rating,
                        "comment": (comment[:500] if comment else None),
                    }
                    if self.incident_collector is not None:
                        await self.incident_collector.collect(
                            source=IncidentSource.LOW_RATING,
                            title=f"user low rating: {rating}",
                            payload=_payload,
                            severity=IncidentSeverity.P2,
                            user_id=user_id,
                            fingerprint_keys=["memory_id"],
                        )
                    else:
                        from src.harness.incident_hook import collect_incident_safely
                        await collect_incident_safely(
                            source=IncidentSource.LOW_RATING,
                            title=f"user low rating: {rating}",
                            payload=_payload,
                            severity=IncidentSeverity.P2,
                            user_id=user_id,
                            fingerprint_keys=["memory_id"],
                        )
                except Exception as hook_err:
                    logger.error(f"[EpisodicMemory] incident hook failed: {hook_err}")

            return True
        except Exception as e:
            logger.error(f"更新记忆反馈失败: {e}")
            return False

    async def add_discovery_path(
        self,
        intent: str,
        user_input: str,
        clarification_rounds: int,
        questions_asked: list[dict[str, Any]],
        user_answers: dict[str, str],
        filled_slots: list[dict[str, Any]],
        final_rating: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """
        存储完整的"需求发掘路径"，用于飞轮优化。

        高评分路径会被聚合分析，自动优化场景模板。
        """
        await self.ensure_initialized()

        path_id = str(uuid.uuid4())
        payload = {
            "memory_id": path_id,
            "type": "discovery_path",
            "intent": intent,
            "original_input": user_input[:500],
            "clarification_rounds": clarification_rounds,
            "questions_asked": json.dumps(questions_asked, ensure_ascii=False),
            "user_answers": json.dumps(user_answers, ensure_ascii=False),
            "filled_slots": json.dumps(filled_slots, ensure_ascii=False),
            "user_rating": final_rating or 0,
            "timestamp": datetime.now().isoformat(),
        }
        if metadata:
            payload.update(metadata)

        content_to_vectorize = (
            f"Intent: {intent}\n"
            f"Input: {user_input[:200]}\n"
            f"Questions: {', '.join(q.get('question', '') for q in questions_asked)}\n"
            f"Answers: {json.dumps(user_answers, ensure_ascii=False)}"
        )

        document = {
            "id": path_id,
            "content": content_to_vectorize,
            "metadata": payload,
        }

        count = await self.vector_store.add_documents(
            self.COLLECTION_NAME, [document]
        )
        if count > 0:
            logger.info(f"已保存需求发掘路径: {path_id}, intent={intent}, rating={final_rating}")
            return path_id
        return None

    async def get_discovery_insights(
        self,
        intent: str,
        top_k: int = 20,
    ) -> dict[str, Any]:
        """
        分析特定场景的需求发掘经验，生成模板优化建议。

        Returns:
            {
                "total_paths": int,
                "avg_rating": float,
                "avg_rounds": float,
                "most_asked_questions": [{"question": str, "count": int}],
                "most_filled_slots": [{"slot": str, "count": int}],
                "suggested_slot_order": [str],
            }
        """
        await self.ensure_initialized()

        results = await self.vector_store.search(
            collection_name=self.COLLECTION_NAME,
            query=f"Intent: {intent} discovery path",
            top_k=top_k,
            score_threshold=0.5,
        )

        paths = [
            r.get("metadata", {})
            for r in results
            if r.get("metadata", {}).get("type") == "discovery_path"
            and r.get("metadata", {}).get("intent") == intent
        ]

        if not paths:
            return {"total_paths": 0}

        # 统计
        total = len(paths)
        ratings = [p.get("user_rating", 0) for p in paths if p.get("user_rating", 0) > 0]
        rounds = [p.get("clarification_rounds", 0) for p in paths]

        # 统计高频追问问题
        question_counts: dict[str, int] = {}
        slot_counts: dict[str, int] = {}

        for p in paths:
            try:
                questions = json.loads(p.get("questions_asked", "[]"))
                for q in questions:
                    q_text = q.get("question", "") if isinstance(q, dict) else str(q)
                    if q_text:
                        question_counts[q_text] = question_counts.get(q_text, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass

            try:
                slots = json.loads(p.get("filled_slots", "[]"))
                for s in slots:
                    s_key = s.get("key", "") if isinstance(s, dict) else str(s)
                    if s_key:
                        slot_counts[s_key] = slot_counts.get(s_key, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass

        # 按频率排序
        most_asked = sorted(question_counts.items(), key=lambda x: x[1], reverse=True)
        most_filled = sorted(slot_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_paths": total,
            "avg_rating": round(sum(ratings) / len(ratings), 1) if ratings else 0,
            "avg_rounds": round(sum(rounds) / total, 1),
            "most_asked_questions": [
                {"question": q, "count": c} for q, c in most_asked[:10]
            ],
            "most_filled_slots": [
                {"slot": s, "count": c} for s, c in most_filled[:10]
            ],
            "suggested_slot_order": [s for s, _ in most_filled],
        }


# 全局实例
episodic_memory = EpisodicMemoryService()
