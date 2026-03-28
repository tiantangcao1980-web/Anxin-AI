"""
A2UI 协议定义与组件构建器 (Agent-to-UI Protocol)

提供后端生成 A2UI JSON 的工具函数。
Agent 使用这些函数构建结构化 UI 描述，通过 WebSocket/SSE 推送给前端渲染。
"""

import uuid
from typing import Optional, List, Dict, Any


def make_id() -> str:
    return str(uuid.uuid4())[:8]


# ========== 推荐卡片 ==========

def recommendation_card(
    title: str,
    *,
    subtitle: str = None,
    description: str = None,
    image: str = None,
    image_fallback: str = None,
    rating: float = None,
    rating_text: str = None,
    tags: List[Dict[str, str]] = None,
    meta: str = None,
    price: Dict[str, Any] = None,
    details: List[Dict[str, str]] = None,
    action: Dict[str, Any] = None,
    secondary_action: Dict[str, Any] = None,
    component_id: str = None,
) -> dict:
    data = {"title": title}
    if subtitle: data["subtitle"] = subtitle
    if description: data["description"] = description
    if image: data["image"] = image
    if image_fallback: data["imageFallback"] = image_fallback
    if rating is not None: data["rating"] = rating
    if rating_text: data["ratingText"] = rating_text
    if tags: data["tags"] = tags
    if meta: data["meta"] = meta
    if price: data["price"] = price
    if details: data["details"] = details
    if action: data["action"] = action
    if secondary_action: data["secondaryAction"] = secondary_action
    return {"id": component_id or make_id(), "type": "recommendation-card", "data": data}


# ========== 律师卡片 ==========

def lawyer_card(
    lawyer_id: str,
    name: str,
    firm: str,
    specialties: List[str],
    rating: float,
    status: str = "online",
    *,
    avatar: str = None,
    title: str = None,
    win_rate: str = None,
    experience: str = None,
    response_time: str = None,
    consult_fee: Dict[str, Any] = None,
    introduction: str = None,
    action: Dict[str, Any] = None,
    component_id: str = None,
) -> dict:
    data = {
        "lawyerId": lawyer_id,
        "name": name,
        "firm": firm,
        "specialties": specialties,
        "rating": rating,
        "status": status,
    }
    if avatar: data["avatar"] = avatar
    if title: data["title"] = title
    if win_rate: data["winRate"] = win_rate
    if experience: data["experience"] = experience
    if response_time: data["responseTime"] = response_time
    if consult_fee: data["consultFee"] = consult_fee
    if introduction: data["introduction"] = introduction
    if action: data["action"] = action
    return {"id": component_id or make_id(), "type": "lawyer-card", "data": data}


# ========== 横滑列表 ==========

def horizontal_scroll(
    items: List[dict],
    *,
    title: str = None,
    show_arrows: bool = True,
    visible_count: int = None,
    component_id: str = None,
) -> dict:
    data = {"items": items, "showArrows": show_arrows}
    if title: data["title"] = title
    if visible_count: data["visibleCount"] = visible_count
    return {"id": component_id or make_id(), "type": "horizontal-scroll", "data": data}


# ========== 表单 Sheet ==========

def form_sheet(
    title: str,
    sections: List[dict],
    submit_action: Dict[str, str],
    *,
    subtitle: str = None,
    header: dict = None,
    cancel_action: Dict[str, str] = None,
    as_sheet: bool = False,
    component_id: str = None,
) -> dict:
    data = {
        "title": title,
        "sections": sections,
        "submitAction": submit_action,
    }
    if subtitle: data["subtitle"] = subtitle
    if header: data["header"] = header
    if cancel_action: data["cancelAction"] = cancel_action
    if as_sheet: data["asSheet"] = True
    return {"id": component_id or make_id(), "type": "form-sheet", "data": data}


def form_section(
    section_id: str,
    label: str,
    section_type: str = "single-select",
    *,
    description: str = None,
    required: bool = False,
    options: List[dict] = None,
    default_value: Any = None,
    placeholder: str = None,
) -> dict:
    data = {"id": section_id, "label": label, "type": section_type}
    if description: data["description"] = description
    if required: data["required"] = True
    if options: data["options"] = options
    if default_value is not None: data["defaultValue"] = default_value
    if placeholder: data["placeholder"] = placeholder
    return data


