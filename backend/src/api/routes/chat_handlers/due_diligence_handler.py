"""企业尽调强路由处理器"""
from typing import Any

from loguru import logger

from src.api.routes.chat_handlers.context import WebSocketContext


async def handle_due_diligence(
    ctx: WebSocketContext,
    content: str,
    agent_name: str | None,
    recovery_map: dict[str, Any] | None,
) -> str | None:
    """
    检测并处理企业尽调请求（强路由）。

    Returns:
        响应文本（已处理） 或 None（不匹配，需走后续流程）。
    """
    from src.services.due_diligence_service import detect_company_due_diligence_request

    if agent_name:
        return None

    dd_request = detect_company_due_diligence_request(content)
    if not dd_request.get("matched"):
        return None

    used_agent = "尽职调查Agent"
    company_name = dd_request.get("company_name")

    await ctx.send("agent_thinking", {
        "agent": used_agent,
        "message": "正在识别调查对象并准备企业尽调结果...",
    })

    if not company_name:
        response_text = (
            "我已识别到您是在发起企业调查/尽调请求，但当前还缺少关键对象。"
            "请提供目标企业的完整名称，最好再补充您重点关注的范围，"
            "例如工商信息、诉讼记录、股权结构、信用情况或合作风险。"
        )
    else:
        try:
            from src.services.due_diligence_service import (
                format_due_diligence_chat_response,
                get_company_info,
            )
            company_data = await get_company_info(company_name)
            response_text = format_due_diligence_chat_response(company_name, company_data)
        except Exception as dd_err:
            logger.error(f"企业调查强路由失败: {dd_err}")
            response_text = f"我已识别到您要调查企业\u201c{company_name}\u201d，但当前尽调服务暂时无法返回可靠结果。请稍后重试，或补充统一社会信用代码和关注范围（工商/诉讼/股权/信用），我会继续按尽调流程处理。"

    # 隐私还原
    if recovery_map:
        from src.services.pii_service import pii_service
        response_text = pii_service.restore(response_text, recovery_map)
        response_text += "\n\n*(注：本回复基于脱敏数据生成，敏感信息已在本地自动还原)*"

    # 流式推送 + 保存
    await ctx.stream_response_tokens(response_text, used_agent)

    from src.services.chat_service import extract_citations
    ws_sources = extract_citations(response_text)

    await ctx.send("done", {
        "agent": used_agent,
        "content": response_text,
        "conversation_id": ctx.conversation_id,
        "sources": [s.model_dump() for s in ws_sources],
    })
    await ctx.save_message("assistant", response_text, used_agent,
                           citations=[s.model_dump() for s in ws_sources])

    return response_text
