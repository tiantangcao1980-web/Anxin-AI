"""
A2UI 协议定义与组件构建器 (Agent-to-UI Protocol)

提供后端生成 A2UI JSON 的工具函数。
Agent 使用这些函数构建结构化 UI 描述，通过 WebSocket/SSE 推送给前端渲染。
"""

import uuid
from typing import Any

JSONDict = dict[str, Any]
StringDict = dict[str, str]

# A2UI 协议版本（语义化版本）：
#   - major：不兼容的协议变更（前端必须升级）
#   - minor：向后兼容的新增字段/事件类型
#   - patch：错误修复
# 老客户端遇到 minor 不识别字段应忽略；遇到 major 不一致应提示用户升级。
A2UI_PROTOCOL_VERSION = "1.0.0"


def make_id() -> str:
    return str(uuid.uuid4())[:8]


# ========== 推荐卡片 ==========


def recommendation_card(
    title: str,
    *,
    subtitle: str | None = None,
    description: str | None = None,
    image: str | None = None,
    image_fallback: str | None = None,
    rating: float | None = None,
    rating_text: str | None = None,
    tags: list[StringDict] | None = None,
    meta: str | None = None,
    price: JSONDict | None = None,
    details: list[StringDict] | None = None,
    action: JSONDict | None = None,
    secondary_action: JSONDict | None = None,
    component_id: str | None = None,
) -> JSONDict:
    data: JSONDict = {"title": title}
    if subtitle:
        data["subtitle"] = subtitle
    if description:
        data["description"] = description
    if image:
        data["image"] = image
    if image_fallback:
        data["imageFallback"] = image_fallback
    if rating is not None:
        data["rating"] = rating
    if rating_text:
        data["ratingText"] = rating_text
    if tags:
        data["tags"] = tags
    if meta:
        data["meta"] = meta
    if price:
        data["price"] = price
    if details:
        data["details"] = details
    if action:
        data["action"] = action
    if secondary_action:
        data["secondaryAction"] = secondary_action
    return {"id": component_id or make_id(), "type": "recommendation-card", "data": data}


# ========== 律师卡片 ==========


def lawyer_card(
    lawyer_id: str,
    name: str,
    firm: str,
    specialties: list[str],
    rating: float,
    status: str = "online",
    *,
    avatar: str | None = None,
    title: str | None = None,
    win_rate: str | None = None,
    experience: str | None = None,
    response_time: str | None = None,
    consult_fee: JSONDict | None = None,
    introduction: str | None = None,
    action: JSONDict | None = None,
    component_id: str | None = None,
) -> JSONDict:
    data: JSONDict = {
        "lawyerId": lawyer_id,
        "name": name,
        "firm": firm,
        "specialties": specialties,
        "rating": rating,
        "status": status,
    }
    if avatar:
        data["avatar"] = avatar
    if title:
        data["title"] = title
    if win_rate:
        data["winRate"] = win_rate
    if experience:
        data["experience"] = experience
    if response_time:
        data["responseTime"] = response_time
    if consult_fee:
        data["consultFee"] = consult_fee
    if introduction:
        data["introduction"] = introduction
    if action:
        data["action"] = action
    return {"id": component_id or make_id(), "type": "lawyer-card", "data": data}


# ========== 横滑列表 ==========


def horizontal_scroll(
    items: list[JSONDict],
    *,
    title: str | None = None,
    show_arrows: bool = True,
    visible_count: int | None = None,
    component_id: str | None = None,
) -> JSONDict:
    data: JSONDict = {"items": items, "showArrows": show_arrows}
    if title:
        data["title"] = title
    if visible_count:
        data["visibleCount"] = visible_count
    return {"id": component_id or make_id(), "type": "horizontal-scroll", "data": data}


# ========== 表单 Sheet ==========


