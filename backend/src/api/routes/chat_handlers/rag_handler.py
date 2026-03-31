# -*- coding: utf-8 -*-
"""知识库 RAG 研究模式处理器"""

from typing import Optional
from loguru import logger
from src.api.routes.chat_handlers.context import WebSocketContext


async def handle_rag_query(
    ctx: WebSocketContext,
    content: str,
    data: dict,
    agent_name: Optional[str],
    recovery_map: Optional[dict],
    user_id: Optional[str] = None,
    current_user=None,
) -> bool:
    """
    知识库研究模式：在聊天内直接执行 RAG 查询。

    Returns:
        True 表示已处理并应 continue，False 表示不匹配。
    """
    _selected_kb_ids = [
        kb_id
        for kb_id in (data.get("knowledge_base_ids") or [])
        if isinstance(kb_id, str) and kb_id
    ]
    _frontend_mode = data.get("mode", "chat")

    if not ((_frontend_mode == "research" or _selected_kb_ids) and not agent_name):
        return False

    await ctx.send("agent_thinking", {
        "agent": "知识库检索Agent",
        "message": "正在检索知识库并整理答案...",
    })

    try:
        from src.core.database import async_session_maker
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
            (float(source.get("score", 0) or 0) for source in raw_sources if isinstance(source, dict)),
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

        # 隐私还原
        if recovery_map:
            from src.services.pii_service import pii_service
            response_text = pii_service.restore(response_text, recovery_map)
            response_text += "\n\n*(注：本回复基于脱敏数据生成，敏感信息已在本地自动还原)*"

        await ctx.stream_response_tokens(response_text, "知识库检索Agent")
        await ctx.send("done", {
            "agent": "知识库检索Agent",
            "content": response_text,
            "memory_id": None,
            "conversation_id": ctx.conversation_id,
            "sources": ws_sources,
        })
        await ctx.save_message("assistant", response_text, "知识库检索Agent", citations=ws_sources)
        return True

    except Exception as rag_err:
        logger.warning(f"知识库研究模式执行失败，回退通用对话链路: {rag_err}")
        await ctx.send("error", {
            "message": f"知识库检索出错，已切换到通用对话模式。({type(rag_err).__name__})",
            "recoverable": True,
        })
        return False
