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
from typing import Optional, Dict, Any, List, Tuple
from loguru import logger

from src.services.a2ui_protocol import (
    a2ui_message, lawyer_card, horizontal_scroll, service_selection,
    text_block, info_banner, button_group, form_sheet, form_section,
    form_option, order_card, detail_list, status_card, progress_steps,
    risk_indicator, divider, contract_preview, recommendation_card,
)


# ========== 意图检测 ==========

# 意图关键词映射
INTENT_PATTERNS: List[Tuple[str, List[str]]] = [
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
        r"尽调",
    ]),
    ("legal_consultation", [
        r"法律.*[问题咨询]", r"法务.*咨询", r"怎么.{0,6}法律",
        r"合法[吗么]", r"违法[吗么]", r"法律上",
    ]),
]


def detect_intent(message: str) -> Optional[str]:
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
    context: Dict[str, Any] = None,
) -> Optional[dict]:
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
    payload: Dict[str, Any] = None,
    form_data: Dict[str, Any] = None,
    context: Dict[str, Any] = None,
) -> Optional[dict]:
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
    
    logger.warning(f"[A2UI] 未处理的 action: {action_id}")
    return None


# ========== 「找律师」完整流程 ==========

# 模拟律师数据库
MOCK_LAWYERS = [
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


async def _handle_find_lawyer(user_message: str, context: dict) -> dict:
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
    cards = []
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
    
    return a2ui_message(
        components,
        text="",
        agent="律师推荐 Agent",
    )


async def _handle_contact_lawyer(payload: dict, context: dict) -> dict:
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
    
    return a2ui_message(components, agent="服务选择 Agent")


async def _handle_select_service(payload: dict, context: dict) -> dict:
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
    
    return a2ui_message(components, agent="委托信息收集 Agent")


async def _handle_submit_engagement(form_data: dict, context: dict) -> dict:
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
    
    return a2ui_message(components, agent="委托确认 Agent")


async def _handle_confirm_engagement(payload: dict, context: dict) -> dict:
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
    
    return a2ui_message(
        components,
        text="",
        agent="委托管理 Agent",
    )


async def _handle_view_lawyer_detail(payload: dict, context: dict) -> dict:
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
    
    return a2ui_message(components, agent="律师详情 Agent")


# ========== 「合同审查」流程 ==========

async def _handle_review_contract(user_message: str, context: dict) -> dict:
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
    
    return a2ui_message(components, agent="合同审查 Agent")


async def _handle_upload_contract(payload: dict, context: dict) -> dict:
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
    return a2ui_message(components, agent="合同审查 Agent")


async def _handle_start_review(payload: dict, context: dict) -> dict:
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
    return a2ui_message(components, agent="合同审查 Agent")


# ========== 「文书起草」流程 ==========

async def _handle_draft_document(user_message: str, context: dict) -> dict:
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
    
    return a2ui_message(components, agent="文书起草 Agent")


# ========== 「风险评估」流程 ==========

async def _handle_risk_assessment(user_message: str, context: dict) -> dict:
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
    
    return a2ui_message(components, agent="风险评估 Agent")


# ========== 「尽职调查」流程 ==========

async def _handle_due_diligence(user_message: str, context: dict) -> dict:
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
    
    return a2ui_message(components, agent="尽职调查 Agent")


# ========== 「法律咨询」流程 ==========

async def _handle_legal_consultation(user_message: str, context: dict) -> dict:
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
    
    return a2ui_message(components, agent="法律咨询 Agent")
