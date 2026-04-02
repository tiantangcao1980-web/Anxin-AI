# -*- coding: utf-8 -*-
"""工作台确认/动作处理器"""

from typing import Optional, Tuple
from loguru import logger
from src.api.routes.chat_handlers.context import WebSocketContext


async def handle_workspace_message(
    ctx: WebSocketContext, msg_type: str, data: dict
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    处理工作台确认回复和工作台动作事件。

    Returns:
        (handled, new_msg_type, updated_data)
        - handled=True, new_msg_type=None → 已完成处理，caller 应 continue
        - handled=True, new_msg_type="clarification_response" → 需要转换后继续走后续流程
        - handled=False → 不匹配，不处理
    """
    if msg_type == "workspace_confirmation_response":
        confirmation_id = data.get("confirmation_id", "")
        selected_ids = data.get("selected_ids", [])
        custom_text = data.get("custom_text", "")
        logger.info(f"收到工作台确认: {confirmation_id}, 选项: {selected_ids}, 自定义: {custom_text[:50] if custom_text else ''}")
        await ctx.send("workspace_confirmation_ack", {
            "confirmation_id": confirmation_id,
            "status": "received",
        })

        # 合并预设选项和自定义输入
        parts = []
        if selected_ids:
            parts.append("、".join(selected_ids))
        if custom_text:
            parts.append(custom_text)

        if parts:
            selections_text = "；".join(parts)
            data["original_content"] = ctx.last_user_content
            data["content"] = selections_text
            data["selections"] = selections_text
            if custom_text:
                data["custom_text"] = custom_text
            logger.info(f"工作台确认 → 转为 clarification_response: {selections_text[:50]}")
            return True, "clarification_response", data
        else:
            return True, None, None

    if msg_type == "workspace_action":
        action_id = data.get("action_id", "")
        payload = data.get("payload")
        logger.info(f"收到工作台动作: {action_id}, payload: {payload}")

        if action_id == "start_processing" and payload:
            await ctx.send("agent_thinking", {
                "agent": "协调调度Agent",
                "message": "收到确认，正在启动智能体协作...",
            })

            content = ctx.last_user_content or "请根据之前的需求分析结果开始处理"
            data["original_content"] = ctx.last_user_content
            data["content"] = content
            data["selections"] = "用户确认开始处理"
            logger.info("工作台开始处理 → 转为 clarification_response")
            return True, "clarification_response", data
        else:
            return True, None, None

    return False, None, None
