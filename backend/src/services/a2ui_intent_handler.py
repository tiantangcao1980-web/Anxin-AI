"""
A2UI 意图处理器

检测用户意图 → 生成对应的 A2UI 结构化响应
支持的意图：
  - find_lawyer：找律师/法律咨询
  - review_contract：合同审查
  - draft_document：文书起草
  - legal_consultation：法律咨询
  - risk_assessment：风险评估
  - due_diligence：尽职调查
"""

import re
import uuid
from typing import Any, cast
from loguru import logger

from src.services.due_diligence_service import get_company_info
from src.services.a2ui_protocol import (
    a2ui_message, lawyer_card, horizontal_scroll, service_selection,
    text_block, info_banner, button_group, form_sheet, form_section,
    form_option, order_card, detail_list, status_card, progress_steps,
    risk_indicator, divider, contract_preview, recommendation_card,
)


# ========== 意图检测 ==========

JSONDict = dict[str, Any]
JSONList = list[JSONDict]
ContextDict = dict[str, Any]
RiskPattern = dict[str, Any]

# 意图关键词映射
INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("find_lawyer", [
        r"找.{0,10}律师", r"推荐.{0,10}律师", r"请.{0,4}律师", r"律师.{0,4}推荐",
        r"帮我找.{0,10}律师", r"需要.{0,10}律师", r"法律咨询", r"咨询律师",
        r"委托.{0,10}律师", r"律师咨询", r"联系律师", r"律师",
    ]),
    ("review_contract", [
        r"审[查阅看核].*合同", r"合同.*审[查阅看核]", r"检查.*合同",
        r"合同.*[问题风险]", r"帮我看.*合同", r"审核.*协议",
    ]),
    ("draft_document", [
        r"起草.*[文书合同协议函]", r"写.*[合同协议律师函]", r"生成.*[文书合同]",
        r"帮我[写拟]", r"草拟",
    ]),
    ("risk_assessment", [
        r"风险.*评估", r"评估.*风险", r"风险分析", r"合规.*检查",
        r"有.*[什么啥].*风险",
    ]),
    ("due_diligence", [
        r"尽职调查", r"背景调查", r"调查.*公司", r"企业.*调查",
        r"尽调", r"查一下.*公司", r"看看.*公司", r"公司.*怎么样",
        r"工商信息", r"股权结构", r"诉讼记录", r"信用记录",
        r"供应商.*靠不靠谱", r"合作方.*风险", r"交易对手.*背景",
    ]),
    ("legal_consultation", [
        r"法律.*[问题咨询]", r"法务.*咨询", r"怎么.{0,6}法律",
        r"合法[吗么]", r"违法[吗么]", r"法律上",
    ]),
]


def detect_intent(message: str) -> str | None:
    """从用户消息中检测 A2UI 意图"""
    message_clean = message.strip().lower()
    
    for intent, patterns in INTENT_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, message_clean):
                logger.info(f"[A2UI] 检测到意图: {intent} (pattern: {pattern})")
                return intent
    
    return None


# ========== A2UI 响应生成 ==========

async def handle_a2ui_intent(
    intent: str,
    user_message: str,
    context: ContextDict | None = None,
) -> JSONDict | None:
    """
    根据意图生成 A2UI WebSocket 消息。
    
    Args:
        intent: 意图类型
        user_message: 用户原始消息
        context: 上下文信息（对话历史、用户信息等）
        
    Returns:
        A2UI WebSocket 消息 dict，或 None
    """
    context = context or {}
    
    handlers = {
        "find_lawyer": _handle_find_lawyer,
        "review_contract": _handle_review_contract,
        "draft_document": _handle_draft_document,
        "risk_assessment": _handle_risk_assessment,
        "due_diligence": _handle_due_diligence,
        "legal_consultation": _handle_legal_consultation,
    }
    
    handler = handlers.get(intent)
    if handler:
        return await handler(user_message, context)
    return None


async def handle_a2ui_event(
    action_id: str,
    component_id: str,
    payload: ContextDict | None = None,
    form_data: ContextDict | None = None,
    context: ContextDict | None = None,
) -> JSONDict | None:
    """
    处理前端 A2UI 事件回调，生成后续响应。
    
    Args:
        action_id: 操作标识
        component_id: 来源组件 ID
        payload: 操作负载
        form_data: 表单数据
        context: 上下文
        
    Returns:
        A2UI WebSocket 消息 dict，或 None
    """
    payload = payload or {}
    form_data = form_data or {}
    context = context or {}
    
    logger.info(f"[A2UI Event] action={action_id}, payload={payload}, form_data={form_data}")
    
    # --- 联系律师 ---
    if action_id == "contact_lawyer":
        return await _handle_contact_lawyer(payload, context)
    
    # --- 选择服务 ---
    if action_id == "select_service":
        return await _handle_select_service(payload, context)
    
    # --- 提交委托表单 ---
    if action_id == "submit_engagement":
        return await _handle_submit_engagement(form_data, context)
    
    # --- 确认委托 ---
    if action_id == "confirm_engagement":
        return await _handle_confirm_engagement(payload, context)
    
    # --- 查看律师详情 ---
    if action_id == "view_lawyer_detail":
        return await _handle_view_lawyer_detail(payload, context)
    
    # --- 上传合同 ---
    if action_id == "upload_contract":
        return await _handle_upload_contract(payload, context)
    
    # --- 开始审查 ---
    if action_id == "start_review":
        return await _handle_start_review(payload, context)

    # --- 开始尽调 ---
    if action_id == "start_due_diligence":
        return await _handle_start_due_diligence(form_data, context)

    # --- 返回对话 / 取消 ---
    if action_id in {"go_back", "cancel_engagement"}:
        return await _handle_go_back(action_id, context)

    # --- 律师推荐扩展动作 ---
    if action_id in {"view_more_lawyers", "ai_match_lawyer", "find_lawyer"}:
        return await _handle_lawyer_followup(action_id, payload, context)

    # --- 合同审查扩展动作 ---
    if action_id in {"paste_contract", "browse_templates", "view_full_report", "ai_suggestions"}:
        return await _handle_contract_followup(action_id, payload, context)

    # --- 文书起草扩展动作 ---
    if action_id == "select_doc_type":
        return await _handle_select_doc_type(payload, context)

    # --- 风险评估细分动作 ---
    if action_id in {"assess_contract_risk", "assess_compliance", "assess_litigation_risk", "assess_ip_risk"}:
        return await _handle_risk_drilldown(action_id, payload, context)

    # --- 委托详情 ---
    if action_id == "view_engagement_detail":
        return await _handle_view_engagement_detail(payload, context)
    
    logger.warning(f"[A2UI] 未处理的 action: {action_id}")
    return None


