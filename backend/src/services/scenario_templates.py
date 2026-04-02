# -*- coding: utf-8 -*-
"""
场景模板引擎 v3 (Scenario Template Engine)

为每种法律场景定义"必要信息清单"，实现精准追问。
基于纯规则评估信息完整度（< 1ms），不依赖 LLM 调用。

核心能力：
1. 场景模板注册表 — 19 个法律场景的 required/optional slots
2. 子模板动态分支 — 根据用户输入自动切换到子场景专用 slots
3. 信息完整度评估 — 基于正则 pattern 提取已填 slot
4. 苏格拉底式渐进追问 — 先核心问题、后细化问题，支持多轮
5. 置信度门控 — 够了就停，不过度追问

v3 改进：
- 扩展 CONTRACT_REVIEW/LITIGATION/LABOR_HR/IP_PROTECTION 子模板
- 新增 DEBT_COLLECTION/CORPORATE_GOVERNANCE/FAMILY_LAW/REAL_ESTATE/CRIMINAL 场景
- 修复完整度评分膨胀（移除消息长度虚加分，改为有效信息密度）
- 提升 min_required_for_proceed 阈值（防止信息不足就跳过追问）
- QA_CONSULTATION 增加引导 slots
- 支持多轮渐进追问标记（round 字段）
"""

import re
from typing import Any, Dict, List, Optional
from loguru import logger


# ========== 场景模板注册表 ==========

