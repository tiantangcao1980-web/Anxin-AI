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


# ========== Harness: 分级完整性门槛 ==========
# 按场景风险分级，高风险场景（正式法律文件/刑事）要求更高完整度才允许生成
COMPLETENESS_THRESHOLDS = {
    # 高风险：生成正式法律文件/涉及人身自由/破产
    "DOCUMENT_DRAFTING":      {"min_score": 0.75, "min_filled_ratio": 0.80},
    "CRIMINAL":               {"min_score": 0.80, "min_filled_ratio": 0.90},
    "LITIGATION_STRATEGY":    {"min_score": 0.70, "min_filled_ratio": 0.70},
    "BANKRUPTCY_INSOLVENCY":  {"min_score": 0.75, "min_filled_ratio": 0.80},
    # 中风险：分析/纠纷处理
    "CONTRACT_REVIEW":        {"min_score": 0.65, "min_filled_ratio": 0.60},
    "LABOR_HR":               {"min_score": 0.65, "min_filled_ratio": 0.60},
    "DEBT_COLLECTION":        {"min_score": 0.65, "min_filled_ratio": 0.60},
    "FAMILY_LAW":             {"min_score": 0.65, "min_filled_ratio": 0.60},
    "DUE_DILIGENCE":          {"min_score": 0.70, "min_filled_ratio": 0.70},
    "EVIDENCE_PROCESSING":    {"min_score": 0.65, "min_filled_ratio": 0.60},
    "REAL_ESTATE":            {"min_score": 0.65, "min_filled_ratio": 0.60},
    "CORPORATE_GOVERNANCE":   {"min_score": 0.65, "min_filled_ratio": 0.60},
    "IP_PROTECTION":          {"min_score": 0.60, "min_filled_ratio": 0.50},
    "TAX_FINANCE":            {"min_score": 0.60, "min_filled_ratio": 0.50},
    # 低风险：咨询/导航
    "QA_CONSULTATION":        {"min_score": 0.35, "min_filled_ratio": 0.00},
    "FIND_LAWYER":            {"min_score": 0.40, "min_filled_ratio": 0.30},
    "TEMPLATE_REQUEST":       {"min_score": 0.20, "min_filled_ratio": 0.00},
    # 计算器类（需要精确参数，宁可多问一轮）
    "LEGAL_CALCULATION":      {"min_score": 0.70, "min_filled_ratio": 0.60},
    # P0 新增场景
    "CONSUMER_PROTECTION":    {"min_score": 0.60, "min_filled_ratio": 0.50},
    "TRAFFIC_ACCIDENT":       {"min_score": 0.65, "min_filled_ratio": 0.60},
    "INSURANCE_CLAIM":        {"min_score": 0.60, "min_filled_ratio": 0.50},
    "SOCIAL_INSURANCE":       {"min_score": 0.55, "min_filled_ratio": 0.40},
    "PROPERTY_MANAGEMENT":    {"min_score": 0.60, "min_filled_ratio": 0.50},
    # 默认（未列出的场景）
    "_default":               {"min_score": 0.60, "min_filled_ratio": 0.50},
}


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
        # V2 修复：上传了参考文档（模板/旧合同）时跳过类型追问
        "auto_complete_if": ["has_attachments"],
        "min_required_for_proceed": 2,
        "sub_templates": {
            "contract": {
                "detect_patterns": [r"合同", r"协议"],
                "required_slots": [
                    {
                        "key": "contract_sub_type", "label": "合同类型",
                        "question": "这是什么类型的合同/协议？",
                        "options": ["买卖/销售合同", "服务合同", "租赁合同", "合作协议", "保密协议（NDA）", "劳动/劳务合同", "其他（请说明）"],
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
                        "question": "合同双方分别是？（可用化名，如：甲方A公司，乙方B公司）",
                        "extract_patterns": [
                            r"甲方", r"乙方", r"公司", r"对方", r"我方",
                            r"买方", r"卖方", r"出租", r"承租",
                        ],
                        "round": 1,
                    },
                    {
                        "key": "contract_subject", "label": "合同标的",
                        "question": "合同涉及的具体标的是什么？（如：商品名称、服务内容）",
                        "extract_patterns": [
                            # 金额标识
                            r"\d+万", r"\d+元", r"金额", r"标的", r"单价", r"总价",
                            # 数量标识（隐含有具体物品）
                            r"\d+台", r"\d+件", r"\d+套", r"\d+吨", r"\d+个", r"\d+份",
                            # 具体品类
                            r"货物", r"商品", r"产品", r"设备", r"材料", r"物料", r"原料",
                            r"电脑", r"笔记本", r"手机", r"服务器", r"家具", r"车辆",
                            r"软件", r"系统", r"配件", r"耗材", r"仪器", r"工具",
                            # 服务类
                            r"服务", r"咨询", r"培训", r"设计", r"开发", r"维护", r"安装",
                            # 房产类
                            r"房屋", r"场地", r"土地", r"写字楼", r"厂房", r"仓库",
                            # 型号/品牌识别（通用）— 连续英文字母+数字（如 ROG5090, iPhone15）
                            r"[A-Za-z]{2,}\d+", r"\d+系列",
                        ],
                        "round": 1,
                    },
                ],
                "optional_slots": [
                    # === Round 2: 交易核心条款（影响合同质量的关键信息）===
                    {
                        "key": "goods_detail", "label": "商品/服务明细",
                        "question": "请补充商品或服务的具体信息（数量、规格、型号、质量标准等）",
                        "extract_patterns": [r"\d+台", r"\d+件", r"\d+吨", r"\d+套", r"规格", r"型号", r"标准"],
                        "round": 2,
                    },
                    {
                        "key": "total_amount", "label": "合同金额",
                        "question": "合同总金额是多少？",
                        "options": ["1万以内", "1-10万", "10-100万", "100万以上", "按实际结算", "其他（请说明）"],
                        "extract_patterns": [r"\d+万", r"\d+元", r"金额", r"总价"],
                        "round": 2,
                    },
                    {
                        "key": "payment_terms", "label": "付款方式",
                        "question": "付款方式和时间安排？",
                        "options": ["一次性付清", "分期付款（预付+尾款）", "货到付款", "月结/季结", "按进度付款", "其他（请说明）"],
                        "extract_patterns": [r"付款", r"支付", r"预付", r"尾款", r"月结", r"分期"],
                        "round": 2,
                    },
                    {
                        "key": "delivery_terms", "label": "交付/交货",
                        "question": "交付时间和地点？",
                        "extract_patterns": [r"交付", r"交货", r"发货", r"配送", r"\d+天", r"\d+日"],
                        "round": 2,
                    },
                    # === Round 3: 风险控制条款（专业合同必备）===
                    {
                        "key": "quality_standard", "label": "质量标准",
                        "question": "商品/服务的验收标准是什么？",
                        "options": ["国家标准", "行业标准", "双方约定标准", "样品标准", "其他（请说明）"],
                        "extract_patterns": [r"标准", r"验收", r"质量", r"检验", r"合格"],
                        "round": 3,
                    },
                    {
                        "key": "warranty_period", "label": "质保期",
                        "question": "质保期多长？",
                        "options": ["无质保", "3个月", "6个月", "1年", "2年", "其他（请说明）"],
                        "extract_patterns": [r"质保", r"保修", r"保质", r"\d+月", r"\d+年"],
                        "round": 3,
                    },
                    {
                        "key": "dispute_resolution", "label": "争议解决",
                        "question": "发生争议时如何解决？",
                        "options": ["协商解决", "提交仲裁委员会仲裁", "向甲方所在地法院起诉", "向乙方所在地法院起诉", "向合同签订地法院起诉", "其他（请说明）"],
                        "extract_patterns": [r"仲裁", r"法院", r"管辖", r"诉讼", r"协商"],
                        "round": 3,
                    },
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
                        "options": ["违约责任", "知识产权归属", "保密条款", "竞业限制", "争议解决方式", "暂时没有", "其他（请说明）"],
                        "extract_patterns": [
                            r"违约", r"知识产权", r"保密", r"竞业", r"仲裁", r"管辖",
                        ],
                        "round": 3,
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
                    r"债务", r"借贷", r"房产", r"婚姻", r"租赁",
                    r"纠纷", r"争议", r"买卖", r"交通", r"医疗",
                ],
                "round": 1,
            },
            {
                "key": "party_role", "label": "当事人角色",
                "question": "您是原告还是被告？",
                "options": ["原告（起诉方）", "被告（被诉方）", "还未确定/考虑中"],
                "extract_patterns": [
                    r"我要起诉", r"我想起诉", r"想告", r"想起诉", r"原告",
                    r"被起诉", r"被告", r"被诉", r"收到传票",
                    r"我是租客", r"我是买方", r"我是卖方", r"我是业主",
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
            # === Round 2: 核心信息 ===
            {
                "key": "dispute_amount", "label": "争议金额",
                "question": "涉及的争议金额大约多少？",
                "options": ["10万以下", "10-50万", "50-500万", "500万以上", "非金钱纠纷", "其他（请说明）"],
                "extract_patterns": [r"\d+万", r"\d+元", r"金额", r"标的", r"赔偿"],
                "round": 2,
            },
            {
                "key": "client_goal", "label": "期望结果",
                "question": "您最希望达到什么结果？",
                "options": ["全额赔偿/返还", "协商和解（接受部分赔偿）", "维护权益（不一定要钱）", "保住合作关系", "获得道歉/纠正", "其他（请说明）"],
                "extract_patterns": [r"赔偿", r"和解", r"调解", r"道歉", r"关系"],
                "round": 2,
            },
            {
                "key": "evidence_status", "label": "证据情况",
                "question": "目前掌握哪些关键证据？",
                "options": ["有书面合同", "有转账/付款记录", "有微信/邮件沟通记录", "有录音/录像", "有第三方证人", "证据较少/不确定", "其他（请说明）"],
                "extract_patterns": [r"合同", r"转账", r"微信", r"录音", r"证人", r"证据"],
                "round": 2,
            },
            {
                "key": "timeline", "label": "时间压力",
                "question": "是否有诉讼时效或期限压力？",
                "options": ["紧急（即将到期）", "有时间", "不确定"],
                "extract_patterns": [r"快到期", r"时效", r"期限", r"快过了"],
                "round": 2,
            },
            # === Round 3: 策略相关 ===
            {
                "key": "prior_communication", "label": "前期沟通",
                "question": "之前是否已与对方沟通过？",
                "options": ["从未沟通", "口头协商过但无果", "已发律师函/催告", "对方完全不回应", "其他（请说明）"],
                "extract_patterns": [r"协商", r"沟通", r"律师函", r"催过", r"不理"],
                "round": 3,
            },
            {
                "key": "opponent_status", "label": "对方情况",
                "question": "对方目前是什么态度/状况？",
                "options": ["正常经营/有偿还能力", "经营困难/可能无力赔偿", "失联/找不到人", "态度强硬/拒绝沟通", "不确定", "其他（请说明）"],
                "extract_patterns": [r"找不到", r"失联", r"困难", r"破产", r"强硬"],
                "round": 3,
            },
            {
                "key": "urgent_measures", "label": "紧急措施",
                "question": "是否需要紧急保全措施？",
                "options": ["需要财产保全（冻结对方账户/资产）", "需要证据保全（防止对方销毁证据）", "需要行为保全（禁令）", "暂不需要", "不确定"],
                "extract_patterns": [r"保全", r"冻结", r"查封", r"禁令", r"紧急"],
                "round": 3,
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

    # ================================================================
    # === 企业经营管理专项场景 (v3.1 — 12 个新增) ===
    # ================================================================

    # ================================================================
    # 20. 融资投资 (企业核心)
    # ================================================================
    "INVESTMENT_FINANCING": {
        "name": "融资投资",
        "required_slots": [
            {
                "key": "financing_type", "label": "融资类型",
                "question": "属于什么类型的融资/投资？",
                "options": ["股权融资（A/B/C轮）", "债权融资（贷款/债券）", "可转债/SAFE", "股权转让", "上市/IPO", "基金投资"],
                "extract_patterns": [
                    r"股权融资", r"[A-Fa-f]轮", r"天使", r"种子",
                    r"贷款", r"债券", r"债权", r"借款",
                    r"可转债", r"SAFE", r"safe",
                    r"股权转让", r"股转",
                    r"上市", r"IPO", r"ipo",
                    r"基金", r"LP", r"GP",
                ],
                "round": 1,
            },
            {
                "key": "role", "label": "您的角色",
                "question": "您是融资方还是投资方？",
                "options": ["融资方/创业公司", "投资方/基金", "财务顾问/FA", "律师/法务"],
                "extract_patterns": [
                    r"融资", r"创业", r"投资方", r"基金", r"FA",
                    r"顾问", r"法务",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "amount", "label": "融资规模",
                "question": "目标融资/投资金额大约多少？",
                "options": ["500万以下", "500万-5000万", "5000万-5亿", "5亿以上", "暂不确定"],
                "extract_patterns": [r"\d+万", r"\d+亿", r"金额"],
                "round": 2,
            },
            {
                "key": "stage", "label": "项目阶段",
                "question": "目前融资到什么阶段？",
                "options": ["前期接洽/意向", "Term Sheet谈判", "尽调中", "交割/签约", "投后管理"],
                "extract_patterns": [r"意向", r"[Tt]erm", r"尽调", r"签约", r"交割"],
                "round": 2,
            },
            {
                "key": "focus", "label": "关注重点",
                "question": "重点关注哪些条款？",
                "options": ["估值与对价", "对赌/业绩承诺", "反稀释保护", "退出机制", "治理权/董事会", "优先清算权"],
                "extract_patterns": [r"估值", r"对赌", r"稀释", r"退出", r"董事", r"清算"],
                "round": 2,
            },
        ],
        "auto_complete_if": ["has_attachments"],
        "min_required_for_proceed": 2,
        "sub_templates": {
            "equity_financing": {
                "detect_patterns": [r"股权融资", r"[A-Fa-f]轮", r"天使", r"种子", r"融资"],
                "required_slots": [
                    {
                        "key": "round_stage", "label": "融资轮次",
                        "question": "当前是第几轮融资？",
                        "options": ["天使/种子轮", "Pre-A / A轮", "B轮", "C轮及以后", "Pre-IPO"],
                        "extract_patterns": [r"天使", r"种子", r"[Aa]轮", r"[Bb]轮", r"[Cc]轮", r"IPO"],
                        "round": 1,
                    },
                    {
                        "key": "need_type", "label": "具体需求",
                        "question": "需要什么帮助？",
                        "options": ["Term Sheet审查", "投资协议起草/审查", "股东协议设计", "交割文件准备", "估值分析建议"],
                        "extract_patterns": [r"[Tt]erm", r"投资协议", r"股东协议", r"交割", r"估值"],
                        "round": 1,
                    },
                ],
            },
        },
    },

    # ================================================================
    # 21. 并购重组
    # ================================================================
    "MA_RESTRUCTURING": {
        "name": "并购重组",
        "required_slots": [
            {
                "key": "ma_type", "label": "交易类型",
                "question": "属于什么类型的并购/重组？",
                "options": ["收购/兼并", "合并", "资产剥离/出售", "公司分立", "业务重组", "管理层收购（MBO）"],
                "extract_patterns": [
                    r"收购", r"兼并", r"合并", r"剥离", r"出售",
                    r"分立", r"重组", r"MBO", r"mbo",
                ],
                "round": 1,
            },
            {
                "key": "role", "label": "您的角色",
                "question": "您是收购方还是被收购方？",
                "options": ["收购方/买方", "被收购方/卖方/目标公司", "财务顾问", "法律顾问"],
                "extract_patterns": [
                    r"收购方", r"买方", r"被收购", r"卖方", r"目标公司",
                    r"顾问",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "deal_structure", "label": "交易结构",
                "question": "倾向什么交易结构？",
                "options": ["股权收购", "资产收购", "增资扩股", "换股合并", "还未确定"],
                "extract_patterns": [r"股权收购", r"资产收购", r"增资", r"换股"],
                "round": 2,
            },
            {
                "key": "deal_value", "label": "交易规模",
                "question": "预估交易金额？",
                "options": ["1000万以下", "1000万-1亿", "1-10亿", "10亿以上", "暂不确定"],
                "extract_patterns": [r"\d+万", r"\d+亿"],
                "round": 2,
            },
            {
                "key": "stage", "label": "项目阶段",
                "question": "并购项目到什么阶段了？",
                "options": ["前期论证/可行性", "意向接洽/LOI", "尽职调查", "协议谈判", "审批/交割"],
                "extract_patterns": [r"论证", r"意向", r"LOI", r"尽调", r"谈判", r"审批", r"交割"],
                "round": 2,
            },
            {
                "key": "regulatory", "label": "审批要求",
                "question": "是否涉及监管审批？",
                "options": ["需要反垄断申报", "需要外资审批", "需要国资审批", "无特殊审批", "不确定"],
                "extract_patterns": [r"反垄断", r"外资", r"国资", r"审批"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # 22. 跨境涉外
    # ================================================================
    "CROSS_BORDER": {
        "name": "跨境涉外",
        "required_slots": [
            {
                "key": "cross_type", "label": "涉外类型",
                "question": "涉及什么类型的跨境业务？",
                "options": ["国际贸易（进出口）", "外商投资/FDI", "对外投资/ODI", "跨境服务/技术", "跨境争议/仲裁", "其他"],
                "extract_patterns": [
                    r"进口", r"出口", r"贸易", r"外商", r"FDI", r"fdi",
                    r"对外投资", r"ODI", r"odi", r"跨境服务",
                    r"国际仲裁", r"跨境争议",
                ],
                "round": 1,
            },
            {
                "key": "jurisdictions", "label": "涉及国家/地区",
                "question": "涉及哪些国家或地区？",
                "options": ["美国", "欧盟/欧洲", "东南亚", "日韩", "中东/非洲", "其他"],
                "extract_patterns": [
                    r"美国", r"欧洲", r"欧盟", r"东南亚", r"日本", r"韩国",
                    r"香港", r"新加坡", r"英国", r"德国",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "compliance_focus", "label": "合规关注",
                "question": "重点关注哪些合规要求？",
                "options": ["出口管制/制裁", "外汇管制", "数据跨境传输", "反腐败(FCPA)", "关税/贸易壁垒", "暂不确定"],
                "extract_patterns": [
                    r"出口管制", r"制裁", r"外汇", r"数据跨境", r"FCPA",
                    r"关税", r"贸易壁垒",
                ],
                "round": 2,
            },
            {
                "key": "contract_law", "label": "适用法律",
                "question": "合同约定适用哪国法律？",
                "options": ["中国法", "美国法/英美法", "香港法", "新加坡法", "尚未确定"],
                "extract_patterns": [r"中国法", r"美国法", r"英美法", r"香港法"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # 23. 数据合规/网络安全
    # ================================================================
    "DATA_COMPLIANCE": {
        "name": "数据合规",
        "required_slots": [
            {
                "key": "data_issue", "label": "数据问题",
                "question": "具体是什么数据合规问题？",
                "options": ["个人信息保护合规", "数据跨境传输", "数据泄露应急", "隐私政策审查", "数据处理协议(DPA)", "网络安全等保"],
                "extract_patterns": [
                    r"个人信息", r"个保", r"PIPL", r"pipl",
                    r"跨境", r"数据出境",
                    r"泄露", r"泄漏", r"应急",
                    r"隐私政策", r"隐私协议",
                    r"DPA", r"dpa", r"数据处理",
                    r"等保", r"网络安全", r"等级保护",
                ],
                "round": 1,
            },
            {
                "key": "data_type", "label": "数据类型",
                "question": "涉及什么类型的数据？",
                "options": ["个人信息/用户数据", "敏感个人信息", "企业商业数据", "政府/公共数据", "医疗健康数据", "金融数据"],
                "extract_patterns": [
                    r"个人信息", r"用户数据", r"敏感", r"商业数据",
                    r"医疗", r"健康", r"金融",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "regulation", "label": "适用法规",
                "question": "需要满足哪些法规要求？",
                "options": ["个保法(PIPL)", "GDPR", "网络安全法", "数据安全法", "行业特定规定", "不确定"],
                "extract_patterns": [r"个保法", r"PIPL", r"GDPR", r"gdpr", r"网络安全法", r"数据安全法"],
                "round": 2,
            },
            {
                "key": "urgency", "label": "紧急程度",
                "question": "是否有紧急情况？",
                "options": ["数据泄露事件处理（紧急）", "监管检查/约谈", "合规建设（常规）", "合同签约前评估"],
                "extract_patterns": [r"泄露", r"检查", r"约谈", r"紧急"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # 24. 反不正当竞争
    # ================================================================
    "ANTI_UNFAIR_COMPETITION": {
        "name": "反不正当竞争",
        "required_slots": [
            {
                "key": "competition_type", "label": "竞争问题",
                "question": "涉及什么不正当竞争问题？",
                "options": ["商业秘密侵犯", "员工跳槽带走客户/技术", "仿冒/混淆", "虚假宣传", "商业诋毁", "不正当手段获取商业机会"],
                "extract_patterns": [
                    r"商业秘密", r"跳槽", r"带走客户", r"仿冒", r"混淆",
                    r"虚假宣传", r"诋毁", r"窃取", r"泄密",
                ],
                "round": 1,
            },
            {
                "key": "role", "label": "您的角色",
                "question": "您是维权方还是被指控方？",
                "options": ["维权方（权益被侵犯）", "被指控方（被指控不正当竞争）", "预防性咨询"],
                "extract_patterns": [r"维权", r"被侵", r"被指控", r"预防"],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "measures_taken", "label": "已采取措施",
                "question": "此前是否已采取保护措施？",
                "options": ["有竞业限制协议", "有保密协议", "有商业秘密管理制度", "都没有"],
                "extract_patterns": [r"竞业", r"保密协议", r"管理制度"],
                "round": 2,
            },
            {
                "key": "loss_estimate", "label": "损失评估",
                "question": "预估造成的损失规模？",
                "options": ["50万以下", "50-500万", "500万以上", "难以量化"],
                "extract_patterns": [r"\d+万", r"损失"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # 25. 特许经营/经销
    # ================================================================
    "FRANCHISE_DISTRIBUTION": {
        "name": "特许经营与经销",
        "required_slots": [
            {
                "key": "business_type", "label": "业务类型",
                "question": "涉及什么类型的商业合作？",
                "options": ["特许经营/加盟", "代理经销", "品牌授权", "区域独家", "供应链合作"],
                "extract_patterns": [
                    r"特许", r"加盟", r"代理", r"经销", r"分销",
                    r"品牌授权", r"独家", r"供应链",
                ],
                "round": 1,
            },
            {
                "key": "role", "label": "您的角色",
                "question": "您是品牌方/授权方还是加盟方/经销商？",
                "options": ["品牌方/特许人/厂家", "加盟方/被特许人/经销商", "第三方咨询"],
                "extract_patterns": [r"品牌方", r"厂家", r"加盟方", r"经销商"],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "need_type", "label": "具体需求",
                "question": "需要什么帮助？",
                "options": ["合同起草/审查", "合规备案（商业特许经营）", "终止/解除纠纷", "区域保护/窜货问题", "费用/返利纠纷"],
                "extract_patterns": [r"合同", r"备案", r"终止", r"解除", r"窜货", r"返利"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # 26. 建设工程
    # ================================================================
    "CONSTRUCTION_ENGINEERING": {
        "name": "建设工程",
        "required_slots": [
            {
                "key": "project_issue", "label": "工程问题",
                "question": "涉及什么建设工程问题？",
                "options": ["工程合同纠纷", "工程款结算/拖欠", "质量/安全问题", "工期延误", "招投标问题", "分包/转包纠纷"],
                "extract_patterns": [
                    r"工程合同", r"工程款", r"结算", r"质量",
                    r"安全", r"工期", r"延误", r"招投标",
                    r"分包", r"转包", r"挂靠",
                ],
                "round": 1,
            },
            {
                "key": "role", "label": "您的角色",
                "question": "您是哪方？",
                "options": ["建设单位/发包方/业主", "施工单位/承包方", "分包方/实际施工人", "监理/设计方", "其他"],
                "extract_patterns": [
                    r"发包", r"业主", r"甲方", r"施工", r"承包",
                    r"分包", r"监理", r"设计",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "project_value", "label": "工程金额",
                "question": "工程涉及的金额？",
                "options": ["500万以下", "500万-5000万", "5000万-5亿", "5亿以上"],
                "extract_patterns": [r"\d+万", r"\d+亿"],
                "round": 2,
            },
            {
                "key": "project_stage", "label": "工程阶段",
                "question": "项目处于什么阶段？",
                "options": ["招投标阶段", "施工中", "竣工验收", "质保期", "已完工有争议"],
                "extract_patterns": [r"招标", r"施工", r"竣工", r"验收", r"质保"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # 27. 政府采购/PPP
    # ================================================================
    "GOVERNMENT_CONTRACTS": {
        "name": "政府采购与PPP",
        "required_slots": [
            {
                "key": "gov_type", "label": "项目类型",
                "question": "涉及什么类型的政府项目？",
                "options": ["政府采购/招标", "PPP项目", "政府补贴/扶持资金", "行政许可/资质", "政府合同纠纷"],
                "extract_patterns": [
                    r"政府采购", r"招标", r"投标", r"PPP", r"ppp",
                    r"补贴", r"扶持", r"资质", r"许可",
                ],
                "round": 1,
            },
            {
                "key": "role", "label": "您的角色",
                "question": "您是供应商还是政府方？",
                "options": ["供应商/投标方", "政府/采购方", "咨询方/代理机构"],
                "extract_patterns": [r"供应商", r"投标", r"政府", r"采购方"],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "need_type", "label": "具体需求",
                "question": "需要什么帮助？",
                "options": ["投标文件审查", "中标后合同谈判", "质疑/投诉", "履约纠纷", "合规风险评估"],
                "extract_patterns": [r"投标", r"中标", r"质疑", r"投诉", r"履约"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # 28. 破产清算
    # ================================================================
    "BANKRUPTCY_INSOLVENCY": {
        "name": "破产与清算",
        "required_slots": [
            {
                "key": "bankruptcy_type", "label": "程序类型",
                "question": "涉及什么类型的破产/清算？",
                "options": ["破产清算", "破产重整", "破产和解", "公司解散清算", "债务重组（非破产）"],
                "extract_patterns": [
                    r"破产清算", r"清算", r"破产重整", r"重整",
                    r"和解", r"解散", r"债务重组",
                ],
                "round": 1,
            },
            {
                "key": "role", "label": "您的角色",
                "question": "您的身份是？",
                "options": ["债务人/企业方", "债权人", "股东", "管理人/清算组", "员工"],
                "extract_patterns": [
                    r"债务人", r"企业", r"债权人", r"股东",
                    r"管理人", r"清算组", r"员工",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "stage", "label": "程序阶段",
                "question": "目前到什么阶段了？",
                "options": ["考虑是否申请破产", "已申请/受理中", "债权申报阶段", "资产处置阶段", "分配/终结"],
                "extract_patterns": [r"申请", r"受理", r"债权申报", r"资产处置", r"分配"],
                "round": 2,
            },
            {
                "key": "debt_scale", "label": "债务规模",
                "question": "负债规模大约多少？",
                "options": ["500万以下", "500万-5000万", "5000万-5亿", "5亿以上"],
                "extract_patterns": [r"\d+万", r"\d+亿"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # 29. 环保合规
    # ================================================================
    "ENVIRONMENTAL_COMPLIANCE": {
        "name": "环保合规",
        "required_slots": [
            {
                "key": "env_issue", "label": "环保问题",
                "question": "涉及什么环保法律问题？",
                "options": ["环评审批", "排污许可", "环境处罚/罚款", "环境污染纠纷", "碳排放/碳交易", "土壤/水污染修复"],
                "extract_patterns": [
                    r"环评", r"排污", r"环保处罚", r"罚款",
                    r"环境污染", r"碳排放", r"碳交易",
                    r"土壤", r"水污染", r"修复",
                ],
                "round": 1,
            },
            {
                "key": "industry", "label": "所属行业",
                "question": "企业所属行业？",
                "options": ["制造业/化工", "建筑/房地产", "能源/矿业", "农业/畜牧", "互联网/科技", "其他"],
                "extract_patterns": [r"制造", r"化工", r"建筑", r"能源", r"矿", r"农业"],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "urgency", "label": "紧急程度",
                "question": "是否有紧急情况？",
                "options": ["被环保部门查处（紧急）", "收到整改通知", "合规建设（常规）", "项目开工前评估"],
                "extract_patterns": [r"查处", r"整改", r"通知", r"开工"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # 30. 反商业贿赂/反腐败
    # ================================================================
    "ANTI_CORRUPTION": {
        "name": "反商业贿赂",
        "required_slots": [
            {
                "key": "corruption_type", "label": "问题类型",
                "question": "涉及什么反腐败/反贿赂问题？",
                "options": ["合规体系建设", "内部调查/举报处理", "政府调查应对", "商业贿赂风险评估", "第三方（代理/中间人）合规", "FCPA/英国反贿赂法"],
                "extract_patterns": [
                    r"合规", r"内部调查", r"举报", r"反贿赂",
                    r"FCPA", r"fcpa", r"代理", r"中间人", r"回扣",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "scope", "label": "涉及范围",
                "question": "涉及哪些业务环节？",
                "options": ["销售/市场推广", "采购/供应链", "政府关系/公关", "招投标", "跨境业务"],
                "extract_patterns": [r"销售", r"采购", r"政府", r"招投标", r"跨境"],
                "round": 2,
            },
            {
                "key": "urgency", "label": "紧急程度",
                "question": "是否涉及紧急事件？",
                "options": ["已被调查（紧急）", "收到举报待处理", "常规合规建设", "预防性评估"],
                "extract_patterns": [r"调查", r"举报", r"紧急"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 1,
    },

    # ================================================================
    # 31. 产品责任/消费者权益
    # ================================================================
    "PRODUCT_LIABILITY": {
        "name": "产品责任与消费者权益",
        "required_slots": [
            {
                "key": "liability_type", "label": "问题类型",
                "question": "涉及什么产品/消费者问题？",
                "options": ["产品质量缺陷", "产品召回", "消费者投诉/维权", "虚假广告/标签", "食品安全", "产品责任诉讼"],
                "extract_patterns": [
                    r"产品质量", r"缺陷", r"召回", r"消费者",
                    r"投诉", r"维权", r"虚假广告", r"标签",
                    r"食品安全", r"产品责任",
                ],
                "round": 1,
            },
            {
                "key": "role", "label": "您的角色",
                "question": "您是生产/销售方还是消费者？",
                "options": ["生产商/制造商", "销售商/平台", "消费者/受害方", "保险公司"],
                "extract_patterns": [r"生产", r"制造", r"销售", r"平台", r"消费者", r"保险"],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "damage_type", "label": "损害类型",
                "question": "造成了什么损害？",
                "options": ["人身伤害", "财产损失", "精神损害", "尚未造成损害（预防）"],
                "extract_patterns": [r"受伤", r"伤害", r"损失", r"精神"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # 法律计算
    # ================================================================
    "LEGAL_CALCULATION": {
        "name": "法律计算",
        "required_slots": [
            {
                "key": "calc_type", "label": "计算类型",
                "question": "您需要计算什么？",
                "options": ["经济补偿金(N/N+1/2N)", "诉讼费", "诉讼时效", "加班费", "工伤赔偿"],
                "extract_patterns": [
                    r"补偿金", r"赔偿金", r"N\+1", r"2N", r"经济补偿",
                    r"诉讼费", r"起诉费", r"受理费",
                    r"时效", r"过期",
                    r"加班费", r"加班",
                    r"工伤", r"伤残",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "monthly_salary", "label": "月工资",
                "question": "月工资（税前）是多少？",
                "extract_patterns": [r"\d+(?:元|块)", r"月薪?\d+", r"工资\d+", r"\d+/月"],
                "round": 1,
            },
            {
                "key": "work_years", "label": "工作年限",
                "question": "在该单位工作了多长时间？",
                "extract_patterns": [r"\d+年", r"干了\d+", r"工作\d+"],
                "round": 1,
            },
            {
                "key": "amount", "label": "标的额/金额",
                "question": "涉及的金额大约是多少？",
                "extract_patterns": [r"\d+万", r"\d+元", r"标的\d+"],
                "round": 1,
            },
            {
                "key": "city", "label": "所在城市",
                "question": "在哪个城市？（影响社平工资和最低工资标准）",
                "extract_patterns": [
                    r"北京|上海|深圳|广州|杭州|南京|苏州|成都|武汉|重庆|天津|西安",
                    r"长沙|郑州|青岛|大连|厦门|福州|合肥|济南|沈阳|哈尔滨",
                ],
                "round": 2,
            },
            {
                "key": "termination_type", "label": "解除类型",
                "question": "是什么情况下的解除/辞退？",
                "options": ["协商解除(N)", "无过失辞退未提前通知(N+1)", "违法辞退(2N)"],
                "extract_patterns": [r"协商", r"无过失", r"违法辞退", r"非法辞退", r"强行辞退"],
                "round": 1,
            },
            {
                "key": "trigger_date", "label": "时效起算日期",
                "question": "权利受到侵害（或知道受侵害）是什么时候？",
                "extract_patterns": [r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}", r"去年", r"今年", r"前年"],
                "round": 1,
            },
            {
                "key": "disability_level", "label": "伤残等级",
                "question": "伤残鉴定的等级是几级？(1-10级)",
                "extract_patterns": [r"\d+级", r"一级|二级|三级|四级|五级|六级|七级|八级|九级|十级"],
                "round": 1,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 1,
        "sub_templates": {
            "severance": {
                "trigger_keywords": ["补偿金", "赔偿金", "N+1", "2N", "辞退", "经济补偿"],
                "extra_required": ["monthly_salary", "work_years"],
                "extra_optional": ["city", "termination_type"],
            },
            "litigation_cost": {
                "trigger_keywords": ["诉讼费", "起诉费", "受理费", "打官司费用"],
                "extra_required": ["amount"],
                "extra_optional": [],
            },
            "statute_of_limitations": {
                "trigger_keywords": ["时效", "过期", "还能起诉", "过了时效"],
                "extra_required": ["trigger_date"],
                "extra_optional": [],
            },
            "overtime_pay": {
                "trigger_keywords": ["加班费", "加班工资", "加班补偿"],
                "extra_required": ["monthly_salary"],
                "extra_optional": [],
            },
            "work_injury": {
                "trigger_keywords": ["工伤", "伤残赔偿", "工伤补偿"],
                "extra_required": ["disability_level", "monthly_salary"],
                "extra_optional": ["city"],
            },
        },
    },

    # ================================================================
    # P0 新增场景：消费者维权
    # ================================================================
    "CONSUMER_PROTECTION": {
        "name": "消费者维权",
        "required_slots": [
            {
                "key": "issue_type", "label": "问题类型",
                "question": "您遇到了什么消费问题？",
                "options": ["商品质量问题", "虚假宣传/欺诈", "预付卡/充值退款", "网购纠纷/退货", "服务质量不达标", "食品安全"],
                "extract_patterns": [
                    r"质量", r"假[货冒]", r"虚假宣传", r"欺[诈骗]", r"退[款货]", r"充值",
                    r"预付", r"网购", r"食品", r"过期", r"霉变", r"投诉",
                ],
                "round": 1,
            },
            {
                "key": "purchase_info", "label": "消费信息",
                "question": "消费金额和消费时间？在哪里消费的？",
                "extract_patterns": [r"\d+元", r"\d+块", r"\d+万", r"淘宝", r"京东", r"拼多多", r"实体店"],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "evidence", "label": "证据情况",
                "question": "有哪些证据？（发票/收据/聊天记录/照片等）",
                "extract_patterns": [r"发票", r"收据", r"截图", r"聊天记录", r"照片", r"视频"],
                "round": 2,
            },
            {
                "key": "merchant_response", "label": "商家态度",
                "question": "联系过商家吗？商家怎么回应的？",
                "options": ["未联系", "商家拒绝处理", "商家同意但未兑现", "商家失联/跑路"],
                "extract_patterns": [r"拒绝", r"不理", r"失联", r"跑路"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # P0 新增场景：交通事故
    # ================================================================
    "TRAFFIC_ACCIDENT": {
        "name": "交通事故",
        "required_slots": [
            {
                "key": "accident_type", "label": "事故类型",
                "question": "事故情况是怎样的？",
                "options": ["追尾", "刮蹭", "行人被撞", "非机动车事故", "多车连环", "单方事故"],
                "extract_patterns": [
                    r"追尾", r"刮蹭", r"撞[了到]", r"被撞", r"碰撞", r"碾压",
                    r"逆行", r"闯红灯", r"超速",
                ],
                "round": 1,
            },
            {
                "key": "injury_status", "label": "伤亡情况",
                "question": "有没有人受伤？伤情如何？",
                "options": ["无人受伤（纯财产损失）", "轻微伤", "轻伤以上", "有人死亡"],
                "extract_patterns": [r"受伤", r"骨折", r"住院", r"伤残", r"死亡", r"没受伤"],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "responsibility", "label": "责任认定",
                "question": "交警有没有出具事故责任认定书？责任怎么划分的？",
                "options": ["全责", "主责", "同等责任", "次责", "无责", "尚未认定"],
                "extract_patterns": [r"全责", r"主责", r"同责", r"次责", r"无责", r"认定书"],
                "round": 1,
            },
            {
                "key": "insurance_status", "label": "保险情况",
                "question": "双方的保险情况？（交强险/商业险）",
                "extract_patterns": [r"交强险", r"商业险", r"三者险", r"全险", r"没有保险"],
                "round": 2,
            },
            {
                "key": "damage_amount", "label": "损失金额",
                "question": "大致的损失金额？（维修费、医疗费等）",
                "extract_patterns": [r"\d+元", r"\d+万", r"修车", r"医疗费"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # P0 新增场景：保险理赔
    # ================================================================
    "INSURANCE_CLAIM": {
        "name": "保险理赔",
        "required_slots": [
            {
                "key": "insurance_type", "label": "保险类型",
                "question": "是什么保险？",
                "options": ["车险", "意外险", "医疗险/健康险", "人寿险", "财产险", "责任险", "工程险"],
                "extract_patterns": [
                    r"车险", r"意外", r"医疗", r"健康", r"人寿", r"财产",
                    r"交强险", r"商业险", r"工程险", r"责任险",
                ],
                "round": 1,
            },
            {
                "key": "claim_issue", "label": "理赔问题",
                "question": "遇到了什么问题？",
                "options": ["保险公司拒赔", "理赔金额过低", "理赔拖延不处理", "对定损金额有异议", "不清楚如何理赔"],
                "extract_patterns": [r"拒赔", r"不赔", r"赔少了", r"拖延", r"定损", r"怎么理赔"],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "claim_amount", "label": "理赔金额",
                "question": "要求理赔的金额大概是多少？保险公司认可多少？",
                "extract_patterns": [r"\d+元", r"\d+万"],
                "round": 2,
            },
            {
                "key": "rejection_reason", "label": "拒赔理由",
                "question": "保险公司拒赔的理由是什么？",
                "extract_patterns": [r"免责", r"不在范围", r"未如实告知", r"等待期", r"除外"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 2,
    },

    # ================================================================
    # P0 新增场景：社保公积金
    # ================================================================
    "SOCIAL_INSURANCE": {
        "name": "社保公积金",
        "required_slots": [
            {
                "key": "issue_type", "label": "问题类型",
                "question": "您遇到了什么社保/公积金问题？",
                "options": ["公司未缴社保", "社保断缴/补缴", "公积金提取", "工伤保险待遇", "生育保险待遇", "养老保险转移"],
                "extract_patterns": [
                    r"没交社保", r"不交社保", r"未缴", r"断缴", r"补缴",
                    r"公积金", r"提取", r"工伤", r"生育", r"养老", r"医保",
                ],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "duration", "label": "时间范围",
                "question": "涉及多长时间？（如未缴社保的月数）",
                "extract_patterns": [r"\d+个?月", r"\d+年", r"一直没交"],
                "round": 1,
            },
            {
                "key": "employer_info", "label": "单位信息",
                "question": "在什么单位工作？是否有劳动合同？",
                "extract_patterns": [r"合同", r"公司", r"单位"],
                "round": 2,
            },
        ],
        "auto_complete_if": [],
        "min_required_for_proceed": 1,
    },

    # ================================================================
    # P0 新增场景：物业管理纠纷
    # ================================================================
    "PROPERTY_MANAGEMENT": {
        "name": "物业管理纠纷",
        "required_slots": [
            {
                "key": "issue_type", "label": "纠纷类型",
                "question": "遇到什么物业问题？",
                "options": ["物业费纠纷", "维修基金使用", "业委会选举/成立", "物业服务质量差", "公共区域权益侵占", "停车位纠纷"],
                "extract_patterns": [
                    r"物业费", r"维修基金", r"业委会", r"服务质量", r"公共区域",
                    r"停车", r"电梯", r"绿化", r"安保",
                ],
                "round": 1,
            },
            {
                "key": "role", "label": "您的身份",
                "question": "您是业主还是物业公司？",
                "options": ["业主", "物业公司", "业委会"],
                "extract_patterns": [r"业主", r"物业公司", r"物业", r"业委会"],
                "round": 1,
            },
        ],
        "optional_slots": [
            {
                "key": "amount", "label": "涉及金额",
                "question": "涉及的金额大约是多少？",
                "extract_patterns": [r"\d+元", r"\d+万"],
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

    # 附件自动提升完整度（合同/文档类场景，附件=核心输入，大幅加分）
    score_boost = 0.0
    if has_attachments and "has_attachments" in template.get("auto_complete_if", []):
        score_boost = 0.5

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

    min_required = template.get("min_required_for_proceed", 2)

    # ===== Harness: 分级完整性判断（替代旧的宽松逻辑）=====
    # 根据场景风险等级使用不同门槛，高风险场景（文书起草/刑事等）需要更高完整度
    threshold = COMPLETENESS_THRESHOLDS.get(intent, COMPLETENESS_THRESHOLDS["_default"])
    min_score = threshold["min_score"]
    min_filled_ratio = threshold["min_filled_ratio"]

    # 附件可降低填充率要求（合同审查场景，附件=核心输入）
    # V2 修复：附件存在时同时降低 min_score，避免"有合同附件还追问合同类型"
    if has_attachments and "has_attachments" in template.get("auto_complete_if", []):
        min_filled_ratio = max(0.0, min_filled_ratio - 0.20)
        min_score = max(0.0, min_score - 0.30)  # 附件是核心输入，score 阈值大幅降低

    filled_ratio = len(filled) / total if total > 0 else 1.0

    # V2 修复：附件存在且分数已有 0.4+ 时直接放行（避免不必要的追问）
    if has_attachments and "has_attachments" in template.get("auto_complete_if", []) and score >= 0.4:
        is_complete = True
        logger.info(
            f"[Harness] 附件充分: intent={intent} | score={score:.2f} | 附件存在 → 直接处理"
        )
    elif score >= min_score and filled_ratio >= min_filled_ratio:
        is_complete = True
    elif not missing:
        # 所有必填项已填，无论分数如何都可以继续
        is_complete = True
    else:
        is_complete = False
        logger.info(
            f"[Harness] 信息不完整: intent={intent} | "
            f"score={score:.2f} (需>={min_score}) | "
            f"filled={len(filled)}/{total} ({filled_ratio:.0%}, 需>={min_filled_ratio:.0%}) | "
            f"has_attachments={has_attachments} | "
            f"缺失: {[s['label'] for s in missing]}"
        )

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

    # 澄清后判断：至少 60% 信息已收集才标记完整
    return {
        "is_complete": score >= 0.6 or not remaining_missing,
        "score": round(score, 2),
        "filled_slots": filled,
        "missing_slots": remaining_missing,
        "questions": [],
        "has_next_round": False,
    }


def reassess_after_clarification(
    user_input: str,
    intent: str,
    original_assessment: Dict[str, Any],
    user_selections: Dict[str, str],
    current_round: int = 1,
    has_attachments: bool = False,
) -> Dict[str, Any]:
    """
    Harness: 补充信息后重新评估完整度（不直接放行）。

    与 merge_clarification_into_slots 的区别：
    1. 使用分级门槛（COMPLETENESS_THRESHOLDS）而非固定 0.6
    2. 如果仍不完整，自动生成下一轮问题
    3. 记录当前轮次，支持最多 3 轮追问

    Args:
        user_input: 原始用户输入
        intent: 意图类型
        original_assessment: 上次 assess_completeness 的结果
        user_selections: 用户在本轮选择的选项 {"问题文本": "选项文本"}
        current_round: 当前已完成的追问轮次
        has_attachments: 是否有附件

    Returns:
        {
            "is_complete": bool,
            "score": float,
            "filled_slots": [...],
            "missing_slots": [...],
            "questions": [...],  # 下一轮问题（如果仍不完整）
            "has_next_round": bool,
            "round": int,        # 当前轮次
            "missing_summary": str,  # 缺失信息摘要（用于告知用户）
        }
    """
    # Step 1: 合并用户选择
    merged = merge_clarification_into_slots(original_assessment, user_selections)

    # Step 2: 用分级门槛重新评估
    threshold = COMPLETENESS_THRESHOLDS.get(intent, COMPLETENESS_THRESHOLDS["_default"])
    min_score = threshold["min_score"]
    min_filled_ratio = threshold["min_filled_ratio"]

    filled = merged["filled_slots"]
    remaining_missing = merged["missing_slots"]
    total = len(filled) + len(remaining_missing)
    filled_ratio = len(filled) / total if total > 0 else 1.0
    score = merged["score"]

    # 附件降低要求
    if has_attachments:
        min_filled_ratio = max(0.0, min_filled_ratio - 0.20)

    is_complete = (score >= min_score and filled_ratio >= min_filled_ratio) or not remaining_missing

    # Step 3: 如果不完整且未到最大轮次，生成下一轮问题
    next_round = current_round + 1
    questions = []
    max_rounds = 3

    if not is_complete and next_round <= max_rounds and remaining_missing:
        # 重新运行 assess_completeness 以获取下一轮的问题
        # 将已有 filled_slots 转为 pre_filled_context
        pre_filled = {s["key"]: s["value"] for s in filled}
        next_assessment = assess_completeness(
            user_input=user_input,
            intent=intent,
            has_attachments=has_attachments,
            pre_filled_context=pre_filled,
            current_round=next_round,
        )
        questions = next_assessment.get("questions", [])

    # Step 4: 生成缺失信息摘要
    missing_summary = ""
    if remaining_missing:
        missing_labels = [s["label"] for s in remaining_missing[:5]]
        missing_summary = "、".join(missing_labels)

    logger.info(
        f"[Harness] 补充后重评估: intent={intent} round={next_round} | "
        f"score={score:.2f} (需>={min_score}) | "
        f"filled={len(filled)}/{total} ({filled_ratio:.0%}) | "
        f"is_complete={is_complete} | "
        f"缺失: {missing_summary or '无'}"
    )

    return {
        "is_complete": is_complete,
        "score": round(score, 2),
        "filled_slots": filled,
        "missing_slots": remaining_missing,
        "questions": questions,
        "has_next_round": len(questions) > 0,
        "round": next_round,
        "missing_summary": missing_summary,
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