def form_sheet(
    title: str,
    sections: list[JSONDict],
    submit_action: StringDict,
    *,
    subtitle: str | None = None,
    header: JSONDict | None = None,
    cancel_action: StringDict | None = None,
    as_sheet: bool = False,
    component_id: str | None = None,
) -> JSONDict:
    data: JSONDict = {
        "title": title,
        "sections": sections,
        "submitAction": submit_action,
    }
    if subtitle:
        data["subtitle"] = subtitle
    if header:
        data["header"] = header
    if cancel_action:
        data["cancelAction"] = cancel_action
    if as_sheet:
        data["asSheet"] = True
    return {"id": component_id or make_id(), "type": "form-sheet", "data": data}


def form_section(
    section_id: str,
    label: str,
    section_type: str = "single-select",
    *,
    description: str | None = None,
    required: bool = False,
    options: list[JSONDict] | None = None,
    default_value: Any = None,
    placeholder: str | None = None,
) -> JSONDict:
    data: JSONDict = {"id": section_id, "label": label, "type": section_type}
    if description:
        data["description"] = description
    if required:
        data["required"] = True
    if options:
        data["options"] = options
    if default_value is not None:
        data["defaultValue"] = default_value
    if placeholder:
        data["placeholder"] = placeholder
    return data


def form_option(
    option_id: str, label: str, *, description: str | None = None, price: JSONDict | None = None
) -> JSONDict:
    data: JSONDict = {"id": option_id, "label": label}
    if description:
        data["description"] = description
    if price:
        data["price"] = price
    return data


# ========== 订单/委托确认卡片 ==========


def order_card(
    item: JSONDict,
    details: list[JSONDict],
    actions: list[JSONDict],
    *,
    title: str | None = None,
    pricing: JSONDict | None = None,
    note: str | None = None,
    component_id: str | None = None,
) -> JSONDict:
    data: JSONDict = {"item": item, "details": details, "actions": actions}
    if title:
        data["title"] = title
    if pricing:
        data["pricing"] = pricing
    if note:
        data["note"] = note
    return {"id": component_id or make_id(), "type": "order-card", "data": data}


# ========== 信息横幅 ==========


def info_banner(
    content: str,
    *,
    variant: str = "info",
    icon: str | None = None,
    action: JSONDict | None = None,
    dismissible: bool = False,
    component_id: str | None = None,
) -> JSONDict:
    data: JSONDict = {"content": content, "variant": variant}
    if icon:
        data["icon"] = icon
    if action:
        data["action"] = action
    if dismissible:
        data["dismissible"] = True
    return {"id": component_id or make_id(), "type": "info-banner", "data": data}


# ========== 按钮组 ==========


def button_group(
    buttons: list[JSONDict],
    *,
    layout: str = "horizontal",
    align: str = "stretch",
    component_id: str | None = None,
) -> JSONDict:
    return {
        "id": component_id or make_id(),
        "type": "button-group",
        "data": {"buttons": buttons, "layout": layout, "align": align},
    }


# ========== 状态卡片 ==========


def status_card(
    status: str,
    title: str,
    *,
    description: str | None = None,
    action: JSONDict | None = None,
    secondary_action: JSONDict | None = None,
    component_id: str | None = None,
) -> JSONDict:
    data: JSONDict = {"status": status, "title": title}
    if description:
        data["description"] = description
    if action:
        data["action"] = action
    if secondary_action:
        data["secondaryAction"] = secondary_action
    return {"id": component_id or make_id(), "type": "status-card", "data": data}


# ========== 详情列表 ==========


def detail_list(
    items: list[JSONDict],
    *,
    title: str | None = None,
    divider: bool = True,
    component_id: str | None = None,
) -> JSONDict:
    data: JSONDict = {"items": items, "divider": divider}
    if title:
        data["title"] = title
    return {"id": component_id or make_id(), "type": "detail-list", "data": data}


# ========== 步骤进度 ==========


def progress_steps(
    steps: list[JSONDict],
    current_step: int,
    *,
    title: str | None = None,
    direction: str = "vertical",
    component_id: str | None = None,
) -> JSONDict:
    data: JSONDict = {"steps": steps, "currentStep": current_step, "direction": direction}
    if title:
        data["title"] = title
    return {"id": component_id or make_id(), "type": "progress-steps", "data": data}


