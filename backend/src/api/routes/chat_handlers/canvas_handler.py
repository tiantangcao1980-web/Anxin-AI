# -*- coding: utf-8 -*-
"""Canvas 编辑/请求处理器"""

from loguru import logger
from src.api.routes.chat_handlers.context import WebSocketContext


async def handle_canvas_message(ctx: WebSocketContext, msg_type: str, data: dict) -> bool:
    """
    处理 Canvas 编辑保存和 AI 优化请求。

    Returns:
        True 表示已处理（caller 应 continue）。
    """
    content = data.get("content", "")

    if msg_type == "canvas_edit":
        canvas_title = data.get("title", "未命名文档")
        canvas_type = data.get("canvas_type", "document")
        logger.info(f"Canvas edit received: {len(content)} chars, title={canvas_title}")

        try:
            from src.core.database import async_session_maker
            from src.services.document_service import DocumentService
            from src.models.document import Document as DocModel
            from sqlalchemy import select as sa_select, and_, cast, String

            async with async_session_maker() as db_session:
                doc_svc = DocumentService(db_session)

                result = await db_session.execute(
                    sa_select(DocModel).where(
                        and_(
                            DocModel.doc_metadata.isnot(None),
                            cast(DocModel.doc_metadata["conversation_id"], String) == ctx.conversation_id,
                            DocModel.description.like("Canvas:%"),
                        )
                    ).order_by(DocModel.updated_at.desc()).limit(1)
                )
                existing_doc = result.scalar_one_or_none()

                if existing_doc:
                    await doc_svc.update_document_content(
                        document_id=existing_doc.id,
                        content=content,
                        change_summary="Canvas 编辑更新",
                    )
                else:
                    doc = await doc_svc.create_text_document(
                        name=canvas_title,
                        content=content,
                        doc_type=canvas_type if canvas_type in ('contract', 'document') else 'other',
                        description=f"Canvas:{canvas_title}",
                    )
                    doc.doc_metadata = {"conversation_id": ctx.conversation_id, "source": "canvas"}

                await db_session.commit()

            await ctx.send("canvas_saved", {"status": "ok", "title": canvas_title})
        except Exception as e:
            logger.warning(f"Canvas 内容保存失败: {e}")
            await ctx.send("canvas_saved", {"status": "error", "message": str(e)})
        return True

    if msg_type == "canvas_request":
        canvas_content = data.get("canvas_content", "")
        canvas_type = data.get("canvas_type", "document")

        if not canvas_content.strip():
            await ctx.send("error", {"content": "Canvas 内容为空，无法优化"})
            return True

        agent_key = "document_drafter"
        if agent_key not in ctx.workforce.agents:
            agent_key = "legal_advisor" if "legal_advisor" in ctx.workforce.agents else list(ctx.workforce.agents.keys())[0]
            logger.warning(f"document_drafter 不可用，回退使用 {agent_key}")

        llm_config = await ctx.load_llm_config()
        await ctx.send("agent_thinking", {"agent": "文书起草Agent", "message": "正在优化文档内容..."})

        try:
            from src.agents.base import _task_llm_config_var
            token = _task_llm_config_var.set(llm_config)
            try:
                optimized = await ctx.workforce.agents[agent_key].chat(
                    f"请优化以下{canvas_type}内容，保持原意但提升专业性和完整性：\n\n{canvas_content}",
                    llm_config=llm_config,
                )
            finally:
                _task_llm_config_var.reset(token)

            await ctx.send("canvas_update", {
                "content": optimized,
                "type": canvas_type,
                "title": "AI 优化版本",
            })
        except Exception as e:
            logger.error(f"Canvas 优化失败: {e}")
            await ctx.send("error", {"content": f"Canvas 优化失败: {str(e)}"})
        return True

    return False
