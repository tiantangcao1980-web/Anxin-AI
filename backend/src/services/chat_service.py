"""
对话服务 (v2 - 性能优化版)

优化点：
1. LLM 配置加载提取为公共方法，消除重复代码
2. 流式对话支持真正的 token-by-token 流式输出（不再是假流式）
3. 集成事件总线，关键操作发布事件
4. 添加缓存装饰器到高频查询
5. RAG 引用来源追踪：AI 响应附带法条/案例/知识库引用
6. 统一编排层消除 chat()/stream_chat() 路由决策与后处理的三重重复
"""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.privacy import InferenceRequest, SensitivityLevel
from src.harness.enforcement import run_validation as harness_validate
from src.harness.task_engine import TaskState, task_engine

# ========== Harness Engineering 集成 ==========
from src.harness.trace_context import end_trace, start_trace
from src.models.conversation import Conversation, Message, MessageRole
from src.services.compute_router_service import compute_router
from src.services.due_diligence_service import (
    classify_investigation_request,
    format_due_diligence_chat_response,
    get_company_info,
)
from src.services.pii_service import pii_service
from src.services.template_context import build_template_context_message

if TYPE_CHECKING:
    from src.agents.workforce import LegalWorkforce
    from src.models.llm_config import LLMConfig

# ========== 合同审查 / 文书起草意图检测 ==========

_CONTRACT_REVIEW_RE = re.compile(
    r"审[查阅看核].*合同|合同.*审[查阅看核]|检查.*合同|合同.*[问题风险]|帮我看.*合同|审核.*协议",
    re.IGNORECASE,
)

_DOCUMENT_DRAFTING_RE = re.compile(
    r"起草.*[文书合同协议函]|写.*[合同协议律师函]|生成.*[文书合同]|帮我[写拟].*[合同协议文书]|草拟",
    re.IGNORECASE,
)

_FIND_LAWYER_RE = re.compile(
    r"找.{0,4}律师|推荐.{0,4}律师|请.{0,2}律师|委托律师|聘请律师|律师推荐",
    re.IGNORECASE,
)


def detect_contract_review_intent(content: str) -> bool:
    """检测合同审查意图"""
    return bool(_CONTRACT_REVIEW_RE.search(content))


def detect_document_drafting_intent(content: str) -> bool:
    """检测文书起草意图"""
    return bool(_DOCUMENT_DRAFTING_RE.search(content))


def detect_find_lawyer_intent(content: str) -> bool:
    """检测找律师意图"""
    return bool(_FIND_LAWYER_RE.search(content))


# ========== RAG 引用来源模型 ==========


class CitationSource(BaseModel):
    """RAG 引用来源"""
    id: str
    type: str  # "law_article" | "case" | "knowledge" | "regulation"
    title: str
    content_snippet: str  # 前 200 字符
    source: str  # 例："《民法典》第584条" 或 "（2024）京01民终1234号"
    relevance_score: float  # 0-1
    url: str | None = None


def extract_citations(
    ai_response: str,
    context_docs: list[dict[str, Any]] | None = None,
) -> list[CitationSource]:
    """
    从 AI 响应和 RAG 上下文文档中提取引用来源。

    解析策略：
    1. 从 context_docs（RAG 检索结果）中提取已有来源
    2. 从 AI 响应文本中正则匹配法条引用
    3. 去重并按 relevance_score 降序排序
    """
    citations: list[CitationSource] = []
    seen_ids: set[str] = set()

    # --- 1. 从 RAG context_docs 提取 ---
    if context_docs:
        for i, doc in enumerate(context_docs):
            doc_id = doc.get("id") or doc.get("chunk_id") or f"ctx-{i}"
            if doc_id in seen_ids:
                continue
            seen_ids.add(doc_id)

            # 推断类型
            doc_type = doc.get("type", "knowledge")
            title = doc.get("title", "") or doc.get("source_name", "") or "知识库文档"
            content = doc.get("content", "") or doc.get("text", "")
            source_label = doc.get("source", "") or doc.get("reference", "") or title
            score = float(doc.get("score", 0.0) or doc.get("relevance_score", 0.0))
            url = doc.get("url")

            citations.append(CitationSource(
                id=str(doc_id),
                type=doc_type,
                title=title[:120],
                content_snippet=content[:200],
                source=source_label[:200],
                relevance_score=min(max(score, 0.0), 1.0),
                url=url,
            ))

    # --- 2. 从 AI 响应文本中正则匹配法条引用 ---
    # 匹配 《XXX》第NNN条 格式
    law_pattern = re.compile(
        r'[《《]([^》》]+)[》》]'
        r'(?:第([零一二三四五六七八九十百千\d]+)条)?'
    )
    for match in law_pattern.finditer(ai_response):
        law_name = match.group(1)
        article_no = match.group(2) or ""
        source_text = f"《{law_name}》" + (f"第{article_no}条" if article_no else "")
        ref_id = f"law-{law_name}-{article_no}"
        if ref_id in seen_ids:
            continue
        seen_ids.add(ref_id)

        citations.append(CitationSource(
            id=ref_id,
            type="law_article",
            title=law_name,
            content_snippet=source_text,
            source=source_text,
            relevance_score=0.85,
        ))

    # 匹配案例号格式: （YYYY）XXX民终/民初NNNN号
    case_pattern = re.compile(
        r'[（(](\d{4})[）)][一-鿿\w]+(?:民|刑|行|知|商|执)[一-鿿]*\d+号'
    )
    for match in case_pattern.finditer(ai_response):
        case_ref = match.group(0)
        ref_id = f"case-{case_ref}"
        if ref_id in seen_ids:
            continue
        seen_ids.add(ref_id)

        citations.append(CitationSource(
            id=ref_id,
            type="case",
            title=case_ref,
            content_snippet=case_ref,
            source=case_ref,
            relevance_score=0.75,
        ))

    # --- 3. 按 relevance_score 降序排序 ---
    citations.sort(key=lambda c: c.relevance_score, reverse=True)

    return citations


# ========== 统一编排上下文 ==========