# ========== 风险指标 ==========


def risk_indicator(
    title: str,
    score: int,
    level: str,
    *,
    max_score: int = 100,
    description: str | None = None,
    factors: list[JSONDict] | None = None,
    action: JSONDict | None = None,
    component_id: str | None = None,
) -> JSONDict:
    data: JSONDict = {"title": title, "score": score, "level": level, "maxScore": max_score}
    if description:
        data["description"] = description
    if factors:
        data["factors"] = factors
    if action:
        data["action"] = action
    return {"id": component_id or make_id(), "type": "risk-indicator", "data": data}


# ========== 文本块 ==========


def text_block(
    content: str,
    *,
    format: str = "markdown",
    collapsible: bool = False,
    preview_lines: int | None = None,
    component_id: str | None = None,
) -> JSONDict:
    data: JSONDict = {"content": content, "format": format}
    if collapsible:
        data["collapsible"] = True
    if preview_lines:
        data["previewLines"] = preview_lines
    return {"id": component_id or make_id(), "type": "text-block", "data": data}


# ========== 分隔线 ==========


def divider(label: str | None = None, component_id: str | None = None) -> JSONDict:
    data: JSONDict = {}
    if label:
        data["label"] = label
    return {"id": component_id or make_id(), "type": "divider", "data": data}


# ========== 服务选择 ==========


def service_selection(
    title: str,
    services: list[JSONDict],
    *,
    subtitle: str | None = None,
    component_id: str | None = None,
) -> JSONDict:
    data: JSONDict = {"title": title, "services": services}
    if subtitle:
        data["subtitle"] = subtitle
    return {"id": component_id or make_id(), "type": "service-selection", "data": data}


# ========== 合同预览 ==========


def contract_preview(
    contract_id: str,
    title: str,
    contract_type: str,
    parties: list[JSONDict],
    key_terms: list[JSONDict],
    risk_level: str,
    actions: list[JSONDict],
    *,
    risk_items: list[JSONDict] | None = None,
    component_id: str | None = None,
) -> JSONDict:
    data: JSONDict = {
        "contractId": contract_id,
        "title": title,
        "type": contract_type,
        "parties": parties,
        "keyTerms": key_terms,
        "riskLevel": risk_level,
        "actions": actions,
    }
    if risk_items:
        data["riskItems"] = risk_items
    return {"id": component_id or make_id(), "type": "contract-preview", "data": data}


# ========== 动作栏 ==========


def action_bar(
    actions: list[JSONDict],
    *,
    position: str = "bottom",
    component_id: str | None = None,
) -> JSONDict:
    """
    底部/顶部操作栏。
    actions: [{"id": "...", "label": "...", "actionId": "...", "variant": "primary|outline|ghost", "icon": "..."}]
    """
    data = {"actions": actions, "position": position}
    return {"id": component_id or make_id(), "type": "action-bar", "data": data}


# ========== 扩展接口：地图组件 ==========


def map_view(
    title: str,
    *,
    center: dict[str, float] | None = None,
    markers: list[JSONDict] | None = None,
    zoom: int = 14,
    map_provider: str = "amap",
    action: JSONDict | None = None,
    component_id: str | None = None,
) -> JSONDict:
    """
    地图视图组件（预留接口）。
    未来可对接高德/百度/Google Maps。
    markers: [{"id": "...", "lat": 39.9, "lng": 116.3, "label": "...", "info": "..."}]
    """
    data: JSONDict = {"title": title, "zoom": zoom, "mapProvider": map_provider}
    if center:
        data["center"] = center
    if markers:
        data["markers"] = markers
    if action:
        data["action"] = action
    return {"id": component_id or make_id(), "type": "map-view", "data": data}


# ========== 扩展接口：支付组件 ==========