def form_option(option_id: str, label: str, *, description: str = None, price: dict = None) -> dict:
    data = {"id": option_id, "label": label}
    if description: data["description"] = description
    if price: data["price"] = price
    return data


# ========== 订单/委托确认卡片 ==========

def order_card(
    item: dict,
    details: List[dict],
    actions: List[dict],
    *,
    title: str = None,
    pricing: dict = None,
    note: str = None,
    component_id: str = None,
) -> dict:
    data = {"item": item, "details": details, "actions": actions}
    if title: data["title"] = title
    if pricing: data["pricing"] = pricing
    if note: data["note"] = note
    return {"id": component_id or make_id(), "type": "order-card", "data": data}


# ========== 信息横幅 ==========

def info_banner(
    content: str,
    *,
    variant: str = "info",
    icon: str = None,
    action: dict = None,
    dismissible: bool = False,
    component_id: str = None,
) -> dict:
    data = {"content": content, "variant": variant}
    if icon: data["icon"] = icon
    if action: data["action"] = action
    if dismissible: data["dismissible"] = True
    return {"id": component_id or make_id(), "type": "info-banner", "data": data}


# ========== 按钮组 ==========

def button_group(
    buttons: List[dict],
    *,
    layout: str = "horizontal",
    align: str = "stretch",
    component_id: str = None,
) -> dict:
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
    description: str = None,
    action: dict = None,
    secondary_action: dict = None,
    component_id: str = None,
) -> dict:
    data = {"status": status, "title": title}
    if description: data["description"] = description
    if action: data["action"] = action
    if secondary_action: data["secondaryAction"] = secondary_action
    return {"id": component_id or make_id(), "type": "status-card", "data": data}


# ========== 详情列表 ==========

def detail_list(
    items: List[dict],
    *,
    title: str = None,
    divider: bool = True,
    component_id: str = None,
) -> dict:
    data = {"items": items, "divider": divider}
    if title: data["title"] = title
    return {"id": component_id or make_id(), "type": "detail-list", "data": data}


# ========== 步骤进度 ==========

def progress_steps(
    steps: List[dict],
    current_step: int,
    *,
    title: str = None,
    direction: str = "vertical",
    component_id: str = None,
) -> dict:
    data = {"steps": steps, "currentStep": current_step, "direction": direction}
    if title: data["title"] = title
    return {"id": component_id or make_id(), "type": "progress-steps", "data": data}


# ========== 风险指标 ==========

def risk_indicator(
    title: str,
    score: int,
    level: str,
    *,
    max_score: int = 100,
    description: str = None,
    factors: List[dict] = None,
    action: dict = None,
    component_id: str = None,
) -> dict:
    data = {"title": title, "score": score, "level": level, "maxScore": max_score}
    if description: data["description"] = description
    if factors: data["factors"] = factors
    if action: data["action"] = action
    return {"id": component_id or make_id(), "type": "risk-indicator", "data": data}


# ========== 文本块 ==========

def text_block(
    content: str,
    *,
    format: str = "markdown",
    collapsible: bool = False,
    preview_lines: int = None,
    component_id: str = None,
) -> dict:
    data = {"content": content, "format": format}
    if collapsible: data["collapsible"] = True
    if preview_lines: data["previewLines"] = preview_lines
    return {"id": component_id or make_id(), "type": "text-block", "data": data}


# ========== 分隔线 ==========

def divider(label: str = None, component_id: str = None) -> dict:
    data = {}
    if label: data["label"] = label
    return {"id": component_id or make_id(), "type": "divider", "data": data}


# ========== 服务选择 ==========

def service_selection(
    title: str,
    services: List[dict],
    *,
    subtitle: str = None,
    component_id: str = None,
) -> dict:
    data = {"title": title, "services": services}
    if subtitle: data["subtitle"] = subtitle
    return {"id": component_id or make_id(), "type": "service-selection", "data": data}


# ========== 合同预览 ==========

def contract_preview(
    contract_id: str,
    title: str,
    contract_type: str,
    parties: List[dict],
    key_terms: List[dict],
    risk_level: str,
    actions: List[dict],
    *,
    risk_items: List[dict] = None,
    component_id: str = None,
) -> dict:
    data = {
        "contractId": contract_id,
        "title": title,
        "type": contract_type,
        "parties": parties,
        "keyTerms": key_terms,
        "riskLevel": risk_level,
        "actions": actions,
    }
    if risk_items: data["riskItems"] = risk_items
    return {"id": component_id or make_id(), "type": "contract-preview", "data": data}


