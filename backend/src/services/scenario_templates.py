# -*- coding: utf-8 -*-
"""
场景模板引擎 (Scenario Template Engine)

为每种法律场景定义"必要信息清单"，实现精准追问。
基于纯规则评估信息完整度（< 1ms），不依赖 LLM 调用。

核心能力：
1. 场景模板注册表 — 10+ 高频法律场景的 required/optional slots
2. 信息完整度评估 — 基于正则 pattern 提取已填 slot
3. 追问问题生成 — 只问最有区分力的问题，最多 3 个
4. 置信度门控 — 够了就停，不过度追问
"""

import re
from typing import Any, Dict, List, Optional
from loguru import logger


# ========== 场景模板注册表 ==========

SCENARIO_TEMPLATES: Dict[str, Dict[str, Any]] = {

    "CONTRACT_REVIEW": {
        "name": "合同审查",
        "required_slots": [
            {
                "key": "contract_type", "label": "合同类型",
                "question": "这是什么类型的合同？",
                "options": ["买卖合同", "服务合同", "租赁合同", "劳动合同", "投资协议", "其他"],
                "extract_patterns": [
                    r"买卖", r"服务", r"租赁", r"劳动", r"投资", r"借款",
                    r"合作", r"技术开发", r"委托", r"加盟", r"特许经营",
                    r"股权转让", r"融资", r"担保", r"保密",
                ],
            },
            {
                "key": "focus_areas", "label": "关注重点",
                "question": "您重点关注哪些方面？",
                "options": ["违约责任", "付款条件", "知识产权", "保密条款", "竞业限制", "全面审查"],
                "extract_patterns": [
                    r"违约", r"付款", r"知识产权", r"保密", r"竞业",
                    r"风险", r"问题", r"陷阱", r"不合理",
                ],
            },
            {
                "key": "contract_value", "label": "合同金额",
                "question": "合同涉及的大致金额？",
                "options": ["10万以下", "10-100万", "100-1000万", "1000万以上", "暂不确定"],
                "extract_patterns": [r"\d+万", r"\d+元", r"金额", r"标的"],
            },
        ],
        "optional_slots": [
            {"key": "counterparty", "label": "对方信息", "question": "交易对方是？"},
            {
                "key": "urgency", "label": "紧急程度",
                "question": "是否有时间限制？",
                "options": ["紧急（1-2天）", "一般（1周内）", "不急"],
                "extract_patterns": [r"急", r"尽快", r"马上", r"明天", r"今天"],
            },
        ],
        "auto_complete_if": ["has_attachments"],
        "min_required_for_proceed": 1,
    },

    "LABOR_HR": {
        "name": "劳动人事",
        "required_slots": [
            {
                "key": "dispute_type", "label": "争议类型",
                "question": "具体是什么劳动问题？",
                "options": ["辞退/解除", "工资拖欠", "工伤认定", "竞业限制", "社保争议", "其他"],
                "extract_patterns": [
                    r"辞退", r"解除", r"拖欠", r"工伤", r"竞业", r"社保",
                    r"加班", r"调岗", r"降薪", r"裁员",
                ],
            },
            {
                "key": "role", "label": "您的角色",
                "question": "您是雇主还是员工？",
                "options": ["我是雇主/HR", "我是员工", "我是第三方咨询"],
                "extract_patterns": [
                    r"我是老板", r"公司方", r"HR", r"人事",
                    r"我被", r"我的工资", r"我的合同", r"员工角度",
                ],
            },
            {
                "key": "employment_status", "label": "在职状态",
                "question": "目前劳动关系状态？",
                "options": ["在职", "已离职", "试用期", "待入职"],
                "extract_patterns": [r"在职", r"离职", r"试用", r"入职"],
            },
        ],
        "optional_slots": [
            {"key": "duration", "label": "工作时长", "question": "在该单位工作了多久？"},
            {
                "key": "has_contract", "label": "劳动合同",
                "question": "是否签订过书面劳动合同？",
                "options": ["是", "否", "不确定"],
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 1,
    },

    "DOCUMENT_DRAFTING": {
        "name": "文书起草",
        "required_slots": [
            {
                "key": "doc_type", "label": "文书类型",
                "question": "需要起草什么类型的文书？",
                "options": ["律师函", "起诉状", "合同", "法律意见书", "公司章程", "其他"],
                "extract_patterns": [
                    r"律师函", r"起诉状", r"答辩状", r"合同", r"意见书",
                    r"章程", r"通知", r"声明", r"备忘录", r"仲裁申请",
                ],
            },
            {
                "key": "purpose", "label": "文书目的",
                "question": "这份文书的核心目的是什么？",
                "options": ["催款/催告", "维权/投诉", "告知/通知", "建立合作关系", "其他"],
                "extract_patterns": [
                    r"催", r"维权", r"投诉", r"通知", r"告知",
                    r"解除", r"终止", r"警告",
                ],
            },
            {
                "key": "parties", "label": "涉及方",
                "question": "涉及哪些当事人？（如：甲方公司名、乙方个人等）",
                "extract_patterns": [
                    r"甲方", r"乙方", r"公司", r"对方", r"我方",
                ],
            },
        ],
        "optional_slots": [
            {
                "key": "style", "label": "风格偏好",
                "question": "文书风格偏好？",
                "options": ["正式严谨", "简洁明了", "强硬/施压", "友好协商"],
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 1,
    },

    "LITIGATION_STRATEGY": {
        "name": "诉讼策略",
        "required_slots": [
            {
                "key": "case_type", "label": "案件类型",
                "question": "属于什么类型的纠纷？",
                "options": ["合同纠纷", "侵权纠纷", "劳动纠纷", "公司纠纷", "知识产权", "其他"],
                "extract_patterns": [
                    r"合同", r"侵权", r"劳动", r"公司", r"知识产权",
                    r"债务", r"借贷", r"房产",
                ],
            },
            {
                "key": "party_role", "label": "当事人角色",
                "question": "您是原告还是被告？",
                "options": ["原告（起诉方）", "被告（被诉方）", "还未确定"],
                "extract_patterns": [
                    r"我要起诉", r"我想告", r"原告",
                    r"被起诉", r"被告", r"被诉", r"收到传票",
                ],
            },
            {
                "key": "dispute_amount", "label": "争议金额",
                "question": "涉及的争议金额大约多少？",
                "options": ["10万以下", "10-50万", "50-500万", "500万以上", "非金钱纠纷"],
                "extract_patterns": [r"\d+万", r"\d+元", r"金额", r"标的", r"赔偿"],
            },
        ],
        "optional_slots": [
            {"key": "evidence_status", "label": "证据情况", "question": "目前掌握哪些证据？"},
            {
                "key": "timeline", "label": "时间节点",
                "question": "是否有诉讼时效压力？",
                "options": ["紧急（即将到期）", "有时间", "不确定"],
                "extract_patterns": [r"快到期", r"时效", r"期限"],
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 1,
    },

    "QA_CONSULTATION": {
        "name": "法律咨询",
        "required_slots": [],
        "optional_slots": [
            {
                "key": "context", "label": "背景信息",
                "question": "方便说一下具体背景吗？这样我能给出更精准的建议。",
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 0,
    },

    "DUE_DILIGENCE": {
        "name": "尽职调查",
        "required_slots": [
            {
                "key": "company_name", "label": "企业名称",
                "question": "请提供目标企业的全称",
                "extract_patterns": [
                    r"[\u4e00-\u9fa5]{2,}(?:有限|股份|集团|科技|实业)公司",
                    r"公司名?[：:是为]?\s*[\u4e00-\u9fa5]{2,}",
                ],
            },
            {
                "key": "focus_scope", "label": "关注范围",
                "question": "重点关注哪些方面？",
                "options": ["工商信息", "诉讼记录", "股权结构", "信用状况", "全面调查"],
                "extract_patterns": [r"工商", r"诉讼", r"股权", r"信用", r"全面"],
            },
        ],
        "optional_slots": [
            {
                "key": "purpose", "label": "调查目的",
                "question": "调查目的是什么？",
                "options": ["投资前调查", "合作前调查", "并购尽调", "供应商审查", "其他"],
                "extract_patterns": [r"投资", r"合作", r"并购", r"供应商"],
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 1,
    },

    "IP_PROTECTION": {
        "name": "知识产权",
        "required_slots": [
            {
                "key": "ip_type", "label": "IP类型",
                "question": "涉及哪种知识产权？",
                "options": ["专利", "商标", "版权/著作权", "商业秘密", "不确定"],
                "extract_patterns": [r"专利", r"商标", r"版权", r"著作权", r"秘密"],
            },
            {
                "key": "action_type", "label": "需求类型",
                "question": "您需要什么帮助？",
                "options": ["申请注册", "侵权维权", "侵权应诉", "转让/许可", "风险评估"],
                "extract_patterns": [
                    r"注册", r"申请", r"侵权", r"维权",
                    r"转让", r"许可", r"被侵", r"仿冒",
                ],
            },
        ],
        "optional_slots": [],
        "auto_complete_if": [],
        "min_required_for_proceed": 1,
    },

    "TAX_FINANCE": {
        "name": "财税合规",
        "required_slots": [
            {
                "key": "tax_issue", "label": "财税问题",
                "question": "具体是什么财税问题？",
                "options": ["税务筹划", "税务争议", "发票问题", "股权转让税", "跨境税务", "其他"],
                "extract_patterns": [
                    r"筹划", r"争议", r"发票", r"股权转让",
                    r"跨境", r"报税", r"退税", r"避税",
                ],
            },
        ],
        "optional_slots": [
            {
                "key": "entity_type", "label": "主体类型",
                "question": "您的企业类型？",
                "options": ["有限责任公司", "个体工商户", "合伙企业", "个人", "其他"],
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 0,
    },

    "REGULATORY_MONITORING": {
        "name": "合规监管",
        "required_slots": [
            {
                "key": "industry", "label": "所属行业",
                "question": "您所在的行业？",
                "options": ["金融", "医药/医疗", "互联网/科技", "教育", "房地产", "制造业", "其他"],
                "extract_patterns": [
                    r"金融", r"医药", r"医疗", r"互联网", r"科技",
                    r"教育", r"房地产", r"制造",
                ],
            },
            {
                "key": "compliance_type", "label": "合规类型",
                "question": "关注哪方面的合规？",
                "options": ["数据隐私/个保法", "反垄断", "反洗钱", "行业监管", "出口管制", "全面合规体检"],
                "extract_patterns": [
                    r"隐私", r"个保", r"数据", r"反垄断", r"反洗钱",
                    r"出口", r"GDPR", r"合规体检",
                ],
            },
        ],
        "optional_slots": [],
        "auto_complete_if": [],
        "min_required_for_proceed": 0,
    },

    "EVIDENCE_PROCESSING": {
        "name": "证据处理",
        "required_slots": [
            {
                "key": "evidence_type", "label": "证据类型",
                "question": "涉及什么类型的证据？",
                "options": ["电子证据（聊天记录/邮件）", "录音/录像", "书面文件", "实物证据", "其他"],
                "extract_patterns": [
                    r"聊天记录", r"邮件", r"录音", r"录像", r"合同",
                    r"微信", r"短信", r"截图",
                ],
            },
            {
                "key": "purpose", "label": "证据目的",
                "question": "这些证据将用于什么场景？",
                "options": ["诉讼举证", "仲裁举证", "证据保全", "证据分析", "公证"],
                "extract_patterns": [
                    r"诉讼", r"仲裁", r"保全", r"分析", r"公证",
                ],
            },
        ],
        "optional_slots": [],
        "auto_complete_if": [],
        "min_required_for_proceed": 1,
    },

    "E_SIGNATURE": {
        "name": "电子签约",
        "required_slots": [
            {
                "key": "sign_type", "label": "签约类型",
                "question": "需要签署什么类型的文件？",
                "options": ["合同签署", "协议签署", "授权文件", "会议决议", "其他"],
                "extract_patterns": [r"合同", r"协议", r"授权", r"决议"],
            },
        ],
        "optional_slots": [],
        "auto_complete_if": ["has_attachments"],
        "min_required_for_proceed": 0,
    },

    "CONTRACT_MANAGEMENT": {
        "name": "合同管理",
        "required_slots": [
            {
                "key": "mgmt_action", "label": "管理操作",
                "question": "需要进行什么合同管理操作？",
                "options": ["合同归档", "到期提醒", "履约跟踪", "合同检索", "状态查询"],
                "extract_patterns": [
                    r"归档", r"到期", r"履约", r"检索", r"查询", r"状态",
                ],
            },
        ],
        "optional_slots": [],
        "auto_complete_if": [],
        "min_required_for_proceed": 0,
    },

    "POLICY_DISTRIBUTION": {
        "name": "制度分发",
        "required_slots": [
            {
                "key": "policy_type", "label": "制度类型",
                "question": "需要发布什么类型的制度？",
                "options": ["员工手册", "规章制度", "通知公告", "培训材料", "其他"],
                "extract_patterns": [r"手册", r"规章", r"制度", r"通知", r"公告", r"培训"],
            },
        ],
        "optional_slots": [],
        "auto_complete_if": [],
        "min_required_for_proceed": 0,
    },

    "FIND_LAWYER": {
        "name": "找律师",
        "required_slots": [
            {
                "key": "legal_area", "label": "法律领域",
                "question": "您需要哪个领域的律师？",
                "options": ["合同纠纷", "劳动争议", "知识产权", "刑事辩护", "公司法务", "婚姻家庭", "其他"],
                "extract_patterns": [
                    r"合同", r"劳动", r"知识产权", r"刑事",
                    r"公司", r"婚姻", r"房产", r"交通事故",
                ],
            },
        ],
        "optional_slots": [
            {
                "key": "location", "label": "所在城市",
                "question": "您在哪个城市？",
                "extract_patterns": [
                    r"北京", r"上海", r"广州", r"深圳", r"杭州",
                    r"成都", r"武汉", r"南京", r"重庆",
                ],
            },
            {
                "key": "budget", "label": "预算范围",
                "question": "大致预算范围？",
                "options": ["5000以内", "5000-2万", "2万-10万", "10万以上", "暂不确定"],
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 0,
    },
}


def get_template(intent: str) -> Optional[Dict[str, Any]]:
    """获取场景模板"""
    return SCENARIO_TEMPLATES.get(intent)


def get_all_intents() -> List[str]:
    """获取所有已注册的意图"""
    return list(SCENARIO_TEMPLATES.keys())


def assess_completeness(
    user_input: str,
    intent: str,
    has_attachments: bool = False,
    pre_filled_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    基于场景模板的信息完整度评估（纯规则，无 LLM 调用，< 1ms）。

    支持置信度门控：够了就停，不过度追问。

    Args:
        user_input: 用户输入文本
        intent: 识别到的意图
        has_attachments: 是否有附件
        pre_filled_context: 从用户画像预填的上下文（减少重复追问）

    Returns:
        {
            "is_complete": bool,
            "score": float (0-1),
            "filled_slots": [{"key": ..., "label": ..., "value": ...}],
            "missing_slots": [{"key": ..., "label": ...}],
            "questions": [{"question": ..., "options": [...], "purpose": ...}],
        }
    """
    template = SCENARIO_TEMPLATES.get(intent)
    if not template:
        return {
            "is_complete": True, "score": 1.0,
            "filled_slots": [], "missing_slots": [], "questions": [],
        }

    required = template["required_slots"]
    if not required:
        return {
            "is_complete": True, "score": 1.0,
            "filled_slots": [], "missing_slots": [], "questions": [],
        }

    pre_filled = pre_filled_context or {}
    input_lower = user_input.lower()
    filled = []
    missing = []

    for slot in required:
        slot_key = slot["key"]

        # 1. 先看用户画像是否已有此信息
        if slot_key in pre_filled and pre_filled[slot_key]:
            filled.append({
                "key": slot_key,
                "label": slot["label"],
                "value": pre_filled[slot_key],
                "source": "profile",
            })
            continue

        # 2. 用正则 pattern 从用户输入中提取
        patterns = slot.get("extract_patterns", [])
        matched_value = None
        for p in patterns:
            match = re.search(p, input_lower)
            if match:
                matched_value = match.group(0)
                break

        if matched_value:
            filled.append({
                "key": slot_key,
                "label": slot["label"],
                "value": matched_value,
                "source": "input",
            })
        else:
            missing.append({"key": slot_key, "label": slot["label"]})

    # 附件自动提升完整度
    score_boost = 0.0
    if has_attachments and "has_attachments" in template.get("auto_complete_if", []):
        score_boost = 0.3

    total = len(required)
    base_score = len(filled) / total if total > 0 else 1.0
    score = min(base_score + score_boost, 1.0)

    # 消息长度也影响完整度（长消息通常包含更多上下文）
    if len(user_input) > 100:
        score = min(score + 0.1, 1.0)
    if len(user_input) > 200:
        score = min(score + 0.1, 1.0)

    # 生成追问问题（置信度门控：最多 3 个，按重要性排序）
    questions = []
    for slot_info in missing[:3]:
        slot_key = slot_info["key"]
        # 从模板中找回完整 slot 定义
        slot_def = next((s for s in required if s["key"] == slot_key), None)
        if slot_def:
            q: Dict[str, Any] = {
                "question": slot_def["question"],
                "purpose": slot_def["label"],
            }
            if "options" in slot_def:
                q["options"] = slot_def["options"]
            questions.append(q)

    min_required = template.get("min_required_for_proceed", 1)
    is_complete = len(filled) >= min_required or score >= 0.7

    return {
        "is_complete": is_complete,
        "score": round(score, 2),
        "filled_slots": filled,
        "missing_slots": [{"key": s["key"], "label": s["label"]} for s in missing],
        "questions": questions,
    }


def merge_clarification_into_slots(
    original_assessment: Dict[str, Any],
    user_selections: Dict[str, str],
) -> Dict[str, Any]:
    """
    将用户的澄清回复合并到 slot 评估中。

    Args:
        original_assessment: assess_completeness 的结果
        user_selections: 用户选择 {"问题文本": "选项文本"}

    Returns:
        更新后的 assessment
    """
    filled = list(original_assessment.get("filled_slots", []))
    remaining_missing = []

    for slot in original_assessment.get("missing_slots", []):
        # 尝试匹配用户选择
        matched = False
        for q_text, answer in user_selections.items():
            if slot["label"] in q_text or slot["key"] in q_text.lower():
                filled.append({
                    "key": slot["key"],
                    "label": slot["label"],
                    "value": answer,
                    "source": "clarification",
                })
                matched = True
                break
        if not matched:
            remaining_missing.append(slot)

    total = len(filled) + len(remaining_missing)
    score = len(filled) / total if total > 0 else 1.0

    return {
        "is_complete": score >= 0.5,  # 澄清后降低阈值
        "score": round(score, 2),
        "filled_slots": filled,
        "missing_slots": remaining_missing,
        "questions": [],  # 澄清后不再追问
    }


def build_context_summary(filled_slots: List[Dict[str, Any]]) -> str:
    """
    将已填充的 slots 构建为上下文摘要，注入到 Agent prompt 中。

    Returns:
        格式化的上下文字符串
    """
    if not filled_slots:
        return ""

    lines = ["[已收集的需求信息]"]
    for slot in filled_slots:
        source_label = {"input": "用户提供", "profile": "用户画像", "clarification": "补充确认"}.get(
            slot.get("source", ""), ""
        )
        lines.append(f"- {slot['label']}: {slot['value']}（{source_label}）")

    return "\n".join(lines)