# ========== 「找律师」完整流程 ==========

# 示例律师数据（开发环境使用，生产环境应从 lawyer_profiles 表查询）
# TODO: v1.1 替换为 LawyerProfile 数据库查询
MOCK_LAWYERS: JSONList = [
    {
        "id": "lawyer-001", "name": "张明", "firm": "金杜律师事务所",
        "title": "合伙人", "specialties": ["合同法", "公司法", "知识产权"],
        "rating": 4.9, "win_rate": "92%", "experience": "15年执业",
        "response_time": "通常3分钟内回复",
        "consult_fee": {"amount": 500, "unit": "次"},
        "status": "online",
        "introduction": "擅长复杂商事合同纠纷、股权架构设计、知识产权保护，曾处理多起标的额过亿案件。",
    },
    {
        "id": "lawyer-002", "name": "李婷", "firm": "中伦律师事务所",
        "title": "高级合伙人", "specialties": ["劳动法", "人事合规", "竞业禁止"],
        "rating": 4.8, "win_rate": "89%", "experience": "12年执业",
        "response_time": "通常5分钟内回复",
        "consult_fee": {"amount": 400, "unit": "次"},
        "status": "online",
        "introduction": "专注劳动法领域，在劳动争议调解、竞业限制、员工股权激励方面有丰富实战经验。",
    },
    {
        "id": "lawyer-003", "name": "王强", "firm": "方达律师事务所",
        "title": "合伙人", "specialties": ["并购重组", "投资基金", "证券法"],
        "rating": 4.7, "win_rate": "95%", "experience": "18年执业",
        "response_time": "通常15分钟内回复",
        "consult_fee": {"amount": 800, "unit": "次"},
        "status": "busy",
        "introduction": "深耕资本市场与并购重组，为数十家上市公司及PE/VC基金提供法律服务。",
    },
    {
        "id": "lawyer-004", "name": "赵雪", "firm": "君合律师事务所",
        "title": "律师", "specialties": ["知识产权", "商标注册", "专利诉讼"],
        "rating": 4.9, "win_rate": "91%", "experience": "8年执业",
        "response_time": "通常5分钟内回复",
        "consult_fee": {"amount": 350, "unit": "次"},
        "status": "online",
        "introduction": "专注知识产权保护，代理过多起重大商标、专利侵权案件，在TMT行业经验丰富。",
    },
    {
        "id": "lawyer-005", "name": "陈浩", "firm": "德恒律师事务所",
        "title": "高级合伙人", "specialties": ["刑事辩护", "行政诉讼", "合规审查"],
        "rating": 4.6, "win_rate": "85%", "experience": "20年执业",
        "response_time": "通常30分钟内回复",
        "consult_fee": {"amount": 600, "unit": "次"},
        "status": "offline",
        "introduction": "在刑事辩护和行政法领域享有盛誉，曾为多家大型国企提供企业合规体系建设服务。",
    },
]


async def _handle_find_lawyer(user_message: str, context: ContextDict) -> JSONDict:
    """处理「找律师」意图 → 推荐律师列表"""
    
    # 根据用户消息匹配合适的律师（简单匹配逻辑，未来可接入真实搜索）
    keyword_specialty_map = {
        "合同": "合同法", "公司": "公司法", "知识产权": "知识产权",
        "劳动": "劳动法", "竞业": "竞业禁止", "并购": "并购重组",
        "投资": "投资基金", "商标": "商标注册", "专利": "专利诉讼",
        "刑事": "刑事辩护", "行政": "行政诉讼",
    }
    
    matched_specialty = None
    for keyword, specialty in keyword_specialty_map.items():
        if keyword in user_message:
            matched_specialty = specialty
            break
    
    # 筛选律师
    if matched_specialty:
        matched_lawyers = [
            l for l in MOCK_LAWYERS if matched_specialty in l["specialties"]
        ]
        if not matched_lawyers:
            matched_lawyers = MOCK_LAWYERS[:3]
    else:
        matched_lawyers = MOCK_LAWYERS[:4]
    
    # 构建律师卡片
    cards: list[JSONDict] = []
    for l in matched_lawyers:
        cards.append(lawyer_card(
            lawyer_id=l["id"], name=l["name"], firm=l["firm"],
            specialties=l["specialties"], rating=l["rating"],
            status=l["status"],
            title=l["title"], win_rate=l["win_rate"],
            experience=l["experience"], response_time=l["response_time"],
            consult_fee=l["consult_fee"], introduction=l["introduction"],
            action={"label": "立即咨询", "actionId": "contact_lawyer"},
        ))
    
    # 构建 A2UI 消息
    components = [
        text_block(
            f"根据您的需求，为您推荐以下{len(matched_lawyers)}位专业律师" 
            + (f"（专长：{matched_specialty}）" if matched_specialty else "") 
            + "：",
            format="markdown",
        ),
    ]
    
    # 多于2个律师时用横滑列表
    if len(cards) > 2:
        components.append(horizontal_scroll(cards, title="推荐律师", visible_count=2))
    else:
        components.extend(cards)
    
    # 添加底部操作
    components.append(divider())
    components.append(button_group(
        buttons=[
            {"id": "btn-more", "label": "查看更多律师", "actionId": "view_more_lawyers", "variant": "outline"},
            {"id": "btn-ai-match", "label": "AI 智能匹配", "actionId": "ai_match_lawyer", "variant": "primary"},
        ],
        layout="horizontal",
        align="stretch",
    ))
    
    return cast(JSONDict, a2ui_message(
        components,
        text="",
        agent="律师推荐 Agent",
    ))