def payment_card(
    title: str,
    amount: float,
    *,
    currency: str = "CNY",
    description: str | None = None,
    payment_methods: list[JSONDict] | None = None,
    order_id: str | None = None,
    pay_action: JSONDict | None = None,
    cancel_action: JSONDict | None = None,
    component_id: str | None = None,
) -> JSONDict:
    """
    支付卡片组件（预留接口）。
    未来可对接微信支付/支付宝/银行卡。
    payment_methods: [{"id": "wechat", "name": "微信支付", "icon": "wechat"}, ...]
    """
    data: JSONDict = {
        "title": title,
        "amount": amount,
        "currency": currency,
    }
    if description:
        data["description"] = description
    if payment_methods:
        data["paymentMethods"] = payment_methods
    if order_id:
        data["orderId"] = order_id
    if pay_action:
        data["payAction"] = pay_action
    if cancel_action:
        data["cancelAction"] = cancel_action
    return {"id": component_id or make_id(), "type": "payment-card", "data": data}


# ========== 扩展接口：律师选择器 ==========


def lawyer_picker(
    title: str,
    lawyers: list[JSONDict],
    *,
    filters: list[JSONDict] | None = None,
    sort_options: list[StringDict] | None = None,
    on_select_action: JSONDict | None = None,
    multi_select: bool = False,
    component_id: str | None = None,
) -> JSONDict:
    """
    律师选择器组件（预留接口）。
    支持筛选、排序、多选等功能。
    filters: [{"id": "specialty", "label": "专长", "options": [...]}, ...]
    sort_options: [{"id": "rating", "label": "评分"}, {"id": "price", "label": "价格"}]
    """
    data: JSONDict = {"title": title, "lawyers": lawyers, "multiSelect": multi_select}
    if filters:
        data["filters"] = filters
    if sort_options:
        data["sortOptions"] = sort_options
    if on_select_action:
        data["onSelectAction"] = on_select_action
    return {"id": component_id or make_id(), "type": "lawyer-picker", "data": data}


# ========== 扩展接口：媒体卡片（图片/视频/文件预览） ==========


def media_card(
    title: str,
    media_type: str,
    url: str,
    *,
    thumbnail: str | None = None,
    description: str | None = None,
    size: str | None = None,
    action: JSONDict | None = None,
    component_id: str | None = None,
) -> JSONDict:
    """
    媒体预览卡片。
    media_type: "image" | "video" | "pdf" | "document"
    """
    data: JSONDict = {"title": title, "mediaType": media_type, "url": url}
    if thumbnail:
        data["thumbnail"] = thumbnail
    if description:
        data["description"] = description
    if size:
        data["size"] = size
    if action:
        data["action"] = action
    return {"id": component_id or make_id(), "type": "media-card", "data": data}


# ========== 扩展接口：日程/预约组件 ==========


def schedule_picker(
    title: str,
    available_slots: list[JSONDict],
    *,
    subtitle: str | None = None,
    duration_options: list[JSONDict] | None = None,
    on_select_action: JSONDict | None = None,
    component_id: str | None = None,
) -> JSONDict:
    """
    日程预约组件（预留接口）。
    available_slots: [{"id": "...", "date": "2026-02-10", "time": "10:00", "available": true}]
    """
    data: JSONDict = {"title": title, "availableSlots": available_slots}
    if subtitle:
        data["subtitle"] = subtitle
    if duration_options:
        data["durationOptions"] = duration_options
    if on_select_action:
        data["onSelectAction"] = on_select_action
    return {"id": component_id or make_id(), "type": "schedule-picker", "data": data}


# ========== 扩展接口：评价/反馈组件 ==========


def feedback_card(
    title: str,
    *,
    rating_enabled: bool = True,
    comment_enabled: bool = True,
    tags: list[str] | None = None,
    submit_action: JSONDict | None = None,
    component_id: str | None = None,
) -> JSONDict:
    """
    评价反馈组件。
    """
    data: JSONDict = {
        "title": title,
        "ratingEnabled": rating_enabled,
        "commentEnabled": comment_enabled,
    }
    if tags:
        data["tags"] = tags
    if submit_action:
        data["submitAction"] = submit_action
    return {"id": component_id or make_id(), "type": "feedback-card", "data": data}


# ========== 扩展接口：通用插件容器 ==========