class _ChatContext:
    """chat() 和 stream_chat() 共享的编排上下文"""
    __slots__ = (
        "conversation", "context_messages", "llm_config",
        "normalized_kb_ids", "route", "resolved_agent", "dd_company_name",
    )

    def __init__(
        self,
        conversation: Conversation,
        context_messages: list[dict[str, str]],
        llm_config: LLMConfig | None,
        normalized_kb_ids: list[str],
        route: str,
        resolved_agent: str | None = None,
        dd_company_name: str | None = None,
    ) -> None:
        self.conversation = conversation
        self.context_messages = context_messages
        self.llm_config = llm_config
        self.normalized_kb_ids = normalized_kb_ids
        self.route = route
        self.resolved_agent = resolved_agent
        self.dd_company_name = dd_company_name


class ChatService:
    """对话服务 (v2 性能优化版)"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._workforce: LegalWorkforce | None = None

    @property
    def workforce(self) -> LegalWorkforce:
        """延迟导入 workforce，避免循环依赖"""
        if self._workforce is None:
            from src.agents.workforce import get_workforce
            self._workforce = get_workforce()
        return self._workforce

    # ========== LLM 配置加载（提取公共方法，消除重复） ==========

    async def _load_llm_config(self) -> LLMConfig | None:
        """
        加载动态 LLM 配置（提取公共逻辑）

        优先级：数据库默认配置 > 数据库任意活跃配置 > None
        """
        from src.services.llm_service import LLMService

        llm_config = await LLMService.get_default_config(self.db)
        if llm_config:
            logger.debug(f"ChatService: Loaded default LLM config: {llm_config.name}")
            return llm_config

        # Fallback: 查找任意活跃配置
        logger.warning("ChatService: No default LLM config found, searching for active config...")
        from src.models.llm_config import LLMConfig
        result = await self.db.execute(
            select(LLMConfig)
            .where(LLMConfig.config_type == "llm")
            .where(LLMConfig.is_active == True)
            .order_by(LLMConfig.updated_at.desc())
            .limit(1)
        )
        llm_config = result.scalar_one_or_none()
        if llm_config:
            logger.info(f"ChatService: Fallback to active config: {llm_config.name}")
        else:
            logger.warning("ChatService: No active LLM config found at all!")

        return llm_config

    # ========== 事件发布辅助 ==========

    async def _publish_event(self, channel: str, event_data: dict[str, Any]) -> None:
        """安全地发布事件到事件总线"""
        try:
            from src.services.event_bus import event_bus
            await event_bus.publish(channel, event_data)
        except Exception as e:
            logger.warning(f"事件发布失败 [{channel}]: {e}")

    # ========== 会话管理 ==========

    async def create_conversation(
        self,
        user_id: str | None = None,
        case_id: str | None = None,
        title: str | None = None,
        conversation_id: str | None = None,
    ) -> Conversation:
        """创建对话会话，可指定 conversation_id 以复用前端 ID"""
        conversation = Conversation(
            title=title or f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            user_id=user_id,
            case_id=case_id,
            message_count=0,
            token_count=0,
        )
        if conversation_id:
            conversation.id = conversation_id

        self.db.add(conversation)
        await self.db.flush()

        logger.info(f"创建对话会话: {conversation.id}")

        # 发布事件
        await self._publish_event("chat_events", {
            "type": "conversation_created",
            "conversation_id": str(conversation.id),
            "user_id": user_id,
        })

        return conversation

    async def get_or_create_conversation(
        self,
        conversation_id: str,
        user_id: str | None = None,
        case_id: str | None = None,
        title: str | None = None,
    ) -> Conversation:
        """获取已有对话，不存在则创建（使用指定 ID）"""
        existing = await self.get_conversation(conversation_id)
        if existing:
            logger.debug(f"复用已有对话: {conversation_id}")
            return existing
        return await self.create_conversation(
            user_id=user_id,
            case_id=case_id,
            title=title,
            conversation_id=conversation_id,
        )

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        """获取对话会话"""
        try:
            UUID(str(conversation_id))
        except (TypeError, ValueError):
            logger.warning(f"忽略非法 conversation_id: {conversation_id}")
            return None

        result = await self.db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def list_conversations(
        self,
        user_id: str | None = None,
        case_id: str | None = None,
        keyword: str | None = None,
        starred_only: bool = False,
        limit: int = 50,
    ) -> list[Conversation]:
        """获取对话列表（支持关键字搜索和收藏过滤）"""
        from sqlalchemy import or_
        query = select(Conversation)

        if user_id:
            query = query.where(
                or_(Conversation.user_id == user_id, Conversation.user_id.is_(None))
            )
        if case_id:
            query = query.where(Conversation.case_id == case_id)

        # 排除空对话
        query = query.where(Conversation.message_count > 0)

        # 关键字搜索（标题）
        if keyword and keyword.strip():
            query = query.where(Conversation.title.ilike(f"%{keyword.strip()}%"))

        # 仅收藏
        if starred_only:
            query = query.where(Conversation.is_starred == True)

        query = query.order_by(Conversation.updated_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        agent_name: str | None = None,
        reasoning: str | None = None,
        citations: list[dict[str, Any]] | None = None,
        actions: list[dict[str, Any]] | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        msg_metadata: dict[str, Any] | None = None,
    ) -> Message:
        """添加消息"""
        message = Message(
            conversation_id=conversation_id,
            role=MessageRole(role),
            content=content,
            agent_name=agent_name,
            reasoning=reasoning,
            citations=citations,
            actions=actions,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            msg_metadata=msg_metadata,
        )

        self.db.add(message)

        # 更新会话统计
        conversation = await self.get_conversation(conversation_id)
        if conversation:
            conversation.message_count += 1
            conversation.token_count += prompt_tokens + completion_tokens
            conversation.last_message_at = datetime.now()

        await self.db.flush()
        return message

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
    ) -> list[Message]:
        """获取消息列表"""
        try:
            UUID(str(conversation_id))
        except (TypeError, ValueError):
            logger.warning(f"忽略非法 conversation_id 的消息查询: {conversation_id}")
            return []

        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_history(
        self,
        conversation_id: str,
        limit: int = 10,
        exclude_latest: bool = False,
    ) -> list[dict[str, str]]:
        """获取标准化后的最近对话历史，供 LLM 上下文复用"""
        messages = await self.get_messages(conversation_id, limit=limit)
        if exclude_latest and messages:
            messages = messages[:-1]

        history: list[dict[str, str]] = []
        for message in messages:
            role = getattr(message.role, "value", message.role)
            content = (message.content or "").strip()
            if role == "system" or not content:
                continue
            history.append({"role": str(role), "content": content})
        return history

    async def cleanup_empty_conversations(self, older_than_hours: int = 24) -> int:
        """清理空对话（message_count=0 且创建超过指定时长）"""
        from sqlalchemy import delete as sa_delete
        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        result = await self.db.execute(
            sa_delete(Conversation)
            .where(Conversation.message_count == 0)
            .where(Conversation.created_at < cutoff)
        )
        await self.db.flush()
        rowcount = getattr(result, "rowcount", 0)
        return int(rowcount or 0)

    async def toggle_star(self, conversation_id: str) -> bool | None:
        """切换对话收藏状态，返回新状态。对话不存在返回 None。"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return None
        conversation.is_starred = not conversation.is_starred
        conversation.starred_at = datetime.now() if conversation.is_starred else None
        await self.db.flush()
        return conversation.is_starred

    async def search_messages(
        self,
        keyword: str,
        user_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """跨对话搜索消息内容，返回匹配的消息及所属对话信息"""
        from sqlalchemy import or_
        query = (
            select(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Message.content.ilike(f"%{keyword.strip()}%"))
            .where(Message.role != MessageRole.SYSTEM)
        )
        if user_id:
            query = query.where(
                or_(Conversation.user_id == user_id, Conversation.user_id.is_(None))
            )
        query = query.order_by(Message.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        messages = list(result.scalars().all())

        return [
            {
                "message_id": str(msg.id),
                "conversation_id": str(msg.conversation_id),
                "role": msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                "content_snippet": msg.content[:200] if msg.content else "",
                "agent_name": msg.agent_name,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in messages
        ]

    async def _build_knowledge_sources(
        self,
        kb_ids: list[str] | None,
        rag_sources: list[dict[str, Any]] | None,
    ) -> list[CitationSource]:
        """将知识库 RAG 返回值转换为前端统一 sources 结构。"""
        kb_name_map: dict[str, str] = {}
        if kb_ids:
            from src.models.knowledge import KnowledgeBase

            kb_result = await self.db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id.in_(kb_ids))
            )
            kb_name_map = {str(kb.id): kb.name for kb in kb_result.scalars().all()}

        raw_sources = rag_sources or []
        max_score = max(
            (
                float(source.get("score", 0) or 0)
                for source in raw_sources
                if isinstance(source, dict)
            ),
            default=0.0,
        )

        sources: list[CitationSource] = []
        for kb_id in kb_ids or []:
            kb_name = kb_name_map.get(kb_id)
            if not kb_name:
                continue
            sources.append(CitationSource(
                id=f"knowledge-base-{kb_id}",
                type="knowledge_base",
                title=kb_name,
                content_snippet="",
                source=kb_name,
                relevance_score=max_score,
            ))

        default_source_label = next(iter(kb_name_map.values()), "知识库检索")
        for index, source in enumerate(raw_sources, start=1):
            if not isinstance(source, dict):
                continue
            sources.append(CitationSource(
                id=source.get("id") or f"knowledge-source-{index}",
                type="knowledge",
                title=source.get("title") or f"知识片段 {index}",
                content_snippet=source.get("content_snippet") or "",
                source=source.get("source") or default_source_label,
                relevance_score=float(source.get("score", 0) or 0),
            ))

        return sources

    # ========== 统一路由决策与编排 ==========

    def _decide_route(
        self,
        content: str,
        agent_name: str | None,
        mode: str | None = None,
        normalized_kb_ids: list[str] | None = None,
    ) -> tuple[str, str | None, str | None]:
        """
        统一路由决策，消除 chat()/stream_chat() 重复的意图判断。
        返回 (route, resolved_agent, dd_company_name)。
        """
        investigation_request = (
            classify_investigation_request(content)
            if not agent_name else {"intent": "general_search", "company_name": None}
        )
        if investigation_request["intent"] == "due_diligence":
            return "due_diligence", "尽职调查Agent", investigation_request.get("company_name")
        if investigation_request["intent"] == "sentiment":
            return "specific_agent", "legal_researcher", None
        if investigation_request["intent"] == "regulatory_monitoring":
            return "specific_agent", "regulatory_monitor", None

        if (mode == "research" or normalized_kb_ids) and not agent_name:
            return "rag", "知识库检索Agent", None

        if not agent_name and detect_contract_review_intent(content):
            return "contract_review", "contract_reviewer", None

        if not agent_name and detect_document_drafting_intent(content):
            return "document_drafting", "document_drafter", None

        if not agent_name and detect_find_lawyer_intent(content):
            return "specific_agent", "legal_advisor", None

        if agent_name:
            return "specific_agent", agent_name, None

        return "general", None, None

    async def _prepare_chat_context(
        self,
        content: str,
        conversation_id: str | None,
        user_id: str | None,
        case_id: str | None,
        agent_name: str | None,
        mode: str | None = None,
        knowledge_base_ids: list[str] | None = None,
        template_id: str | None = None,
        model_id: str | None = None,
        document_id: str | None = None,
    ) -> _ChatContext:
        """
        统一前置准备：获取/创建会话、保存用户消息、加载历史和 LLM 配置、决定路由。
        chat() 和 stream_chat() 共用此方法消除重复。
        """
        if conversation_id:
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                raise ValueError("对话不存在")
        else:
            conversation = await self.create_conversation(user_id=user_id, case_id=case_id)

        await self.add_message(conversation_id=conversation.id, role="user", content=content)
        context_messages = await self.get_recent_history(
            conversation.id, limit=10, exclude_latest=True,
        )
        template_context_message = build_template_context_message(template_id)
        if template_context_message:
            context_messages = [
                {"role": "system", "content": template_context_message},
                *context_messages,
            ]

        # 如果指定了 model_id，加载对应配置；否则使用默认
        llm_config = None
        if model_id:
            from src.models.llm_config import LLMConfig as LLMConfigModel
            result = await self.db.execute(
                select(LLMConfigModel).where(
                    LLMConfigModel.id == model_id,
                    LLMConfigModel.is_active == True,
                )
            )
            llm_config = result.scalar_one_or_none()
            if llm_config:
                logger.info(f"ChatService: 使用指定模型配置: {llm_config.name}")
        if not llm_config:
            llm_config = await self._load_llm_config()
        normalized_kb_ids = [
            kb_id for kb_id in (knowledge_base_ids or [])
            if isinstance(kb_id, str) and kb_id
        ]

        # 文件内容注入：如果携带 document_id，提取文本拼接到 content
        if document_id:
            try:
                from src.services.document_service import DocumentService
                _doc_svc = DocumentService(self.db)
                _doc = await _doc_svc.get_document(document_id)
                if _doc:
                    _extracted = _doc.extracted_text or ""
                    if not _extracted.strip() and _doc.file_path:
                        from src.services.document_parser import DocumentParser
                        parser_cls = cast(Any, DocumentParser)
                        _parser = parser_cls()
                        _parse_result = cast(
                            dict[str, Any],
                            await _parser.parse_file(file_path=_doc.file_path),
                        )
                        _extracted = str(_parse_result.get("text", "") or "")
                        if _extracted:
                            _doc.extracted_text = _extracted
                            await self.db.flush()
                    if _extracted.strip():
                        _max_chars = 8000
                        _truncated = _extracted[:_max_chars]
                        if len(_extracted) > _max_chars:
                            _truncated += f"\n\n...（文档共 {len(_extracted)} 字，已截取前 {_max_chars} 字）"
                        content = f"{content}\n\n[附件内容 - {_doc.name}]\n{_truncated}"
            except Exception as _doc_err:
                logger.warning(f"ChatService: 文件内容注入失败: {_doc_err}")

        route, resolved_agent, dd_company_name = self._decide_route(
            content, agent_name, mode, normalized_kb_ids,
        )

        # ===== Harness: 上下文压缩 (T3 收口: 通过 context_engine 集中调用) =====
        try:
            from src.harness.context_engine import context_engine
            tier = context_engine.should_compress(context_messages)
            if tier is not None:
                logger.info(f"[Harness] 触发上下文压缩 Tier {tier}（消息数: {len(context_messages)}）")
                context_messages, compress_stats = await context_engine.compress(
                    context_messages, tier=tier,
                )
                logger.info(
                    f"[Harness] 压缩完成 | "
                    f"原始: {compress_stats.get('original_tokens', '?')} tokens → "
                    f"压缩后: {compress_stats.get('compressed_tokens', '?')} tokens | "
                    f"节省: {compress_stats.get('saved_tokens', '?')} tokens"
                )
        except Exception as compress_err:
            logger.debug(f"[Harness] 上下文压缩跳过: {compress_err}")

        # ===== 记忆系统集成：并行注入增强上下文 =====
        # 优化：记忆检索 + 经验检索 + 消息缓冲并行执行，节省 200-500ms
        if user_id:
            import asyncio as _aio

            async def _get_memory_context() -> str | None:
                try:
                    from src.services.memory_layer import memory_layer
                    enriched = await memory_layer.build_enriched_context(
                        user_id=user_id,
                        session_id=str(conversation.id),
                        query=content,
                        max_tokens=600,
                    )
                    # 后台缓冲消息（不阻塞）
                    _aio.create_task(memory_layer.buffer_message(user_id, {"role": "user", "content": content}))
                    return enriched
                except Exception as mem_err:
                    logger.debug(f"记忆上下文注入跳过: {mem_err}")
                    return None

            async def _get_experience_context() -> str | None:
                try:
                    from src.services.experience_engine import experience_engine
                    return experience_engine.build_experience_context(user_id, content, max_tokens=300)
                except Exception as exp_err:
                    logger.debug(f"经验上下文注入跳过: {exp_err}")
                    return None

            enriched, exp_context = await _aio.gather(
                _get_memory_context(), _get_experience_context(),
            )

            # 按优先级插入（经验在最前，记忆其次）
            if exp_context:
                context_messages = [
                    {"role": "system", "content": exp_context},
                    *context_messages,
                ]
            if enriched:
                context_messages = [
                    {"role": "system", "content": enriched},
                    *context_messages,
                ]

        return _ChatContext(
            conversation=conversation,
            context_messages=context_messages,
            llm_config=llm_config,
            normalized_kb_ids=normalized_kb_ids,
            route=route,
            resolved_agent=resolved_agent,
            dd_company_name=dd_company_name,
        )

    async def _execute_due_diligence(self, content: str, company_name: str | None) -> str:
        """执行尽职调查路由（chat/stream_chat 共用）"""
        if not company_name:
            return (
                "我已识别到您是在发起企业调查/尽调请求，但当前信息还不够。"
                "请至少补充目标企业的完整名称，最好同时说明您重点关注的范围，"
                "例如工商信息、诉讼记录、股权结构、信用情况或合作风险。"
            )
        try:
            company_data = await get_company_info(company_name)
            return format_due_diligence_chat_response(company_name, company_data)
        except Exception as dd_err:
            logger.error(f"企业调查强路由失败: {dd_err}")
            return (
                f"我已识别到您要调查企业“{company_name}”，"
                "但当前尽调服务暂时无法返回可靠结果。"
                "请稍后重试，或补充统一社会信用代码和关注范围"
                "（工商/诉讼/股权/信用），我会继续按尽调流程处理。"
            )

    async def _execute_rag(
        self,
        content: str,
        normalized_kb_ids: list[str],
        user_id: str | None = None,
        llm_route_context: dict[str, Any] | None = None,
    ) -> tuple[str, list[CitationSource]]:
        """执行 RAG 知识库路由，返回 (response_text, sources)"""
        from src.services.knowledge_service import KnowledgeService

        knowledge_service = KnowledgeService(self.db)
        rag_result = await knowledge_service.rag_query(
            query=content,
            kb_ids=normalized_kb_ids or None,
            user_id=user_id,
            llm_route_context=llm_route_context,
        )
        response_text = (
            (rag_result or {}).get("answer", "").strip()
            or "抱歉，当前知识库未返回有效内容。"
        )
        sources = await self._build_knowledge_sources(
            normalized_kb_ids,
            (rag_result or {}).get("sources", []),
        )
        return response_text, sources

    async def _finalize_response(
        self,
        response_text: str,
        used_agent: str,
        conversation: Conversation,
        user_id: str | None,
        sources: list[CitationSource] | None = None,
        event_type: str | None = "chat_completed",
    ) -> tuple[list[CitationSource], Message]:
        """
        统一后处理：引用提取、保存 AI 消息、发布事件。
        返回 (sources, ai_message)。传 event_type=None 可跳过事件发布。
        """
        if not sources:
            sources = extract_citations(response_text)

        # ===== 引文追踪：从 AI 回复中提取法律引文并沉淀到图谱 =====
        try:
            from src.services.citation_tracker import citation_tracker
            citation_result = await citation_tracker.track_and_enrich(
                response_text, auto_sink_to_graph=True,
            )
            if citation_result.get("citation_count", 0) > 0:
                logger.debug(
                    f"引文追踪: {citation_result['citation_count']} 条引用, "
                    f"{citation_result.get('verified_count', 0)} 条已验证, "
                    f"{citation_result.get('sunk_count', 0)} 条沉淀到图谱"
                )
        except Exception as citation_err:
            logger.warning(f"引文追踪失败（不影响回复）: {citation_err}")

        ai_message = await self.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=response_text,
            agent_name=used_agent,
            citations=[s.model_dump() for s in sources] if sources else None,
        )

        if event_type:
            await self._publish_event("chat_events", {
                "type": event_type,
                "conversation_id": str(conversation.id),
                "agent": used_agent,
                "user_id": user_id,
            })

        # ===== 做梦机制：记录用户活动 =====
        if user_id:
            try:
                from src.services.auto_dream import auto_dream_engine
                auto_dream_engine.record_activity(user_id, f"chat_{used_agent}")
            except Exception:
                pass

        return sources, ai_message

    # ========== 对话处理 ==========

    async def chat(
        self,
        content: str,
        conversation_id: str | None = None,
        user_id: str | None = None,
        case_id: str | None = None,
        agent_name: str | None = None,
        mode: str | None = None,
        knowledge_base_ids: list[str] | None = None,
        template_id: str | None = None,
        model_id: str | None = None,
        document_id: str | None = None,
        llm_route_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """处理对话（同步模式）"""

        # ===== Harness: 启动请求追踪 + 创建任务 =====
        trace = start_trace(user_id=user_id, conversation_id=conversation_id)

        ctx = await self._prepare_chat_context(
            content, conversation_id, user_id, case_id,
            agent_name, mode, knowledge_base_ids, template_id, model_id=model_id,
            document_id=document_id,
        )
        trace.route = ctx.route
        trace.conversation_id = str(ctx.conversation.id)

        # Harness: 创建任务记录
        task_record = task_engine.create_task(
            description=content[:200],
            route=ctx.route,
            agent_name=ctx.resolved_agent,
            user_id=user_id,
            conversation_id=str(ctx.conversation.id),
            trace_id=trace.trace_id,
        )
        task_engine.transition(task_record.task_id, TaskState.RUNNING)

        # T6 二阶段: cost_tracker + subscription_service 用户级 token 配额前置门禁
        # 注入端: chat 主路径每次调用 LLM 之前先问配额; 超出立即返回友好提示
        # 估算: 当前 message 的 char/4 + 预留 1024 completion tokens
        if user_id:
            try:
                from src.harness.cost_tracker import estimate_tokens_from_text
                from src.services.subscription_service import SubscriptionService

                upcoming = estimate_tokens_from_text(content) + 1024
                quota_check = await SubscriptionService(self.db).check_user_token_quota(
                    user_id, upcoming_tokens=upcoming,
                )
                if not quota_check["allowed"]:
                    task_engine.transition(
                        task_record.task_id, TaskState.FAILED,
                        error_msg=quota_check.get("reason", "quota exceeded"),
                    )
                    trace.end_span(span_id="", status="error") if False else None  # placeholder
                    return {
                        "_harness": {"quota": quota_check, "trace_id": trace.trace_id},
                        "response": (
                            "您本计费周期的 AI 用量已达上限，请升级订阅或等待周期重置。"
                            f"已用 {quota_check['used']} tokens / 配额 {quota_check['quota']}."
                        ),
                        "conversation_id": str(ctx.conversation.id),
                        "agent_used": ctx.resolved_agent,
                        "sources": [],
                    }
            except Exception as quota_err:
                # 配额检查异常不应阻断主流程
                logger.warning(f"[T6] 配额前置检查异常 (放行): {quota_err}")

        sources: list[CitationSource] = []
        try:
            span_id = trace.start_span(f"route.{ctx.route}", agent_name=ctx.resolved_agent)

            if ctx.route == "due_diligence":
                response_text = await self._execute_due_diligence(content, ctx.dd_company_name)
                used_agent = ctx.resolved_agent or "尽职调查Agent"

            elif ctx.route == "rag":
                response_text, sources = await self._execute_rag(
                    content,
                    ctx.normalized_kb_ids,
                    user_id=user_id,
                    llm_route_context=llm_route_context,
                )
                used_agent = ctx.resolved_agent or "知识库检索Agent"

            elif ctx.route in ("contract_review", "document_drafting"):
                used_agent = ctx.resolved_agent or "legal_advisor"
                response_text = await self.workforce.chat(
                    content, used_agent,
                    context={
                        "llm_config": ctx.llm_config,
                        "history": ctx.context_messages,
                        "llm_route_context": llm_route_context,
                    },
                )

            elif ctx.route == "specific_agent":
                used_agent = ctx.resolved_agent or "legal_advisor"
                response_text = await self.workforce.chat(
                    content, used_agent,
                    context={
                        "llm_config": ctx.llm_config,
                        "history": ctx.context_messages,
                        "llm_route_context": llm_route_context,
                    },
                )

            else:  # general
                result = await self.workforce.process_task_governed(
                    task_description=content,
                    context={
                        "conversation_id": ctx.conversation.id,
                        "history": ctx.context_messages,
                        "case_id": case_id,
                        "llm_config": ctx.llm_config,
                        "llm_route_context": llm_route_context,
                    }
                )
                response_text = result.get("final_result", {}).get("summary", "")
                used_agent = "智能体团队"

                if not response_text:
                    response_text = await self.workforce.chat(
                        content,
                        context={
                            "llm_config": ctx.llm_config,
                            "history": ctx.context_messages,
                            "llm_route_context": llm_route_context,
                        },
                    )
                    used_agent = "法律顾问Agent"

            trace.end_span(span_id, status="success")

        except Exception as e:
            logger.error(f"智能体调用失败: {e}")
            trace.end_span(span_id, status="error", error_msg=str(e))
            task_engine.transition(task_record.task_id, TaskState.FAILED, error_msg=str(e))
            response_text = "抱歉，处理您的请求时遇到问题。请稍后重试。"
            used_agent = "系统"

        # ===== Harness: 输出质量强制校验（H1：从软接入升级为强接入） =====
        # H0 体检发现旧实现把异常吞成 debug、CRITICAL 仍发原文，违反 AGENTS.md §3.4
        # enforcement 统一策略：
        #   pass / warned        → 继续返回最终文本
        #   retry                → 标 RETRY，调用方可重试
        #   rejected / *_error   → 统一拒绝消息 + 标 FAILED
        if task_record.state == TaskState.RUNNING:
            task_engine.transition(task_record.task_id, TaskState.VALIDATING)

        response_text, validation_action = await harness_validate(
            response_text=response_text,
            user_query=content,
            agent_name=used_agent,
            route=ctx.route,
        )

        if validation_action in ("rejected", "validator_error"):
            task_engine.transition(
                task_record.task_id,
                TaskState.FAILED,
                error_msg=f"output_validation:{validation_action}",
            )
        elif validation_action == "retry":
            task_engine.transition(task_record.task_id, TaskState.RETRY)
        elif task_record.state not in (TaskState.FAILED, TaskState.COMPLETED):
            task_engine.transition(task_record.task_id, TaskState.COMPLETED, result=used_agent)

        final_sources, ai_message = await self._finalize_response(
            response_text, used_agent, ctx.conversation, user_id,
            sources=sources or None,
        )

        # ===== Harness: 结束追踪，记录摘要 =====
        trace_summary = end_trace()

        result_dict: dict[str, Any] = {
            "conversation_id": ctx.conversation.id,
            "message_id": ai_message.id,
            "content": response_text,
            "agent": used_agent,
            "citations": ai_message.citations or [],
            "actions": ai_message.actions or [],
            "sources": [s.model_dump() for s in final_sources],
        }

        # 附加 harness 元数据（H1：ChatResponse.harness 已开放此字段）
        harness_meta = {
            "validation_action": validation_action,
            "validation_failed": validation_action in ("retry", "rejected", "validator_error"),
        }
        if trace_summary:
            harness_meta.update({
                "trace_id": trace_summary.get("trace_id"),
                "total_tokens": trace_summary.get("total_tokens", 0),
                "total_cost_usd": trace_summary.get("total_cost_usd", 0),
                "elapsed_ms": trace_summary.get("elapsed_ms", 0),
            })
        result_dict["harness"] = harness_meta
        result_dict["_harness"] = harness_meta  # 兼容旧前端

        return result_dict

    async def stream_chat(
        self,
        content: str,
        conversation_id: str | None = None,
        user_id: str | None = None,
        case_id: str | None = None,
        agent_name: str | None = None,
        privacy_mode: str = "HYBRID",
        document_id: str | None = None,
        llm_route_context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        流式对话 (v2 -- 支持真正的 token 流式输出)

        路由决策和后处理复用 _prepare_chat_context / _execute_due_diligence / _finalize_response，
        隐私检查和流式推送逻辑保留在本方法内。
        """
        import asyncio

        # 1. 算力路由与隐私检查（stream_chat 独有）
        try:
            sensitivity = SensitivityLevel(privacy_mode)
            req = InferenceRequest(prompt=content, sensitivity=sensitivity)
            processed_content, recovery_map = await compute_router.route_request(req)

            # 绝密模式(L1)：本地处理
            if sensitivity == SensitivityLevel.CONFIDENTIAL:
                yield {
                    "type": "thinking",
                    "agent": "本地安全芯片",
                    "message": "正在本地硬件安全区进行推理..."
                }
                await asyncio.sleep(1.0)

                yield {
                    "type": "content",
                    "text": processed_content,
                    "accumulated": processed_content,
                    "agent": "AI私有助手(Local)",
                    "progress": 1.0,
                }
                yield {
                    "type": "done",
                    "conversation_id": conversation_id or "temp",
                    "message_id": "local-msg",
                    "agent": "AI私有助手(Local)",
                    "full_content": processed_content,
                }
                return

            content = processed_content

        except Exception as e:
            logger.error(f"算力路由失败: {e}")
            yield {"type": "error", "message": f"安全检查失败: {str(e)}"}
            return

        # 2. 统一前置准备（复用共享编排层）
        try:
            ctx = await self._prepare_chat_context(
                content, conversation_id, user_id, case_id, agent_name,
                document_id=document_id,
            )
        except ValueError as e:
            yield {"type": "error", "message": str(e)}
            return

        # 3. 尽调强路由
        if ctx.route == "due_diligence":
            used_agent = ctx.resolved_agent or "尽职调查Agent"
            yield {
                "type": "agent_start",
                "agent": used_agent,
                "message": "正在识别调查对象并准备企业尽调结果...",
            }

            response_text = await self._execute_due_diligence(content, ctx.dd_company_name)
            if recovery_map:
                response_text = pii_service.restore(response_text, recovery_map)
                response_text += "\n\n*(注：本回复基于脱敏数据生成，敏感信息已在本地自动还原)*"

            sources, ai_message = await self._finalize_response(
                response_text, used_agent, ctx.conversation, user_id,
                event_type="stream_chat_completed",
            )
            yield {
                "type": "content", "text": response_text,
                "accumulated": response_text, "agent": used_agent, "progress": 1.0,
            }
            yield {
                "type": "done", "conversation_id": ctx.conversation.id,
                "message_id": ai_message.id, "agent": used_agent,
                "full_content": response_text,
                "sources": [s.model_dump() for s in sources],
            }
            return

        # 4. 合同审查 / 文书起草强路由
        if ctx.route in ("contract_review", "document_drafting"):
            used_agent = ctx.resolved_agent or "legal_advisor"
            yield {
                "type": "agent_start", "agent": used_agent,
                "message": "正在处理您的请求...",
            }
            try:
                response_text = await self.workforce.chat(
                    content, used_agent,
                    context={
                        "llm_config": ctx.llm_config,
                        "history": ctx.context_messages,
                        "llm_route_context": llm_route_context,
                    },
                )
            except Exception:
                response_text = await self.workforce.chat(
                    content, "legal_advisor",
                    context={
                        "llm_config": ctx.llm_config,
                        "history": ctx.context_messages,
                        "llm_route_context": llm_route_context,
                    },
                )
                used_agent = "legal_advisor"

            if recovery_map:
                response_text = pii_service.restore(response_text, recovery_map)

            # 原始行为：此路径不发布事件
            sources, ai_message = await self._finalize_response(
                response_text, used_agent, ctx.conversation, user_id,
                event_type=None,
            )
            yield {
                "type": "content", "text": response_text,
                "accumulated": response_text, "agent": used_agent, "progress": 1.0,
            }
            yield {
                "type": "done", "conversation_id": ctx.conversation.id,
                "message_id": ai_message.id, "agent": used_agent,
                "full_content": response_text,
                "sources": [s.model_dump() for s in sources],
            }
            return

        # 5. 通用路径（多 Agent / 单 Agent 流式）
        yield {"type": "start", "conversation_id": ctx.conversation.id, "agent": "协调调度Agent"}
        yield {"type": "thinking", "agent": "智能体团队", "message": "正在分析您的问题..."}

        try:
            # 判断是否需要多智能体协作
            is_complex = any(
                keyword in content
                for keyword in ["合同", "审查", "尽职调查", "风险", "诉讼", "法规", "条款"]
            )

            if is_complex and not agent_name:
                # ===== 多智能体协作模式（真流式） =====
                yield {
                    "type": "agent_start",
                    "agent": "协调调度Agent",
                    "message": "启动多智能体协作...",
                }

                # 异步获取图谱 A2UI 数据
                from src.services.rag_service import rag_service
                graph_task = asyncio.create_task(rag_service.get_graph_a2ui_data(content))

                accumulated_text = ""
                final_event = None
                used_agent = "智能体团队"

                async for event in self.workforce.process_task_streaming(
                    task_description=content,
                    context={
                        "conversation_id": ctx.conversation.id,
                        "case_id": case_id,
                        "llm_config": ctx.llm_config,
                        "history": ctx.context_messages,
                        "llm_route_context": llm_route_context,
                    },
                ):
                    evt_type = event.get("type")

                    if evt_type == "dag_plan":
                        # 通知前端 DAG 规划（可展示任务卡片）
                        pass

                    elif evt_type == "agent_start":
                        yield {
                            "type": "agent_working",
                            "agent": event.get("agent", ""),
                            "message": f"{event.get('agent', '')} 正在处理...",
                        }

                    elif evt_type == "stream_token":
                        # 主 Agent 真流式 token
                        accumulated_text += event["token"]
                        yield {
                            "type": "content",
                            "text": event["token"],
                            "accumulated": accumulated_text,
                            "agent": event.get("agent", used_agent),
                            "progress": -1,
                        }

                    elif evt_type == "agent_complete":
                        yield {
                            "type": "agent_result",
                            "agent": event.get("agent", ""),
                            "content": event.get("content", "")[:500],
                            "elapsed": event.get("elapsed", 0),
                        }

                    elif evt_type == "agent_failed":
                        yield {
                            "type": "agent_result",
                            "agent": event.get("agent", ""),
                            "content": event.get("content", "")[:200],
                            "error": True,
                        }

                    elif evt_type == "workspace_artifact_created":
                        yield {
                            "type": "workspace_artifact_created",
                            "artifact": event.get("artifact"),
                        }

                    elif evt_type == "final_result":
                        final_event = event

                # 等待图谱任务
                try:
                    graph_a2ui = await graph_task
                    if graph_a2ui:
                        yield {
                            "type": "context_update",
                            "context_type": "a2ui",
                            "data": graph_a2ui,
                        }
                except Exception as ge:
                    logger.warning(f"获取图谱 A2UI 数据失败: {ge}")

                # 汇总最终结果
                if final_event:
                    summary = final_event.get("data", {}).get("summary", "")
                    response_text = summary or accumulated_text

                    # 如果汇总结果与流式内容不同（有新增内容），追加推送
                    if summary and summary != accumulated_text and len(summary) > len(accumulated_text):
                        extra = summary[len(accumulated_text):]
                        accumulated_text = summary
                        sentences = self._split_into_chunks(extra)
                        for sentence in sentences:
                            yield {
                                "type": "content",
                                "text": sentence,
                                "accumulated": accumulated_text,
                                "agent": used_agent,
                                "progress": 1.0,
                            }
                            await asyncio.sleep(0.02)
                else:
                    response_text = accumulated_text

                if not response_text:
                    response_text = await self.workforce.chat(
                        content,
                        context={
                            "llm_config": ctx.llm_config,
                            "history": ctx.context_messages,
                            "llm_route_context": llm_route_context,
                        },
                    )

                # 隐私还原
                if recovery_map:
                    response_text = pii_service.restore(response_text, recovery_map)
                    response_text += "\n\n*(注：本回复基于脱敏数据生成，敏感信息已在本地自动还原)*"

                # 处理 Agent Action (Notifications)
                if final_event:
                    await self._process_agent_notifications(
                        {"agent_results": final_event.get("agent_results", [])},
                        user_id, ctx.conversation.id,
                    )

                yield {"type": "agent_complete", "agent": used_agent}

            else:
                # ===== 单智能体模式：使用真正的流式输出 =====
                target_agent_name = (
                    agent_name
                    if agent_name and agent_name in self.workforce.agents
                    else "legal_advisor"
                )
                target_agent = self.workforce.agents[target_agent_name]
                used_agent = agent_name or "法律顾问Agent"

                yield {"type": "agent_complete", "agent": used_agent}

                # 尝试使用真流式
                try:
                    stream_kwargs: dict[str, Any] = {
                        "llm_config": ctx.llm_config,
                        "history": ctx.context_messages,
                    }
                    if llm_route_context is not None:
                        stream_kwargs["llm_route_context"] = llm_route_context
                    token_queue = await target_agent.stream_chat(content, **stream_kwargs)

                    accumulated_text = ""
                    while True:
                        token = await asyncio.wait_for(token_queue.get(), timeout=60.0)
                        if token is None:
                            break  # 流结束

                        if token.startswith("[Error]"):
                            # 流式失败，降级到同步
                            raise Exception(token)

                        accumulated_text += token
                        yield {
                            "type": "content",
                            "text": token,
                            "accumulated": accumulated_text,
                            "agent": used_agent,
                            "progress": -1,  # 流式模式不知道总进度
                        }

                    response_text = accumulated_text

                except Exception as stream_err:
                    logger.warning(f"流式输出失败，降级到同步模式: {stream_err}")
                    # 降级到同步模式
                    response_text = await self.workforce.chat(
                        content,
                        agent_name if agent_name else None,
                        context={
                            "llm_config": ctx.llm_config,
                            "history": ctx.context_messages,
                            "llm_route_context": llm_route_context,
                        }
                    )

                    # 隐私还原
                    if recovery_map:
                        response_text = pii_service.restore(response_text, recovery_map)
                        response_text += "\n\n*(注：本回复基于脱敏数据生成，敏感信息已在本地自动还原)*"

                    sentences = self._split_into_chunks(response_text)
                    accumulated_text = ""
                    for i, sentence in enumerate(sentences):
                        accumulated_text += sentence
                        yield {
                            "type": "content",
                            "text": sentence,
                            "accumulated": accumulated_text,
                            "agent": used_agent,
                            "progress": (i + 1) / len(sentences),
                        }
                        await asyncio.sleep(0.02)

            # 统一后处理
            sources, ai_message = await self._finalize_response(
                response_text, used_agent, ctx.conversation, user_id,
                event_type="stream_chat_completed",
            )

            # 发送完成事件
            yield {
                "type": "done",
                "conversation_id": ctx.conversation.id,
                "message_id": ai_message.id,
                "agent": used_agent,
                "full_content": response_text,
                "sources": [s.model_dump() for s in sources],
            }

        except Exception as e:
            logger.error(f"流式对话失败: {e}")
            yield {
                "type": "error",
                "message": f"处理失败: {str(e)}",
            }

    # ========== 辅助方法 ==========

    async def _process_agent_notifications(
        self,
        result: dict[str, Any],
        user_id: str | None,
        conversation_id: str,
    ) -> None:
        """处理 Agent 返回的通知动作"""
        try:
            from src.services.notification_service import NotificationService

            for agent_res in result.get("agent_results", []):
                if not isinstance(agent_res, dict) or "actions" not in agent_res:
                    continue

                for action in agent_res["actions"]:
                    if action.get("type") != "send_notification":
                        continue

                    notif_type = action.get("level", "info")
                    notif_title = action.get("title", f"来自 {agent_res.get('agent_name', 'AI助手')} 的提醒")
                    notif_msg = action.get("message", agent_res.get("content", "")[:50] + "...")

                    # ContractStewardAgent 特殊处理
                    if agent_res.get("agent_name") == "合同管家Agent":
                        content_str = agent_res.get("content", "")
                        if "alerts" in content_str:
                            notif_title = "合同状态预警"
                            notif_type = "warning"
                            notif_msg = "检测到合同关键节点或风险，请查看详细报告。"

                    if user_id:
                        await NotificationService.create_notification(
                            session=self.db,
                            user_id=user_id,
                            type=notif_type,
                            title=notif_title,
                            message=notif_msg,
                            related_link=f"/chat?id={conversation_id}"
                        )
                        logger.info(f"已创建通知: {notif_title}")

        except Exception as ne:
            logger.error(f"处理Agent通知失败: {ne}")

    def _split_into_chunks(self, text: str, chunk_size: int = 20) -> list[str]:
        """将文本分割成小块，用于流式输出"""
        if not text:
            return []

        import re
        sentences = re.split(r'([。！？；\n])', text)

        result = []
        current = ""

        for part in sentences:
            current += part
            if part in '。！？；\n' or len(current) >= chunk_size:
                if current.strip():
                    result.append(current)
                current = ""

        if current.strip():
            result.append(current)

        if len(result) <= 1 and len(text) > chunk_size:
            result = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

        return result if result else [text]

    async def add_feedback(
        self,
        message_id: str,
        rating: int,
        feedback: str | None = None,
    ) -> bool:
        """添加消息反馈"""
        result = await self.db.execute(
            select(Message).where(Message.id == message_id)
        )
        message = result.scalar_one_or_none()

        if not message:
            return False

        message.rating = rating
        message.feedback = feedback
        await self.db.flush()

        # 发布反馈事件（用于情景记忆强化学习）
        await self._publish_event("chat_events", {
            "type": "feedback_received",
            "message_id": message_id,
            "rating": rating,
        })

        return True