async def _handle_contact_lawyer(payload: ContextDict, context: ContextDict) -> JSONDict:
    """处理「联系律师」操作 → 显示服务选择"""
    lawyer_id = payload.get("lawyerId", "")
    
    # 找到律师信息
    lawyer = next((l for l in MOCK_LAWYERS if l["id"] == lawyer_id), MOCK_LAWYERS[0])
    
    components = [
        info_banner(
            f"您正在联系 {lawyer['name']}律师（{lawyer['firm']}）",
            variant="info",
        ),
        service_selection(
            title="请选择咨询服务类型",
            subtitle="不同服务类型有不同的服务方式和收费标准",
            services=[
                {
                    "id": "quick_consult",
                    "name": "快速咨询",
                    "description": "在线即时文字咨询，适合简单法律问题",
                    "features": ["15分钟在线问答", "文字交流", "基础法律建议"],
                    "price": {"amount": 99, "unit": "次", "label": "限时特惠"},
                    "actionId": "select_service",
                    "popular": False,
                },
                {
                    "id": "standard_consult",
                    "name": "标准咨询",
                    "description": "深度法律咨询，包含详细的书面法律意见",
                    "features": ["60分钟深度交流", "书面法律意见书", "后续1次跟进", "资料审阅"],
                    "price": {"amount": lawyer["consult_fee"]["amount"], "unit": "次"},
                    "actionId": "select_service",
                    "popular": True,
                },
                {
                    "id": "engagement",
                    "name": "委托代理",
                    "description": "全程法律代理服务，适合复杂案件或诉讼",
                    "features": ["全程跟进", "代理出庭/谈判", "法律文书起草", "定期进度汇报"],
                    "price": {"amount": 5000, "unit": "起", "label": "根据案件复杂度"},
                    "actionId": "select_service",
                    "popular": False,
                },
            ],
        ),
    ]
    
    return cast(JSONDict, a2ui_message(components, agent="服务选择 Agent"))


async def _handle_select_service(payload: ContextDict, context: ContextDict) -> JSONDict:
    """处理「选择服务」操作 → 显示委托信息表单"""
    service_id = payload.get("serviceId", "standard_consult")
    
    service_names = {
        "quick_consult": "快速咨询",
        "standard_consult": "标准咨询",
        "engagement": "委托代理",
    }
    
    components = [
        form_sheet(
            title=f"填写{service_names.get(service_id, '咨询')}信息",
            subtitle="请填写以下信息以便律师更好地为您服务",
            sections=[
                form_section(
                    "case_type", "案件类型", "single-select",
                    required=True,
                    options=[
                        form_option("contract", "合同纠纷"),
                        form_option("labor", "劳动争议"),
                        form_option("ip", "知识产权"),
                        form_option("corporate", "公司治理"),
                        form_option("criminal", "刑事辩护"),
                        form_option("other", "其他"),
                    ],
                ),
                form_section(
                    "urgency", "紧急程度", "single-select",
                    options=[
                        form_option("normal", "普通（7日内处理）"),
                        form_option("urgent", "加急（24小时内）", price={"amount": 200, "label": "加急费"}),
                        form_option("critical", "紧急（2小时内）", price={"amount": 500, "label": "紧急费"}),
                    ],
                    default_value="normal",
                ),
                form_section(
                    "description", "案件描述", "textarea",
                    required=True,
                    placeholder="请简要描述您的法律问题（如涉及金额、时间、关键事实等）",
                ),
                form_section(
                    "contact_method", "联系方式", "single-select",
                    options=[
                        form_option("online", "在线沟通"),
                        form_option("phone", "电话沟通"),
                        form_option("video", "视频会议"),
                        form_option("in_person", "当面咨询"),
                    ],
                    default_value="online",
                ),
            ],
            submit_action={"label": "提交委托申请", "actionId": "submit_engagement"},
            cancel_action={"label": "返回", "actionId": "go_back"},
        ),
    ]
    
    return cast(JSONDict, a2ui_message(components, agent="委托信息收集 Agent"))


