# -*- coding: utf-8 -*-
"""
AI 旁听助手服务

在 IM 对话或匿名咨询中，旁听消息流并实时推送法律分析，
对话结束后生成结构化纪要和待办事项。
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_maker
from src.models.meeting_record import MeetingRecord


# ========== 旁听 Prompt ==========

LISTENER_SYSTEM_PROMPT = """你是安心法务的 AI 法律助手，正在旁听一场对话。

你的职责：
1. 识别对话中的法律要点并标注类别（事实陈述/法律问题/风险点/决策事项）
2. 发现潜在法律风险时标注风险等级（高/中/低）
3. 关联相关法律条文
4. 提出简短专业建议

输出格式（JSON）：
{
  "has_legal_content": true/false,
  "points": [
    {
      "type": "risk|legal_issue|fact|decision",
      "title": "要点标题（10字以内）",
      "detail": "简要说明（50字以内）",
      "risk_level": "high|medium|low|null",
      "related_law": "相关法条（如有）"
    }
  ]
}

如果对话内容不涉及法律问题，返回 {"has_legal_content": false, "points": []}。
只分析最新的对话内容，不要重复之前已经分析过的内容。务必简洁。"""

SUMMARY_SYSTEM_PROMPT = """你是安心法务的 AI 法律助手，请根据以下完整的咨询/对话记录，生成结构化纪要。

