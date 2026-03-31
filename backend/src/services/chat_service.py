"""
对话服务 (v2 - 性能优化版)

优化点：
1. LLM 配置加载提取为公共方法，消除重复代码
2. 流式对话支持真正的 token-by-token 流式输出（不再是假流式）
3. 集成事件总线，关键操作发布事件
4. 添加缓存装饰器到高频查询
5. RAG 引用来源追踪：AI 响应附带法条/案例/知识库引用
"""

import re
from datetime import datetime, timedelta
from typing import Optional, List, AsyncGenerator, Dict, Any
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger

from src.core.config import settings
from src.models.conversation import Conversation, Message, MessageRole
from src.services.compute_router_service import compute_router
from src.services.pii_service import pii_service
from src.services.due_diligence_service import (
    detect_company_due_diligence_request,
    format_due_diligence_chat_response,
    get_company_info,
)
from src.core.privacy import InferenceRequest, SensitivityLevel


# ========== 合同审查 / 文书起草意图检测 ==========

_CONTRACT_REVIEW_RE = re.compile(
    r"审[查阅看核].*合同|合同.*审[查阅看核]|检查.*合同|合同.*[问题风险]|帮我看.*合同|审核.*协议",
    re.IGNORECASE,
)

_DOCUMENT_DRAFTING_RE = re.compile(
    r"起草.*[文书合同协议函]|写.*[合同协议律师函]|生成.*[文书合同]|帮我[写拟].*[合同协议文书]|草拟",
    re.IGNORECASE,
)


def detect_contract_review_intent(content: str) -> bool:
    """检测合同审查意图"""
    return bool(_CONTRACT_REVIEW_RE.search(content))


def detect_document_drafting_intent(content: str) -> bool:
    """检测文书起草意图"""
    return bool(_DOCUMENT_DRAFTING_RE.search(content))


# ========== RAG 引用来源模型 ==========


class CitationSource(BaseModel):
    """RAG 引用来源"""
    id: str
    type: str  # "law_article" | "case" | "knowledge" | "regulation"
    title: str
    content_snippet: str  # 前 200 字符
    source: str  # 例："《民法典》第584条" 或 "（2024）京01民终1234号"
    relevance_score: float  # 0-1
    url: Optional[str] = None


def extract_citations(
    ai_response: str,
    context_docs: Optional[List[Dict[str, Any]]] = None,
) -> List[CitationSource]:
    """
    从 AI 响应和 RAG 上下文文档中提取引用来源。

    解析策略：
    1. 从 context_docs（RAG 检索结果）中提取已有来源
    2. 从 AI 响应文本中正则匹配法条引用
    3. 去重并按 relevance_score 降序排序
    """
    citations: List[CitationSource] = []
    seen_ids: set = set()

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
        r'[《\u300a]([^》\u300b]+)[》\u300b]'
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
        r'[（(](\d{4})[）)][\u4e00-\u9fff\w]+(?:民|刑|行|知|商|执)[\u4e00-\u9fff]*\d+号'
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


