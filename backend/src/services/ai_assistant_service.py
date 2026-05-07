"""AI 私有助手服务"""

from datetime import datetime, timedelta
from typing import Any, cast
from uuid import uuid4

import httpx
from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.llm_helper import LLMConfigResult, get_llm_config
from src.models.ai_assistant import (
    AIAssistantConfig,
    AIAssistantFeedback,
    ConversationSummary,
)
from src.models.conversation import Conversation, Message, MessageRole

# ========== 可用 Agent 注册表 ==========

AVAILABLE_AGENTS: list[dict[str, Any]] = [
    {
        "key": "legal_advisor",
        "name": "法律顾问",
        "description": "综合法律咨询，提供专业法律建议和解决方案",
        "capabilities": ["法律咨询", "法规解读", "方案建议"],
        "icon": "scale",
    },
    {
        "key": "contract_reviewer",
        "name": "合同审查",
        "description": "审查合同条款，识别风险点和不合规内容",
        "capabilities": ["合同审查", "条款分析", "风险识别"],
        "icon": "file-text",
    },
    {
        "key": "risk_assessor",
        "name": "风险评估",
        "description": "全面评估法律风险，提供风险等级和应对策略",
        "capabilities": ["风险评估", "合规检查", "预警分析"],
        "icon": "shield-alert",
    },
    {
        "key": "due_diligence",
        "name": "尽职调查",
        "description": "企业背景调查、股权结构分析、诉讼历史查询",
        "capabilities": ["企业调查", "股权分析", "诉讼查询"],
        "icon": "search",
    },
    {
        "key": "litigation_strategist",
        "name": "诉讼策略",
        "description": "制定诉讼策略，分析胜诉可能性和诉讼路径",
        "capabilities": ["诉讼分析", "策略规划", "证据评估"],
        "icon": "gavel",
    },
    {
        "key": "compliance_officer",
        "name": "合规审查",
        "description": "企业合规审查，确保业务符合法律法规要求",
        "capabilities": ["合规审查", "制度建设", "整改建议"],
        "icon": "check-circle",
    },
    {
        "key": "ip_specialist",
        "name": "知识产权",
        "description": "商标、专利、著作权等知识产权保护和维权",
        "capabilities": ["商标注册", "专利分析", "侵权鉴定"],
        "icon": "lightbulb",
    },
    {
        "key": "labor_compliance",
        "name": "劳动合规",
        "description": "劳动法合规咨询，劳动争议处理和用工风险防范",
        "capabilities": ["劳动合规", "争议调解", "用工风险"],
        "icon": "users",
    },
    {
        "key": "tax_compliance",
        "name": "税务合规",
        "description": "税务法规咨询，纳税筹划和税务风险防范",
        "capabilities": ["税务咨询", "纳税筹划", "风险防范"],
        "icon": "calculator",
    },
    {
        "key": "document_drafter",
        "name": "文书起草",
        "description": "起草法律文书，包括合同、协议、意见书等",
        "capabilities": ["合同起草", "文书撰写", "模板生成"],
        "icon": "pen-tool",
    },
    {
        "key": "evidence_analyst",
        "name": "证据分析",
        "description": "分析证据材料，评估证据效力和证据链完整性",
        "capabilities": ["证据分析", "效力评估", "证据链梳理"],
        "icon": "clipboard-list",
    },
    {
        "key": "regulatory_monitor",
        "name": "法规监控",
        "description": "监控法律法规变动，及时推送影响企业的政策变化",
        "capabilities": ["法规监控", "政策推送", "影响评估"],
        "icon": "bell",
    },
    {
        "key": "legal_researcher",
        "name": "法律研究",
        "description": "检索法律文献和判例，提供法律研究报告",
        "capabilities": ["文献检索", "判例分析", "研究报告"],
        "icon": "book-open",
    },
]


# 全局 HTTP 客户端，用于复用连接池
_shared_http_client: httpx.AsyncClient | None = None

def get_shared_http_client() -> httpx.AsyncClient:
    global _shared_http_client
    if _shared_http_client is None or _shared_http_client.is_closed:
        _shared_http_client = httpx.AsyncClient(timeout=60.0)
    return _shared_http_client