async def _handle_submit_engagement(form_data: ContextDict, context: ContextDict) -> JSONDict:
    """处理「提交委托」操作 → 显示确认订单"""
    
    case_type_names = {
        "contract": "合同纠纷", "labor": "劳动争议", "ip": "知识产权",
        "corporate": "公司治理", "criminal": "刑事辩护", "other": "其他",
    }
    urgency_names = {
        "normal": "普通（7日内）", "urgent": "加急（24小时内）", "critical": "紧急（2小时内）",
    }
    contact_names = {
        "online": "在线沟通", "phone": "电话沟通", "video": "视频会议", "in_person": "当面咨询",
    }
    
    base_fee = 500
    urgency_fee = {"normal": 0, "urgent": 200, "critical": 500}.get(form_data.get("urgency", "normal"), 0)
    
    components = [
        order_card(
            title="委托确认",
            item={
                "title": "标准法律咨询服务",
                "subtitle": case_type_names.get(form_data.get("case_type", "other"), "法律服务"),
                "specs": f"服务方式：{contact_names.get(form_data.get('contact_method', 'online'), '在线')}",
                "price": {"amount": base_fee + urgency_fee},
            },
            details=[
                {"label": "案件类型", "value": case_type_names.get(form_data.get("case_type", "other"), "其他")},
                {"label": "紧急程度", "value": urgency_names.get(form_data.get("urgency", "normal"), "普通")},
                {"label": "联系方式", "value": contact_names.get(form_data.get("contact_method", "online"), "在线沟通")},
                {"label": "案件描述", "value": (form_data.get("description", "")[:50] + "...") if len(form_data.get("description", "")) > 50 else form_data.get("description", "未填写")},
            ],
            pricing={
                "items": [
                    {"label": "咨询服务费", "amount": base_fee},
                    *([{"label": "加急费", "amount": urgency_fee, "type": "add"}] if urgency_fee > 0 else []),
                    {"label": "平台服务费", "amount": 0, "original": 50, "type": "subtract"},
                ],
                "total": {"label": "合计", "amount": base_fee + urgency_fee},
            },
            actions=[
                {"label": "取消", "actionId": "cancel_engagement", "variant": "outline"},
                {"label": "确认委托", "actionId": "confirm_engagement", "variant": "primary"},
            ],
            note="提交后律师将在约定时间内联系您。委托成功后可在「案件管理」中查看进度。",
        ),
    ]
    
    return cast(JSONDict, a2ui_message(components, agent="委托确认 Agent"))


async def _handle_confirm_engagement(payload: ContextDict, context: ContextDict) -> JSONDict:
    """处理「确认委托」→ 显示成功状态 + 进度"""
    
    engagement_id = str(uuid.uuid4())[:8]
    
    components = [
        status_card(
            "success",
            "委托提交成功！",
            description=f"委托编号：ENG-{engagement_id}。律师将在约定时间内与您联系。",
            action={"label": "查看委托详情", "actionId": "view_engagement_detail"},
            secondary_action={"label": "返回对话", "actionId": "go_back"},
        ),
        divider(label="委托进度"),
        progress_steps(
            title="委托处理流程",
            current_step=1,
            steps=[
                {"id": "s1", "label": "提交委托", "status": "completed", "description": "您已成功提交委托申请", "timestamp": "刚刚"},
                {"id": "s2", "label": "律师确认", "status": "active", "description": "等待律师确认接受委托"},
                {"id": "s3", "label": "资料准备", "status": "pending", "description": "双方准备相关资料"},
                {"id": "s4", "label": "咨询进行", "status": "pending", "description": "律师提供专业咨询"},
                {"id": "s5", "label": "服务完成", "status": "pending", "description": "出具法律意见/完成代理"},
            ],
            direction="vertical",
        ),
    ]
    
    return cast(JSONDict, a2ui_message(
        components,
        text="",
        agent="委托管理 Agent",
    ))


async def _handle_view_lawyer_detail(payload: ContextDict, context: ContextDict) -> JSONDict:
    """查看律师详情"""
    lawyer_id = payload.get("lawyerId", "")
    lawyer = next((l for l in MOCK_LAWYERS if l["id"] == lawyer_id), MOCK_LAWYERS[0])
    
    components = [
        lawyer_card(
            lawyer_id=lawyer["id"], name=lawyer["name"], firm=lawyer["firm"],
            specialties=lawyer["specialties"], rating=lawyer["rating"],
            status=lawyer["status"], title=lawyer["title"],
            win_rate=lawyer["win_rate"], experience=lawyer["experience"],
            response_time=lawyer["response_time"], consult_fee=lawyer["consult_fee"],
            introduction=lawyer["introduction"],
            action={"label": "立即咨询", "actionId": "contact_lawyer"},
        ),
        detail_list(
            title="详细信息",
            items=[
                {"label": "执业证号", "value": f"1101201{hash(lawyer['id']) % 10000:04d}"},
                {"label": "执业年限", "value": lawyer["experience"]},
                {"label": "胜诉率", "value": lawyer["win_rate"], "valueType": "badge", "color": "green"},
                {"label": "咨询费", "value": f"¥{lawyer['consult_fee']['amount']}/次", "valueType": "highlight"},
                {"label": "所在地区", "value": "北京市朝阳区"},
                {"label": "服务评价", "value": f"{lawyer['rating']}分（128条评价）"},
            ],
        ),
    ]
    
    return cast(JSONDict, a2ui_message(components, agent="律师详情 Agent"))


# ========== 「合同审查」流程 ==========

async def _handle_review_contract(user_message: str, context: ContextDict) -> JSONDict:
    """处理「合同审查」意图"""
    
    components = [
        text_block("收到！我可以帮您审查合同，快速识别风险条款。请选择审查方式："),
        button_group(
            buttons=[
                {"id": "btn-upload", "label": "上传合同文件", "actionId": "upload_contract", "variant": "primary", "icon": "file-text"},
                {"id": "btn-paste", "label": "粘贴合同文本", "actionId": "paste_contract", "variant": "outline"},
                {"id": "btn-template", "label": "使用合同模板", "actionId": "browse_templates", "variant": "ghost"},
            ],
            layout="vertical",
            align="stretch",
        ),
        info_banner(
            "支持 .doc/.docx/.pdf 格式，文件大小不超过 20MB",
            variant="info",
            dismissible=True,
        ),
    ]
    
    return cast(JSONDict, a2ui_message(components, agent="合同审查 Agent"))


