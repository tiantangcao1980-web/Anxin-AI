# -*- coding: utf-8 -*-
"""A2UI 事件处理器"""

from loguru import logger
from src.api.routes.chat_handlers.context import WebSocketContext


async def handle_a2ui_event(ctx: WebSocketContext, data: dict) -> bool:
    """
    处理 A2UI 前端交互事件。

    Returns:
        True 表示已处理（caller 应 continue），False 表示需要回退到对话流。
    """
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
            context={"conversation_id": ctx.conversation_id},
        )
        if a2ui_response:
            await ctx.send(a2ui_response.get("type", "a2ui_message"), a2ui_response)
            await ctx.save_message("user", f"[用户操作] {a2ui_action_id}")
            await ctx.save_message("assistant", f"[A2UI 交互响应] {a2ui_action_id}", "A2UI Agent")
            await ctx.send("done", {
                "conversation_id": ctx.conversation_id,
                "a2ui": True,
            })
            return True
        else:
            logger.warning(f"[A2UI] action '{a2ui_action_id}' 无匹配处理器，回退到对话流")
            return False
    except Exception as e:
        logger.error(f"A2UI 事件处理失败: {e}", exc_info=True)
        await ctx.send("error", {"content": f"操作处理失败: {str(e)}"})
        return True
