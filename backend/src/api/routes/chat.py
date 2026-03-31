"""AI对话路由"""

import json
import asyncio
from typing import Optional, List, AsyncGenerator
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.core.responses import UnifiedResponse
from src.core.database import get_db
from src.core.deps import (
    get_current_user,
    get_current_user_required,
    rate_limit,
    rate_limit_chat,
    require_permission,
    Permission,
)
from src.services.chat_service import ChatService, extract_citations
from src.services.audit_service import AuditService
from src.models.audit import AuditAction, ResourceType
from src.models.user import User
from src.agents.workforce import get_workforce
from src.services.episodic_memory_service import episodic_memory
from src.services.event_bus import event_bus
from src.services.compute_router_service import compute_router
from src.services.pii_service import pii_service
from src.services.due_diligence_service import (
    detect_company_due_diligence_request,
    format_due_diligence_chat_response,
    get_company_info,
)
from src.core.privacy import InferenceRequest, SensitivityLevel

router = APIRouter()


class ChatMessage(BaseModel):
    """聊天消息"""
    content: str
    conversation_id: Optional[str] = None
    case_id: Optional[str] = None
    agent_name: Optional[str] = None
    privacy_mode: Optional[str] = "HYBRID"
    mode: Optional[str] = "chat"
    knowledge_base_ids: Optional[List[str]] = None


class ChatResponse(BaseModel):
    """聊天响应"""
    conversation_id: str
    message_id: str
    content: str
    agent: str
    citations: list = []
    actions: list = []
    sources: list = []  # RAG 引用来源列表
    memory_id: Optional[str] = None


class MessageItem(BaseModel):
    """消息项"""
    id: str
    role: str
    content: str
    agent_name: Optional[str] = None
    created_at: str
    sources: list = []


@router.post("/", response_model=UnifiedResponse)
async def send_message(
    request: Request,
    message: ChatMessage,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
    _: None = Depends(rate_limit_chat),
):
    """发送消息并获取AI回复"""
    service = ChatService(db)
    
    result = await service.chat(
        content=message.content,
        conversation_id=message.conversation_id,
        user_id=user.id if user else None,
        case_id=message.case_id,
        agent_name=message.agent_name,
        mode=message.mode,
        knowledge_base_ids=message.knowledge_base_ids,
    )
    
    # 记录审计日志
    if user:
        audit_service = AuditService(db)
        await audit_service.log_from_request(
            request=request,
            action=AuditAction.CHAT_MESSAGE.value,
            resource_type=ResourceType.CONVERSATION.value,
            resource_id=result["conversation_id"],
            user=user,
            extra_data={
                "message_length": len(message.content),
                "agent": result.get("agent"),
            }
        )
    
    return UnifiedResponse.success(data=ChatResponse(**result))


@router.get("/history", response_model=UnifiedResponse)
async def get_chat_history(
    conversation_id: Optional[str] = None,
    case_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """获取对话历史"""
    service = ChatService(db)
    
    if conversation_id:
        messages = await service.get_messages(conversation_id, limit)
        data = {
            "conversation_id": conversation_id,
            "messages": [
                MessageItem(
                    id=m.id,
                    role=m.role.value,
                    content=m.content,
                    agent_name=m.agent_name,
                    created_at=m.created_at.isoformat(),
                    sources=m.citations or [],
                )
                for m in messages
            ],
            "total": len(messages)
        }
        return UnifiedResponse.success(data=data)
    else:
        conversations = await service.list_conversations(
            user_id=user.id if user else None,
            case_id=case_id,
            limit=limit,
        )
        data = {
            "conversations": [
                {
                    "id": c.id,
                    "title": c.title,
                    "message_count": c.message_count,
                    "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
                    "created_at": c.created_at.isoformat(),
                }
                for c in conversations
            ],
            "total": len(conversations)
        }
        return UnifiedResponse.success(data=data)


@router.delete("/conversations/{conversation_id}", response_model=UnifiedResponse)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """删除对话"""
    from src.models.conversation import Conversation, Message as MessageModel
    from sqlalchemy import delete as sa_delete, select
    
    # 验证对话存在
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        return UnifiedResponse.error(message="对话不存在", code=404)
    
    # 删除消息和对话（cascade 应该自动处理，但显式更安全）
    await db.execute(sa_delete(MessageModel).where(MessageModel.conversation_id == conversation_id))
    await db.execute(sa_delete(Conversation).where(Conversation.id == conversation_id))
    await db.commit()
    
    return UnifiedResponse.success(data={"deleted": True})


class BatchDeleteRequest(BaseModel):
    """批量删除对话请求"""
    conversation_ids: List[str]


@router.post("/conversations/batch-delete")
async def batch_delete_conversations(
    payload: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """批量删除对话"""
    from src.models.conversation import Conversation, Message as MessageModel
    from sqlalchemy import delete as sa_delete
    
    ids = payload.conversation_ids
    if not ids:
        return UnifiedResponse.error(message="请提供要删除的对话 ID 列表")
    
    try:
        # 先删除消息（子表），再删除对话（主表）
        await db.execute(
            sa_delete(MessageModel).where(MessageModel.conversation_id.in_(ids))
        )
        await db.execute(
            sa_delete(Conversation).where(Conversation.id.in_(ids))
        )
        await db.commit()
        logger.info(f"批量删除对话成功: {len(ids)} 个")
        return UnifiedResponse.success(data={"deleted": True, "count": len(ids)})
    except Exception as e:
        await db.rollback()
        logger.error(f"批量删除对话失败: {e}")
        return UnifiedResponse.error(message=f"批量删除失败: {str(e)}")


@router.patch("/conversations/{conversation_id}", response_model=UnifiedResponse)
async def update_conversation(
    conversation_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """更新对话标题"""
    from src.models.conversation import Conversation
    from sqlalchemy import select, update as sa_update
    
    body = await request.json()
    title = body.get("title", "").strip()
    if not title:
        return UnifiedResponse.error(message="标题不能为空")
    
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        return UnifiedResponse.error(message="对话不存在", code=404)
    
    await db.execute(
        sa_update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(title=title)
    )
    await db.commit()
    
    return UnifiedResponse.success(data={"id": conversation_id, "title": title})


@router.post("/conversations/cleanup", response_model=UnifiedResponse)
async def cleanup_empty_conversations(
    db: AsyncSession = Depends(get_db),
):
    """清理空对话（24小时前创建但没有任何消息的对话）"""
    try:
        svc = ChatService(db)
        count = await svc.cleanup_empty_conversations(older_than_hours=24)
        await db.commit()
        return UnifiedResponse.success(data={"cleaned": count})
    except Exception as e:
        logger.error(f"清理空对话失败: {e}")
        return UnifiedResponse.error(message="清理失败")


@router.post("/stream")
async def stream_chat_endpoint(
    request: Request,
    message: ChatMessage,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
    _: None = Depends(rate_limit(limit=20, window=60, endpoint="chat_stream")),
):
    """
    流式对话响应 (Server-Sent Events)
    
    返回SSE格式的流式响应，支持以下事件类型：
    - start: 开始处理
    - thinking: 思考中
    - agent_start: 智能体开始工作
    - agent_working: 智能体正在工作
    - agent_complete: 智能体完成
    - content: 内容片段
    - done: 完成
    - error: 错误
    """
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        service = ChatService(db)
        
        try:
            async for event in service.stream_chat(
                content=message.content,
                conversation_id=message.conversation_id,
                user_id=user.id if user else None,
                case_id=message.case_id,
                agent_name=message.agent_name,
            ):
                # 将事件转换为SSE格式
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                
                # 如果是完成或错误事件，记录审计日志
                if event.get("type") == "done" and user:
                    try:
                        audit_service = AuditService(db)
                        await audit_service.log_from_request(
                            request=request,
                            action=AuditAction.CHAT_MESSAGE.value,
                            resource_type=ResourceType.CONVERSATION.value,
                            resource_id=event.get("conversation_id"),
                            user=user,
                            extra_data={
                                "stream": True,
                                "agent": event.get("agent"),
                            }
                        )
                        await db.commit()
                    except Exception as log_err:
                        logger.error(f"审计日志记录失败: {log_err}")
            
        except Exception as e:
            logger.error(f"流式对话失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream; charset=utf-8",
        }
    )


@router.post("/stream/v2")
async def stream_chat_v2(
    request: Request,
    message: ChatMessage,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.USE_CHAT)),
    _: None = Depends(rate_limit(limit=20, window=60, endpoint="chat_stream")),
):
    """
    增强版流式对话（需要认证）
    
    与/stream接口相同，但需要用户登录
    """
    async def generate_stream() -> AsyncGenerator[str, None]:
        service = ChatService(db)
        
        try:
            async for event in service.stream_chat(
                content=message.content,
                conversation_id=message.conversation_id,
                user_id=user.id,
                case_id=message.case_id,
                agent_name=message.agent_name,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            # 提交事务
            await db.commit()
            
        except Exception as e:
            logger.error(f"流式对话失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream; charset=utf-8",
        }
    )