async def _handle_upload_contract(payload: ContextDict, context: ContextDict) -> JSONDict:
    """处理合同上传后的审查"""
    components = [
        progress_steps(
            title="合同审查进度",
            current_step=1,
            steps=[
                {"id": "s1", "label": "文件上传", "status": "completed"},
                {"id": "s2", "label": "文本提取", "status": "active"},
                {"id": "s3", "label": "条款分析", "status": "pending"},
                {"id": "s4", "label": "风险评估", "status": "pending"},
                {"id": "s5", "label": "生成报告", "status": "pending"},
            ],
            direction="horizontal",
        ),
        text_block("正在分析您的合同文件，请稍候..."),
    ]
    return cast(JSONDict, a2ui_message(components, agent="合同审查 Agent"))


async def _handle_start_review(payload: ContextDict, context: ContextDict) -> JSONDict:
    """审查完成后的结果展示"""
    components = [
        risk_indicator(
            title="合同风险评分",
            score=72,
            level="medium",
            description="该合同存在部分风险条款需要关注",
            factors=[
                {"label": "违约责任", "score": 60, "maxScore": 100, "level": "medium"},
                {"label": "知识产权", "score": 85, "maxScore": 100, "level": "low"},
                {"label": "保密条款", "score": 45, "maxScore": 100, "level": "high"},
                {"label": "争议解决", "score": 90, "maxScore": 100, "level": "low"},
            ],
            action={"label": "查看详细报告", "actionId": "view_full_report"},
        ),
        button_group(
            buttons=[
                {"id": "btn-consult", "label": "咨询律师", "actionId": "find_lawyer", "variant": "primary"},
                {"id": "btn-modify", "label": "AI 修改建议", "actionId": "ai_suggestions", "variant": "outline"},
            ],
        ),
    ]
    return cast(JSONDict, a2ui_message(components, agent="合同审查 Agent"))


# ========== 「文书起草」流程 ==========

async def _handle_draft_document(user_message: str, context: ContextDict) -> JSONDict:
    """处理「文书起草」意图"""
    
    components = [
        text_block("好的，我来帮您起草法律文书。请选择文书类型："),
        service_selection(
            title="选择文书类型",
            services=[
                {
                    "id": "contract", "name": "合同/协议",
                    "description": "各类商事合同、服务协议、保密协议等",
                    "features": ["智能条款生成", "风险检测", "多方签约"],
                    "actionId": "select_doc_type",
                },
                {
                    "id": "lawyer_letter", "name": "律师函",
                    "description": "催款函、警告函、维权通知函等",
                    "features": ["专业法律措辞", "法条引用", "律所盖章"],
                    "popular": True,
                    "actionId": "select_doc_type",
                },
                {
                    "id": "legal_opinion", "name": "法律意见书",
                    "description": "针对特定法律问题出具的专业意见",
                    "features": ["深度法律分析", "风险评估", "专家建议"],
                    "actionId": "select_doc_type",
                },
                {
                    "id": "authorization", "name": "授权/委托书",
                    "description": "授权委托书、法人委托书等",
                    "features": ["标准格式", "条款完善", "签章流程"],
                    "actionId": "select_doc_type",
                },
            ],
        ),
    ]
    
    return cast(JSONDict, a2ui_message(components, agent="文书起草 Agent"))


# ========== 「风险评估」流程 ==========

async def _handle_risk_assessment(user_message: str, context: ContextDict) -> JSONDict:
    """处理「风险评估」意图"""
    
    components = [
        text_block("我来帮您进行风险评估。请告诉我需要评估的领域："),
        button_group(
            buttons=[
                {"id": "btn-contract-risk", "label": "合同风险", "actionId": "assess_contract_risk", "variant": "outline"},
                {"id": "btn-compliance", "label": "合规审查", "actionId": "assess_compliance", "variant": "outline"},
                {"id": "btn-litigation", "label": "诉讼风险", "actionId": "assess_litigation_risk", "variant": "outline"},
                {"id": "btn-ip", "label": "知识产权风险", "actionId": "assess_ip_risk", "variant": "outline"},
            ],
            layout="grid",
        ),
    ]
    
    return cast(JSONDict, a2ui_message(components, agent="风险评估 Agent"))


# ========== 「尽职调查」流程 ==========

async def _handle_due_diligence(user_message: str, context: ContextDict) -> JSONDict:
    """处理「尽职调查」意图"""
    
    components = [
        text_block("收到！请提供需要调查的企业信息："),
        form_sheet(
            title="企业尽职调查",
            sections=[
                form_section("company_name", "企业名称", "text-input", required=True, placeholder="请输入完整的企业名称"),
                form_section("investigation_scope", "调查范围", "multi-select", options=[
                    form_option("basic", "基础工商信息"),
                    form_option("financial", "财务状况"),
                    form_option("litigation", "诉讼记录"),
                    form_option("compliance", "合规情况"),
                    form_option("ip", "知识产权"),
                    form_option("related_parties", "关联方分析"),
                ]),
                form_section("purpose", "调查目的", "single-select", options=[
                    form_option("investment", "投资决策"),
                    form_option("cooperation", "合作评估"),
                    form_option("ma", "并购重组"),
                    form_option("supplier", "供应商审核"),
                ]),
            ],
            submit_action={"label": "开始调查", "actionId": "start_due_diligence"},
        ),
    ]
    
    return cast(JSONDict, a2ui_message(components, agent="尽职调查 Agent"))