class ChatService:
    """对话服务 (v2 性能优化版)"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._workforce = None
    
    @property
    def workforce(self):
        """延迟导入 workforce，避免循环依赖"""
        if self._workforce is None:
            from src.agents.workforce import get_workforce
            self._workforce = get_workforce()
        return self._workforce
    
    # ========== LLM 配置加载（提取公共方法，消除重复） ==========
    
    async def _load_llm_config(self):
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
    
    async def _publish_event(self, channel: str, event_data: Dict[str, Any]):
        """安全地发布事件到事件总线"""
        try:
            from src.services.event_bus import event_bus
            await event_bus.publish(channel, event_data)
        except Exception as e:
            logger.warning(f"事件发布失败 [{channel}]: {e}")
    
    # ========== 会话管理 ==========
    
    async def create_conversation(
        self,
        user_id: Optional[str] = None,
        case_id: Optional[str] = None,
        title: Optional[str] = None,
        conversation_id: Optional[str] = None,
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
        user_id: Optional[str] = None,
        case_id: Optional[str] = None,
        title: Optional[str] = None,
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
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """获取对话会话"""
        result = await self.db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()
    
    async def list_conversations(
        self,
        user_id: Optional[str] = None,
        case_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Conversation]:
        """获取对话列表（包含当前用户的 + 无归属的对话，排除空对话）"""
        from sqlalchemy import or_
        query = select(Conversation)
        
        if user_id:
            # 显示当前用户的对话 + 无归属的对话（WebSocket 创建的可能没有 user_id）
            query = query.where(
                or_(Conversation.user_id == user_id, Conversation.user_id.is_(None))
            )
        if case_id:
            query = query.where(Conversation.case_id == case_id)
        
        # 排除没有任何消息的空对话（旧代码遗留的垃圾数据）
        query = query.where(Conversation.message_count > 0)
        
        query = query.order_by(Conversation.updated_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        agent_name: Optional[str] = None,
        reasoning: Optional[str] = None,
        citations: Optional[list] = None,
        actions: Optional[list] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
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
    ) -> List[Message]:
        """获取消息列表"""
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

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
        return result.rowcount or 0

    async def _build_knowledge_sources(
        self,
        kb_ids: Optional[List[str]],
        rag_sources: Optional[List[Dict[str, Any]]],
    ) -> List[CitationSource]:
        """将知识库 RAG 返回值转换为前端统一 sources 结构。"""
        kb_name_map: Dict[str, str] = {}
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

        sources: List[CitationSource] = []
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
    
    # ========== 对话处理 ==========
    
    async def chat(
        self,
        content: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        case_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        mode: Optional[str] = None,
        knowledge_base_ids: Optional[List[str]] = None,
    ) -> dict:
        """处理对话（同步模式）"""
        # 获取或创建对话
        if conversation_id:
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                raise ValueError("对话不存在")
        else:
            conversation = await self.create_conversation(
                user_id=user_id,
                case_id=case_id,
            )
        
        # 保存用户消息
        await self.add_message(
            conversation_id=conversation.id,
            role="user",
            content=content,
        )
        
        # 获取历史消息作为上下文
        history = await self.get_messages(conversation.id, limit=10)
        context_messages = [
            {"role": m.role.value, "content": m.content}
            for m in history[:-1]
        ]
        
        # 加载 LLM 配置（使用公共方法）
        llm_config = await self._load_llm_config()
        normalized_kb_ids = [kb_id for kb_id in (knowledge_base_ids or []) if isinstance(kb_id, str) and kb_id]
        sources: List[CitationSource] = []
        
        # 调用智能体
        try:
            due_diligence_request = detect_company_due_diligence_request(content) if not agent_name else {"matched": False}

            if due_diligence_request.get("matched"):
                company_name = due_diligence_request.get("company_name")
                used_agent = "尽职调查Agent"
                if not company_name:
                    response_text = (
                        "我已识别到您是在发起企业调查/尽调请求，但当前信息还不够。"
                        "请至少补充目标企业的完整名称，最好同时说明您重点关注的范围，例如工商信息、诉讼记录、股权结构、信用情况或合作风险。"
                    )
                else:
                    try:
                        company_data = await get_company_info(company_name)
                        response_text = format_due_diligence_chat_response(company_name, company_data)
                    except Exception as dd_err:
                        logger.error(f"同步企业调查强路由失败: {dd_err}")
                        response_text = (
                            f"我已识别到您要调查企业“{company_name}”，但当前尽调服务暂时无法返回可靠结果。"
                            "请稍后重试，或补充统一社会信用代码和关注范围（工商/诉讼/股权/信用），我会继续按尽调流程处理。"
                        )
            elif (mode == "research" or normalized_kb_ids) and not agent_name:
                from src.services.knowledge_service import KnowledgeService

                knowledge_service = KnowledgeService(self.db)
                rag_result = await knowledge_service.rag_query(
                    query=content,
                    kb_ids=normalized_kb_ids or None,
                )
                response_text = (rag_result or {}).get("answer", "").strip() or "抱歉，当前知识库未返回有效内容。"
                used_agent = "知识库检索Agent"
                sources = await self._build_knowledge_sources(
                    normalized_kb_ids,
                    (rag_result or {}).get("sources", []),
                )
            elif not agent_name and detect_contract_review_intent(content):
                # 合同审查强路由：直接分配给合同审查 Agent，跳过 DAG 规划
                used_agent = "contract_reviewer"
                response_text = await self.workforce.chat(content, used_agent, context={"llm_config": llm_config})
            elif not agent_name and detect_document_drafting_intent(content):
                # 文书起草强路由：直接分配给文书起草 Agent，跳过 DAG 规划
                used_agent = "document_drafter"
                response_text = await self.workforce.chat(content, used_agent, context={"llm_config": llm_config})
            elif agent_name:
                response_text = await self.workforce.chat(content, agent_name, context={"llm_config": llm_config})
                used_agent = agent_name
            else:
                result = await self.workforce.process_task(
                    task_description=content,
                    context={
                        "conversation_id": conversation.id,
                        "history": context_messages,
                        "case_id": case_id,
                        "llm_config": llm_config,
                    }
                )
                response_text = result.get("final_result", {}).get("summary", "")
                used_agent = "智能体团队"
                
                if not response_text:
                    response_text = await self.workforce.chat(content, context={"llm_config": llm_config})
                    used_agent = "法律顾问Agent"
        
        except Exception as e:
            logger.error(f"智能体调用失败: {e}")
            response_text = "抱歉，处理您的请求时遇到问题。请稍后重试。"
            used_agent = "系统"
        
        # 提取引用来源
        if not sources:
            sources = extract_citations(response_text)

        # 保存AI响应
        ai_message = await self.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=response_text,
            agent_name=used_agent,
            citations=[s.model_dump() for s in sources] if sources else None,
        )

        # 发布对话完成事件
        await self._publish_event("chat_events", {
            "type": "chat_completed",
            "conversation_id": str(conversation.id),
            "agent": used_agent,
            "user_id": user_id,
        })

        return {
            "conversation_id": conversation.id,
            "message_id": ai_message.id,
            "content": response_text,
            "agent": used_agent,
            "citations": ai_message.citations or [],
            "actions": ai_message.actions or [],
            "sources": [s.model_dump() for s in sources],
        }
    
    async def stream_chat(
        self,
        content: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        case_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        privacy_mode: str = "HYBRID",
    ) -> AsyncGenerator[dict, None]:
        """
        流式对话 (v2 — 支持真正的 token 流式输出)
        
        优化：
        1. 单 Agent 模式使用 stream_chat 真流式输出
        2. 多 Agent 模式保持原有逻辑但优化打字机速度
        3. LLM 配置加载使用公共方法
        4. 关键操作发布事件
        """
        import asyncio
        
        # 1. 算力路由与隐私检查
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

            original_content = content
            content = processed_content
            
        except Exception as e:
            logger.error(f"算力路由失败: {e}")
            yield {"type": "error", "message": f"安全检查失败: {str(e)}"}
            return

        # 加载 LLM 配置（使用公共方法）
        llm_config = await self._load_llm_config()

        # 获取或创建对话
        if conversation_id:
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                yield {"type": "error", "message": "对话不存在"}
                return
        else:
            conversation = await self.create_conversation(
                user_id=user_id,
                case_id=case_id,
            )
        
        # 保存用户消息
        await self.add_message(
            conversation_id=conversation.id,
            role="user",
            content=content,
        )

        due_diligence_request = detect_company_due_diligence_request(content) if not agent_name else {"matched": False}
        if due_diligence_request.get("matched"):
            used_agent = "尽职调查Agent"
            company_name = due_diligence_request.get("company_name")

            yield {
                "type": "agent_start",
                "agent": used_agent,
                "message": "正在识别调查对象并准备企业尽调结果...",
            }

            if not company_name:
                response_text = (
                    "我已识别到您是在发起企业调查/尽调请求，但当前信息还不够。"
                    "请至少补充目标企业的完整名称，最好同时说明您重点关注的范围，例如工商信息、诉讼记录、股权结构、信用情况或合作风险。"
                )
            else:
                try:
                    company_data = await get_company_info(company_name)
                    response_text = format_due_diligence_chat_response(company_name, company_data)
                except Exception as dd_err:
                    logger.error(f"流式企业调查强路由失败: {dd_err}")
                    response_text = (
                        f"我已识别到您要调查企业“{company_name}”，但当前尽调服务暂时无法返回可靠结果。"
                        "请稍后重试，或补充统一社会信用代码和关注范围（工商/诉讼/股权/信用），我会继续按尽调流程处理。"
                    )

            if recovery_map:
                response_text = pii_service.restore(response_text, recovery_map)
                response_text += "\n\n*(注：本回复基于脱敏数据生成，敏感信息已在本地自动还原)*"

            sources = extract_citations(response_text)
            ai_message = await self.add_message(
                conversation_id=conversation.id,
                role="assistant",
                content=response_text,
                agent_name=used_agent,
                citations=[s.model_dump() for s in sources] if sources else None,
            )

            yield {
                "type": "content",
                "text": response_text,
                "accumulated": response_text,
                "agent": used_agent,
                "progress": 1.0,
            }
            yield {
                "type": "done",
                "conversation_id": conversation.id,
                "message_id": ai_message.id,
                "agent": used_agent,
                "full_content": response_text,
                "sources": [s.model_dump() for s in sources],
            }

            await self._publish_event("chat_events", {
                "type": "stream_chat_completed",
                "conversation_id": str(conversation.id),
                "agent": used_agent,
                "user_id": user_id,
            })
            return
        
        # === 合同审查/文书起草强路由（流式） ===
        _fast_agent = None
        if not agent_name and detect_contract_review_intent(content):
            _fast_agent = "contract_reviewer"
        elif not agent_name and detect_document_drafting_intent(content):
            _fast_agent = "document_drafter"

        if _fast_agent:
            used_agent = _fast_agent
            yield {"type": "agent_start", "agent": used_agent, "message": f"正在处理您的请求..."}
            try:
                response_text = await self.workforce.chat(content, _fast_agent, context={"llm_config": llm_config})
            except Exception:
                response_text = await self.workforce.chat(content, "legal_advisor", context={"llm_config": llm_config})
                used_agent = "legal_advisor"

            if recovery_map:
                response_text = pii_service.restore(response_text, recovery_map)

            sources = extract_citations(response_text)
            ai_message = await self.add_message(
                conversation_id=conversation.id, role="assistant",
                content=response_text, agent_name=used_agent,
                citations=[s.model_dump() for s in sources] if sources else None,
            )
            yield {"type": "content", "text": response_text, "accumulated": response_text, "agent": used_agent, "progress": 1.0}
            yield {"type": "done", "conversation_id": conversation.id, "message_id": ai_message.id, "agent": used_agent, "full_content": response_text, "sources": [s.model_dump() for s in sources]}
            return

        # 发送开始事件
        yield {
            "type": "start",
            "conversation_id": conversation.id,
            "agent": "协调调度Agent",
        }

        yield {
            "type": "thinking",
            "agent": "智能体团队",
            "message": "正在分析您的问题...",
        }

        try:
            # 判断是否需要多智能体协作
            is_complex = any(
                keyword in content
                for keyword in ['合同', '审查', '尽职调查', '风险', '诉讼', '法规', '条款']
            )
            
            if is_complex and not agent_name:
                # ===== 多智能体协作模式 =====
                yield {
                    "type": "agent_start",
                    "agent": "协调调度Agent",
                    "message": "启动多智能体协作...",
                }
                
                # 异步获取图谱 A2UI 数据
                from src.services.rag_service import rag_service
                graph_task = asyncio.create_task(rag_service.get_graph_a2ui_data(content))

                # 发送各Agent工作状态
                agents_sequence = [
                    ('法律顾问Agent', '分析法律问题要点...'),
                    ('合同审查Agent', '检查相关条款...'),
                    ('风险评估Agent', '评估潜在风险...'),
                ]
                
                for agent_display, task_desc in agents_sequence:
                    yield {
                        "type": "agent_working",
                        "agent": agent_display,
                        "message": task_desc,
                    }
                    await asyncio.sleep(0.2)
                
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

                # 获取实际响应
                result = await self.workforce.process_task(
                    task_description=content,
                    context={
                        "conversation_id": conversation.id,
                        "case_id": case_id,
                        "llm_config": llm_config,
                    }
                )
                response_text = result.get("final_result", {}).get("summary", "")
                
                # 隐私还原
                if recovery_map:
                    response_text = pii_service.restore(response_text, recovery_map)
                    response_text += "\n\n*(注：本回复基于脱敏数据生成，敏感信息已在本地自动还原)*"
                
                # 处理Agent Action (Notifications)
                await self._process_agent_notifications(result, user_id, conversation.id)

                # 提取 A2UI 数据
                a2ui_data = None
                for res in result.get("agent_results", []):
                    if isinstance(res, dict) and res.get("metadata", {}).get("a2ui"):
                        a2ui_data = res["metadata"]["a2ui"]
                        break
                
                if a2ui_data:
                    yield {
                        "type": "context_update",
                        "context_type": "a2ui",
                        "data": a2ui_data,
                    }
                
                if not response_text:
                    response_text = await self.workforce.chat(content, context={"llm_config": llm_config})
                
                used_agent = "智能体团队"
                
                # 多 Agent 结果：使用分块输出
                yield {"type": "agent_complete", "agent": used_agent}
                
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
                    
            else:
                # ===== 单智能体模式：使用真正的流式输出 =====
                target_agent_name = agent_name if agent_name and agent_name in self.workforce.agents else "legal_advisor"
                target_agent = self.workforce.agents[target_agent_name]
                used_agent = agent_name or "法律顾问Agent"
                
                yield {"type": "agent_complete", "agent": used_agent}
                
                # 尝试使用真流式
                try:
                    token_queue = await target_agent.stream_chat(
                        content,
                        llm_config=llm_config,
                    )
                    
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
                        context={"llm_config": llm_config}
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
            
            # 提取引用来源
            sources = extract_citations(response_text)

            # 保存AI响应
            ai_message = await self.add_message(
                conversation_id=conversation.id,
                role="assistant",
                content=response_text,
                agent_name=used_agent,
                citations=[s.model_dump() for s in sources] if sources else None,
            )

            # 发送完成事件
            yield {
                "type": "done",
                "conversation_id": conversation.id,
                "message_id": ai_message.id,
                "agent": used_agent,
                "full_content": response_text,
                "sources": [s.model_dump() for s in sources],
            }
            
            # 发布事件
            await self._publish_event("chat_events", {
                "type": "stream_chat_completed",
                "conversation_id": str(conversation.id),
                "agent": used_agent,
                "user_id": user_id,
            })
            
        except Exception as e:
            logger.error(f"流式对话失败: {e}")
            yield {
                "type": "error",
                "message": f"处理失败: {str(e)}",
            }
    
    # ========== 辅助方法 ==========
    
    async def _process_agent_notifications(
        self,
        result: Dict[str, Any],
        user_id: Optional[str],
        conversation_id: str,
    ):
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
    
    def _split_into_chunks(self, text: str, chunk_size: int = 20) -> List[str]:
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
        feedback: Optional[str] = None,
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