@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket 实时对话 (v4)
    
    新增事件类型：
    - requirement_analysis: 需求分析结果（右侧工作台）
    - thinking_content: 思考推理过程（思考链）
    - agent_result: 单个 Agent 中间结果（右侧工作台）
    - content_token: 流式 token 输出
    - canvas_open: 打开 Canvas 画布
    - canvas_update: AI 更新 Canvas 内容
    - tab_switch: 建议切换右侧 Tab
    """
    await websocket.accept()
    logger.info(f"WebSocket连接建立: {session_id}")
    
    workforce = get_workforce()
    
    from src.core.database import async_session_maker
    from src.services.llm_service import LLMService
    from src.services.chat_service import ChatService
    from src.agents.base import _task_llm_config_var
    
    # --- 尝试导入 a2ui_builder（可选模块） ---
    try:
        from src.services.a2ui_builder import build_response_a2ui
    except ImportError:
        def build_response_a2ui(*args, **kwargs):
            return None

    # --- 导入流式 A2UI 协议辅助函数 ---
    from src.services.a2ui_protocol import (
        a2ui_stream_start, a2ui_stream_component, a2ui_stream_delta, a2ui_stream_end,
    )
    
    # 使用前端传来的 session_id 作为 conversation_id（get_or_create 模式）
    # 确保刷新页面后前端可以用同一个 ID 查到历史消息
    conversation_id = session_id
    try:
        async with async_session_maker() as db_session:
            chat_service = ChatService(db_session)
            conversation = await chat_service.get_or_create_conversation(
                conversation_id=session_id,
                title=f"对话 {session_id[:8]}",
            )
            conversation_id = str(conversation.id)
            await db_session.commit()
    except Exception as e:
        logger.warning(f"WebSocket: 创建/获取对话记录失败: {e}")
        conversation_id = session_id  # 即使数据库操作失败也保持 session_id
    
    # WebSocket 连接状态标记，避免在连接关闭后反复发送产生大量警告
    _ws_closed = False

    # 订阅 EventBus
    async def event_handler(event_data):
        if _ws_closed:
            return
        try:
            await websocket.send_json({"type": "event_bus_msg", "data": event_data})
        except Exception:
            pass

    await event_bus.subscribe("agent_events", event_handler)

    # --- 辅助函数 ---
    async def _send(event_type: str, data: dict):
        """安全发送 WebSocket 消息"""
        nonlocal _ws_closed
        if _ws_closed:
            return
        try:
            await websocket.send_json({**data, "type": event_type, "session_id": session_id})
        except Exception as e:
            if "close" in str(e).lower():
                _ws_closed = True
            logger.warning(f"WS 发送失败: {e}")

    async def _load_llm_config():
        try:
            async with async_session_maker() as db_session:
                cfg = await LLMService.get_default_config(db_session)
                if not cfg:
                    from src.models.llm_config import LLMConfig
                    from sqlalchemy import select
                    result_cfg = await db_session.execute(
                        select(LLMConfig)
                        .where(LLMConfig.config_type == "llm")
                        .where(LLMConfig.is_active == True)
                        .order_by(LLMConfig.updated_at.desc())
                        .limit(1)
                    )
                    cfg = result_cfg.scalar_one_or_none()
                return cfg
        except Exception as e:
            logger.warning(f"WebSocket: 加载LLM配置失败: {e}")
            return None

    _save_lock = asyncio.Lock()  # 串行化消息保存，防止竞态

    async def _save_message(role: str, content: str, agent_name: str = None, citations: Optional[list] = None):
        if not conversation_id:
            return
        async with _save_lock:
            try:
                async with async_session_maker() as db_session:
                    svc = ChatService(db_session)
                    await svc.add_message(
                        conversation_id=conversation_id, role=role,
                        content=content, agent_name=agent_name,
                        citations=citations,
                    )
                    # 第一条用户消息时，自动更新对话标题（检查是否仍是默认标题）
                    if role == "user":
                        from src.models.conversation import Conversation as ConvModel
                        from sqlalchemy import select as sa_select, update as sa_update
                        result = await db_session.execute(
                            sa_select(ConvModel.title).where(ConvModel.id == conversation_id)
                        )
                        current_title = result.scalar_one_or_none()
                        # 仅当标题仍为默认值 "对话 xxx" 时才更新
                        if current_title and current_title.startswith("对话 "):
                            title_text = content.replace("[附件:", "").strip()[:50]
                            if title_text:
                                await db_session.execute(
                                    sa_update(ConvModel)
                                    .where(ConvModel.id == conversation_id)
                                    .values(title=title_text)
                                )
                                # 通知前端更新侧边栏标题
                                await _send("conversation_title_updated", {
                                    "conversation_id": conversation_id,
                                    "title": title_text,
                                })
                    await db_session.commit()
            except Exception as e:
                logger.warning(f"WebSocket: 保存消息失败: {e}")
                # 通知前端保存失败
                await _send("save_warning", {
                    "message": "消息可能未成功保存，建议刷新页面",
                })

    async def _ws_callback(event_type: str, data: dict):
        """统一的 ws 回调 — 将 workforce 事件直接推送给前端"""
        await _send(event_type, data)

    async def _stream_response_tokens(text: str, agent: str):
        """将完整响应文本逐块流式推送（模拟 token 流）"""
        if not text:
            return
        # 按标点/换行符分块，每块 20-50 字符
        import re
        chunks = re.split(r'([。！？；\n])', text)
        accumulated = ""
        buf = ""
        for chunk in chunks:
            buf += chunk
            if chunk in '。！？；\n' or len(buf) >= 30:
                if buf.strip():
                    accumulated += buf
                    await _send("content_token", {
                        "token": buf,
                        "accumulated": accumulated,
                        "agent": agent,
                    })
                    await asyncio.sleep(0.02)
                buf = ""
        if buf.strip():
            accumulated += buf
            await _send("content_token", {
                "token": buf,
                "accumulated": accumulated,
                "agent": agent,
            })

    # 会话内消息计数器 — 用于 Coordinator 渐进式响应策略
    _session_message_count = 0
    # 最近一条用户消息 — 用于工作台确认后恢复上下文
    _last_user_content = ""

    async def _stream_a2ui_components(
        components: list,
        agent: str = "AI 助手",
        stream_id: str = None,
        delay: float = 0.05,
    ):
        """
        流式推送 A2UI 组件列表（千问 StreamObject 风格）。
        
        前端会逐个渲染组件，实现"卡片逐步生长"的效果。
        
        Args:
            components: A2UI 组件 dict 列表
            agent: Agent 名称
            stream_id: 流 ID（自动生成）
            delay: 组件间发送间隔（秒），默认 50ms（快速出卡片）
        """
        if not components:
            return
        
        import uuid
        sid = stream_id or f"stream-{str(uuid.uuid4())[:8]}"
        
        # 1. stream_start — 前端显示骨架屏
        await _send("a2ui_stream", a2ui_stream_start(sid, agent=agent))
        
        # 2. 逐个推送组件（极短间隔，让用户立即看到内容）
        for comp in components:
            await _send("a2ui_stream", a2ui_stream_component(sid, comp, agent=agent))
            if delay > 0:
                await asyncio.sleep(delay)
        
        # 3. stream_end — 前端移除骨架屏
        await _send("a2ui_stream", a2ui_stream_end(sid))

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")
            content = data.get("content", "")
            agent_name = data.get("agent_name")
            privacy_mode = data.get("privacy_mode", "HYBRID")
            
            # === A2UI 事件处理 ===
            if msg_type == "a2ui_event":
                a2ui_action_id = data.get("action_id", "")
                a2ui_component_id = data.get("component_id", "")
                a2ui_payload = data.get("payload", {})
                a2ui_form_data = data.get("form_data", {})
                logger.info(f"[A2UI Event] action={a2ui_action_id}, component={a2ui_component_id}")
                
                try:
                    from src.services.a2ui_intent_handler import handle_a2ui_event as _handle_a2ui_evt
                    a2ui_response = await _handle_a2ui_evt(
                        action_id=a2ui_action_id,
                        component_id=a2ui_component_id,
                        payload=a2ui_payload,
                        form_data=a2ui_form_data,
                        context={"conversation_id": conversation_id},
                    )
                    if a2ui_response:
                        await _send(a2ui_response.get("type", "a2ui_message"), a2ui_response)
                        # 保存用户的 A2UI 交互到对话历史
                        await _save_message(
                            "user",
                            f"[用户操作] {a2ui_action_id}",
                            None,
                        )
                        await _save_message(
                            "assistant",
                            f"[A2UI 交互响应] {a2ui_action_id}",
                            f"A2UI Agent",
                        )
                        # 发送 done 信号
                        await _send("done", {
                            "conversation_id": conversation_id,
                            "a2ui": True,
                        })
                    else:
                        logger.warning(f"[A2UI] action '{a2ui_action_id}' 无匹配处理器，回退到对话流")
                        # 如果没有匹配的 A2UI 处理器，将 action 作为用户消息发送到 LLM
                        content = f"用户执行了操作: {a2ui_action_id}"
                        # 不 continue，让后续 Agent 逻辑处理
                except Exception as e:
                    logger.error(f"A2UI 事件处理失败: {e}", exc_info=True)
                    await _send("error", {"content": f"操作处理失败: {str(e)}"})
                continue

            # === 工作台确认回复 ===
            if msg_type == "workspace_confirmation_response":
                confirmation_id = data.get("confirmation_id", "")
                selected_ids = data.get("selected_ids", [])
                logger.info(f"收到工作台确认: {confirmation_id}, 选项: {selected_ids}")
                await _send("workspace_confirmation_ack", {
                    "confirmation_id": confirmation_id,
                    "status": "received",
                })
                
                # === 将用户选择转换为 clarification_response 格式，复用已有流程 ===
                if selected_ids:
                    selections_text = "、".join(selected_ids)
                    # 改写 msg_type 和 data，让下游 clarification_response 逻辑处理
                    msg_type = "clarification_response"
                    data["original_content"] = _last_user_content
                    data["content"] = selections_text
                    data["selections"] = selections_text
                    content = selections_text
                    logger.info(f"工作台确认 → 转为 clarification_response: {selections_text[:50]}")
                    # 不 continue — 让流程走到 clarification_response 处理
                else:
                    continue

            # === 工作台动作响应 ===
            if msg_type == "workspace_action":
                action_id = data.get("action_id", "")
                payload = data.get("payload")
                logger.info(f"收到工作台动作: {action_id}, payload: {payload}")
                
                if action_id == "start_processing" and payload:
                    # 用户点击"开始处理" → 转为 clarification_response 格式，复用已有流程
                    await _send("agent_thinking", {
                        "agent": "协调调度Agent",
                        "message": "收到确认，正在启动智能体协作...",
                    })
                    
                    content = _last_user_content or "请根据之前的需求分析结果开始处理"
                    msg_type = "clarification_response"
                    data["original_content"] = _last_user_content
                    data["content"] = content
                    data["selections"] = "用户确认开始处理"
                    logger.info(f"工作台开始处理 → 转为 clarification_response")
                    # 不 continue — 让流程走到 clarification_response 处理
                else:
                    continue

            # === Canvas 编辑事件 ===
            if msg_type == "canvas_edit":
                canvas_title = data.get("title", "未命名文档")
                canvas_type = data.get("canvas_type", "document")
                logger.info(f"Canvas edit received: {len(content)} chars, title={canvas_title}")
                
                # 保存/更新 Canvas 内容到文档系统
                try:
                    async with async_session_maker() as db_session:
                        from src.services.document_service import DocumentService
                        from src.models.document import Document as DocModel
                        from sqlalchemy import select as sa_select
                        
                        doc_svc = DocumentService(db_session)
                        
                        # 通过 doc_metadata 中的 conversation_id 查找已关联的 Canvas 文档
                        from sqlalchemy import and_, cast, String
                        result = await db_session.execute(
                            sa_select(DocModel).where(
                                and_(
                                    DocModel.doc_metadata.isnot(None),
                                    cast(DocModel.doc_metadata["conversation_id"], String) == conversation_id,
                                    DocModel.description.like("Canvas:%"),
                                )
                            ).order_by(DocModel.updated_at.desc()).limit(1)
                        )
                        existing_doc = result.scalar_one_or_none()
                        
                        if existing_doc:
                            # 更新已有文档
                            await doc_svc.update_document_content(
                                document_id=existing_doc.id,
                                content=content,
                                change_summary=f"Canvas 编辑更新",
                            )
                        else:
                            # 创建新文档（不传 case_id，用 doc_metadata 关联对话）
                            doc = await doc_svc.create_text_document(
                                name=canvas_title,
                                content=content,
                                doc_type=canvas_type if canvas_type in ['contract', 'document'] else 'other',
                                description=f"Canvas:{canvas_title}",
                            )
                            # 补充 metadata 关联
                            doc.doc_metadata = {"conversation_id": conversation_id, "source": "canvas"}
                        
                        await db_session.commit()
                        
                    await _send("canvas_saved", {"status": "ok", "title": canvas_title})
                except Exception as e:
                    logger.warning(f"Canvas 内容保存失败: {e}")
                    await _send("canvas_saved", {"status": "error", "message": str(e)})
                continue
            
            if msg_type == "canvas_request":
                # 用户请求 AI 优化 Canvas 内容
                canvas_content = data.get("canvas_content", "")
                canvas_type = data.get("canvas_type", "document")
                
                if not canvas_content.strip():
                    await _send("error", {"content": "Canvas 内容为空，无法优化"})
                    continue
                
                # 检查 Agent 是否可用
                agent_key = "document_drafter"
                if agent_key not in workforce.agents:
                    # 回退使用法律顾问 Agent
                    agent_key = "legal_advisor" if "legal_advisor" in workforce.agents else list(workforce.agents.keys())[0]
                    logger.warning(f"document_drafter 不可用，回退使用 {agent_key}")
                
                llm_config = await _load_llm_config()
                
                await _send("agent_thinking", {"agent": "文书起草Agent", "message": "正在优化文档内容..."})
                
                try:
                    token = _task_llm_config_var.set(llm_config)
                    try:
                        optimized = await workforce.agents[agent_key].chat(
                            f"请优化以下{canvas_type}内容，保持原意但提升专业性和完整性：\n\n{canvas_content}",
                            llm_config=llm_config,
                        )
                    finally:
                        _task_llm_config_var.reset(token)
                    
                    await _send("canvas_update", {
                        "content": optimized,
                        "type": canvas_type,
                        "title": "AI 优化版本",
                    })
                except Exception as e:
                    logger.error(f"Canvas 优化失败: {e}")
                    await _send("error", {"content": f"Canvas 优化失败: {str(e)}"})
                continue
            
            # === 1. 算力路由与隐私检查 ===
            try:
                sensitivity = SensitivityLevel(privacy_mode)
                req = InferenceRequest(prompt=content, sensitivity=sensitivity)
                processed_content, recovery_map = await compute_router.route_request(req)
                
                if sensitivity == SensitivityLevel.CONFIDENTIAL:
                    await _send("agent_thinking", {"agent": "本地安全芯片", "message": "正在本地硬件安全区进行推理..."})
                    await _send("agent_response", {"agent": "AI私有助手(Local)", "content": processed_content})
                    await _save_message("user", content)
                    await _save_message("assistant", processed_content, "AI私有助手(Local)")
                    continue

                content = processed_content
                
            except Exception as e:
                logger.error(f"算力路由失败: {e}")
                await _send("error", {"content": f"安全检查失败: {str(e)}"})
                continue
            
            # === 持久化用户消息 & 更新会话计数器 ===
            await _save_message("user", content)
            _session_message_count += 1
            _last_user_content = content

            # === 企业调查强路由：避免“调查公司”掉回通用闲聊 ===
            _due_diligence_request = detect_company_due_diligence_request(content) if not agent_name else {"matched": False}
            if _due_diligence_request.get("matched"):
                used_agent = "尽职调查Agent"
                company_name = _due_diligence_request.get("company_name")

                await _send("agent_thinking", {
                    "agent": used_agent,
                    "message": "正在识别调查对象并准备企业尽调结果...",
                })

                if not company_name:
                    response_text = (
                        "我已识别到您是在发起企业调查/尽调请求，但当前还缺少关键对象。"
                        "请提供目标企业的完整名称，最好再补充您重点关注的范围，例如工商信息、诉讼记录、股权结构、信用情况或合作风险。"
                    )
                else:
                    try:
                        company_data = await get_company_info(company_name)
                        response_text = format_due_diligence_chat_response(company_name, company_data)
                    except Exception as dd_err:
                        logger.error(f"企业调查强路由失败: {dd_err}")
                        response_text = (
                            f"我已识别到您要调查企业“{company_name}”，但当前尽调服务暂时无法返回可靠结果。"
                            "请稍后重试，或补充统一社会信用代码和关注范围（工商/诉讼/股权/信用），我会继续按尽调流程处理。"
                        )

                if recovery_map:
                    response_text = pii_service.restore(response_text, recovery_map)
                    response_text += "\n\n*(注：本回复基于脱敏数据生成，敏感信息已在本地自动还原)*"

                panel_data = build_response_a2ui(used_agent, response_text, content)
                if panel_data:
                    await _send("context_update", {"context_type": "a2ui", "data": panel_data})

                await _stream_response_tokens(response_text, used_agent)
                ws_sources = extract_citations(response_text)
                await _send("done", {
                    "agent": used_agent,
                    "content": response_text,
                    "memory_id": None,
                    "conversation_id": conversation_id,
                    "sources": [s.model_dump() for s in ws_sources],
                })
                await _save_message(
                    "assistant",
                    response_text,
                    used_agent,
                    citations=[s.model_dump() for s in ws_sources],
                )
                continue

            # === 知识库研究模式：在聊天内直接执行 RAG ===
            _selected_kb_ids = [
                kb_id
                for kb_id in (data.get("knowledge_base_ids") or [])
                if isinstance(kb_id, str) and kb_id
            ]
            _frontend_mode = data.get("mode", "chat")
            if (_frontend_mode == "research" or _selected_kb_ids) and not agent_name:
                await _send("agent_thinking", {
                    "agent": "知识库检索Agent",
                    "message": "正在检索知识库并整理答案...",
                })

                try:
                    async with async_session_maker() as db_session:
                        from sqlalchemy import select as sa_select
                        from src.models.knowledge import KnowledgeBase
                        from src.services.knowledge_service import KnowledgeService

                        kb_name_map = {}
                        if _selected_kb_ids:
                            kb_result = await db_session.execute(
                                sa_select(KnowledgeBase).where(KnowledgeBase.id.in_(_selected_kb_ids))
                            )
                            kb_name_map = {
                                str(kb.id): kb.name
                                for kb in kb_result.scalars().all()
                            }

                        knowledge_service = KnowledgeService(db_session)
                        rag_result = await knowledge_service.rag_query(
                            query=content,
                            kb_ids=_selected_kb_ids or None,
                            user_id=user_id,
                            org_id=getattr(current_user, 'org_id', None) if current_user else None,
                        )

                    response_text = (rag_result or {}).get("answer", "").strip()
                    if not response_text:
                        raise ValueError("知识库未返回有效回答")

                    raw_sources = (rag_result or {}).get("sources", []) or []
                    max_score = max(
                        (
                            float(source.get("score", 0) or 0)
                            for source in raw_sources
                            if isinstance(source, dict)
                        ),
                        default=0.0,
                    )

                    ws_sources = []
                    for kb_id in _selected_kb_ids:
                        kb_name = kb_name_map.get(kb_id)
                        if not kb_name:
                            continue
                        ws_sources.append({
                            "id": f"knowledge-base-{kb_id}",
                            "type": "knowledge_base",
                            "title": kb_name,
                            "source": kb_name,
                            "relevance_score": max_score,
                        })

                    default_source_label = next(iter(kb_name_map.values()), "知识库检索")
                    for idx, source in enumerate(raw_sources, start=1):
                        if not isinstance(source, dict):
                            continue
                        ws_sources.append({
                            "id": source.get("id") or f"knowledge-source-{idx}",
                            "type": "knowledge",
                            "title": source.get("title") or f"知识片段 {idx}",
                            "source": source.get("source") or default_source_label,
                            "content_snippet": source.get("content_snippet") or "",
                            "relevance_score": float(source.get("score", 0) or 0),
                        })

                    if recovery_map:
                        response_text = pii_service.restore(response_text, recovery_map)
                        response_text += "\n\n*(注：本回复基于脱敏数据生成，敏感信息已在本地自动还原)*"

                    await _stream_response_tokens(response_text, "知识库检索Agent")
                    await _send("done", {
                        "agent": "知识库检索Agent",
                        "content": response_text,
                        "memory_id": None,
                        "conversation_id": conversation_id,
                        "sources": ws_sources,
                    })
                    await _save_message(
                        "assistant",
                        response_text,
                        "知识库检索Agent",
                        citations=ws_sources,
                    )
                    continue
                except Exception as rag_err:
                    logger.warning(f"知识库研究模式执行失败，回退通用对话链路: {rag_err}")
                    await _send("error", {
                        "message": f"知识库检索出错，已切换到通用对话模式。({type(rag_err).__name__})",
                        "recoverable": True,
                    })
            
            # === A2UI 意图检测 — 仅作为辅助提示传递给 Coordinator，不拦截 ===
            _intent_hint = None
            try:
                from src.services.a2ui_intent_handler import detect_intent
                _intent_hint = detect_intent(content)
                if _intent_hint:
                    logger.info(f"[A2UI] 意图提示(非拦截): {_intent_hint}")
            except ImportError:
                logger.debug("A2UI 意图处理器未安装，跳过")
            except Exception as e:
                logger.warning(f"A2UI 意图检测失败: {e}")
            
            # === 加载 LLM 配置 ===
            llm_config = await _load_llm_config()
            
            # === 2. 快速路径判断 — 简单消息直接回复，跳过需求分析 ===
            
            # 规则引擎：判断是否是简单消息（无需 LLM 调用）
            _simple_greetings = {'你好', '您好', 'hi', 'hello', '嗨', '在吗', '你好啊', '您好啊', '早上好', '下午好', '晚上好'}
            _content_stripped = content.strip().lower().rstrip('。！？!?.~')
            _is_simple = (
                len(content) < 15 and not any(kw in content for kw in ['合同', '审查', '风险', '诉讼', '起草', '文书', '律师函', '律师', '员工', '辞退', '税', '签约', '侵权'])
            ) or _content_stripped in _simple_greetings
            
            # 复杂任务关键词（覆盖所有 Coordinator 支持的意图场景，确保进入渐进式策略评估）
            _complex_keywords = [
                # 合同相关
                '合同', '审查', '协议', '条款', '签约', '归档',
                # 诉讼/仲裁
                '诉讼', '仲裁', '起诉', '胜诉', '败诉', '判决',
                # 尽职调查
                '尽职调查', '尽调', '背景调查',
                # 风险/合规
                '风险', '合规', '监管', '政策', '新规',
                # 文书/方案
                '方案', '起草', '文书', '律师函',
                # 知识产权
                '侵权', '专利', '商标', '知识产权', '版权',
                # 劳动/人事
                '员工', '辞退', '劳动', '入职', '赔偿',
                # 财税
                '税', '财务', '发票', '报销',
                # 律师/服务匹配
                '律师', '法律顾问', '律所',
                # 证据
                '证据', '录音', '鉴定',
                # 制度/公告
                '制度', '公告', '手册', '通知',
            ]
            _is_complex_by_keyword = any(kw in content for kw in _complex_keywords)
            
            if msg_type == "clarification_response":
                # 合并澄清回复和原始问题
                original = data.get("original_content", "")
                selections = data.get("selections", "")
                content = f"{original}\n\n用户补充信息：{content}\n选择：{selections}"
                await _save_message("user", content)
                req_analysis = {"is_complete": True, "summary": content[:100], "complexity": "moderate"}
                _is_simple = False
                _is_complex_by_keyword = True
            elif _is_simple:
                # === 快速路径：简单消息直接回复，不走需求分析和意图识别 ===
                req_analysis = {"is_complete": True, "summary": content, "complexity": "simple"}
                logger.info(f"快速路径：简单消息 '{content[:20]}' 直接回复")
            elif _is_complex_by_keyword:
                # === 复杂任务：走需求分析 ===
                await _send("agent_thinking", {"agent": "需求分析Agent", "message": "正在分析您的需求..."})
                
                try:
                    token = _task_llm_config_var.set(llm_config)
                    try:
                        req_analysis = await workforce.requirement_analyst.analyze_requirement(
                            content, 
                            has_attachments=bool(data.get("has_attachments")),
                            llm_config=llm_config,
                        )
                    finally:
                        _task_llm_config_var.reset(token)
                    
                    # 推送需求分析结果到右侧工作台
                    await _send("requirement_analysis", req_analysis)
                    await _send("thinking_content", {
                        "agent": "需求分析Agent",
                        "content": f"**需求摘要**: {req_analysis.get('summary', '')}\n\n**复杂度**: {req_analysis.get('complexity', 'simple')}",
                        "phase": "requirement",
                    })
                    
                    # 如果需求不完整，智能选择澄清方式
                    if not req_analysis.get("is_complete", True) and req_analysis.get("guidance_questions"):
                        guidance_qs = req_analysis.get("guidance_questions", [])
                        
                        # 判断是否需要结构化多选（多项并行选择场景）
                        _needs_structured = len(guidance_qs) >= 3 or any(
                            len(q.get("options", [])) > 3 for q in guidance_qs if isinstance(q, dict)
                        )
                        
                        if _needs_structured:
                            # 复杂多选场景：使用结构化 clarification_request
                            await _send("clarification_request", {
                                "message": f"为了更好地帮助您，请补充以下信息：\n\n需求摘要：{req_analysis.get('summary', '')}",
                                "questions": guidance_qs,
                                "original_content": content,
                                "requirement_summary": req_analysis.get("summary", ""),
                            })
                            await _save_message("assistant", req_analysis.get("summary", ""), "需求分析Agent")
                            continue
                        else:
                            # 简单追问场景：Agent 通过自然对话追问，不中断流程
                            # 将引导问题转为自然语言追问，让 Agent 在回复中自然地提出
                            questions_text = "\n".join(
                                f"- {q.get('question', q) if isinstance(q, dict) else q}"
                                for q in guidance_qs
                            )
                            # 标记需求分析为"已完成"以继续走 Agent 管线
                            req_analysis["is_complete"] = True
                            req_analysis["natural_followup"] = (
                                f"请在回复中自然地向用户追问以下信息（不要使用列表形式，"
                                f"用对话的方式友好地询问）：\n{questions_text}"
                            )
                        
                except Exception as e:
                    logger.warning(f"需求分析失败，继续处理: {e}")
                    req_analysis = {"is_complete": True, "summary": content[:100], "complexity": "simple"}
            else:
                # === 中等复杂度：跳过需求分析，直接单 Agent 回复 ===
                req_analysis = {"is_complete": True, "summary": content[:100], "complexity": "simple"}
            
            try:
                # 判断是否需要多智能体协作
                complexity = req_analysis.get("complexity", "simple")
                is_complex = (complexity in ("moderate", "complex") or _is_complex_by_keyword) and not _is_simple
                
                memory_id = None
                # 默认响应策略 — 简单路径为 chat_only，复杂路径由 Coordinator 决定
                _response_strategy = "chat_only"
                
                if is_complex:
                    await _send("agent_start", {
                        "agent": "协调调度Agent",
                        "message": "正在分配最佳智能体处理您的需求...",
                    })
                    
                    # 执行任务（注入 ws_callback + 意图提示 + 会话上下文）
                    _has_attachments = bool(data.get("has_attachments"))
                    # 信息充分度判断：有附件 或 消息较长（>80字）或 非首轮对话
                    _has_sufficient_info = (
                        _has_attachments
                        or len(content) > 80
                        or _session_message_count > 1
                    )
                    _task_context = {
                        "llm_config": llm_config,
                        "intent_hint": _intent_hint,
                        "conversation_turns": _session_message_count,
                        "has_sufficient_info": _has_sufficient_info,
                        "files": [data.get("document_id")] if data.get("document_id") else [],
                        "mode": data.get("mode", "chat"),  # 前端功能模式药丸 → Coordinator 策略优化
                    }
                    # 如果有自然追问提示，注入到任务描述中
                    _task_content = content
                    _natural_followup = req_analysis.get("natural_followup")
                    if _natural_followup:
                        _task_content = f"{content}\n\n[系统提示] {_natural_followup}"
                    
                    result = await workforce.process_task(
                        _task_content, 
                        context=_task_context,
                        ws_callback=_ws_callback,
                    )
                    memory_id = result.get("memory_id")
                    
                    # 根据 response_strategy 决定是否触发右侧面板
                    _response_strategy = result.get("analysis", {}).get("response_strategy", "chat_only")
                    if _response_strategy == "workspace":
                        await _send("panel_trigger", {"reason": "complex_task", "tab": "smart"})
                    
                    # 提取 A2UI 数据
                    a2ui_data = None
                    a2ui_components = []
                    for res in result.get("agent_results", []):
                        if isinstance(res, dict) and res.get("metadata", {}).get("a2ui"):
                            a2ui_data = res["metadata"]["a2ui"]
                            # 提取内嵌组件列表（用于流式推送）
                            if isinstance(a2ui_data, dict) and a2ui_data.get("components"):
                                a2ui_components.extend(a2ui_data["components"])
                            elif isinstance(a2ui_data, dict) and a2ui_data.get("a2ui", {}).get("components"):
                                a2ui_components.extend(a2ui_data["a2ui"]["components"])
                    
                    # 提取响应文本（先于 A2UI 推送，以便确定 agent 名称）
                    response_text = result.get("final_result", {}).get("summary", "")
                    if not response_text:
                        # 尝试从 agent_results 中提取内容
                        for ar in result.get("agent_results", []):
                            if isinstance(ar, dict) and ar.get("content"):
                                response_text = ar["content"]
                                break
                    if not response_text:
                        response_text = await workforce.chat(content, context={"llm_config": llm_config})
                    used_agent = "智能体团队"
                    
                    # 根据 response_strategy 控制 A2UI 发送
                    # chat_only → 不发送 A2UI（纯文本对话）
                    # chat_with_a2ui / chat_with_streaming_a2ui → 流式推送 A2UI 到对话流（内联卡片）
                    # workspace → 推送到右侧面板
                    if _response_strategy != "chat_only":
                        if a2ui_components and _response_strategy in ("chat_with_a2ui", "chat_with_streaming_a2ui"):
                            # 千问 StreamObject 风格：逐个流式推送 A2UI 组件到对话流
                            await _stream_a2ui_components(
                                a2ui_components,
                                agent=used_agent,
                                delay=0.04,  # 40ms 极速出卡片
                            )
                        elif a2ui_data:
                            # workspace 策略：推送到右侧面板
                            await _send("context_update", {"context_type": "a2ui", "data": a2ui_data})
                    
                    # 流式推送多智能体结果（而非一次性 done）
                    await _stream_response_tokens(response_text, used_agent)
                    
                    # === 智能 Canvas 自动打开 — 仅在 workspace 策略下触发 ===
                    intent = result.get("analysis", {}).get("intent", "")
                    _is_doc_task = intent in ("DOCUMENT_DRAFTING", "CONTRACT_REVIEW", "CONTRACT_MANAGEMENT") or \
                        any(kw in content for kw in ['起草', '草拟', '协议', '合同', '文书', '方案', '律师函'])
                    
                    if _response_strategy == "workspace" and _is_doc_task and len(response_text) > 200:
                        canvas_type = "contract" if any(kw in content for kw in ['合同', '协议', '合伙']) else "document"
                        await _send("canvas_open", {
                            "type": canvas_type,
                            "title": req_analysis.get("summary", "文档")[:50],
                            "content": response_text,
                        })
                    
                else:
                    # 单智能体对话 — 直接回复，无需多余的思考事件
                    target_agent = agent_name or "legal_advisor"
                    display_name = agent_name or "法律顾问Agent"
                    
                    # 如果有自然追问提示，注入到单 Agent 输入中
                    _agent_input = content
                    _natural_followup = req_analysis.get("natural_followup")
                    if _natural_followup:
                        _agent_input = f"{content}\n\n[系统提示] {_natural_followup}"
                    
                    # 使用流式输出
                    try:
                        token_var = _task_llm_config_var.set(llm_config)
                        try:
                            agent_obj = workforce.agents.get(target_agent, workforce.agents["legal_advisor"])
                            token_queue = await agent_obj.stream_chat(_agent_input, llm_config=llm_config)
                            
                            accumulated = ""
                            while True:
                                tok = await asyncio.wait_for(token_queue.get(), timeout=60.0)
                                if tok is None:
                                    break
                                if tok.startswith("[Error]"):
                                    raise Exception(tok)
                                accumulated += tok
                                await _send("content_token", {
                                    "token": tok,
                                    "accumulated": accumulated,
                                    "agent": display_name,
                                })
                            
                            response_text = accumulated
                            used_agent = display_name
                        finally:
                            _task_llm_config_var.reset(token_var)
                    except Exception as stream_err:
                        logger.warning(f"流式输出失败，降级到同步: {stream_err}")
                        response_text = await workforce.chat(_agent_input, agent_name, context={"llm_config": llm_config})
                        used_agent = agent_name or "法律顾问Agent"
                        # 将同步结果流式推送
                        await _stream_response_tokens(response_text, used_agent)
                
                # === 隐私还原 ===
                if recovery_map:
                    response_text = pii_service.restore(response_text, recovery_map)
                    response_text += "\n\n*(注：本回复基于脱敏数据生成，敏感信息已在本地自动还原)*"
                
                # === 生成 A2UI — 仅在非 chat_only 策略时发送 ===
                if _response_strategy != "chat_only":
                    panel_data = build_response_a2ui(used_agent, response_text, content)
                    if panel_data:
                        # 如果 panel_data 包含 A2UI 组件，尝试流式推送到对话流
                        _panel_components = []
                        if isinstance(panel_data, dict):
                            _panel_components = panel_data.get("components", [])
                            if not _panel_components and panel_data.get("a2ui", {}).get("components"):
                                _panel_components = panel_data["a2ui"]["components"]
                        
                        if _panel_components and _response_strategy in ("chat_with_a2ui", "chat_with_streaming_a2ui"):
                            # chat_with_a2ui：流式推送 A2UI 组件到对话流（内联卡片）
                            await _stream_a2ui_components(
                                _panel_components,
                                agent=used_agent,
                                delay=0.12,
                            )
                        else:
                            # workspace：推送到右侧面板
                            await _send("context_update", {"context_type": "a2ui", "data": panel_data})

                # === 提取引用来源 ===
                ws_sources = extract_citations(response_text)

                # === 发送最终完成事件 ===
                await _send("done", {
                    "agent": used_agent,
                    "content": response_text,
                    "memory_id": memory_id,
                    "conversation_id": conversation_id,
                    "sources": [s.model_dump() for s in ws_sources],
                })

                await _save_message(
                    "assistant",
                    response_text,
                    used_agent,
                    citations=[s.model_dump() for s in ws_sources],
                )
                
            except Exception as e:
                logger.error(f"智能体调用失败: {e}")
                await _send("error", {"content": f"处理失败: {str(e)}"})
            
    except WebSocketDisconnect:
        _ws_closed = True
        logger.info(f"WebSocket断开连接: {session_id}")
    except RuntimeError as e:
        _ws_closed = True
        # Starlette 在连接已断开时可能抛 RuntimeError 而非 WebSocketDisconnect
        logger.info(f"WebSocket运行时断开: {session_id} ({e})")
    except Exception as e:
        _ws_closed = True
        logger.error(f"WebSocket未知异常: {session_id} - {e}")


@router.post("/feedback/memory", response_model=UnifiedResponse)
async def submit_memory_feedback(
    memory_id: str,
    rating: int,
    comment: Optional[str] = None,
):
    """
    提交情景记忆反馈
    用于强化学习（Rating >= 4 为正反馈，< 2 为负反馈）
    """
    success = await episodic_memory.update_feedback(memory_id, rating, comment or "")
    
    if success:
        return UnifiedResponse.success(message="反馈已提交，Agent 已从经验中学习")
    else:
        return UnifiedResponse.error(code=404, message="记忆记录不存在")


@router.post("/handover", response_model=UnifiedResponse)
async def create_handover(
    request: Request,
    conversation_id: str,
    summary: str,
    priority: str = "normal",
    user: Optional[User] = Depends(get_current_user),
):
    """
    创建人工交接任务
    将当前对话内容和摘要转交给人类律师
    """
    # 模拟发送邮件或工单系统
    # 实际项目中这里会调用工单系统 API 或发送邮件
    
    logger.info(f"Creating handover for conversation {conversation_id}, user {user.id if user else 'anonymous'}")
    
    # 模拟处理时间
    await asyncio.sleep(1)
    
    return UnifiedResponse.success(
        data={
            "ticket_id": f"TICKET-{conversation_id[:8]}",
            "status": "submitted",
            "estimated_response": "24小时内",
            "message": "已成功转交专业律师团队，我们将尽快与您联系。"
        }
    )


@router.get("/agents", response_model=UnifiedResponse)
async def get_available_agents():
    """获取可用的智能体列表"""
    workforce = get_workforce()
    data = {
        "agents": workforce.get_agents_info()
    }
    return UnifiedResponse.success(data=data)


@router.get("/conversations/{conversation_id}/canvas", response_model=UnifiedResponse)
async def get_conversation_canvas(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取对话关联的 Canvas 文档内容"""
    try:
        from src.models.document import Document as DocModel
        from sqlalchemy import select as sa_select, and_, cast, String
        
        result = await db.execute(
            sa_select(DocModel).where(
                and_(
                    DocModel.doc_metadata.isnot(None),
                    cast(DocModel.doc_metadata["conversation_id"], String) == conversation_id,
                    DocModel.description.like("Canvas:%"),
                )
            ).order_by(DocModel.updated_at.desc()).limit(1)
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            return UnifiedResponse.success(data=None, message="无关联文档")
        
        # 读取文档内容
        content = doc.extracted_text or ""
        if not content and doc.file_path:
            # 尝试从文件路径读取
            try:
                from pathlib import Path
                fp = Path(doc.file_path)
                if fp.exists():
                    content = fp.read_text(encoding="utf-8")
            except Exception:
                pass
        
        return UnifiedResponse.success(data={
            "document_id": doc.id,
            "title": doc.name,
            "content": content,
            "type": doc.doc_type.value if doc.doc_type else "document",
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
        })
    except Exception as e:
        logger.error(f"获取 Canvas 文档失败: {e}")
        return UnifiedResponse.success(data=None, message="获取失败")