async def _handle_start_due_diligence(form_data: ContextDict, context: ContextDict) -> JSONDict:
    """处理「开始调查」操作 → 返回尽调摘要卡片"""
    company_name = (form_data.get("company_name") or "").strip()
    investigation_scope = form_data.get("investigation_scope") or []
    purpose = form_data.get("purpose") or "cooperation"

    if not company_name:
        return cast(JSONDict, a2ui_message(
            [
                info_banner("请先填写需要调查的企业名称。", variant="warning"),
                text_block("建议填写完整企业名称，必要时补充统一社会信用代码，以便提高调查准确性。"),
            ],
            agent="尽职调查 Agent",
        ))

    scope_labels = {
        "basic": "基础工商信息",
        "financial": "财务状况",
        "litigation": "诉讼记录",
        "compliance": "合规情况",
        "ip": "知识产权",
        "related_parties": "关联方分析",
    }
    purpose_labels = {
        "investment": "投资决策",
        "cooperation": "合作评估",
        "ma": "并购重组",
        "supplier": "供应商审核",
    }

    try:
        company_data = await get_company_info(company_name)
    except Exception as e:
        logger.error(f"[A2UI] 尽调查询失败: {e}")
        return cast(JSONDict, a2ui_message(
            [
                status_card(
                    "warning",
                    f"{company_name} 调查暂时失败",
                    description="当前尽调服务未返回可靠结果，请稍后重试，或补充统一社会信用代码后再次发起调查。",
                ),
                text_block("如果您需要，我也可以先帮您列出尽调清单，包括工商、诉讼、股权、信用和合规核查项。"),
            ],
            agent="尽职调查 Agent",
        ))

    basic_info = company_data.get("basic_info", {}) or {}
    litigation = company_data.get("litigation", {}) or {}
    credit = company_data.get("credit", {}) or {}
    risk = company_data.get("risk", {}) or {}

    overall_rating = str(risk.get("overall_rating", "medium")).lower()
    status_map = {
        "low": ("success", "低风险"),
        "medium": ("info", "中风险"),
        "high": ("warning", "高风险"),
        "critical": ("error", "重大风险"),
    }
    status_variant, risk_label = status_map.get(overall_rating, ("info", overall_rating or "待核验"))

    focus_scope = [scope_labels[item] for item in investigation_scope if item in scope_labels]
    risk_points = [str(item).strip() for item in (risk.get("risk_points") or []) if str(item).strip()]
    recommendations = [str(item).strip() for item in (risk.get("recommendations") or []) if str(item).strip()]
    total_cases = int(litigation.get("plaintiff_cases", 0) or 0) + int(litigation.get("defendant_cases", 0) or 0)

    components = [
        status_card(
            status_variant,
            f"{company_name} 调查已完成",
            description=(
                f"调查目的：{purpose_labels.get(purpose, '合作评估')}。"
                f"综合判断为{risk_label}，您可以继续查看关键发现并决定是否深入调查。"
            ),
        ),
        detail_list(
            [
                {"label": "企业名称", "value": basic_info.get("name") or company_name},
                {"label": "经营状态", "value": basic_info.get("status") or "待核验"},
                {"label": "法定代表人", "value": basic_info.get("legal_representative") or "待核验"},
                {"label": "注册资本", "value": basic_info.get("registered_capital") or "待核验"},
                {"label": "诉讼案件数", "value": str(total_cases)},
                {"label": "信用评级", "value": credit.get("credit_rating") or "待核验"},
            ],
            title="关键调查结果",
        ),
    ]

    if focus_scope:
        components.append(text_block(f"本次重点关注范围：{'、'.join(focus_scope)}。"))

    if risk_points:
        components.append(recommendation_card(
            title="重点风险提示",
            description="；".join(risk_points[:3]),
            meta=f"综合风险等级：{risk_label}",
        ))

    if recommendations:
        components.append(detail_list(
            [{"label": f"建议 {idx + 1}", "value": item} for idx, item in enumerate(recommendations[:3])],
            title="建议动作",
        ))

    components.append(button_group(
        buttons=[
            {"id": "btn-continue-dd", "label": "继续补充调查", "actionId": "start_due_diligence", "variant": "outline"},
            {"id": "btn-consult-lawyer", "label": "咨询律师解读", "actionId": "find_lawyer", "variant": "primary"},
        ],
        layout="horizontal",
    ))

    return cast(JSONDict, a2ui_message(components, agent="尽职调查 Agent"))


async def _handle_go_back(action_id: str, context: ContextDict) -> JSONDict:
    message = "已返回对话，您可以继续补充信息或发起新的法务需求。"
    if action_id == "cancel_engagement":
        message = "已取消当前委托流程，您可以重新选择律师或继续描述需求。"
    return cast(JSONDict, a2ui_message(
        [
            info_banner(message, variant="info"),
            text_block("如果您愿意，我可以继续帮您做律师匹配、合同审查、企业调查或文书起草。"),
        ],
        agent="交互助手 Agent",
    ))


async def _handle_lawyer_followup(action_id: str, payload: ContextDict, context: ContextDict) -> JSONDict:
    if action_id == "ai_match_lawyer":
        # 从上下文提取用户描述，进行关键词匹配推荐
        user_text = (context.get("user_message") or context.get("last_user_message") or "").lower()
        keyword_specialty_map = {
            "合同": "合同法", "公司": "公司法", "知识产权": "知识产权",
            "劳动": "劳动法", "竞业": "竞业禁止", "并购": "并购重组",
            "投资": "投资基金", "商标": "商标注册", "专利": "专利诉讼",
            "刑事": "刑事辩护", "行政": "行政诉讼", "合规": "合规审查",
        }
        matched_specialties = [sp for kw, sp in keyword_specialty_map.items() if kw in user_text]

        if matched_specialties:
            scored = []
            for l in MOCK_LAWYERS:
                overlap = len(set(l["specialties"]) & set(matched_specialties))
                if overlap > 0:
                    scored.append((overlap, l["rating"], l))
            scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
            matched_lawyers = [item[2] for item in scored[:3]]
        else:
            # 无法提取关键词时，按评分排序推荐
            matched_lawyers = sorted(MOCK_LAWYERS, key=lambda l: l["rating"], reverse=True)[:3]

        cards = []
        for l in matched_lawyers:
            cards.append(lawyer_card(
                lawyer_id=l["id"], name=l["name"], firm=l["firm"],
                specialties=l["specialties"], rating=l["rating"],
                status=l["status"], title=l["title"], win_rate=l["win_rate"],
                experience=l["experience"], response_time=l["response_time"],
                consult_fee=l["consult_fee"],
            ))

        match_desc = f"已根据您的问题（{'、'.join(matched_specialties[:3])}）智能匹配" if matched_specialties else "已为您推荐评分最高的律师"
        return cast(JSONDict, a2ui_message(
            [
                info_banner(f"{match_desc}以下律师：", variant="success"),
                horizontal_scroll(cards),
                text_block("您也可以补充案件类型、所在城市或预算范围，获得更精准的推荐。"),
            ],
            agent="律师推荐 Agent",
        ))

    if action_id == "find_lawyer":
        return await _handle_find_lawyer("帮我推荐合适的律师", context)

    return await _handle_find_lawyer("查看更多律师推荐", context)


