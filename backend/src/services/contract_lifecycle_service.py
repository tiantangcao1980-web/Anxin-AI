"""
合同生命周期管理服务

覆盖合同从签订到终止的完整生命周期：
1. 合同模板库 — 15+合同模板（5种劳动合同 + 销售/服务/工程/借款/保密等）
2. 合同执行监控 — 到期提醒、付款节点、交付节点
3. 违约风险预警 — 对方违约迹象识别
4. 后续追踪闭环 — 发函→等回应→升级诉讼

场景覆盖：
- 企业主：销售/服务/工程合同的签订与履行监控
- HR经理：5种劳动合同（全职/兼职/实习/高管/劳务派遣）
- 物业公司：物业服务合同+批量催收追踪
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from loguru import logger

from src.models.contract import Contract, ContractStatus

LEGAL_TRANSITIONS: dict[ContractStatus, frozenset[ContractStatus]] = {
    ContractStatus.DRAFT: frozenset({
        ContractStatus.PENDING_REVIEW,
        ContractStatus.UNDER_REVIEW,
        ContractStatus.TERMINATED,
    }),
    ContractStatus.PENDING_REVIEW: frozenset({
        ContractStatus.UNDER_REVIEW,
        ContractStatus.APPROVED,
        ContractStatus.DRAFT,
        ContractStatus.TERMINATED,
    }),
    ContractStatus.UNDER_REVIEW: frozenset({
        ContractStatus.PENDING_REVIEW,
        ContractStatus.REVIEW_FAILED,
        ContractStatus.APPROVED,
        ContractStatus.TERMINATED,
    }),
    ContractStatus.REVIEW_FAILED: frozenset({
        ContractStatus.UNDER_REVIEW,
        ContractStatus.DRAFT,
        ContractStatus.TERMINATED,
    }),
    ContractStatus.APPROVED: frozenset({
        ContractStatus.SIGNED,
        ContractStatus.TERMINATED,
    }),
    ContractStatus.SIGNED: frozenset({
        ContractStatus.ACTIVE,
        ContractStatus.EXPIRED,
        ContractStatus.TERMINATED,
    }),
    ContractStatus.ACTIVE: frozenset({
        ContractStatus.EXPIRED,
        ContractStatus.TERMINATED,
    }),
    ContractStatus.EXPIRED: frozenset(),
    ContractStatus.TERMINATED: frozenset(),
}


class IllegalStateTransition(ValueError):  # noqa: N818
    """Raised when a contract status change violates the lifecycle matrix."""


def normalize_contract_status(status: ContractStatus | str) -> ContractStatus:
    if isinstance(status, ContractStatus):
        return status
    try:
        return ContractStatus(status)
    except ValueError as exc:
        raise IllegalStateTransition(f"Unsupported contract status: {status}") from exc


def can_transition_contract(
    current_status: ContractStatus | str,
    target_status: ContractStatus | str,
) -> bool:
    current = normalize_contract_status(current_status)
    target = normalize_contract_status(target_status)
    return current == target or target in LEGAL_TRANSITIONS[current]


class ContractLifecycleStateMachine:
    """Single gateway for contract status changes."""

    @staticmethod
    def transition(
        contract: Contract,
        target_status: ContractStatus | str,
        *,
        actor_id: str | None = None,
        reason: str | None = None,
    ) -> Contract:
        current = normalize_contract_status(contract.status)
        target = normalize_contract_status(target_status)
        if current == target:
            return contract
        if target not in LEGAL_TRANSITIONS[current]:
            raise IllegalStateTransition(
                f"Illegal contract status transition: {current.value} -> {target.value}"
            )

        contract.status = target
        logger.info(
            "合同状态转换: contract_id={}, {} -> {}, actor={}, reason={}",
            contract.id,
            current.value,
            target.value,
            actor_id or "system",
            reason or "",
        )
        return contract


# ========== 1. 合同模板库 ==========

CONTRACT_TEMPLATES: dict[str, dict[str, Any]] = {

    # ===== 劳动合同（5种）=====

    "labor_fulltime": {
        "name": "全日制劳动合同",
        "category": "劳动用工",
        "applicable": "全职员工",
        "key_clauses": [
            "合同期限（固定期限/无固定期限）",
            "工作内容和工作地点",
            "工作时间和休息休假",
            "劳动报酬（基本工资+绩效+补贴）",
            "社会保险和福利待遇",
            "劳动保护和劳动条件",
            "保密义务和竞业限制（如需要）",
            "试用期条款（期限+工资不低于80%）",
            "合同解除和终止条件",
        ],
        "legal_basis": [
            "《劳动合同法》第17条（劳动合同应当具备的条款）",
            "《劳动合同法》第19条（试用期规定）",
            "《劳动合同法》第20条（试用期工资不低于约定工资80%）",
        ],
        "risk_checkpoints": [
            "试用期是否超出法定上限（3年以上固定期限→最长6个月）",
            "试用期工资是否不低于约定工资的80%",
            "是否约定了服务期但未提供专项培训",
            "竞业限制期限是否超过2年",
            "竞业限制是否约定了补偿金（月均不低于工资30%）",
        ],
    },

    "labor_parttime": {
        "name": "非全日制劳动合同",
        "category": "劳动用工",
        "applicable": "兼职员工（日均不超4小时，周不超24小时）",
        "key_clauses": [
            "工作时间（日均≤4小时，周≤24小时）",
            "劳动报酬（小时工资，不低于最低小时工资标准）",
            "结算周期（最长不超过15天）",
            "终止条件（双方可随时通知终止，无需补偿）",
        ],
        "legal_basis": [
            "《劳动合同法》第68-72条（非全日制用工特别规定）",
        ],
        "risk_checkpoints": [
            "工作时间是否超过法定上限（超过则按全日制处理）",
            "工资结算周期是否超过15天",
            "是否约定了试用期（非全日制不得约定试用期）",
        ],
    },

    "labor_intern": {
        "name": "实习协议",
        "category": "劳动用工",
        "applicable": "在校学生实习",
        "key_clauses": [
            "实习期限和内容",
            "实习补贴/报酬",
            "工作时间（不得影响正常学业）",
            "安全保护措施",
            "保密义务",
            "学校/企业/学生三方权利义务",
            "意外伤害保险（企业应购买）",
        ],
        "legal_basis": [
            "《职业学校学生实习管理规定》",
            "注意：实习关系不是劳动关系，不适用《劳动合同法》",
        ],
        "risk_checkpoints": [
            "是否购买了意外伤害保险",
            "实习内容是否与专业相关",
            "是否安排了加班（实习生不应加班）",
            "是否扣押了实习生身份证件",
        ],
    },

    "labor_executive": {
        "name": "高管劳动合同",
        "category": "劳动用工",
        "applicable": "总经理、副总经理、财务总监等高管",
        "key_clauses": [
            "劳动合同基本条款（同全日制）",
            "竞业限制条款（期限≤2年，补偿金≥月工资30%）",
            "保密条款（商业秘密、客户资料等）",
            "绩效考核与薪酬结构（基本工资+绩效奖金+股权激励）",
            "服务期约定（如有专项培训）",
            "解除条件（特别约定的解除事由）",
            "离职交接（客户资源、商业秘密等）",
            "知识产权归属（职务发明）",
        ],
        "legal_basis": [
            "《劳动合同法》第17条+第23-25条",
            "《公司法》第146条（高管忠实义务和勤勉义务）",
        ],
        "risk_checkpoints": [
            "竞业限制补偿金是否约定清楚（月工资30%以上）",
            "知识产权归属是否明确",
            "股权激励是否有行权条件和退出机制",
            "离职交接是否有明确流程和责任",
        ],
    },

    "labor_dispatch": {
        "name": "劳务派遣协议",
        "category": "劳动用工",
        "applicable": "通过劳务派遣公司使用的临时性/辅助性/替代性岗位员工",
        "key_clauses": [
            "派遣单位与用工单位的权利义务划分",
            "派遣岗位（临时性/辅助性/替代性）",
            "派遣期限",
            "同工同酬条款",
            "社保和劳动保护责任划分",
            "退回条件和程序",
            "工伤责任承担",
        ],
        "legal_basis": [
            "《劳动合同法》第57-67条（劳务派遣特别规定）",
            "《劳务派遣暂行规定》（派遣比例不超10%）",
        ],
        "risk_checkpoints": [
            "派遣单位是否有劳务派遣经营许可证",
            "派遣岗位是否属于临时性/辅助性/替代性",
            "派遣比例是否超过用工总量的10%",
            "是否实现了同工同酬",
        ],
    },

    # ===== 商业合同 =====

    "sales_contract": {
        "name": "销售/采购合同",
        "category": "商业合同",
        "applicable": "货物买卖、设备采购",
        "key_clauses": [
            "标的物（品名、规格、数量、质量标准）",
            "价格与付款方式（预付/货到付款/分期）",
            "交付时间与方式（送达/自提/物流）",
            "验收标准与异议期",
            "质量保证期",
            "违约责任（延迟交货/延迟付款/质量不合格）",
            "不可抗力",
            "争议解决（法院/仲裁+管辖地）",
        ],
        "risk_checkpoints": [
            "付款条件是否对己方有利（预付比例、尾款条件）",
            "验收标准是否明确具体（避免主观判断）",
            "违约金是否约定了具体比例",
            "质保期内的返修/退换条件",
        ],
    },

    "service_contract": {
        "name": "服务/委托合同",
        "category": "商业合同",
        "applicable": "咨询、软件开发、设计、代理等服务",
        "key_clauses": [
            "服务内容与范围（详细的工作说明书/SOW）",
            "交付成果与验收标准",
            "服务期限和里程碑",
            "服务费用与付款节点",
            "知识产权归属",
            "保密条款",
            "违约责任",
            "服务质量标准/SLA",
        ],
        "risk_checkpoints": [
            "交付标准是否可量化（避免'甲方满意'等主观条款）",
            "知识产权归属是否明确（特别是软件/设计作品）",
            "变更管理（需求变更的审批流程和费用调整）",
            "是否有竞业限制/排他条款",
        ],
    },

    "construction_contract": {
        "name": "建设工程合同",
        "category": "商业合同",
        "applicable": "工程施工、装修装饰",
        "key_clauses": [
            "工程概况（名称、地点、内容、规模）",
            "工期（开工日期、竣工日期、里程碑节点）",
            "合同价款与支付方式（进度款/结算/质保金）",
            "质量标准",
            "安全生产责任",
            "竣工验收标准与程序",
            "缺陷责任期和质保金",
            "工程变更和签证管理",
        ],
        "risk_checkpoints": [
            "是否存在违法分包/转包",
            "质保金比例是否合理（一般不超过合同价的3%）",
            "工期延误的违约金是否约定",
            "工程签证管理流程是否明确",
        ],
    },

    "loan_contract": {
        "name": "借款合同",
        "category": "商业合同",
        "applicable": "企业间借贷、民间借贷",
        "key_clauses": [
            "借款金额",
            "借款期限",
            "利率（年利率，不得超过法定上限）",
            "还款方式（一次性/分期/先息后本）",
            "担保方式（保证/抵押/质押）",
            "提前还款条件",
            "逾期违约责任",
            "争议解决",
        ],
        "risk_checkpoints": [
            "利率是否超过LPR的4倍（超过部分不受法律保护）",
            "是否约定了复利（注意司法态度）",
            "担保是否办理了登记（抵押登记/质押交付）",
            "是否有资金来源合法性问题",
        ],
    },

    "nda_contract": {
        "name": "保密协议/NDA",
        "category": "商业合同",
        "applicable": "商业合作前的信息保护",
        "key_clauses": [
            "保密信息的定义和范围",
            "保密义务和使用限制",
            "保密期限",
            "例外情形（公开信息、独立开发等）",
            "违约责任",
            "信息返还/销毁义务",
        ],
        "risk_checkpoints": [
            "保密范围是否过宽或过窄",
            "保密期限是否合理",
            "违约金金额是否有约定",
        ],
    },
}


# ========== 2. 合同执行监控 ==========

@dataclass
class ContractMilestone:
    """合同里程碑/关键节点"""
    name: str
    due_date: str                 # YYYY-MM-DD
    type: str = "payment"         # payment / delivery / review / expiry
    amount: float = 0             # 涉及金额
    status: str = "pending"       # pending / done / overdue / warning
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "due_date": self.due_date,
            "type": self.type,
            "amount": self.amount,
            "status": self.status,
            "note": self.note,
        }


@dataclass
class ContractTracker:
    """合同追踪器"""
    contract_id: str
    contract_name: str
    counterparty: str
    contract_type: str
    start_date: str
    end_date: str
    total_amount: float = 0
    milestones: list[ContractMilestone] = field(default_factory=list)
    status: str = "active"        # active / completed / terminated / disputed
    follow_ups: list[dict[str, Any]] = field(default_factory=list)  # 后续追踪记录

    def check_alerts(self) -> list[dict[str, Any]]:
        """检查预警"""
        alerts: list[dict[str, Any]] = []
        today = date.today()

        for m in self.milestones:
            if m.status == "done":
                continue
            try:
                due = datetime.strptime(m.due_date, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue

            days_until = (due - today).days

            if days_until < 0:
                m.status = "overdue"
                alerts.append({
                    "level": "danger",
                    "message": f"⚠️ {m.name} 已逾期 {abs(days_until)} 天（应于 {m.due_date} 完成）",
                    "milestone": m.name,
                    "overdue_days": abs(days_until),
                })
            elif days_until <= 7:
                m.status = "warning"
                alerts.append({
                    "level": "warning",
                    "message": f"📢 {m.name} 将于 {days_until} 天后到期（{m.due_date}）",
                    "milestone": m.name,
                    "days_until": days_until,
                })
            elif days_until <= 30:
                alerts.append({
                    "level": "info",
                    "message": f"📋 {m.name} 将于 {days_until} 天后到期（{m.due_date}）",
                    "milestone": m.name,
                    "days_until": days_until,
                })

        # 合同到期检查
        try:
            end = datetime.strptime(self.end_date, "%Y-%m-%d").date()
            days_to_end = (end - today).days
            if days_to_end < 0:
                alerts.append({
                    "level": "danger",
                    "message": f"⚠️ 合同已于 {self.end_date} 到期",
                })
            elif days_to_end <= 30:
                alerts.append({
                    "level": "warning",
                    "message": f"📢 合同将于 {days_to_end} 天后到期（{self.end_date}），请提前安排续签或终止",
                })
        except (ValueError, TypeError):
            pass

        return alerts

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_name": self.contract_name,
            "counterparty": self.counterparty,
            "contract_type": self.contract_type,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "total_amount": self.total_amount,
            "milestones": [m.to_dict() for m in self.milestones],
            "status": self.status,
            "alerts": self.check_alerts(),
            "follow_ups": self.follow_ups,
        }


# ========== 3. 后续追踪闭环 ==========

FOLLOW_UP_CHAINS: dict[str, list[dict[str, Any]]] = {
    "demand_letter": [
        {
            "stage": "sent",
            "label": "律师函已发出",
            "question": "律师函已发出，请关注对方是否在限期内回应。对方有回应了吗？",
            "options": ["已回应，同意支付", "已回应，有异议", "未回应，已超期限"],
            "next": {
                "已回应，同意支付": "payment_tracking",
                "已回应，有异议": "negotiation",
                "未回应，已超期限": "escalate_litigation",
            },
        },
        {
            "stage": "payment_tracking",
            "label": "等待付款",
            "question": "对方同意支付。请确认是否已收到款项？",
            "options": ["已收到全款", "部分收到", "承诺后仍未付"],
            "next": {
                "已收到全款": "resolved",
                "部分收到": "partial_payment",
                "承诺后仍未付": "escalate_litigation",
            },
        },
        {
            "stage": "negotiation",
            "label": "协商中",
            "question": "正在与对方协商。协商结果如何？",
            "options": ["达成和解方案", "协商破裂", "对方提出反诉"],
            "next": {
                "达成和解方案": "settlement",
                "协商破裂": "escalate_litigation",
                "对方提出反诉": "escalate_litigation",
            },
        },
        {
            "stage": "escalate_litigation",
            "label": "升级诉讼",
            "question": "建议提起诉讼。是否需要我帮您：\n1. 计算诉讼费用\n2. 准备起诉材料\n3. 评估胜败风险",
            "options": ["准备起诉", "再观察一段时间", "放弃追讨"],
        },
        {
            "stage": "settlement",
            "label": "和解",
            "question": "请确认和解协议内容，我可以帮您起草和解协议书。对方是否按和解协议履行？",
            "options": ["已按约履行", "未按约履行"],
            "next": {
                "已按约履行": "resolved",
                "未按约履行": "escalate_litigation",
            },
        },
        {
            "stage": "resolved",
            "label": "已解决",
            "question": "恭喜！此事项已解决。建议保存所有往来函件和付款凭证作为档案。",
        },
    ],

    "contract_breach": [
        {
            "stage": "discovered",
            "label": "发现违约",
            "question": "已确认对方存在违约行为。您希望如何处理？",
            "options": ["先协商解决", "直接发律师函", "解除合同"],
            "next": {
                "先协商解决": "negotiation",
                "直接发律师函": "demand_letter_sent",
                "解除合同": "termination",
            },
        },
        {
            "stage": "demand_letter_sent",
            "label": "律师函已发出",
            "question": "催告函已发出，请在限期后告知对方反应。",
            "options": ["对方整改了", "对方未回应", "对方有异议"],
            "next": {
                "对方整改了": "resolved",
                "对方未回应": "escalate",
                "对方有异议": "negotiation",
            },
        },
        {
            "stage": "termination",
            "label": "合同解除",
            "question": "合同已解除。是否需要追究违约赔偿？",
            "options": ["需要追偿", "不追偿"],
            "next": {
                "需要追偿": "escalate",
                "不追偿": "resolved",
            },
        },
        {
            "stage": "negotiation",
            "label": "协商中",
            "question": "正在协商。结果如何？",
            "options": ["达成一致", "协商破裂"],
            "next": {
                "达成一致": "resolved",
                "协商破裂": "escalate",
            },
        },
        {
            "stage": "escalate",
            "label": "法律行动",
            "question": "建议通过诉讼/仲裁解决。我可以帮您计算诉讼费、准备材料。",
        },
        {
            "stage": "resolved",
            "label": "已解决",
            "question": "此事项已解决。建议归档保存相关文件。",
        },
    ],
}


class ContractLifecycleService:
    """合同生命周期管理服务"""

    def __init__(self) -> None:
        self._trackers: dict[str, ContractTracker] = {}

    # ===== 模板库 =====

    def get_template_catalog(self, category: str | None = None) -> list[dict[str, Any]]:
        """获取模板目录"""
        result: list[dict[str, Any]] = []
        for key, tpl in CONTRACT_TEMPLATES.items():
            if category and tpl["category"] != category:
                continue
            result.append({
                "template_id": key,
                "name": tpl["name"],
                "category": tpl["category"],
                "applicable": tpl["applicable"],
                "key_clauses_count": len(tpl["key_clauses"]),
                "risk_checkpoints_count": len(tpl.get("risk_checkpoints", [])),
            })
        return result

    def get_template_detail(self, template_id: str) -> dict[str, Any] | None:
        """获取模板详情"""
        tpl = CONTRACT_TEMPLATES.get(template_id)
        if not tpl:
            return None
        return {**tpl, "template_id": template_id}

    def get_template_risk_checklist(self, template_id: str) -> str:
        """获取合同风险检查清单 Markdown"""
        tpl = CONTRACT_TEMPLATES.get(template_id)
        if not tpl:
            return "模板不存在"

        lines = [
            f"## {tpl['name']} — 风险检查清单\n",
            f"**适用对象**：{tpl['applicable']}\n",
            "### 必备条款\n",
        ]
        for clause in tpl["key_clauses"]:
            lines.append(f"- [ ] {clause}")

        if tpl.get("risk_checkpoints"):
            lines.append("\n### ⚠️ 风险检查点\n")
            for point in tpl["risk_checkpoints"]:
                lines.append(f"- [ ] {point}")

        if tpl.get("legal_basis"):
            lines.append("\n### 法律依据\n")
            for lb in tpl["legal_basis"]:
                lines.append(f"- {lb}")

        return "\n".join(lines)

    # ===== 执行监控 =====

    def create_tracker(
        self,
        contract_name: str,
        counterparty: str,
        contract_type: str,
        start_date: str,
        end_date: str,
        total_amount: float = 0,
        milestones: list[dict[str, Any]] | None = None,
    ) -> ContractTracker:
        """创建合同追踪器"""
        import uuid
        tracker = ContractTracker(
            contract_id=str(uuid.uuid4())[:12],
            contract_name=contract_name,
            counterparty=counterparty,
            contract_type=contract_type,
            start_date=start_date,
            end_date=end_date,
            total_amount=total_amount,
        )

        if milestones:
            for m in milestones:
                tracker.milestones.append(ContractMilestone(**m))

        self._trackers[tracker.contract_id] = tracker
        return tracker

    def get_all_alerts(self) -> list[dict[str, Any]]:
        """获取所有合同的预警信息"""
        all_alerts: list[dict[str, Any]] = []
        for tracker in self._trackers.values():
            alerts = tracker.check_alerts()
            for alert in alerts:
                alert["contract_name"] = tracker.contract_name
                alert["counterparty"] = tracker.counterparty
            all_alerts.extend(alerts)
        # 按严重级别排序
        level_order = {"danger": 0, "warning": 1, "info": 2}
        all_alerts.sort(key=lambda a: level_order.get(a.get("level", "info"), 3))
        return all_alerts

    # ===== 后续追踪 =====

    def get_follow_up_chain(self, chain_type: str) -> list[dict[str, Any]] | None:
        """获取追踪链"""
        return FOLLOW_UP_CHAINS.get(chain_type)

    def get_follow_up_stage(self, chain_type: str, stage: str) -> dict[str, Any] | None:
        """获取追踪链的某个阶段"""
        chain = FOLLOW_UP_CHAINS.get(chain_type, [])
        for item in chain:
            if item["stage"] == stage:
                return item
        return None

    def get_next_follow_up(
        self,
        chain_type: str,
        current_stage: str,
        user_choice: str,
    ) -> dict[str, Any] | None:
        """根据用户选择获取下一步追踪"""
        stage = self.get_follow_up_stage(chain_type, current_stage)
        if not stage or "next" not in stage:
            return None
        next_stage_name = stage["next"].get(user_choice)
        if not next_stage_name:
            return None
        return self.get_follow_up_stage(chain_type, next_stage_name)


# 全局实例
contract_lifecycle_service = ContractLifecycleService()