输出格式（JSON）：
{
  "title": "纪要标题（15字以内）",
  "abstract": "咨询摘要（200字以内）",
  "case_elements": {
    "parties": "当事人信息",
    "timeline": "时间线",
    "amount": "涉及金额",
    "dispute_focus": "争议焦点"
  },
  "legal_analysis": [
    {"point": "分析要点", "law_reference": "相关法条", "conclusion": "结论"}
  ],
  "risk_assessment": {
    "level": "high|medium|low",
    "risks": ["风险1", "风险2"]
  },
  "recommendations": ["建议1", "建议2"],
  "action_items": [
    {"task": "待办事项", "priority": "high|medium|low"}
  ]
}"""


class MeetingAssistantService:
    """AI 旁听助手管理器（进程级单例）"""

    def __init__(self):
        # conversation_id → 缓冲状态
        self._buffers: Dict[str, _MessageBuffer] = {}

    def is_listening(self, conversation_id: str) -> bool:
        return conversation_id in self._buffers

    async def start_listening(
        self,
        db: AsyncSession,
        conversation_id: str,
        conversation_type: str,
        user_id: str,
    ) -> MeetingRecord:
        """开启 AI 旁听"""
        if self.is_listening(conversation_id):
            # 返回已有记录
            result = await db.execute(
                select(MeetingRecord).where(
                    MeetingRecord.conversation_id == conversation_id,
                    MeetingRecord.status == "listening",
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing

        record = MeetingRecord(
            id=str(uuid4()),
            conversation_id=conversation_id,
            conversation_type=conversation_type,
            status="listening",
            started_by=user_id,
            insights=[],
            action_items=[],
        )
        db.add(record)
        await db.flush()

        self._buffers[conversation_id] = _MessageBuffer(
            record_id=record.id,
            conversation_id=conversation_id,
        )

        logger.info(f"AI 旁听已开启: conv={conversation_id}, record={record.id}")
        return record

    async def stop_listening(
        self,
        db: AsyncSession,
        conversation_id: str,
    ) -> Optional[MeetingRecord]:
        """停止旁听并生成纪要"""
        buf = self._buffers.pop(conversation_id, None)
        if not buf:
            return None

        result = await db.execute(
            select(MeetingRecord).where(MeetingRecord.id == buf.record_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            return None

        # 生成完整对话文本
        transcript = "\n".join(
            f"{m['sender']}: {m['content']}" for m in buf.all_messages
        )
        record.transcript_text = transcript

        # 生成结构化纪要
        summary = await self._generate_summary(transcript)
        record.summary = summary
        if summary and "action_items" in summary:
            record.action_items = summary["action_items"]

        record.status = "completed"
        record.ended_at = datetime.now(timezone.utc)

        await db.flush()
        logger.info(f"AI 旁听已结束: conv={conversation_id}, record={record.id}")
        return record

    async def on_message(
        self,
        conversation_id: str,
        sender_id: str,
        content: str,
        sender_name: str = "",
    ) -> None:
        """消息钩子 — 由 IM/匿名聊天的消息流异步调用"""
        buf = self._buffers.get(conversation_id)
        if not buf:
            return

        buf.add_message(sender_id, sender_name or sender_id[:8], content)

        # 检查是否触发分析（累积 3 条或超过 30 秒）
        if buf.should_analyze():
            messages_batch = buf.flush()
            asyncio.create_task(
                self._analyze_and_push(conversation_id, buf.record_id, messages_batch)
            )

    async def get_record(self, db: AsyncSession, conversation_id: str) -> Optional[MeetingRecord]:
        """获取对话的旁听记录"""
        result = await db.execute(
            select(MeetingRecord).where(
                MeetingRecord.conversation_id == conversation_id,
            ).order_by(MeetingRecord.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_records_by_user(
        self, db: AsyncSession, user_id: str, page: int = 1, page_size: int = 20
    ) -> tuple[list, int]:
        """获取用户的旁听记录列表"""
        from sqlalchemy import func as sa_func
        count_result = await db.execute(
            select(sa_func.count()).where(MeetingRecord.started_by == user_id)
        )
        total = count_result.scalar() or 0

        result = await db.execute(
            select(MeetingRecord)
            .where(MeetingRecord.started_by == user_id)
            .order_by(MeetingRecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        records = list(result.scalars().all())
        return records, total

    # ========== 内部方法 ==========

    async def _analyze_and_push(
        self, conversation_id: str, record_id: str, messages: List[dict]
    ) -> None:
        """异步分析消息批次并推送结果"""
        try:
            # 构建分析文本
            text = "\n".join(f"{m['sender']}: {m['content']}" for m in messages)

            # 调用 LLM 分析
            analysis = await self._call_llm_analysis(text)

            if not analysis or not analysis.get("has_legal_content"):
                return

            # 构建 insight 卡片
            insight = {
                "id": str(uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "points": analysis.get("points", []),
            }

            # 存储到记录
            async with async_session_maker() as db:
                result = await db.execute(
                    select(MeetingRecord).where(MeetingRecord.id == record_id)
                )
                record = result.scalar_one_or_none()
                if record:
                    existing = record.insights or []
                    existing.append(insight)
                    record.insights = existing
                    await db.commit()

            # 通过 IM WebSocket 推送给对话参与者
            await self._push_insight_to_conversation(conversation_id, insight)

        except Exception as e:
            logger.error(f"AI 旁听分析失败: conv={conversation_id}, error={e}")

    async def _call_llm_analysis(self, text: str) -> Optional[dict]:
        """调用 LLM 分析对话内容"""
        import json

        try:
            from src.agents.workforce import get_workforce
            workforce = get_workforce()
            # 使用 coordinator 的基础 agent 直接分析
            agent = workforce._agents.get("legal_advisor")
            if not agent:
                # fallback：用任意可用的 agent
                agent = next(iter(workforce._agents.values()), None)
            if not agent:
                logger.warning("无可用 Agent，跳过旁听分析")
                return None

            response = await agent.chat(
                message=f"请分析以下对话内容：\n\n{text}",
                system_prompt_override=LISTENER_SYSTEM_PROMPT,
                max_tokens=500,
            )

            # 解析 JSON 响应
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return None

        except Exception as e:
            logger.error(f"LLM 分析调用失败: {e}")
            return None

    async def _generate_summary(self, transcript: str) -> Optional[dict]:
        """生成结构化纪要"""
        if not transcript or len(transcript.strip()) < 20:
            return None

        import json

        try:
            from src.agents.workforce import get_workforce
            workforce = get_workforce()
            agent = workforce._agents.get("legal_advisor")
            if not agent:
                agent = next(iter(workforce._agents.values()), None)
            if not agent:
                return None

            # 截取最后 6000 字符避免超出上下文
            truncated = transcript[-6000:] if len(transcript) > 6000 else transcript

            response = await agent.chat(
                message=f"请根据以下对话记录生成结构化纪要：\n\n{truncated}",
                system_prompt_override=SUMMARY_SYSTEM_PROMPT,
                max_tokens=1500,
            )

            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return None

        except Exception as e:
            logger.error(f"纪要生成失败: {e}")
            return None

    async def _push_insight_to_conversation(
        self, conversation_id: str, insight: dict
    ) -> None:
        """通过 IM WebSocket 推送 AI 分析卡片"""
        try:
            from src.services.im_hub import im_manager
            from src.services.im_service import IMService

            async with async_session_maker() as db:
                service = IMService(db)
                participant_ids = await service.get_participant_ids(conversation_id)

                if participant_ids:
                    # 构建卡片内容
                    points_text = "\n".join(
                        f"- **{p.get('title', '')}**（{p.get('type', '')}）: {p.get('detail', '')}"
                        + (f" ⚠️ 风险: {p['risk_level']}" if p.get("risk_level") else "")
                        + (f" 📖 {p['related_law']}" if p.get("related_law") else "")
                        for p in insight.get("points", [])
                    )

                    card_message = {
                        "type": "ai_insight",
                        "data": {
                            "id": insight["id"],
                            "timestamp": insight["timestamp"],
                            "points": insight["points"],
                            "text": points_text,
                            "source": "ai_listener",
                        },
                    }

                    await im_manager.broadcast_to_conversation(
                        participant_ids=participant_ids,
                        message=card_message,
                    )

        except Exception as e:
            logger.error(f"推送 AI insight 失败: {e}")


class _MessageBuffer:
    """对话消息缓冲器"""

    BATCH_SIZE = 3  # 累积 N 条触发分析
    MAX_WAIT_SECONDS = 30  # 最大等待秒数

    def __init__(self, record_id: str, conversation_id: str):
        self.record_id = record_id
        self.conversation_id = conversation_id
        self.pending: List[dict] = []
        self.all_messages: List[dict] = []
        self.last_analyze_time = time.time()

    def add_message(self, sender_id: str, sender_name: str, content: str):
        msg = {"sender_id": sender_id, "sender": sender_name, "content": content}
        self.pending.append(msg)
        self.all_messages.append(msg)

    def should_analyze(self) -> bool:
        if not self.pending:
            return False
        if len(self.pending) >= self.BATCH_SIZE:
            return True
        if time.time() - self.last_analyze_time >= self.MAX_WAIT_SECONDS:
            return True
        return False

    def flush(self) -> List[dict]:
        batch = self.pending[:]
        self.pending.clear()
        self.last_analyze_time = time.time()
        return batch


# 进程级单例
meeting_assistant = MeetingAssistantService()