async def _handle_contract_followup(action_id: str, payload: ContextDict, context: ContextDict) -> JSONDict:
    if action_id == "paste_contract":
        return cast(JSONDict, a2ui_message(
            [
                info_banner("请直接把合同全文粘贴到对话框中，我会继续做条款解析和风险审查。", variant="info"),
                text_block("如果合同较长，建议优先上传文件；如果只想看重点，也可以只粘贴关键条款。"),
            ],
            agent="合同审查 Agent",
        ))

    if action_id == "browse_templates":
        return cast(JSONDict, a2ui_message(
            [
                service_selection(
                    title="常用合同模板",
                    services=[
                        {"id": "nda", "name": "保密协议", "description": "适用于合作前信息披露场景", "features": ["标准保密条款", "违约责任"], "actionId": "select_doc_type"},
                        {"id": "service", "name": "服务合同", "description": "适用于技术/咨询/外包服务合作", "features": ["服务范围", "付款条款"], "actionId": "select_doc_type"},
                        {"id": "procurement", "name": "采购合同", "description": "适用于设备/货物采购与供应商合作", "features": ["验收条款", "违约责任"], "actionId": "select_doc_type"},
                    ],
                    subtitle="选择模板后，我会继续帮您起草或审查。",
                )
            ],
            agent="合同审查 Agent",
        ))

    if action_id == "view_full_report":
        return cast(JSONDict, a2ui_message(
            [
                status_card("info", "详细报告已准备", description="建议重点查看违约责任、保密条款、争议解决和知识产权归属。"),
                detail_list(
                    [
                        {"label": "高优先级", "value": "保密条款责任边界不清，建议补充泄密责任与例外情形。"},
                        {"label": "中优先级", "value": "违约责任上限未明确，建议约定赔偿上限或计算方式。"},
                        {"label": "中优先级", "value": "争议解决地未约定，建议明确法院或仲裁机构。"},
                    ],
                    title="合同审查重点",
                ),
            ],
            agent="合同审查 Agent",
        ))

    return cast(JSONDict, a2ui_message(
        [
            recommendation_card(
                title="AI 修改建议",
                description="建议先补齐违约责任、争议解决、保密范围和知识产权归属四类核心条款，再进行最终定稿。",
                meta="优先处理高风险条款后再发给对方确认",
            ),
            text_block("如果您愿意，我也可以继续按条款逐段给出修改稿。"),
        ],
        agent="合同审查 Agent",
    ))


async def _handle_select_doc_type(payload: ContextDict, context: ContextDict) -> JSONDict:
    doc_type = payload.get("serviceId") or payload.get("docType") or "general"
    doc_titles = {
        "contract": "合同/协议",
        "lawyer_letter": "律师函",
        "legal_opinion": "法律意见书",
        "authorization": "授权/委托书",
        "nda": "保密协议",
        "service": "服务合同",
        "procurement": "采购合同",
    }
    title = doc_titles.get(doc_type, "法律文书")
    return cast(JSONDict, a2ui_message(
        [
            form_sheet(
                title=f"{title}信息收集",
                subtitle="补充关键信息后，我就可以继续起草。",
                sections=[
                    form_section("parties", "主体信息", "textarea", required=True, placeholder="请输入甲乙方/委托方等主体信息"),
                    form_section("purpose", "文书目的", "textarea", required=True, placeholder="例如：催款、合作签约、授权代理"),
                    form_section("key_terms", "关键要求", "textarea", placeholder="例如：金额、期限、违约责任、保密要求"),
                ],
                submit_action={"label": "继续起草", "actionId": "go_back"},
            )
        ],
        agent="文书起草 Agent",
    ))


