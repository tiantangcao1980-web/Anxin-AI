"""AI对话路由"""

import json
import asyncio
from typing import Optional, List, AsyncGenerator
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.core.responses import UnifiedResponse
from src.core.database import get_db
from src.core.deps import (
    get_current_user_required,
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
from src.core.privacy import InferenceRequest, SensitivityLevel
from src.api.routes.chat_handlers import (
    WebSocketContext,
    handle_a2ui_event,
    handle_workspace_message,
    handle_canvas_message,
    handle_due_diligence,
    handle_rag_query,
)

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
    model_id: Optional[str] = None  # 指定使用的 LLM 配置 ID

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        """拒绝空消息和纯空白消息，避免触发整条生成链路"""
        normalized = value.strip()
        if not normalized:
            raise ValueError("消息内容不能为空")
        return normalized


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
    user: User = Depends(get_current_user_required),
    _: None = Depends(rate_limit_chat),
):
    """发送消息并获取AI回复"""
    service = ChatService(db)
    
    result = await service.chat(
        content=message.content,
        conversation_id=message.conversation_id,
        user_id=user.id,
        case_id=message.case_id,
        agent_name=message.agent_name,
        mode=message.mode,
        knowledge_base_ids=message.knowledge_base_ids,
        model_id=message.model_id,
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
    keyword: Optional[str] = None,
    starred: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取对话历史（支持关键字搜索和收藏过滤）"""
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
            user_id=user.id,
            case_id=case_id,
            keyword=keyword,
            starred_only=starred or False,
            limit=limit,
        )
        data = {
            "conversations": [
                {
                    "id": c.id,
                    "title": c.title,
                    "message_count": c.message_count,
                    "is_starred": getattr(c, "is_starred", False),
                    "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
                    "created_at": c.created_at.isoformat(),
                }
                for c in conversations
            ],
            "total": len(conversations)
        }
        return UnifiedResponse.success(data=data)


@router.post("/conversations/{conversation_id}/star", response_model=UnifiedResponse)
async def toggle_conversation_star(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """切换对话收藏状态"""
    service = ChatService(db)
    new_state = await service.toggle_star(conversation_id)
    if new_state is None:
        return UnifiedResponse.error(message="对话不存在", code=404)
    await db.commit()
    return UnifiedResponse.success(data={"is_starred": new_state})


@router.get("/messages/search", response_model=UnifiedResponse)
async def search_messages(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """跨对话搜索消息内容"""
    service = ChatService(db)
    results = await service.search_messages(keyword=q, user_id=user.id, limit=limit)
    return UnifiedResponse.success(data={"results": results, "total": len(results)})


@router.delete("/conversations/{conversation_id}", response_model=UnifiedResponse)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
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
    user: User = Depends(get_current_user_required),
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
    user: User = Depends(get_current_user_required),
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
    admin: User = Depends(get_current_user_required),
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
    user: User = Depends(get_current_user_required),
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
                user_id=user.id,
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
    from src.services.chat_service import ChatService
    from src.agents.base import _task_llm_config_var

    # --- 尝试导入 a2ui_builder（可选模块） ---
    try:
        from src.services.a2ui_builder import build_response_a2ui
    except ImportError:
        def build_response_a2ui(*args, **kwargs):
            return None

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

    # 创建 WebSocket 上下文对象（封装所有共享状态和辅助方法）
    ctx = WebSocketContext(websocket, session_id, conversation_id, workforce)

    # 订阅 EventBus
    async def event_handler(event_data):
        if ctx._ws_closed:
            return
        try:
            await ctx.ws.send_json({"type": "event_bus_msg", "data": event_data})
        except Exception:
            pass

    await event_bus.subscribe("agent_events", event_handler)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")
            content = data.get("content", "")
            agent_name = data.get("agent_name")
            privacy_mode = data.get("privacy_mode", "HYBRID")
            
            # === A2UI 事件处理 ===
            if msg_type == "a2ui_event":
                if await handle_a2ui_event(ctx, data):
                    continue
                content = f"用户执行了操作: {data.get('action_id', '')}"

            # === 工作台确认/动作 ===
            if msg_type in ("workspace_confirmation_response", "workspace_action"):
                handled, new_type, new_data = await handle_workspace_message(ctx, msg_type, data)
                if handled and new_type is None:
                    continue
                if handled and new_type:
                    msg_type = new_type
                    data = new_data
                    content = data.get("content", "")

            # === Canvas ===
            if msg_type in ("canvas_edit", "canvas_request"):
                if await handle_canvas_message(ctx, msg_type, data):
                    continue
            
            # === 1. 算力路由与隐私检查 ===
            try:
                sensitivity = SensitivityLevel(privacy_mode)
                req = InferenceRequest(prompt=content, sensitivity=sensitivity)
                processed_content, recovery_map = await compute_router.route_request(req)

                if sensitivity == SensitivityLevel.CONFIDENTIAL:
                    await ctx.send("agent_thinking", {"agent": "\u672c\u5730\u5b89\u5168\u82af\u7247", "message": "\u6b63\u5728\u672c\u5730\u786c\u4ef6\u5b89\u5168\u533a\u8fdb\u884c\u63a8\u7406..."})
                    await ctx.send("agent_response", {"agent": "AI\u79c1\u6709\u52a9\u624b(Local)", "content": processed_content})
                    await ctx.save_message("user", content)
                    await ctx.save_message("assistant", processed_content, "AI\u79c1\u6709\u52a9\u624b(Local)")
                    continue

                content = processed_content

            except Exception as e:
                logger.error(f"\u7b97\u529b\u8def\u7531\u5931\u8d25: {e}")
                await ctx.send("error", {"content": f"\u5b89\u5168\u68c0\u67e5\u5931\u8d25: {str(e)}"})
                continue

            # === \u6301\u4e45\u5316\u7528\u6237\u6d88\u606f & \u66f4\u65b0\u4f1a\u8bdd\u8ba1\u6570\u5668 ===
            await ctx.save_message("user", content)
            recent_history = await ctx.load_recent_history(limit=10)
            ctx.session_message_count += 1
            ctx.last_user_content = content

            # === 文件内容注入：将附件文本提取并拼接到用户消息中 ===
            _document_id = data.get("document_id")
            if _document_id:
                try:
                    await ctx.send("agent_thinking", {"agent": "文档解析", "message": "正在提取附件内容..."})
                    async with async_session_maker() as _doc_db:
                        from src.services.document_service import DocumentService
                        _doc_svc = DocumentService(_doc_db)
                        _doc = await _doc_svc.get_document(_document_id)
                        if _doc:
                            _extracted = _doc.extracted_text or ""
                            # 如果文档没有已提取的文本，实时解析
                            if not _extracted.strip() and _doc.file_path:
                                from src.services.document_parser import DocumentParser
                                _parser = DocumentParser()
                                _parse_result = await _parser.parse_file(file_path=_doc.file_path)
                                _extracted = _parse_result.get("text", "")
                                if _extracted:
                                    _doc.extracted_text = _extracted
                                    await _doc_db.commit()
                            if _extracted.strip():
                                _max_chars = 8000
                                _truncated = _extracted[:_max_chars]
                                if len(_extracted) > _max_chars:
                                    _truncated += f"\n\n...（文档共 {len(_extracted)} 字，已截取前 {_max_chars} 字）"
                                content = f"{content}\n\n[附件内容 - {_doc.name}]\n{_truncated}"
                                await ctx.send("file_parsed", {
                                    "document_id": _document_id,
                                    "file_name": _doc.name,
                                    "char_count": len(_extracted),
                                    "truncated": len(_extracted) > _max_chars,
                                })
                            else:
                                await ctx.send("file_parsed", {
                                    "document_id": _document_id,
                                    "file_name": getattr(_doc, 'name', ''),
                                    "error": "无法提取文件内容",
                                })
                except Exception as _doc_err:
                    logger.warning(f"文件内容注入失败: {_doc_err}")
                    await ctx.send("file_parsed", {"document_id": _document_id, "error": str(_doc_err)})

            # === 企业调查强路由 ===
            dd_result = await handle_due_diligence(ctx, content, agent_name, recovery_map)
            if dd_result is not None:
                continue

            # === 知识库研究模式 ===
            _ws_user_id = data.get("user_id")
            if await handle_rag_query(ctx, content, data, agent_name, recovery_map, user_id=_ws_user_id):
                continue
            
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
            llm_config = await ctx.load_llm_config()

            # === 1.5 对话修复检测 — 矛盾/主题跳转（纯规则，< 1ms） ===
            if msg_type != "clarification_response" and recent_history and len(recent_history) >= 2:
                try:
                    from src.services.prompt_assembler import prompt_assembler
                    _repair = prompt_assembler.detect_contradiction(content, recent_history)
                    if _repair:
                        logger.info(f"对话修复检测: {_repair['type']}")
                        await ctx.send("conversation_repair", {
                            "repair_type": _repair["type"],
                            "message": _repair["message"],
                            "options": _repair.get("options", []),
                            "original_content": content,
                        })
                        await ctx.save_message("assistant", _repair["message"], "需求分析Agent")
                        continue
                except Exception as _repair_err:
                    logger.debug(f"对话修复检测跳过: {_repair_err}")

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
                await ctx.save_message("user", content)
                req_analysis = {"is_complete": True, "summary": content[:100], "complexity": "moderate"}
                _is_simple = False
                _is_complex_by_keyword = True
            elif _is_simple:
                # === 快速路径：简单消息直接回复，不走需求分析和意图识别 ===
                req_analysis = {"is_complete": True, "summary": content, "complexity": "simple"}
                logger.info(f"快速路径：简单消息 '{content[:20]}' 直接回复")
            elif not _is_simple:
                # === 所有非简单消息统一走合并需求分析+意图识别 ===
                # （修复"中间层黑洞"：原来没命中关键词的消息被跳过分析）
                await ctx.send("agent_thinking", {"agent": "需求分析Agent", "message": "正在分析您的需求..."})

                try:
                    token = _task_llm_config_var.set(llm_config)
                    try:
                        req_analysis = await workforce.coordinator.analyze_and_classify(
                            content,
                            has_attachments=bool(data.get("has_attachments")),
                            llm_config=llm_config,
                        )
                    finally:
                        _task_llm_config_var.reset(token)

                    # 推送需求分析结果到右侧工作台
                    await ctx.send("requirement_analysis", req_analysis)

                    # 就绪度评分推送（阶段4能力：让用户看到信息收集进度）
                    _completeness_score = req_analysis.get("completeness_score", 1.0)
                    _filled_slots = req_analysis.get("filled_slots", [])
                    _missing_elements = req_analysis.get("missing_elements", [])
                    await ctx.send("thinking_content", {
                        "agent": "需求分析Agent",
                        "content": (
                            f"**需求摘要**: {req_analysis.get('summary', '')}\n\n"
                            f"**复杂度**: {req_analysis.get('complexity', 'simple')}\n\n"
                            f"**信息就绪度**: {int(_completeness_score * 100)}%"
                            + (f"\n\n**已收集**: {', '.join(s.get('label', '') for s in _filled_slots)}" if _filled_slots else "")
                            + (f"\n\n**待补充**: {', '.join(_missing_elements)}" if _missing_elements else "")
                        ),
                        "phase": "requirement",
                        "readiness_score": _completeness_score,
                        "filled_slots": _filled_slots,
                        "missing_elements": _missing_elements,
                    })

                    # 如果需求不完整，智能选择澄清方式
                    if not req_analysis.get("is_complete", True) and req_analysis.get("guidance_questions"):
                        guidance_qs = req_analysis.get("guidance_questions", [])

                        # 判断是否需要结构化多选（多项并行选择场景）
                        _needs_structured = len(guidance_qs) >= 2 or any(
                            len(q.get("options", [])) > 3 for q in guidance_qs if isinstance(q, dict)
                        )

                        if _needs_structured:
                            # 结构化场景：使用 ClarificationBubble
                            await ctx.send("clarification_request", {
                                "message": f"为了更好地帮助您，请补充以下信息：\n\n需求摘要：{req_analysis.get('summary', '')}",
                                "questions": guidance_qs,
                                "original_content": content,
                                "requirement_summary": req_analysis.get("summary", ""),
                                "readiness_score": _completeness_score,
                            })
                            await ctx.save_message("assistant", req_analysis.get("summary", ""), "需求分析Agent")
                            continue
                        else:
                            # 简单追问场景：Agent 通过自然对话追问，不中断流程
                            questions_text = "\n".join(
                                f"- {q.get('question', q) if isinstance(q, dict) else q}"
                                for q in guidance_qs
                            )
                            req_analysis["is_complete"] = True
                            req_analysis["natural_followup"] = (
                                f"请在回复中自然地向用户追问以下信息（不要使用列表形式，"
                                f"用对话的方式友好地询问）：\n{questions_text}"
                            )

                except Exception as e:
                    logger.warning(f"需求分析失败，继续处理: {e}")
                    req_analysis = {"is_complete": True, "summary": content[:100], "complexity": "simple"}
            
            try:
                # 判断是否需要多智能体协作
                complexity = req_analysis.get("complexity", "simple")
                _has_legal_intent = req_analysis.get("intent") not in (None, "", "QA_CONSULTATION") or _is_complex_by_keyword
                is_complex = (complexity in ("moderate", "complex") or _has_legal_intent) and not _is_simple
                
                memory_id = None
                # 默认响应策略 — 简单路径为 chat_only，复杂路径由 Coordinator 决定
                _response_strategy = "chat_only"
                
                if is_complex:
                    # 执行任务上下文准备
                    _has_attachments = bool(data.get("has_attachments"))
                    _has_sufficient_info = (
                        _has_attachments
                        or len(content) > 80
                        or ctx.session_message_count > 1
                    )
                    _task_content = content
                    _natural_followup = req_analysis.get("natural_followup")
                    if _natural_followup:
                        _task_content = f"{content}\n\n[系统提示] {_natural_followup}"

                    # --- 真流式快速路径：单 Agent 意图直接走 stream_chat ---
                    _merged_intent = req_analysis.get("intent", "")
                    _merged_confidence = req_analysis.get("confidence", 0)
                    # 单 Agent 快速路径意图列表（FAST_PATH_ROUTES 中只有 1 个 task 的意图）
                    _SINGLE_AGENT_INTENTS = {
                        "QA_CONSULTATION": "legal_advisor",
                        "DUE_DILIGENCE": "due_diligence",
                        "DOCUMENT_DRAFTING": "document_drafter",
                        "IP_PROTECTION": "ip_specialist",
                        "REGULATORY_MONITORING": "regulatory_monitor",
                        "TAX_FINANCE": "tax_compliance",
                        "LABOR_HR": "labor_compliance",
                        "EVIDENCE_PROCESSING": "evidence_analyst",
                        "E_SIGNATURE": "contract_steward",
                        "CONTRACT_MANAGEMENT": "contract_steward",
                        "POLICY_DISTRIBUTION": "labor_compliance",
                    }
                    _fast_agent = _SINGLE_AGENT_INTENTS.get(_merged_intent) if _merged_confidence >= 0.7 else None

                    if _fast_agent and _fast_agent in workforce.agents:
                        # 真流式：单 Agent 直接 stream_chat，首 token 延迟最低
                        logger.info(f"⚡ 真流式快速路径: intent={_merged_intent}, agent={_fast_agent}")
                        await ctx.send("agent_start", {
                            "agent": workforce.agents[_fast_agent].name,
                            "message": f"{workforce.agents[_fast_agent].name} 正在处理...",
                        })

                        try:
                            _agent_obj = workforce.agents[_fast_agent]
                            token_var = _task_llm_config_var.set(llm_config)
                            try:
                                _dynamic_max_tokens = ctx.estimate_max_tokens(
                                    content, req_analysis.get("complexity", "moderate"), _merged_intent
                                )
                                token_queue = await _agent_obj.stream_chat(
                                    _task_content,
                                    llm_config=llm_config,
                                    history=recent_history,
                                    max_tokens=_dynamic_max_tokens,
                                )

                                response_text = ""
                                while True:
                                    token = await token_queue.get()
                                    if token is None:
                                        break
                                    response_text += token
                                    await ctx.send("content_token", {
                                        "token": token,
                                        "accumulated": response_text,
                                        "agent": _agent_obj.name,
                                    })
                            finally:
                                _task_llm_config_var.reset(token_var)

                            used_agent = _fast_agent
                            _response_strategy = "chat_only"
                            memory_id = None
                        except Exception as fast_err:
                            logger.warning(f"真流式快速路径失败，降级到 process_task: {fast_err}")
                            _fast_agent = None  # 标记降级

                    if not _fast_agent:
                        # --- 完整 DAG 路径：多 Agent 协作 ---
                        await ctx.send("agent_start", {
                            "agent": "协调调度Agent",
                            "message": "正在分配最佳智能体处理您的需求...",
                        })

                        _task_context = {
                            "llm_config": llm_config,
                            "history": recent_history,
                            "intent_hint": _intent_hint,
                            "conversation_turns": ctx.session_message_count,
                            "has_sufficient_info": _has_sufficient_info,
                            "files": [data.get("document_id")] if data.get("document_id") else [],
                            "mode": data.get("mode", "chat"),
                            "pre_intent": req_analysis.get("intent"),
                            "pre_confidence": req_analysis.get("confidence", 0),
                        }

                        result = await workforce.process_task(
                            _task_content,
                            context=_task_context,
                            ws_callback=ctx.ws_callback,
                        )
                        memory_id = result.get("memory_id")

                        # 根据 response_strategy 决定是否触发右侧面板
                        _response_strategy = result.get("analysis", {}).get("response_strategy", "chat_only")
                        if _response_strategy == "workspace":
                            await ctx.send("panel_trigger", {"reason": "complex_task", "tab": "smart"})

                        # 提取 A2UI 数据
                        a2ui_data = None
                        a2ui_components = []
                        for res in result.get("agent_results", []):
                            if isinstance(res, dict) and res.get("metadata", {}).get("a2ui"):
                                a2ui_data = res["metadata"]["a2ui"]
                                if isinstance(a2ui_data, dict) and a2ui_data.get("components"):
                                    a2ui_components.extend(a2ui_data["components"])
                                elif isinstance(a2ui_data, dict) and a2ui_data.get("a2ui", {}).get("components"):
                                    a2ui_components.extend(a2ui_data["a2ui"]["components"])

                        # 提取响应文本
                        response_text = result.get("final_result", {}).get("summary", "")
                        if not response_text:
                            for ar in result.get("agent_results", []):
                                if isinstance(ar, dict) and ar.get("content"):
                                    response_text = ar["content"]
                                    break
                        if not response_text:
                            response_text = await workforce.chat(
                                content,
                                context={"llm_config": llm_config, "history": recent_history},
                            )
                        used_agent = "智能体团队"

                        # 根据 response_strategy 控制 A2UI 发送
                        if _response_strategy != "chat_only":
                            if a2ui_components and _response_strategy in ("chat_with_a2ui", "chat_with_streaming_a2ui"):
                                await ctx.stream_a2ui_components(
                                    a2ui_components,
                                    agent=used_agent,
                                    delay=0.04,
                                )
                            elif a2ui_data:
                                await ctx.send("context_update", {"context_type": "a2ui", "data": a2ui_data})

                        # 伪流式推送多智能体汇总结果
                        await ctx.stream_response_tokens(response_text, used_agent)

                        # === 智能 Canvas 自动打开 — 仅在 workspace 策略下触发 ===
                        intent = result.get("analysis", {}).get("intent", "")
                        _is_doc_task = intent in ("DOCUMENT_DRAFTING", "CONTRACT_REVIEW", "CONTRACT_MANAGEMENT") or \
                            any(kw in content for kw in ['起草', '草拟', '协议', '合同', '文书', '方案', '律师函'])

                        if _response_strategy == "workspace" and _is_doc_task and len(response_text) > 200:
                            canvas_type = "contract" if any(kw in content for kw in ['合同', '协议', '合伙']) else "document"
                            await ctx.send("canvas_open", {
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
                            _simple_max_tokens = ctx.estimate_max_tokens(
                                content, req_analysis.get("complexity", "simple"),
                            )
                            token_queue = await agent_obj.stream_chat(
                                _agent_input,
                                llm_config=llm_config,
                                history=recent_history,
                                max_tokens=_simple_max_tokens,
                            )
                            
                            accumulated = ""
                            while True:
                                tok = await asyncio.wait_for(token_queue.get(), timeout=60.0)
                                if tok is None:
                                    break
                                if tok.startswith("[Error]"):
                                    raise Exception(tok)
                                accumulated += tok
                                await ctx.send("content_token", {
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
                        response_text = await workforce.chat(
                            _agent_input,
                            agent_name,
                            context={"llm_config": llm_config, "history": recent_history},
                        )
                        used_agent = agent_name or "法律顾问Agent"
                        # 将同步结果流式推送
                        await ctx.stream_response_tokens(response_text, used_agent)
                
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
                            await ctx.stream_a2ui_components(
                                _panel_components,
                                agent=used_agent,
                                delay=0.12,
                            )
                        else:
                            # workspace：推送到右侧面板
                            await ctx.send("context_update", {"context_type": "a2ui", "data": panel_data})

                # === 提取引用来源 ===
                ws_sources = extract_citations(response_text)

                # === 发送最终完成事件 ===
                await ctx.send("done", {
                    "agent": used_agent,
                    "content": response_text,
                    "memory_id": memory_id,
                    "conversation_id": conversation_id,
                    "sources": [s.model_dump() for s in ws_sources],
                })

                await ctx.save_message(
                    "assistant",
                    response_text,
                    used_agent,
                    citations=[s.model_dump() for s in ws_sources],
                )

                # === 经验沉淀：保存需求发掘路径到情景记忆 ===
                try:
                    _discovery_intent = req_analysis.get("intent", "")
                    _guidance_qs = req_analysis.get("guidance_questions", [])
                    _filled_slots = req_analysis.get("filled_slots", [])
                    if _discovery_intent and (_guidance_qs or _filled_slots):
                        from src.services.episodic_memory_service import episodic_memory
                        await episodic_memory.add_discovery_path(
                            intent=_discovery_intent,
                            user_input=content[:500],
                            clarification_rounds=1 if msg_type == "clarification_response" else 0,
                            questions_asked=_guidance_qs,
                            user_answers={},
                            filled_slots=_filled_slots,
                            metadata={"conversation_id": conversation_id},
                        )
                except Exception as _mem_err:
                    logger.debug(f"经验沉淀跳过: {_mem_err}")

                # === 用户画像更新 ===
                try:
                    _ws_user_id = data.get("user_id") or ctx.user_id
                    if _ws_user_id:
                        from src.services.user_profile_service import UserProfileService
                        async with async_session_maker() as _profile_db:
                            _profile_svc = UserProfileService(_profile_db)
                            await _profile_svc.update_after_session(
                                user_id=_ws_user_id,
                                intent=req_analysis.get("intent", "QA_CONSULTATION"),
                                clarification_rounds=1 if msg_type == "clarification_response" else 0,
                                user_input_sample=content[:300],
                            )
                            await _profile_db.commit()
                except Exception as _profile_err:
                    logger.debug(f"用户画像更新跳过: {_profile_err}")

            except Exception as e:
                logger.error(f"智能体调用失败: {e}")
                await ctx.send("error", {"content": f"处理失败: {str(e)}"})
            
    except WebSocketDisconnect:
        ctx._ws_closed = True
        logger.info(f"WebSocket断开连接: {session_id}")
    except RuntimeError as e:
        ctx._ws_closed = True
        # Starlette 在连接已断开时可能抛 RuntimeError 而非 WebSocketDisconnect
        logger.info(f"WebSocket运行时断开: {session_id} ({e})")
    except Exception as e:
        ctx._ws_closed = True
        logger.error(f"WebSocket未知异常: {session_id} - {e}")


@router.post("/feedback/memory", response_model=UnifiedResponse)
async def submit_memory_feedback(
    memory_id: str,
    rating: int,
    comment: Optional[str] = None,
    user: User = Depends(get_current_user_required),
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
    user: User = Depends(get_current_user_required),
):
    """
    创建人工交接任务
    将当前对话内容和摘要转交给人类律师
    """
    # 模拟发送邮件或工单系统
    # 实际项目中这里会调用工单系统 API 或发送邮件
    
    logger.info(f"Creating handover for conversation {conversation_id}, user {user.id}")
    
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
async def get_available_agents(user: User = Depends(get_current_user_required)):
    """获取可用的智能体列表"""
    workforce = get_workforce()
    data = {
        "agents": workforce.get_agents_info()
    }
    return UnifiedResponse.success(data=data)


@router.get("/models", response_model=UnifiedResponse)
async def get_available_models(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取可用的 LLM 模型列表（供对话中切换模型使用）"""
    from src.services.llm_service import LLMService
    result = await LLMService.list_configs(db, config_type="llm", is_active=True, page_size=50)
    configs = result.get("items", [])
    models = [
        {
            "id": str(c.id),
            "name": c.name,
            "provider": c.provider,
            "model": c.model_name,
            "is_default": c.is_default,
        }
        for c in configs
    ]
    return UnifiedResponse.success(data={"models": models})


@router.get("/conversations/{conversation_id}/canvas", response_model=UnifiedResponse)
async def get_conversation_canvas(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
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