def plugin_container(
    plugin_type: str,
    config: JSONDict,
    *,
    title: str | None = None,
    fallback_text: str = "该功能即将开放",
    component_id: str | None = None,
) -> JSONDict:
    """
    通用插件容器 — Skills/MCP 扩展的统一接口。
    plugin_type: 插件类型标识（如 "mcp_tool", "skill_action"）
    config: 插件配置数据
    """
    data: JSONDict = {
        "pluginType": plugin_type,
        "config": config,
        "fallbackText": fallback_text,
    }
    if title:
        data["title"] = title
    return {"id": component_id or make_id(), "type": "plugin-container", "data": data}


# ========== A2UI 消息包装器 ==========


def a2ui_message(
    components: list[JSONDict],
    *,
    text: str = "",
    agent: str = "AI 助手",
    message_id: str | None = None,
) -> JSONDict:
    """
    构建完整的 A2UI 消息，用于 WebSocket 发送。

    Returns:
        WebSocket 消息格式：
        {
            "type": "a2ui_message",
            "text": "...",
            "agent": "...",
            "a2ui_id": "...",
            "components": [...],
        }
    """
    return {
        "type": "a2ui_message",
        "protocolVersion": A2UI_PROTOCOL_VERSION,
        "text": text,
        "agent": agent,
        "a2ui_id": message_id or make_id(),
        "components": components,
    }


# ========== StreamObject 流式 A2UI 协议 ==========


def a2ui_stream_start(
    stream_id: str | None = None,
    *,
    agent: str = "AI 助手",
    metadata: JSONDict | None = None,
) -> JSONDict:
    """
    构建流式 A2UI 开始事件。

    前端收到后初始化缓冲区并显示骨架屏。

    Returns:
        WebSocket 消息格式：
        {
            "type": "a2ui_stream",
            "streamId": "...",
            "action": "stream_start",
            "agent": "...",
        }
    """
    event: JSONDict = {
        "type": "a2ui_stream",
        "protocolVersion": A2UI_PROTOCOL_VERSION,
        "streamId": stream_id or make_id(),
        "action": "stream_start",
        "agent": agent,
    }
    if metadata:
        event["metadata"] = metadata
    return event


def a2ui_stream_component(
    stream_id: str,
    component: JSONDict,
    *,
    agent: str | None = None,
) -> JSONDict:
    """
    构建流式 A2UI 新增组件事件。

    向已有流追加一个完整组件（如一张律师卡片）。

    Args:
        stream_id: 流 ID（与 stream_start 一致）
        component: 完整的 A2UI 组件 dict（如 lawyer_card(...) 的返回值）

    Returns:
        WebSocket 消息格式：
        {
            "type": "a2ui_stream",
            "streamId": "...",
            "action": "stream_component",
            "component": {...},
        }
    """
    event: JSONDict = {
        "type": "a2ui_stream",
        "streamId": stream_id,
        "action": "stream_component",
        "component": component,
    }
    if agent:
        event["agent"] = agent
    return event


def a2ui_stream_delta(
    stream_id: str,
    component_id: str,
    delta: JSONDict,
) -> JSONDict:
    """
    构建流式 A2UI 增量更新事件。

    对已有组件的 data 字段进行 deep merge 更新（例如评分加载后填入）。

    Args:
        stream_id: 流 ID
        component_id: 要更新的组件 ID
        delta: 要合并到组件 data 的增量数据

    Returns:
        WebSocket 消息格式：
        {
            "type": "a2ui_stream",
            "streamId": "...",
            "action": "stream_delta",
            "componentId": "...",
            "delta": {...},
        }
    """
    return {
        "type": "a2ui_stream",
        "streamId": stream_id,
        "action": "stream_delta",
        "componentId": component_id,
        "delta": delta,
    }


def a2ui_stream_end(stream_id: str) -> JSONDict:
    """
    构建流式 A2UI 结束事件。

    前端收到后清理骨架屏，标记流为完成状态。

    Returns:
        WebSocket 消息格式：
        {
            "type": "a2ui_stream",
            "streamId": "...",
            "action": "stream_end",
        }
    """
    return {
        "type": "a2ui_stream",
        "streamId": stream_id,
        "action": "stream_end",
    }