# ========== 动作栏 ==========

def action_bar(
    actions: List[dict],
    *,
    position: str = "bottom",
    component_id: str = None,
) -> dict:
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
    center: Dict[str, float] = None,
    markers: List[Dict[str, Any]] = None,
    zoom: int = 14,
    map_provider: str = "amap",
    action: dict = None,
    component_id: str = None,
) -> dict:
    """
    地图视图组件（预留接口）。
    未来可对接高德/百度/Google Maps。
    markers: [{"id": "...", "lat": 39.9, "lng": 116.3, "label": "...", "info": "..."}]
    """
    data = {"title": title, "zoom": zoom, "mapProvider": map_provider}
    if center: data["center"] = center
    if markers: data["markers"] = markers
    if action: data["action"] = action
    return {"id": component_id or make_id(), "type": "map-view", "data": data}


# ========== 扩展接口：支付组件 ==========

def payment_card(
    title: str,
    amount: float,
    *,
    currency: str = "CNY",
    description: str = None,
    payment_methods: List[Dict[str, Any]] = None,
    order_id: str = None,
    pay_action: dict = None,
    cancel_action: dict = None,
    component_id: str = None,
) -> dict:
    """
    支付卡片组件（预留接口）。
    未来可对接微信支付/支付宝/银行卡。
    payment_methods: [{"id": "wechat", "name": "微信支付", "icon": "wechat"}, ...]
    """
    data = {
        "title": title,
        "amount": amount,
        "currency": currency,
    }
    if description: data["description"] = description
    if payment_methods: data["paymentMethods"] = payment_methods
    if order_id: data["orderId"] = order_id
    if pay_action: data["payAction"] = pay_action
    if cancel_action: data["cancelAction"] = cancel_action
    return {"id": component_id or make_id(), "type": "payment-card", "data": data}


# ========== 扩展接口：律师选择器 ==========

def lawyer_picker(
    title: str,
    lawyers: List[dict],
    *,
    filters: List[Dict[str, Any]] = None,
    sort_options: List[Dict[str, str]] = None,
    on_select_action: dict = None,
    multi_select: bool = False,
    component_id: str = None,
) -> dict:
    """
    律师选择器组件（预留接口）。
    支持筛选、排序、多选等功能。
    filters: [{"id": "specialty", "label": "专长", "options": [...]}, ...]
    sort_options: [{"id": "rating", "label": "评分"}, {"id": "price", "label": "价格"}]
    """
    data = {"title": title, "lawyers": lawyers, "multiSelect": multi_select}
    if filters: data["filters"] = filters
    if sort_options: data["sortOptions"] = sort_options
    if on_select_action: data["onSelectAction"] = on_select_action
    return {"id": component_id or make_id(), "type": "lawyer-picker", "data": data}


# ========== 扩展接口：媒体卡片（图片/视频/文件预览） ==========

def media_card(
    title: str,
    media_type: str,
    url: str,
    *,
    thumbnail: str = None,
    description: str = None,
    size: str = None,
    action: dict = None,
    component_id: str = None,
) -> dict:
    """
    媒体预览卡片。
    media_type: "image" | "video" | "pdf" | "document"
    """
    data = {"title": title, "mediaType": media_type, "url": url}
    if thumbnail: data["thumbnail"] = thumbnail
    if description: data["description"] = description
    if size: data["size"] = size
    if action: data["action"] = action
    return {"id": component_id or make_id(), "type": "media-card", "data": data}


# ========== 扩展接口：日程/预约组件 ==========

def schedule_picker(
    title: str,
    available_slots: List[Dict[str, Any]],
    *,
    subtitle: str = None,
    duration_options: List[Dict[str, Any]] = None,
    on_select_action: dict = None,
    component_id: str = None,
) -> dict:
    """
    日程预约组件（预留接口）。
    available_slots: [{"id": "...", "date": "2026-02-10", "time": "10:00", "available": true}]
    """
    data = {"title": title, "availableSlots": available_slots}
    if subtitle: data["subtitle"] = subtitle
    if duration_options: data["durationOptions"] = duration_options
    if on_select_action: data["onSelectAction"] = on_select_action
    return {"id": component_id or make_id(), "type": "schedule-picker", "data": data}


