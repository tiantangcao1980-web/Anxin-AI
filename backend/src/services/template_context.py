from __future__ import annotations

from src.services.template_engine import get_template_by_id

FRONTEND_TEMPLATE_NAMES = {
    "nda": "保密协议",
    "labor": "劳动合同",
    "service": "服务协议",
    "lawyer-letter": "律师函",
    "legal-opinion": "法律意见书",
}


def resolve_template_name(template_id: str | None) -> str | None:
    if not template_id:
        return None

    template = get_template_by_id(template_id)
    return template.name if template else FRONTEND_TEMPLATE_NAMES.get(template_id)


def build_template_context_message(template_id: str | None) -> str | None:
    template_name = resolve_template_name(template_id)
    if not template_name:
        return None

    return f"当前输出模板：{template_name}\n" "请优先遵循该模板的结构、章节顺序与文书语气输出。"


def inject_template_context(content: str, template_id: str | None) -> str:
    template_message = build_template_context_message(template_id)
    if not template_message:
        return content

    return f"【{template_message}】\n" f"{content}"