class AIAssistantService:
    """AI 私有助手服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 助手配置
    # ------------------------------------------------------------------

    async def get_or_create_config(self, org_id: str) -> dict[str, Any]:
        """获取组织的助手配置，不存在则创建默认配置"""
        result = await self.db.execute(
            select(AIAssistantConfig).where(
                AIAssistantConfig.org_id == org_id,
                AIAssistantConfig.is_active == True,
            )
        )
        config = result.scalar_one_or_none()

        if config:
            return config.to_dict()

        # 创建默认配置
        config = AIAssistantConfig(
            id=str(uuid4()),
            org_id=org_id,
            name="安心法务助手",
            welcome_message="您好！我是您的专属法务助手，有什么法律问题可以帮您？",
            personality={
                "style": "professional",
                "tone": "formal",
                "language": "zh-CN",
            },
            enabled_agents=[
                "legal_advisor",
                "contract_reviewer",
                "risk_assessor",
            ],
            knowledge_base_ids=[],
            max_context_turns=10,
            temperature=0.7,
            is_active=True,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config.to_dict()

    async def update_config(self, config_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """更新助手配置"""
        result = await self.db.execute(
            select(AIAssistantConfig).where(AIAssistantConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError(f"助手配置不存在: {config_id}")

        allowed_fields = {
            "name", "description", "avatar_url", "welcome_message",
            "system_prompt", "personality", "enabled_agents",
            "knowledge_base_ids", "max_context_turns", "temperature",
            "llm_config_id", "is_active",
        }
        for key, value in data.items():
            if key in allowed_fields:
                setattr(config, key, value)

        await self.db.commit()
        await self.db.refresh(config)
        return config.to_dict()

    async def get_available_agents(self) -> list[dict[str, Any]]:
        """返回所有可用 Agent 列表"""
        return AVAILABLE_AGENTS

    # ------------------------------------------------------------------
    # 对话摘要
    # ------------------------------------------------------------------

    async def generate_summary(
        self, conversation_id: str, user_id: str
    ) -> dict[str, Any]:
        """
        为对话生成 AI 摘要。

        1. 从 conversations / messages 表获取消息历史
        2. 调用 LLM 生成摘要
        3. 存储到 ConversationSummary
        """
        # 获取消息历史
        conv_result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = conv_result.scalar_one_or_none()
        if not conversation:
            raise ValueError(f"对话不存在: {conversation_id}")

        msg_result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = msg_result.scalars().all()
        if not messages:
            raise ValueError("对话没有消息记录")

        # 拼接对话文本
        dialogue_lines: list[str] = []
        for msg in messages:
            role_label = "用户" if msg.role == MessageRole.USER.value else "助手"
            content = msg.content or ""
            dialogue_lines.append(f"{role_label}: {content}")
        dialogue_text = "\n".join(dialogue_lines)

        # 调用 LLM 生成摘要
        llm_config = await get_llm_config(db_session=self.db)
        summary_prompt = (
            "请总结以下法律咨询对话，提取：\n"
            "1. 关键话题（key_topics）：列表形式\n"
            "2. 待办事项（action_items）：列表形式\n"
            "3. 情感倾向（sentiment）：positive / neutral / negative\n"
            "4. 涉及的法律领域（legal_domains）：如 contract, labor, ip, tax 等\n"
            "5. 总结摘要（summary）：一段简明扼要的总结\n\n"
            "请以 JSON 格式返回，包含以上五个字段。\n\n"
            f"对话内容：\n{dialogue_text[:6000]}"
        )

        summary_data = await self._call_llm(llm_config, summary_prompt)

        # 解析 LLM 返回
        import json

        parsed: dict[str, Any] = {}
        try:
            # 尝试直接解析 JSON
            clean = summary_data.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            parsed = json.loads(clean)
        except json.JSONDecodeError:
            logger.warning("LLM 返回非 JSON 格式，使用原文作为摘要")
            parsed = {"summary": summary_data}

        # 检查是否已存在摘要（更新）
        existing = await self.db.execute(
            select(ConversationSummary).where(
                ConversationSummary.conversation_id == conversation_id
            )
        )
        record = existing.scalar_one_or_none()

        if record:
            record.summary = parsed.get("summary", summary_data)
            record.key_topics = parsed.get("key_topics", [])
            record.action_items = parsed.get("action_items", [])
            record.sentiment = parsed.get("sentiment", "neutral")
            record.legal_domains = parsed.get("legal_domains", [])
            record.turn_count = len(messages)
            record.token_count = sum(len(m.content or "") for m in messages)
        else:
            record = ConversationSummary(
                id=str(uuid4()),
                conversation_id=conversation_id,
                user_id=user_id,
                summary=parsed.get("summary", summary_data),
                key_topics=parsed.get("key_topics", []),
                action_items=parsed.get("action_items", []),
                sentiment=parsed.get("sentiment", "neutral"),
                turn_count=len(messages),
                token_count=sum(len(m.content or "") for m in messages),
                legal_domains=parsed.get("legal_domains", []),
            )
            self.db.add(record)

        await self.db.commit()
        await self.db.refresh(record)
        return record.to_dict()

    async def get_summaries(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> list[dict[str, Any]]:
        """获取用户的对话摘要列表"""
        result = await self.db.execute(
            select(ConversationSummary)
            .where(ConversationSummary.user_id == user_id)
            .order_by(ConversationSummary.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        summaries = result.scalars().all()
        return [summary.to_dict() for summary in summaries]

    # ------------------------------------------------------------------
    # 反馈
    # ------------------------------------------------------------------

    async def submit_feedback(self, data: dict[str, Any]) -> dict[str, Any]:
        """提交反馈"""
        feedback = AIAssistantFeedback(
            id=str(uuid4()),
            assistant_config_id=data.get("assistant_config_id"),
            user_id=data["user_id"],
            conversation_id=data.get("conversation_id"),
            message_id=data.get("message_id"),
            rating=data["rating"],
            feedback_text=data.get("feedback_text"),
            feedback_type=data.get("feedback_type", "helpful"),
        )
        self.db.add(feedback)
        await self.db.commit()
        await self.db.refresh(feedback)
        return feedback.to_dict()

    async def get_feedback_stats(
        self,
        assistant_config_id: str | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        获取反馈统计。

        返回:
            total_feedbacks, avg_rating, rating_distribution,
            type_distribution, trend
        """
        since = datetime.utcnow() - timedelta(days=days)
        base_filter = AIAssistantFeedback.created_at >= since
        if assistant_config_id:
            base_filter = and_(
                base_filter,
                AIAssistantFeedback.assistant_config_id == assistant_config_id,
            )

        # 总量 & 均分
        agg = await self.db.execute(
            select(
                func.count(AIAssistantFeedback.id).label("total"),
                func.avg(AIAssistantFeedback.rating).label("avg_rating"),
            ).where(base_filter)
        )
        row = agg.one()
        total = row.total or 0
        avg_rating = round(float(row.avg_rating or 0), 2)

        # 评分分布
        dist_result = await self.db.execute(
            select(
                AIAssistantFeedback.rating,
                func.count(AIAssistantFeedback.id),
            )
            .where(base_filter)
            .group_by(AIAssistantFeedback.rating)
        )
        rating_distribution = dict.fromkeys(range(1, 6), 0)
        for rating_val, cnt in dist_result.all():
            rating_distribution[rating_val] = cnt

        # 类型分布
        type_result = await self.db.execute(
            select(
                AIAssistantFeedback.feedback_type,
                func.count(AIAssistantFeedback.id),
            )
            .where(base_filter)
            .group_by(AIAssistantFeedback.feedback_type)
        )
        type_distribution: dict[str | None, int] = {
            feedback_type: int(count)
            for feedback_type, count in type_result.all()
        }

        # 每日趋势
        trend_result = await self.db.execute(
            select(
                func.date(AIAssistantFeedback.created_at).label("date"),
                func.avg(AIAssistantFeedback.rating).label("avg_rating"),
                func.count(AIAssistantFeedback.id).label("count"),
            )
            .where(base_filter)
            .group_by(func.date(AIAssistantFeedback.created_at))
            .order_by(func.date(AIAssistantFeedback.created_at))
        )
        trend = [
            {
                "date": str(r.date),
                "avg_rating": round(float(r.avg_rating or 0), 2),
                "count": r.count,
            }
            for r in trend_result.all()
        ]

        return {
            "total_feedbacks": total,
            "avg_rating": avg_rating,
            "rating_distribution": rating_distribution,
            "type_distribution": type_distribution,
            "trend": trend,
        }

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    async def _call_llm(llm_config: LLMConfigResult, prompt: str) -> str:
        """调用 LLM 获取文本响应"""
        api_base = llm_config.api_base_url.rstrip("/")
        url = f"{api_base}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        if llm_config.api_key:
            headers["Authorization"] = f"Bearer {llm_config.api_key}"

        payload = {
            "model": llm_config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": llm_config.temperature,
            "max_tokens": min(llm_config.max_tokens, 2000),
        }

        client = get_shared_http_client()
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = cast(dict[str, Any], resp.json())
            return cast(str, data["choices"][0]["message"]["content"])
        except Exception as e:
            logger.exception(f"LLM 调用失败: {e}")
            return f"摘要生成失败: {e}"