# ========== 扩展接口：评价/反馈组件 ==========

def feedback_card(
    title: str,
    *,
    rating_enabled: bool = True,
    comment_enabled: bool = True,
    tags: List[str] = None,
    submit_action: dict = None,
    component_id: str = None,
) -> dict:
    """
    评价反馈组件。
    """
    data = {
        "title": title,
        "ratingEnabled": rating_enabled,
        "commentEnabled": comment_enabled,
    }
    if tags: data["tags"] = tags
    if submit_action: data["submitAction"] = submit_action
    return {"id": component_id or make_id(), "type": "feedback-card", "data": data}


# ========== 扩展接口：通用插件容器 ==========

def plugin_container(
    plugin_type: str,
    config: Dict[str, Any],
    *,
    title: str = None,
    fallback_text: str = "该功能即将开放",
    component_id: str = None,
) -> dict:
    """
    通用插件容器 — Skills/MCP 扩展的统一接口。
    plugin_type: 插件类型标识（如 "mcp_tool", "skill_action"）
    config: 插件配置数据
    """
    data = {
        "pluginType": plugin_type,
        "config": config,
        "fallbackText": fallback_text,
    }
    if title: data["title"] = title
    return {"id": component_id or make_id(), "type": "plugin-container", "data": data}


# ========== A2UI 消息包装器 ==========

def a2ui_message(
    components: List[dict],
    *,
    text: str = "",
    agent: str = "AI 助手",
    message_id: str = None,
) -> dict:
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
        "text": text,
        "agent": agent,
        "a2ui_id": message_id or make_id(),
        "components": components,
    }


# ========== StreamObject 流式 A2UI 协议 ==========

def a2ui_stream_start(
    stream_id: str = None,
    *,
    agent: str = "AI 助手",
    metadata: Dict[str, Any] = None,
) -> dict:
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
    event = {
        "type": "a2ui_stream",
        "streamId": stream_id or make_id(),
        "action": "stream_start",
        "agent": agent,
    }
    if metadata:
        event["metadata"] = metadata
    return event


def a2ui_stream_component(
    stream_id: str,
    component: dict,
    *,
    agent: str = None,
) -> dict:
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
    event = {
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
    delta: Dict[str, Any],
) -> dict:
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


def a2ui_stream_end(stream_id: str) -> dict:
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
    steps: List[Dict[str, Any]],
    *,
    case_type: str = None,
    estimated_completion: str = None,
    actions: List[dict] = None,
    component_id: str = None,
) -> dict:
    """
    案件进度时间线卡片。

    steps: [{"id": "...", "label": "...", "status": "completed|active|pending|error", "description": "...", "timestamp": "...", "agent": "..."}]
    """
    data = {
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
    dimensions: List[Dict[str, Any]],
    *,
    subtitle: str = None,
    summary: str = None,
    recommendations: List[str] = None,
    actions: List[dict] = None,
    component_id: str = None,
) -> dict:
    """
    风险评估雷达图卡片。

    dimensions: [{"id": "...", "label": "...", "score": 75, "level": "medium", "trend": "up|down|stable"}]
    """
    data = {
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
    clauses: List[Dict[str, Any]],
    *,
    subtitle: str = None,
    summary: dict = None,
    actions: List[dict] = None,
    component_id: str = None,
) -> dict:
    """
    合同条款对比卡片。

    clauses: [{"id": "...", "clauseTitle": "...", "changeType": "added|removed|modified|unchanged",
               "leftContent": "...", "rightContent": "...", "riskLevel": "low|medium|high", "comment": "..."}]
    """
    data = {
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
    items: List[Dict[str, Any]],
    total: Dict[str, Any],
    *,
    subtitle: str = None,
    discounts: List[dict] = None,
    packages: List[dict] = None,
    payment_methods: List[dict] = None,
    notes: List[str] = None,
    actions: List[dict] = None,
    component_id: str = None,
) -> dict:
    """
    费用估算卡片。

    items: [{"id": "...", "label": "...", "amount": 500, "unit": "元/小时", "optional": false}]
    total: {"label": "预计总费用", "amount": 5000, "original": 6000}
    """
    data = {
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