SCENARIO_TEMPLATES: Dict[str, Dict[str, Any]] = {

    # ================================================================
    # 1. 合同审查
    # ================================================================
    "CONTRACT_REVIEW": {
        "name": "合同审查",
        "required_slots": [
            {
                "key": "contract_type", "label": "合同类型",
                "question": "这是什么类型的合同？",
                "options": ["买卖/销售合同", "服务/委托合同", "租赁合同", "劳动合同", "投资/融资协议", "其他"],
                "extract_patterns": [
                    r"买卖", r"销售", r"采购", r"服务", r"委托", r"租赁",
                    r"劳动", r"投资", r"借款", r"合作", r"技术开发",
                    r"加盟", r"特许经营", r"股权转让", r"融资", r"担保", r"保密",
                ],
                "round": 1,
            },
            {
                "key": "focus_areas", "label": "关注重点",
                "question": "您重点关注哪些方面？",
                "options": ["违约责任", "付款条件", "知识产权", "保密条款", "竞业限制", "全面审查"],
                "extract_patterns": [
                    r"违约", r"付款", r"知识产权", r"保密", r"竞业",
                    r"风险", r"问题", r"陷阱", r"不合理",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "contract_value", "label": "合同金额",
                "question": "合同涉及的大致金额？（影响风险评估等级）",
                "options": ["10万以下", "10-100万", "100-1000万", "1000万以上", "暂不确定"],
                "extract_patterns": [r"\d+万", r"\d+元", r"金额", r"标的"],
                "round": 2,
            },
            {
                "key": "sign_status", "label": "签署状态",
                "question": "合同目前处于什么阶段？",
                "options": ["谈判中/未签署", "已签署/待履行", "履行中有争议", "已到期待续签"],
                "extract_patterns": [r"还没签", r"已签", r"在谈", r"即将签", r"到期"],
                "round": 2,
            },
            {"key": "counterparty", "label": "对方信息", "question": "交易对方是？", "round": 2},
            {
                "key": "urgency", "label": "紧急程度",
                "question": "是否有时间限制？",
                "options": ["紧急（1-2天）", "一般（1周内）", "不急"],
                "extract_patterns": [r"急", r"尽快", r"马上", r"明天", r"今天"],
                "round": 2,
            },
        ],
        "auto_complete_if": ["has_attachments"],
        "min_required_for_proceed": 2,
        "sub_templates": {
            "labor_contract": {
                "detect_patterns": [r"劳动合同", r"劳动"],
                "required_slots": [
                    {
                        "key": "labor_focus", "label": "关注重点",
                        "question": "劳动合同审查重点关注什么？",
                        "options": ["试用期条款", "竞业限制/保密", "薪酬福利", "解除/终止条件", "加班与休假", "全面审查"],
                        "extract_patterns": [r"试用", r"竞业", r"保密", r"薪酬", r"解除", r"加班"],
                        "round": 1,
                    },
                    {
                        "key": "role", "label": "审查方角色",
                        "question": "您是用人单位还是劳动者？",
                        "options": ["用人单位/HR", "劳动者/员工"],
                        "extract_patterns": [r"公司", r"HR", r"人事", r"员工", r"我要入职"],
                        "round": 1,
                    },
                ],
            },
            "investment_agreement": {
                "detect_patterns": [r"投资", r"融资", r"股权"],
                "required_slots": [
                    {
                        "key": "invest_focus", "label": "关注重点",
                        "question": "投资协议审查重点关注什么？",
                        "options": ["估值与对价", "对赌条款", "反稀释保护", "退出机制", "治理权利", "全面审查"],
                        "extract_patterns": [r"估值", r"对赌", r"稀释", r"退出", r"治理"],
                        "round": 1,
                    },
                    {
                        "key": "invest_role", "label": "您的角色",
                        "question": "您是投资方还是融资方？",
                        "options": ["投资方/基金", "融资方/创业公司", "第三方顾问"],
                        "extract_patterns": [r"投资方", r"基金", r"VC", r"融资", r"创业"],
                        "round": 1,
                    },
                ],
            },
        },
    },

    # ================================================================
    # 2. 劳动人事
    # ================================================================
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
                "round": 1,
            },
            {
                "key": "role", "label": "您的角色",
                "question": "您是雇主还是员工？",
                "options": ["我是雇主/HR", "我是员工", "我是第三方咨询"],
                "extract_patterns": [
                    r"我是老板", r"公司方", r"HR", r"人事",
                    r"我被", r"我的工资", r"我的合同", r"员工角度",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "employment_status", "label": "在职状态",
                "question": "目前劳动关系状态？",
                "options": ["在职", "已离职", "试用期", "待入职"],
                "extract_patterns": [r"在职", r"离职", r"试用", r"入职"],
                "round": 2,
            },
            {"key": "duration", "label": "工作时长", "question": "在该单位工作了多久？", "round": 2},
            {
                "key": "has_contract", "label": "劳动合同",
                "question": "是否签订过书面劳动合同？",
                "options": ["有书面合同", "没有签合同", "合同已过期"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
        "sub_templates": {
            "dismissal": {
                "detect_patterns": [r"辞退", r"解除", r"裁员", r"开除", r"被炒"],
                "required_slots": [
                    {
                        "key": "dismissal_type", "label": "解除方式",
                        "question": "是哪种解除方式？",
                        "options": ["公司单方辞退", "协商解除", "合同到期不续", "员工被迫离职", "不确定"],
                        "extract_patterns": [r"辞退", r"协商", r"到期", r"被迫", r"逼我走"],
                        "round": 1,
                    },
                    {
                        "key": "role", "label": "您的角色",
                        "question": "您是被辞退的一方还是公司方？",
                        "options": ["我是被辞退的员工", "我是公司/HR"],
                        "extract_patterns": [r"我被", r"公司", r"HR"],
                        "round": 1,
                    },
                ],
                "optional_slots": [
                    {
                        "key": "compensation", "label": "补偿情况",
                        "question": "公司是否提出经济补偿？",
                        "options": ["有补偿但偏低", "拒绝补偿", "还在协商中", "已接受补偿"],
                        "extract_patterns": [r"补偿", r"赔偿", r"N\+", r"n\+"],
                        "round": 2,
                    },
                    {
                        "key": "work_years", "label": "工作年限",
                        "question": "在该单位工作了几年？（影响补偿计算）",
                        "extract_patterns": [r"\d+年", r"半年", r"几个月"],
                        "round": 2,
                    },
                ],
            },
            "wage_dispute": {
                "detect_patterns": [r"拖欠", r"工资", r"欠薪", r"加班费"],
                "required_slots": [
                    {
                        "key": "wage_type", "label": "拖欠类型",
                        "question": "具体拖欠了什么？",
                        "options": ["基本工资", "加班费", "提成/奖金", "社保/公积金", "多项拖欠"],
                        "extract_patterns": [r"工资", r"加班", r"提成", r"奖金", r"社保"],
                        "round": 1,
                    },
                    {
                        "key": "amount_duration", "label": "金额与时长",
                        "question": "大约拖欠了多少钱、多长时间？",
                        "extract_patterns": [r"\d+万", r"\d+元", r"\d+个月", r"半年"],
                        "round": 1,
                    },
                ],
            },
            "work_injury": {
                "detect_patterns": [r"工伤", r"受伤", r"职业病"],
                "required_slots": [
                    {
                        "key": "injury_stage", "label": "处理阶段",
                        "question": "工伤处理到哪个阶段了？",
                        "options": ["刚受伤/未申报", "已申报待认定", "已认定待鉴定", "已鉴定谈赔偿", "赔偿有争议"],
                        "extract_patterns": [r"刚", r"申报", r"认定", r"鉴定", r"赔偿"],
                        "round": 1,
                    },
                    {
                        "key": "injury_detail", "label": "伤情概况",
                        "question": "伤情大致情况？（如：骨折、截肢、职业病等）",
                        "extract_patterns": [r"骨折", r"截肢", r"烧伤", r"职业病", r"死亡"],
                        "round": 1,
                    },
                ],
            },
        },
    },

    # ================================================================
    # 3. 文书起草
    # ================================================================
    "DOCUMENT_DRAFTING": {
        "name": "文书起草",
        "required_slots": [
            {
                "key": "doc_type", "label": "文书类型",
                "question": "需要起草什么类型的文书？",
                "options": ["律师函", "起诉状/答辩状", "合同/协议", "法律意见书", "公司章程", "其他"],
                "extract_patterns": [
                    r"律师函", r"起诉状", r"答辩状", r"合同", r"协议", r"意见书",
                    r"章程", r"通知", r"声明", r"备忘录", r"仲裁申请",
                ],
                "round": 1,
            },
            {
                "key": "purpose", "label": "文书目的",
                "question": "这份文书的核心目的是什么？",
                "options": ["催款/催告", "维权/投诉", "告知/通知", "建立合作关系", "其他"],
                "extract_patterns": [
                    r"催", r"维权", r"投诉", r"通知", r"告知",
                    r"解除", r"终止", r"警告",
                ],
                "round": 1,
            },
            {
                "key": "parties", "label": "涉及方",
                "question": "涉及哪些当事人？（如：甲方公司名、乙方个人等）",
                "extract_patterns": [
                    r"甲方", r"乙方", r"公司", r"对方", r"我方",
                ],
                "round": 2,
            },
        ],
        "optional_slots": [
            {
                "key": "style", "label": "风格偏好",
                "question": "文书风格偏好？",
                "options": ["正式严谨", "简洁明了", "强硬/施压", "友好协商"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
        "sub_templates": {
            "contract": {
                "detect_patterns": [r"合同", r"协议"],
                "required_slots": [
                    {
                        "key": "contract_sub_type", "label": "合同类型",
                        "question": "这是什么类型的合同/协议？",
                        "options": ["买卖/销售合同", "服务合同", "租赁合同", "合作协议", "保密协议（NDA）", "劳动/劳务合同"],
                        "extract_patterns": [
                            r"买卖", r"销售", r"采购", r"购销",
                            r"服务", r"委托", r"咨询", r"外包",
                            r"租赁", r"租房", r"厂房",
                            r"合作", r"战略", r"联营", r"框架",
                            r"保密", r"NDA", r"nda",
                            r"劳动", r"劳务", r"用工", r"雇佣",
                            r"加盟", r"特许", r"代理", r"经销", r"分销",
                            r"技术开发", r"技术转让", r"许可",
                            r"股权转让", r"投资", r"融资",
                            r"借款", r"借贷", r"担保",
                        ],
                        "round": 1,
                    },
                    {
                        "key": "contract_parties", "label": "合同双方",
                        "question": "合同双方分别是？（如：甲方XXX公司，乙方XXX）",
                        "extract_patterns": [
                            r"甲方", r"乙方", r"公司", r"对方", r"我方",
                            r"买方", r"卖方", r"出租", r"承租",
                        ],
                        "round": 1,
                    },
                    {
                        "key": "contract_subject", "label": "合同标的",
                        "question": "合同涉及的主要内容是什么？（如：标的物、服务内容、金额等）",
                        "extract_patterns": [
                            r"\d+万", r"\d+元", r"金额", r"标的",
                            r"货物", r"商品", r"产品", r"设备",
                            r"房屋", r"场地", r"土地",
                        ],
                        "round": 2,
                    },
                ],
                "optional_slots": [
                    {
                        "key": "contract_term", "label": "合同期限",
                        "question": "合同期限大约多长？",
                        "options": ["1年以内", "1-3年", "3年以上", "一次性交易", "暂不确定"],
                        "extract_patterns": [r"\d+年", r"\d+月", r"长期", r"短期", r"一次"],
                        "round": 2,
                    },
                    {
                        "key": "special_terms", "label": "特殊条款",
                        "question": "是否有需要特别关注的条款？",
                        "options": ["违约责任", "知识产权归属", "保密条款", "竞业限制", "争议解决方式", "暂时没有"],
                        "extract_patterns": [
                            r"违约", r"知识产权", r"保密", r"竞业", r"仲裁", r"管辖",
                        ],
                        "round": 2,
                    },
                ],
            },
            "lawyer_letter": {
                "detect_patterns": [r"律师函"],
                "required_slots": [
                    {
                        "key": "letter_purpose", "label": "律师函目的",
                        "question": "发送律师函的目的是什么？",
                        "options": ["催款/催告", "维权警告", "解除/终止合同", "要求停止侵权", "告知/通知"],
                        "extract_patterns": [
                            r"催款", r"催告", r"催收", r"维权", r"警告",
                            r"解除", r"终止", r"侵权", r"通知",
                        ],
                        "round": 1,
                    },
                    {
                        "key": "letter_parties", "label": "发送对象",
                        "question": "律师函发送给谁？（个人/公司名称）",
                        "extract_patterns": [r"甲方", r"乙方", r"公司", r"对方", r"我方"],
                        "round": 1,
                    },
                    {
                        "key": "letter_facts", "label": "基本事实",
                        "question": "请简述涉及的基本事实（如：欠款金额、违约情况等）",
                        "extract_patterns": [r"\d+万", r"\d+元", r"欠款", r"违约", r"损失"],
                        "round": 2,
                    },
                ],
            },
            "complaint": {
                "detect_patterns": [r"起诉状", r"答辩状", r"仲裁申请"],
                "required_slots": [
                    {
                        "key": "case_type", "label": "案件类型",
                        "question": "属于什么类型的纠纷？",
                        "options": ["合同纠纷", "侵权纠纷", "劳动争议", "知识产权", "民间借贷", "其他"],
                        "extract_patterns": [r"合同", r"侵权", r"劳动", r"知识产权", r"借贷"],
                        "round": 1,
                    },
                    {
                        "key": "complaint_role", "label": "诉讼角色",
                        "question": "您是起诉方还是应诉方？",
                        "options": ["起诉方（需要起诉状）", "应诉方（需要答辩状）"],
                        "extract_patterns": [r"起诉", r"答辩", r"被告"],
                        "round": 1,
                    },
                    {
                        "key": "dispute_facts", "label": "纠纷事实",
                        "question": "请简述纠纷的基本事实和诉求",
                        "extract_patterns": [r"要求", r"赔偿", r"返还", r"支付"],
                        "round": 2,
                    },
                ],
            },
        },
    },

    # ================================================================
    # 4. 诉讼策略
    # ================================================================
    "LITIGATION_STRATEGY": {
        "name": "诉讼策略",
        "required_slots": [
            {
                "key": "case_type", "label": "案件类型",
                "question": "属于什么类型的纠纷？",
                "options": ["合同纠纷", "侵权纠纷", "劳动纠纷", "公司纠纷", "知识产权", "民间借贷", "其他"],
                "extract_patterns": [
                    r"合同", r"侵权", r"劳动", r"公司", r"知识产权",
                    r"债务", r"借贷", r"房产", r"婚姻",
                ],
                "round": 1,
            },
            {
                "key": "party_role", "label": "当事人角色",
                "question": "您是原告还是被告？",
                "options": ["原告（起诉方）", "被告（被诉方）", "还未确定/考虑中"],
                "extract_patterns": [
                    r"我要起诉", r"我想告", r"原告",
                    r"被起诉", r"被告", r"被诉", r"收到传票",
                ],
                "round": 1,
            },
            {
                "key": "litigation_stage", "label": "诉讼阶段",
                "question": "目前处于什么阶段？",
                "options": ["起诉前准备", "一审进行中", "一审已判/考虑上诉", "二审/再审", "执行阶段"],
                "extract_patterns": [
                    r"还没起诉", r"准备起诉", r"一审", r"二审", r"再审",
                    r"执行", r"判决", r"上诉",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "dispute_amount", "label": "争议金额",
                "question": "涉及的争议金额大约多少？",
                "options": ["10万以下", "10-50万", "50-500万", "500万以上", "非金钱纠纷"],
                "extract_patterns": [r"\d+万", r"\d+元", r"金额", r"标的", r"赔偿"],
                "round": 2,
            },
            {"key": "evidence_status", "label": "证据情况", "question": "目前掌握哪些证据？", "round": 2},
            {
                "key": "timeline", "label": "时间压力",
                "question": "是否有诉讼时效或期限压力？",
                "options": ["紧急（即将到期）", "有时间", "不确定"],
                "extract_patterns": [r"快到期", r"时效", r"期限", r"快过了"],
                "round": 2,
            },
            {
                "key": "has_lawyer", "label": "是否有律师",
                "question": "目前是否已有代理律师？",
                "options": ["已有律师", "没有律师", "正在找律师"],
                "extract_patterns": [r"有律师", r"请了律师", r"没有律师", r"自己"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
        "sub_templates": {
            "contract_dispute": {
                "detect_patterns": [r"合同纠纷", r"合同.*违约", r"违约"],
                "required_slots": [
                    {
                        "key": "party_role", "label": "诉讼角色",
                        "question": "您是守约方还是被指控违约方？",
                        "options": ["我是守约方（对方违约）", "我被指控违约", "双方互有违约"],
                        "extract_patterns": [r"对方违约", r"我被", r"双方"],
                        "round": 1,
                    },
                    {
                        "key": "breach_type", "label": "违约情形",
                        "question": "具体是什么违约情况？",
                        "options": ["不付款/延迟付款", "不交货/质量问题", "单方解除合同", "违反保密/竞业", "其他违约"],
                        "extract_patterns": [r"不付", r"欠款", r"质量", r"解除", r"保密"],
                        "round": 1,
                    },
                ],
            },
            "tort_dispute": {
                "detect_patterns": [r"侵权", r"人身伤害", r"损害赔偿"],
                "required_slots": [
                    {
                        "key": "tort_type", "label": "侵权类型",
                        "question": "属于什么侵权类型？",
                        "options": ["人身伤害", "财产损害", "名誉/隐私侵权", "产品责任", "医疗纠纷", "交通事故"],
                        "extract_patterns": [r"受伤", r"损害", r"名誉", r"产品", r"医疗", r"交通"],
                        "round": 1,
                    },
                    {
                        "key": "damage_facts", "label": "损害事实",
                        "question": "请简述损害的基本事实和损失情况",
                        "extract_patterns": [r"损失", r"\d+万", r"受伤", r"赔偿"],
                        "round": 1,
                    },
                ],
            },
        },
    },

    # ================================================================
    # 5. 法律咨询 (v3: 增加引导 slots)
    # ================================================================
    "QA_CONSULTATION": {
        "name": "法律咨询",
        "required_slots": [
            {
                "key": "legal_domain", "label": "法律领域",
                "question": "您想咨询哪方面的法律问题？",
                "options": ["合同/商事", "劳动/用工", "知识产权", "公司/股权", "婚姻家庭", "房产/物权", "其他"],
                "extract_patterns": [
                    r"合同", r"劳动", r"知识产权", r"专利", r"商标",
                    r"公司", r"股权", r"婚姻", r"离婚", r"房产", r"房屋",
                    r"借贷", r"侵权", r"刑事",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "context", "label": "背景信息",
                "question": "方便说一下具体背景吗？这样我能给出更精准的建议。",
                "round": 1,
            },
            {
                "key": "purpose", "label": "咨询目的",
                "question": "您咨询的目的是？",
                "options": ["了解权利义务", "评估风险", "寻求解决方案", "确认法律法规", "纯学术了解"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 1,
    },

    # ================================================================
    # 6. 尽职调查
    # ================================================================
    "DUE_DILIGENCE": {
        "name": "尽职调查",
        "required_slots": [
            {
                "key": "company_name", "label": "企业名称",
                "question": "请提供目标企业的名称",
                "extract_patterns": [
                    r"[\u4e00-\u9fa5]{2,}(?:有限|股份|集团|科技|实业|网络|信息|电子|生物|医药)(?:公司|企业)?",
                    r"公司名?[：:是为]?\s*[\u4e00-\u9fa5]{2,}",
                    r"[\u4e00-\u9fa5]{2,}(?:公司|企业|集团)",
                ],
                "round": 1,
            },
            {
                "key": "focus_scope", "label": "关注范围",
                "question": "重点关注哪些方面？",
                "options": ["工商信息", "诉讼记录", "股权结构", "信用状况", "全面调查"],
                "extract_patterns": [r"工商", r"诉讼", r"股权", r"信用", r"全面"],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "purpose", "label": "调查目的",
                "question": "调查目的是什么？",
                "options": ["投资前调查", "合作前调查", "并购尽调", "供应商审查", "其他"],
                "extract_patterns": [r"投资", r"合作", r"并购", r"供应商"],
                "round": 2,
            },
            {
                "key": "urgency", "label": "紧急程度",
                "question": "调查时间要求？",
                "options": ["紧急（1-3天）", "一般（1-2周）", "不急"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # 7. 知识产权
    # ================================================================
    "IP_PROTECTION": {
        "name": "知识产权",
        "required_slots": [
            {
                "key": "ip_type", "label": "IP类型",
                "question": "涉及哪种知识产权？",
                "options": ["专利", "商标", "版权/著作权", "商业秘密", "不确定"],
                "extract_patterns": [r"专利", r"商标", r"版权", r"著作权", r"秘密"],
                "round": 1,
            },
            {
                "key": "action_type", "label": "需求类型",
                "question": "您需要什么帮助？",
                "options": ["申请注册", "侵权维权", "侵权应诉", "转让/许可", "风险评估"],
                "extract_patterns": [
                    r"注册", r"申请", r"侵权", r"维权",
                    r"转让", r"许可", r"被侵", r"仿冒",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "ip_status", "label": "权利状态",
                "question": "知识产权目前的状态？",
                "options": ["已注册/已授权", "申请中", "还未申请", "被驳回/异议"],
                "extract_patterns": [r"已注册", r"已授权", r"申请中", r"驳回"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
        "sub_templates": {
            "patent": {
                "detect_patterns": [r"专利"],
                "required_slots": [
                    {
                        "key": "patent_action", "label": "专利需求",
                        "question": "具体需要什么专利服务？",
                        "options": ["发明专利申请", "实用新型申请", "外观设计申请", "专利侵权分析", "专利无效宣告", "FTO检索"],
                        "extract_patterns": [r"发明", r"实用", r"外观", r"侵权", r"无效", r"FTO", r"fto"],
                        "round": 1,
                    },
                ],
            },
            "trademark": {
                "detect_patterns": [r"商标"],
                "required_slots": [
                    {
                        "key": "tm_action", "label": "商标需求",
                        "question": "具体需要什么商标服务？",
                        "options": ["商标注册申请", "商标近似检索", "商标侵权维权", "商标异议/撤销", "商标转让/许可"],
                        "extract_patterns": [r"注册", r"检索", r"近似", r"侵权", r"异议", r"转让"],
                        "round": 1,
                    },
                    {
                        "key": "tm_name", "label": "商标名称",
                        "question": "商标名称或内容是什么？",
                        "extract_patterns": [r"商标.*?[\"\"「」''][\u4e00-\u9fa5A-Za-z]+"],
                        "round": 1,
                    },
                ],
            },
        },
    },

    # ================================================================
    # 8. 财税合规
    # ================================================================
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
                "round": 1,
            },
            {
                "key": "entity_type", "label": "主体类型",
                "question": "您的企业类型？",
                "options": ["有限责任公司", "个体工商户", "合伙企业", "个人", "其他"],
                "extract_patterns": [r"公司", r"个体", r"合伙", r"个人"],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "tax_amount", "label": "涉及金额",
                "question": "涉及的大致金额？",
                "options": ["10万以下", "10-100万", "100万以上", "暂不确定"],
                "extract_patterns": [r"\d+万", r"\d+元"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # 9. 合规监管
    # ================================================================
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
                "round": 1,
            },
            {
                "key": "compliance_type", "label": "合规类型",
                "question": "关注哪方面的合规？",
                "options": ["数据隐私/个保法", "反垄断", "反洗钱", "行业监管", "出口管制", "全面合规体检"],
                "extract_patterns": [
                    r"隐私", r"个保", r"数据", r"反垄断", r"反洗钱",
                    r"出口", r"GDPR", r"合规体检",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # 10. 证据处理
    # ================================================================
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
                "round": 1,
            },
            {
                "key": "purpose", "label": "证据目的",
                "question": "这些证据将用于什么场景？",
                "options": ["诉讼举证", "仲裁举证", "证据保全", "证据分析", "公证"],
                "extract_patterns": [
                    r"诉讼", r"仲裁", r"保全", r"分析", r"公证",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # 11. 电子签约
    # ================================================================
    "E_SIGNATURE": {
        "name": "电子签约",
        "required_slots": [
            {
                "key": "sign_type", "label": "签约类型",
                "question": "需要签署什么类型的文件？",
                "options": ["合同签署", "协议签署", "授权文件", "会议决议", "其他"],
                "extract_patterns": [r"合同", r"协议", r"授权", r"决议"],
                "round": 1,
            },
        ],
        "optional_slots": [],
        "auto_complete_if": ["has_attachments"],
        "min_required_for_proceed": 1,
    },

    # ================================================================
    # 12. 合同管理
    # ================================================================
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
                "round": 1,
            },
        ],
        "optional_slots": [],
        "auto_complete_if": [],
        "min_required_for_proceed": 1,
    },

    # ================================================================
    # 13. 制度分发
    # ================================================================
    "POLICY_DISTRIBUTION": {
        "name": "制度分发",
        "required_slots": [
            {
                "key": "policy_type", "label": "制度类型",
                "question": "需要发布什么类型的制度？",
                "options": ["员工手册", "规章制度", "通知公告", "培训材料", "其他"],
                "extract_patterns": [r"手册", r"规章", r"制度", r"通知", r"公告", r"培训"],
                "round": 1,
            },
        ],
        "optional_slots": [],
        "auto_complete_if": [],
        "min_required_for_proceed": 1,
    },

    # ================================================================
    # 14. 找律师
    # ================================================================
    "FIND_LAWYER": {
        "name": "找律师",
        "required_slots": [
            {
                "key": "legal_area", "label": "法律领域",
                "question": "您需要哪个领域的律师？",
                "options": ["合同纠纷", "劳动争议", "知识产权", "刑事辩护", "公司法务", "婚姻家庭", "房产纠纷", "其他"],
                "extract_patterns": [
                    r"合同", r"劳动", r"知识产权", r"刑事",
                    r"公司", r"婚姻", r"房产", r"交通事故",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "location", "label": "所在城市",
                "question": "您在哪个城市？",
                "extract_patterns": [
                    r"北京", r"上海", r"广州", r"深圳", r"杭州",
                    r"成都", r"武汉", r"南京", r"重庆", r"天津",
                    r"苏州", r"长沙", r"郑州", r"西安", r"青岛",
                ],
                "round": 1,
            },
            {
                "key": "budget", "label": "预算范围",
                "question": "大致预算范围？",
                "options": ["5000以内", "5000-2万", "2万-10万", "10万以上", "暂不确定"],
                "round": 2,
            },
            {
                "key": "case_brief", "label": "案情简述",
                "question": "简单描述您的情况（帮助匹配经验最对口的律师）",
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 1,
    },

    # ================================================================
    # 15. 债务催收 (NEW v3)
    # ================================================================
    "DEBT_COLLECTION": {
        "name": "债务催收",
        "required_slots": [
            {
                "key": "debt_type", "label": "债务类型",
                "question": "属于什么类型的债务？",
                "options": ["合同欠款", "民间借贷", "工程款", "货款", "服务费", "其他"],
                "extract_patterns": [
                    r"欠款", r"借贷", r"借钱", r"工程款", r"货款",
                    r"服务费", r"尾款", r"欠我", r"不还钱",
                ],
                "round": 1,
            },
            {
                "key": "debt_amount", "label": "欠款金额",
                "question": "大约欠了多少钱？",
                "options": ["5万以下", "5-50万", "50-500万", "500万以上"],
                "extract_patterns": [r"\d+万", r"\d+元", r"几十万", r"百万"],
                "round": 1,
            },
            {
                "key": "has_evidence", "label": "凭证情况",
                "question": "有哪些欠款凭证？",
                "options": ["有合同/借条", "有转账记录", "有聊天记录", "只有口头约定", "多种凭证都有"],
                "extract_patterns": [
                    r"合同", r"借条", r"借据", r"欠条", r"转账",
                    r"聊天记录", r"微信", r"口头",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "overdue_period", "label": "逾期时长",
                "question": "已经逾期多长时间了？",
                "options": ["3个月以内", "3-12个月", "1-3年", "超过3年（注意时效）"],
                "extract_patterns": [r"\d+个月", r"\d+年", r"好几年", r"很久"],
                "round": 2,
            },
            {
                "key": "collection_stage", "label": "催收阶段",
                "question": "目前催收到哪个阶段？",
                "options": ["还没催过", "催过没用", "已发律师函", "准备起诉", "已有判决待执行"],
                "extract_patterns": [r"催过", r"律师函", r"起诉", r"判决", r"执行"],
                "round": 2,
            },
            {
                "key": "debtor_status", "label": "对方状况",
                "question": "对方（欠款人）目前的态度和状况？",
                "options": ["失联/找不到人", "承认欠款但不还", "否认欠款", "有还款意愿但无力", "公司已注销/破产"],
                "extract_patterns": [r"失联", r"找不到", r"不承认", r"没钱", r"破产", r"注销"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # 16. 公司治理 (NEW v3)
    # ================================================================
    "CORPORATE_GOVERNANCE": {
        "name": "公司治理",
        "required_slots": [
            {
                "key": "governance_type", "label": "治理问题",
                "question": "具体是什么公司治理问题？",
                "options": ["股东纠纷/僵局", "股权架构设计", "章程/协议修改", "公司设立/变更", "并购重组", "清算注销"],
                "extract_patterns": [
                    r"股东", r"股权", r"章程", r"设立", r"并购",
                    r"重组", r"清算", r"注销", r"增资", r"减资",
                    r"分红", r"表决", r"僵局",
                ],
                "round": 1,
            },
            {
                "key": "company_type", "label": "公司类型",
                "question": "公司是什么类型？",
                "options": ["有限责任公司", "股份有限公司", "合伙企业", "外资企业", "个人独资", "拟设立/筹备中"],
                "extract_patterns": [r"有限", r"股份", r"合伙", r"外资", r"独资"],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "shareholder_count", "label": "股东数量",
                "question": "目前有几位股东？",
                "options": ["2位", "3-5位", "5位以上"],
                "round": 2,
            },
            {
                "key": "role_in_company", "label": "您的角色",
                "question": "您在公司中的角色？",
                "options": ["大股东/控股", "小股东/少数", "管理层/高管", "外部顾问"],
                "extract_patterns": [r"大股东", r"控股", r"小股东", r"管理层", r"顾问"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # 17. 婚姻家庭 (NEW v3)
    # ================================================================
    "FAMILY_LAW": {
        "name": "婚姻家庭",
        "required_slots": [
            {
                "key": "family_issue", "label": "家事类型",
                "question": "涉及什么家庭法律问题？",
                "options": ["离婚/分居", "财产分割", "子女抚养/探视", "遗产继承", "家庭暴力", "其他"],
                "extract_patterns": [
                    r"离婚", r"分居", r"财产分割", r"抚养", r"探视",
                    r"遗产", r"继承", r"遗嘱", r"家暴", r"婚前",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "marriage_status", "label": "婚姻状态",
                "question": "目前的婚姻状态？",
                "options": ["已婚/共同生活中", "分居中", "协商离婚中", "诉讼离婚中", "已离婚有纠纷"],
                "extract_patterns": [r"已婚", r"分居", r"协议", r"诉讼", r"已离"],
                "round": 2,
            },
            {
                "key": "has_children", "label": "子女情况",
                "question": "是否有未成年子女？",
                "options": ["有未成年子女", "子女已成年", "没有子女"],
                "round": 2,
            },
            {
                "key": "property_involved", "label": "财产情况",
                "question": "涉及哪些主要财产？",
                "options": ["房产", "车辆", "存款/投资", "公司股权", "暂不清楚"],
                "extract_patterns": [r"房子", r"房产", r"车", r"存款", r"股权", r"公司"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 1,
        "sub_templates": {
            "divorce": {
                "detect_patterns": [r"离婚", r"分居"],
                "required_slots": [
                    {
                        "key": "divorce_type", "label": "离婚方式",
                        "question": "您倾向哪种离婚方式？",
                        "options": ["协议离婚（双方同意）", "诉讼离婚（一方不同意）", "还在考虑/不确定"],
                        "extract_patterns": [r"协议", r"诉讼", r"不同意", r"同意"],
                        "round": 1,
                    },
                    {
                        "key": "core_concern", "label": "核心关切",
                        "question": "您最关心的问题是什么？",
                        "options": ["子女抚养权", "财产分割", "债务分担", "对方过错/赔偿", "尽快结束婚姻"],
                        "extract_patterns": [r"孩子", r"抚养", r"财产", r"债务", r"出轨", r"过错"],
                        "round": 1,
                    },
                ],
            },
            "inheritance": {
                "detect_patterns": [r"遗产", r"继承", r"遗嘱"],
                "required_slots": [
                    {
                        "key": "inheritance_type", "label": "继承类型",
                        "question": "属于什么继承情形？",
                        "options": ["有遗嘱继承", "无遗嘱（法定继承）", "遗嘱效力有争议", "想提前立遗嘱", "继承人之间有纠纷"],
                        "extract_patterns": [r"遗嘱", r"法定", r"纠纷", r"立遗嘱"],
                        "round": 1,
                    },
                ],
            },
        },
    },

    # ================================================================
    # 18. 房产纠纷 (NEW v3)
    # ================================================================
    "REAL_ESTATE": {
        "name": "房产纠纷",
        "required_slots": [
            {
                "key": "re_type", "label": "房产问题类型",
                "question": "涉及什么房产法律问题？",
                "options": ["房屋买卖纠纷", "租赁纠纷", "物业纠纷", "拆迁/征收", "建设工程", "产权确认"],
                "extract_patterns": [
                    r"买房", r"卖房", r"房屋买卖", r"租房", r"租赁",
                    r"物业", r"拆迁", r"征收", r"工程", r"产权",
                    r"交房", r"逾期", r"质量",
                ],
                "round": 1,
            },
            {
                "key": "role", "label": "您的角色",
                "question": "您是哪方？",
                "options": ["买方/购房者", "卖方/业主", "租客/承租方", "房东/出租方", "开发商", "其他"],
                "extract_patterns": [
                    r"买方", r"购房", r"卖方", r"业主", r"租客",
                    r"房东", r"开发商",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "property_value", "label": "房产价值",
                "question": "房产大致价值？",
                "options": ["100万以下", "100-500万", "500-1000万", "1000万以上", "暂不确定"],
                "extract_patterns": [r"\d+万", r"\d+元"],
                "round": 2,
            },
            {
                "key": "dispute_detail", "label": "纠纷详情",
                "question": "具体争议点是什么？",
                "options": ["拒绝履约/不过户", "房屋质量问题", "逾期交房", "合同解除/退房", "定金/中介费纠纷"],
                "extract_patterns": [r"过户", r"质量", r"逾期", r"交房", r"退房", r"定金", r"中介"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # 19. 刑事相关 (NEW v3)
    # ================================================================
    "CRIMINAL": {
        "name": "刑事相关",
        "required_slots": [
            {
                "key": "criminal_stage", "label": "案件阶段",
                "question": "目前处于什么阶段？",
                "options": ["被传唤/约谈", "被刑事拘留", "已批准逮捕", "审查起诉中", "法院审理中", "已判决/想上诉"],
                "extract_patterns": [
                    r"传唤", r"约谈", r"拘留", r"逮捕", r"起诉",
                    r"审理", r"判决", r"上诉",
                ],
                "round": 1,
            },
            {
                "key": "role", "label": "您的角色",
                "question": "您与案件的关系？",
                "options": ["当事人/嫌疑人本人", "家属/亲友", "被害人", "单位负责人"],
                "extract_patterns": [
                    r"我被", r"家属", r"家人", r"亲属", r"被害",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "charge_type", "label": "涉嫌罪名",
                "question": "涉嫌或被控什么罪名？（如不清楚可选不确定）",
                "options": ["诈骗类", "职务侵占/挪用", "非法经营", "故意伤害", "交通肇事", "不确定"],
                "extract_patterns": [
                    r"诈骗", r"侵占", r"挪用", r"非法经营", r"伤害",
                    r"交通肇事", r"受贿", r"行贿",
                ],
                "round": 2,
            },
            {
                "key": "has_lawyer", "label": "律师情况",
                "question": "是否已经委托辩护律师？",
                "options": ["已有律师", "还没有/急需律师", "想换律师"],
                "extract_patterns": [r"有律师", r"没有律师", r"找律师"],
                "round": 2,
            },
            {
                "key": "bail_status", "label": "取保候审",
                "question": "是否在争取取保候审？",
                "options": ["想申请取保", "已被取保", "被拒绝取保", "不需要/不适用"],
                "extract_patterns": [r"取保", r"候审"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },
}


def get_template(intent: str) -> Optional[Dict[str, Any]]:
    """获取场景模板"""
    return SCENARIO_TEMPLATES.get(intent)


def get_all_intents() -> List[str]:
    """获取所有已注册的意图"""
    return list(SCENARIO_TEMPLATES.keys())


# ========== 有效信息密度评估（替代简单的长度加分） ==========

# 高价值信息 pattern — 用于评估消息中是否包含实质信息
_INFO_DENSITY_PATTERNS = [
    r"\d+万", r"\d+元", r"\d+年",                           # 金额/时间量化
    r"甲方|乙方|买方|卖方|出租|承租",                          # 主体角色
    r"[\u4e00-\u9fa5]{2,}(?:公司|企业|集团)",                  # 公司名
    r"合同|协议|借条|欠条|发票",                               # 法律文件
    r"违约|侵权|拖欠|解除|终止|赔偿|损失",                      # 法律事实
    r"20\d{2}年|去年|今年|上个月|\d+月\d+日",                  # 时间节点
    r"北京|上海|广州|深圳|[\u4e00-\u9fa5]{2,3}(?:市|区|县)",   # 地点
]


def _calc_info_density_bonus(user_input: str) -> float:
    """
    计算有效信息密度加分（替代原来的 len > 100 → +0.1）。
    只有真正包含有价值的法律事实信息时才加分。
    """
    matched_count = 0
    for pattern in _INFO_DENSITY_PATTERNS:
        if re.search(pattern, user_input):
            matched_count += 1

    # 0-1个匹配: 0分; 2个: +0.05; 3个: +0.10; 4+个: +0.15
    if matched_count >= 4:
        return 0.15
    elif matched_count >= 3:
        return 0.10
    elif matched_count >= 2:
        return 0.05
    return 0.0


def assess_completeness(
    user_input: str,
    intent: str,
    has_attachments: bool = False,
    pre_filled_context: Optional[Dict[str, Any]] = None,
    current_round: int = 1,
) -> Dict[str, Any]:
    """
    基于场景模板的信息完整度评估（纯规则，无 LLM 调用，< 1ms）。

    支持置信度门控：够了就停，不过度追问。
    支持多轮渐进追问：通过 current_round 控制只生成当轮的问题。

    Args:
        user_input: 用户输入文本
        intent: 识别到的意图
        has_attachments: 是否有附件
        pre_filled_context: 从用户画像预填的上下文（减少重复追问）
        current_round: 当前追问轮次（1=首轮核心问题，2=细化补充）

    Returns:
        {
            "is_complete": bool,
            "score": float (0-1),
            "filled_slots": [{"key": ..., "label": ..., "value": ...}],
            "missing_slots": [{"key": ..., "label": ...}],
            "questions": [{"question": ..., "options": [...], "purpose": ..., "round": 1|2}],
            "has_next_round": bool,  # 是否还有下一轮问题
        }
    """
    template = SCENARIO_TEMPLATES.get(intent)
    if not template:
        return {
            "is_complete": True, "score": 1.0,
            "filled_slots": [], "missing_slots": [], "questions": [],
            "has_next_round": False,
        }

    required = list(template["required_slots"])
    optional_extra = list(template.get("optional_slots", []))

    # === 子模板动态分支 ===
    sub_templates = template.get("sub_templates", {})
    _matched_sub = None
    if sub_templates:
        for sub_key, sub_def in sub_templates.items():
            for pattern in sub_def.get("detect_patterns", []):
                if re.search(pattern, user_input):
                    _matched_sub = sub_key
                    break
            if _matched_sub:
                break
        if _matched_sub:
            sub = sub_templates[_matched_sub]
            required = sub["required_slots"]
            if "optional_slots" in sub:
                optional_extra = sub["optional_slots"] + optional_extra
            logger.debug(f"子模板匹配: {_matched_sub}, 切换到专用 slots")

    if not required:
        return {
            "is_complete": True, "score": 1.0,
            "filled_slots": [], "missing_slots": [], "questions": [],
            "has_next_round": False,
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
            missing.append({"key": slot_key, "label": slot["label"], "round": slot.get("round", 1)})

    # 附件自动提升完整度
    score_boost = 0.0
    if has_attachments and "has_attachments" in template.get("auto_complete_if", []):
        score_boost = 0.3

    total = len(required)
    base_score = len(filled) / total if total > 0 else 1.0
    score = min(base_score + score_boost, 1.0)

    # 有效信息密度加分（替代原来的消息长度虚加分）
    info_bonus = _calc_info_density_bonus(user_input)
    score = min(score + info_bonus, 1.0)

    # === 苏格拉底式渐进追问：按 round 分层 ===
    # 第1轮只问核心问题（round=1），第2轮补充细化（round=2）
    current_round_questions = []
    next_round_questions = []

    # 从 missing required slots 中按 round 筛选
    for slot_info in missing:
        slot_key = slot_info["key"]
        slot_round = slot_info.get("round", 1)
        slot_def = next((s for s in required if s["key"] == slot_key), None)
        if not slot_def:
            continue

        q: Dict[str, Any] = {
            "question": slot_def["question"],
            "purpose": slot_def["label"],
            "round": slot_round,
        }
        if "options" in slot_def:
            q["options"] = slot_def["options"]

        if slot_round <= current_round:
            current_round_questions.append(q)
        else:
            next_round_questions.append(q)

    # 当前轮最多 3 个问题
    questions = current_round_questions[:3]

    # 如果当前轮问题不足 3 个，从 optional 补充（也按 round 过滤）
    if len(questions) < 3 and optional_extra:
        for opt_slot in optional_extra:
            if len(questions) >= 3:
                break
            opt_key = opt_slot["key"]
            opt_round = opt_slot.get("round", 2)
            if opt_round > current_round:
                next_round_questions.append({
                    "question": opt_slot["question"],
                    "purpose": opt_slot["label"],
                    "round": opt_round,
                    "optional": True,
                })
                continue
            if any(f["key"] == opt_key for f in filled):
                continue
            if opt_key in pre_filled and pre_filled[opt_key]:
                continue
            q = {
                "question": opt_slot["question"],
                "purpose": opt_slot["label"],
                "optional": True,
                "round": opt_round,
            }
            if "options" in opt_slot:
                q["options"] = opt_slot["options"]
            questions.append(q)

    min_required = template.get("min_required_for_proceed", 1)
    is_complete = len(filled) >= min_required or score >= 0.7

    return {
        "is_complete": is_complete,
        "score": round(score, 2),
        "filled_slots": filled,
        "missing_slots": [{"key": s["key"], "label": s["label"]} for s in missing],
        "questions": questions,
        "has_next_round": len(next_round_questions) > 0,
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
        "is_complete": score >= 0.5,
        "score": round(score, 2),
        "filled_slots": filled,
        "missing_slots": remaining_missing,
        "questions": [],
        "has_next_round": False,
    }


def build_context_summary(filled_slots: List[Dict[str, Any]]) -> str:
    """
    将已填充的 slots 构建为上下文摘要，注入到 Agent prompt 中。
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


def get_template_context_for_llm(intent: str, user_input: str) -> str:
    """
    为 LLM 合并分析注入场景模板上下文（Fix 7）。

    当关键词未命中需要 LLM 分析时，将匹配的模板 slot 信息注入到 prompt 中，
    约束 LLM 生成的 guidance_questions 与模板一致。

    Returns:
        模板上下文提示文本（可直接拼接到 LLM prompt 中）
    """
    template = SCENARIO_TEMPLATES.get(intent)
    if not template:
        return ""

    required = list(template.get("required_slots", []))
    optional = list(template.get("optional_slots", []))

    # 检查子模板
    sub_templates = template.get("sub_templates", {})
    matched_sub = None
    if sub_templates:
        for sub_key, sub_def in sub_templates.items():
            for pattern in sub_def.get("detect_patterns", []):
                if re.search(pattern, user_input):
                    matched_sub = sub_key
                    break
            if matched_sub:
                break
        if matched_sub:
            sub = sub_templates[matched_sub]
            required = sub["required_slots"]
            if "optional_slots" in sub:
                optional = sub["optional_slots"]

    lines = [f"\n### 场景模板参考（{template['name']}）"]
    lines.append("请优先围绕以下信息维度生成 guidance_questions：")

    for i, slot in enumerate(required, 1):
        opts = "、".join(slot.get("options", [])) if "options" in slot else "开放式"
        lines.append(f"  {i}. {slot['label']}: {slot['question']}（选项: {opts}）")

    if optional:
        lines.append("可选补充：")
        for slot in optional[:3]:
            opts = "、".join(slot.get("options", [])) if "options" in slot else "开放式"
            lines.append(f"  - {slot['label']}: {slot['question']}（选项: {opts}）")

    return "\n".join(lines)