# ========== 法务专用卡片构建器 ==========


def case_progress_card(
    case_id: str,
    title: str,
    current_phase: str,
    progress: int,
    steps: list[JSONDict],
    *,
    case_type: str | None = None,
    estimated_completion: str | None = None,
    actions: list[JSONDict] | None = None,
    component_id: str | None = None,
) -> JSONDict:
    """
    案件进度时间线卡片。

    steps: [{"id": "...", "label": "...", "status": "completed|active|pending|error", "description": "...", "timestamp": "...", "agent": "..."}]
    """
    data: JSONDict = {
        "caseId": case_id,
        "title": title,
        "currentPhase": current_phase,
        "progress": progress,
        "steps": steps,
    }
    if case_type:
        data["caseType"] = case_type
    if estimated_completion:
        data["estimatedCompletion"] = estimated_completion
    if actions:
        data["actions"] = actions
    return {"id": component_id or make_id(), "type": "case-progress", "data": data}


def risk_assessment_card(
    title: str,
    overall_score: int,
    overall_level: str,
    dimensions: list[JSONDict],
    *,
    subtitle: str | None = None,
    summary: str | None = None,
    recommendations: list[str] | None = None,
    actions: list[JSONDict] | None = None,
    component_id: str | None = None,
) -> JSONDict:
    """
    风险评估雷达图卡片。

    dimensions: [{"id": "...", "label": "...", "score": 75, "level": "medium", "trend": "up|down|stable"}]
    """
    data: JSONDict = {
        "title": title,
        "overallScore": overall_score,
        "overallLevel": overall_level,
        "dimensions": dimensions,
    }
    if subtitle:
        data["subtitle"] = subtitle
    if summary:
        data["summary"] = summary
    if recommendations:
        data["recommendations"] = recommendations
    if actions:
        data["actions"] = actions
    return {"id": component_id or make_id(), "type": "risk-assessment", "data": data}


def contract_compare_card(
    title: str,
    left_label: str,
    right_label: str,
    clauses: list[JSONDict],
    *,
    subtitle: str | None = None,
    summary: JSONDict | None = None,
    actions: list[JSONDict] | None = None,
    component_id: str | None = None,
) -> JSONDict:
    """
    合同条款对比卡片。

    clauses: [{"id": "...", "clauseTitle": "...", "changeType": "added|removed|modified|unchanged",
               "leftContent": "...", "rightContent": "...", "riskLevel": "low|medium|high", "comment": "..."}]
    """
    data: JSONDict = {
        "title": title,
        "leftLabel": left_label,
        "rightLabel": right_label,
        "clauses": clauses,
    }
    if subtitle:
        data["subtitle"] = subtitle
    if summary:
        data["summary"] = summary
    if actions:
        data["actions"] = actions
    return {"id": component_id or make_id(), "type": "contract-compare", "data": data}


def fee_estimate_card(
    title: str,
    items: list[JSONDict],
    total: JSONDict,
    *,
    subtitle: str | None = None,
    discounts: list[JSONDict] | None = None,
    packages: list[JSONDict] | None = None,
    payment_methods: list[JSONDict] | None = None,
    notes: list[str] | None = None,
    actions: list[JSONDict] | None = None,
    component_id: str | None = None,
) -> JSONDict:
    """
    费用估算卡片。

    items: [{"id": "...", "label": "...", "amount": 500, "unit": "元/小时", "optional": false}]
    total: {"label": "预计总费用", "amount": 5000, "original": 6000}
    """
    data: JSONDict = {
        "title": title,
        "items": items,
        "total": total,
    }
    if subtitle:
        data["subtitle"] = subtitle
    if discounts:
        data["discounts"] = discounts
    if packages:
        data["packages"] = packages
    if payment_methods:
        data["paymentMethods"] = payment_methods
    if notes:
        data["notes"] = notes
    if actions:
        data["actions"] = actions
    return {"id": component_id or make_id(), "type": "fee-estimate", "data": data}