def _compute_risk_score(action_id: str, context: ContextDict) -> tuple[str, int, str, str, list[str]]:
    """根据用户输入动态计算风险评分和风险点"""
    user_text = (context.get("user_message") or context.get("last_user_message") or "").lower()

    # 每种风险类型的关键词 → (权重, 风险描述)
    _RISK_PATTERNS: dict[str, RiskPattern] = {
        "assess_contract_risk": {
            "title": "合同风险",
            "base_score": 55,
            "keywords": {
                "违约": (12, "存在违约责任条款风险"),
                "赔偿": (10, "赔偿金额或方式需明确约定"),
                "验收": (8, "验收标准不够具体可能引发争议"),
                "保密": (6, "保密义务范围需确认"),
                "解除": (10, "合同解除条件需要关注"),
                "不可抗力": (5, "不可抗力条款覆盖范围是否充分"),
                "争议": (8, "争议解决方式（仲裁/诉讼）需明确"),
                "付款": (9, "付款条件和时间节点需严格约定"),
                "质保": (7, "质保期限和范围需确认"),
            },
            "fallback_desc": "建议上传合同文本，以便精准识别条款风险点。",
        },
        "assess_compliance": {
            "title": "合规审查",
            "base_score": 50,
            "keywords": {
                "数据": (10, "数据合规（个人信息保护法）需重点关注"),
                "隐私": (10, "用户隐私保护措施需核查"),
                "许可": (8, "业务经营许可证和资质需确认"),
                "审批": (7, "内部审批流程需规范化"),
                "出口": (9, "出口管制合规需评估"),
                "反垄断": (11, "反垄断合规风险需专项排查"),
                "税务": (8, "税务合规需核查申报义务"),
                "环保": (7, "环保合规义务需确认"),
            },
            "fallback_desc": "建议描述业务场景和行业领域，以便进行针对性合规排查。",
        },
        "assess_litigation_risk": {
            "title": "诉讼风险",
            "base_score": 60,
            "keywords": {
                "证据": (12, "证据链完整性是胜诉关键"),
                "时效": (10, "诉讼时效需确认是否在有效期内"),
                "管辖": (7, "管辖权归属需提前确认"),
                "送达": (6, "送达问题可能影响诉讼进程"),
                "保全": (9, "财产保全可降低执行难度"),
                "和解": (5, "可评估和解的性价比"),
                "败诉": (11, "败诉风险需综合评估证据和法律依据"),
                "上诉": (7, "二审改判可能性需评估"),
            },
            "fallback_desc": "建议提供案件事实和现有证据情况，以便评估诉讼胜率。",
        },
        "assess_ip_risk": {
            "title": "知识产权风险",
            "base_score": 50,
            "keywords": {
                "专利": (10, "专利权属和有效性需核查"),
                "商标": (9, "商标近似和在先权利需排查"),
                "著作权": (8, "著作权归属和授权范围需确认"),
                "侵权": (12, "侵权比对结论需专业鉴定支持"),
                "授权": (8, "授权链条完整性需追溯"),
                "开源": (9, "开源协议合规（GPL/MIT等）需核查"),
                "竞业": (7, "竞业限制条款可能涉及商业秘密"),
                "域名": (5, "域名权属和恶意抢注需关注"),
            },
            "fallback_desc": "建议描述具体的知识产权类型和争议焦点。",
        },
    }

    pattern = _RISK_PATTERNS.get(action_id, _RISK_PATTERNS["assess_contract_risk"])
    score = int(pattern["base_score"])
    matched_risks: list[str] = []

    for keyword, (weight, risk_desc) in cast(dict[str, tuple[int, str]], pattern["keywords"]).items():
        if keyword in user_text:
            score += weight
            matched_risks.append(risk_desc)

    score = max(20, min(95, score))
    level = "low" if score < 50 else ("medium" if score < 70 else "high")

    if matched_risks:
        desc = "；".join(matched_risks[:4]) + "。"
    else:
        desc = str(pattern["fallback_desc"])

    return str(pattern["title"]), score, level, desc, matched_risks


async def _handle_risk_drilldown(action_id: str, payload: ContextDict, context: ContextDict) -> JSONDict:
    title, score, level, desc, matched = _compute_risk_score(action_id, context)

    components = [risk_indicator(title=title, score=score, level=level, description=desc)]

    if matched:
        components.append(
            detail_list(
                [{"label": f"风险点 {i+1}", "value": r} for i, r in enumerate(matched[:6])],
                title="识别到的风险点",
            )
        )

    components.append(
        text_block("如果您补充合同文本、事实经过或证据材料，我可以进一步把风险拆到更细的维度。")
    )

    return cast(JSONDict, a2ui_message(components, agent="风险评估 Agent"))


async def _handle_view_engagement_detail(payload: ContextDict, context: ContextDict) -> JSONDict:
    return cast(JSONDict, a2ui_message(
        [
            detail_list(
                [
                    {"label": "当前状态", "value": "等待律师确认"},
                    {"label": "预计响应", "value": "通常 30 分钟内"},
                    {"label": "服务方式", "value": "在线沟通"},
                    {"label": "下一步", "value": "律师确认后会通知您补充资料或安排沟通"},
                ],
                title="委托详情",
            ),
            progress_steps(
                title="当前进度",
                current_step=1,
                steps=[
                    {"id": "s1", "label": "提交委托", "status": "completed"},
                    {"id": "s2", "label": "律师确认", "status": "active"},
                    {"id": "s3", "label": "资料补充", "status": "pending"},
                    {"id": "s4", "label": "服务进行中", "status": "pending"},
                ],
                direction="vertical",
            ),
        ],
        agent="委托管理 Agent",
    ))


# ========== 「法律咨询」流程 ==========

async def _handle_legal_consultation(user_message: str, context: ContextDict) -> JSONDict:
    """处理「法律咨询」意图 → 提供快速分析入口"""
    
    components = [
        text_block("我可以为您提供以下法律服务："),
        service_selection(
            title="选择服务",
            services=[
                {
                    "id": "ai_consult", "name": "AI 智能咨询",
                    "description": "AI 即时分析您的法律问题，提供初步建议",
                    "features": ["即时响应", "法条检索", "案例参考", "免费"],
                    "price": {"amount": 0, "label": "免费"},
                    "actionId": "select_service",
                    "popular": True,
                },
                {
                    "id": "lawyer_consult", "name": "律师在线咨询",
                    "description": "连接专业律师，获得权威法律意见",
                    "features": ["专业律师", "一对一", "保密承诺", "出具意见书"],
                    "price": {"amount": 99, "unit": "起"},
                    "actionId": "select_service",
                },
            ],
        ),
    ]
    
    return cast(JSONDict, a2ui_message(components, agent="法律咨询 Agent"))
