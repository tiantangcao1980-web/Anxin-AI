"""
流程向导服务 — 逐步引导合规操作

核心场景（HR最需要）：
1. 辞退流程向导：第1步评估合法性→第2步准备文件→第3步送达通知→第4步交接→第5步结算
2. 工伤处理向导：报告→送医→申报→鉴定→赔偿
3. 裁员流程向导：方案制定→工会通告→政府报告→人员确定→执行
4. 公司设立向导：核名→章程→验资→登记→刻章→税务
5. 合同纠纷处理：违约认定→发函→协商→调解→诉讼

设计理念：
- 每步有明确的操作指引和需要生成的文件
- 步骤之间有前置条件检查
- 每步完成后自动推进到下一步
- 支持从任意步骤介入（用户可能已完成部分步骤）
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class WizardStep:
    """流程向导单步"""
    step_id: int
    name: str
    description: str
    actions: list[str]                    # 需要执行的操作
    documents: list[str]                  # 本步需要生成/准备的文件
    legal_basis: list[str]                # 法律依据
    warnings: list[str] = field(default_factory=list)  # 风险提示
    prerequisites: list[str] = field(default_factory=list)  # 前置条件
    estimated_days: int = 0               # 预估耗时（天）
    status: str = "pending"               # pending / current / done / skipped

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "description": self.description,
            "actions": self.actions,
            "documents": self.documents,
            "legal_basis": self.legal_basis,
            "warnings": self.warnings,
            "prerequisites": self.prerequisites,
            "estimated_days": self.estimated_days,
            "status": self.status,
        }


@dataclass
class WizardInstance:
    """流程向导实例"""
    wizard_id: str
    wizard_type: str
    title: str
    steps: list[WizardStep]
    current_step: int = 1
    context: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    status: str = "active"  # active / completed / paused

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def progress(self) -> float:
        done = sum(1 for s in self.steps if s.status == "done")
        return done / self.total_steps if self.total_steps > 0 else 0

    @property
    def total_days(self) -> int:
        return sum(s.estimated_days for s in self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "wizard_id": self.wizard_id,
            "wizard_type": self.wizard_type,
            "title": self.title,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "progress": f"{self.progress:.0%}",
            "total_estimated_days": self.total_days,
            "status": self.status,
            "steps": [s.to_dict() for s in self.steps],
        }

    def to_markdown(self) -> str:
        """输出当前步骤的详细 Markdown 指引"""
        if self.current_step > self.total_steps:
            return "## ✅ 所有步骤已完成\n\n恭喜！流程已全部完成。"

        step = self.steps[self.current_step - 1]
        lines = [
            f"## {self.title}",
            f"**进度：第 {self.current_step}/{self.total_steps} 步 ({self.progress:.0%})**\n",
            f"### 当前步骤：{step.name}",
            f"{step.description}\n",
        ]

        if step.prerequisites:
            lines.append("### 前置条件")
            for p in step.prerequisites:
                lines.append(f"- [ ] {p}")
            lines.append("")

        lines.append("### 需要做的事")
        for i, a in enumerate(step.actions, 1):
            lines.append(f"{i}. {a}")
        lines.append("")

        if step.documents:
            lines.append("### 需要准备的文件")
            for d in step.documents:
                lines.append(f"- 📄 {d}")
            lines.append("")

        if step.legal_basis:
            lines.append("### 法律依据")
            for lb in step.legal_basis:
                lines.append(f"- {lb}")
            lines.append("")

        if step.warnings:
            lines.append("### ⚠️ 注意事项")
            for w in step.warnings:
                lines.append(f"- {w}")
            lines.append("")

        if step.estimated_days:
            lines.append(f"**预估耗时**：约 {step.estimated_days} 个工作日\n")

        # 显示后续步骤概览
        if self.current_step < self.total_steps:
            lines.append("### 后续步骤")
            for s in self.steps[self.current_step:]:
                lines.append(f"- 第{s.step_id}步：{s.name}")

        return "\n".join(lines)


# ========== 流程向导定义 ==========

WIZARD_DEFINITIONS: dict[str, dict[str, Any]] = {

    # =============================================
    # 1. 辞退员工流程
    # =============================================
    "employee_termination": {
        "title": "员工辞退合规流程向导",
        "description": "确保辞退过程每一步都合法合规，避免劳动仲裁败诉",
        "steps": [
            WizardStep(
                step_id=1, name="合法性评估",
                description="确认辞退理由是否合法，选择正确的解除方式",
                actions=[
                    "确认辞退原因属于《劳动合同法》规定的合法解除情形",
                    "判断适用N/N+1/2N中的哪种补偿标准",
                    "检查员工是否处于受保护期（孕期、工伤、医疗期等）",
                    "评估是否有充分的证据支持辞退理由",
                ],
                documents=["辞退合法性评估报告"],
                legal_basis=[
                    "《劳动合同法》第39条（过失性辞退，无需补偿）",
                    "《劳动合同法》第40条（无过失性辞退，N+1或提前30天通知后N）",
                    "《劳动合同法》第41条（经济性裁员，N）",
                    "《劳动合同法》第42条（不得解除的情形）",
                ],
                warnings=[
                    "孕期/产期/哺乳期女职工不得辞退（第42条第4款）",
                    "患职业病或工伤在规定医疗期内的不得辞退",
                    "在本单位连续工作满15年且距退休不足5年的不得辞退",
                ],
                estimated_days=1,
            ),
            WizardStep(
                step_id=2, name="计算补偿金",
                description="精确计算应付经济补偿金/赔偿金",
                actions=[
                    "计算员工前12个月平均工资（含奖金、津贴、加班费）",
                    "确认工作年限（入职日期到解除日期）",
                    "计算经济补偿金（注意高薪封顶和年限封顶）",
                    "核算未休年假补偿、未结工资等",
                ],
                documents=["经济补偿金计算明细表", "工资条核对单"],
                legal_basis=[
                    "《劳动合同法》第47条（经济补偿标准）",
                    "《劳动合同法》第87条（违法辞退双倍赔偿）",
                ],
                warnings=[
                    "月工资超过当地社平工资3倍的，按3倍计算，且年限不超过12年",
                    "代通知金按实际工资计算，不受3倍封顶限制",
                ],
                prerequisites=["已完成合法性评估"],
                estimated_days=1,
            ),
            WizardStep(
                step_id=3, name="准备文件",
                description="准备辞退所需的全部法律文件",
                actions=[
                    "起草《解除劳动合同通知书》",
                    "准备《经济补偿金确认书》",
                    "准备《工作交接清单》",
                    "准备《离职证明》（解除后出具）",
                    "通知工会（如有）",
                ],
                documents=[
                    "解除劳动合同通知书",
                    "经济补偿金确认书",
                    "工作交接清单",
                    "离职证明（预备）",
                    "工会告知函（如有工会）",
                ],
                legal_basis=[
                    "《劳动合同法》第43条（解除劳动合同应事先通知工会）",
                    "《劳动合同法》第50条（用人单位应出具解除证明）",
                ],
                warnings=[
                    "未通知工会可能被认定为程序违法",
                    "通知书必须送达本人签收，留存证据",
                ],
                prerequisites=["已计算补偿金额"],
                estimated_days=2,
            ),
            WizardStep(
                step_id=4, name="送达通知",
                description="向员工送达解除通知并协商",
                actions=[
                    "安排面谈（建议有HR和部门负责人在场，必要时录音）",
                    "当面送达《解除劳动合同通知书》",
                    "说明解除原因、补偿方案",
                    "请员工签收通知书（如拒签则见证人签字+邮寄EMS）",
                    "协商一致的，签署《协商解除协议》",
                ],
                documents=["面谈记录", "送达签收回执", "协商解除协议（如适用）"],
                legal_basis=[
                    "《劳动合同法》第36条（协商一致解除）",
                    "《劳动合同法》第40条（提前30天书面通知或额外支付1个月工资）",
                ],
                warnings=[
                    "面谈时不得使用威胁、欺骗手段",
                    "拒签时务必有证人+EMS邮寄，保留送达证据",
                    "录音需注意当地法律对单方录音的态度",
                ],
                prerequisites=["已准备全部文件"],
                estimated_days=1,
            ),
            WizardStep(
                step_id=5, name="结算与交接",
                description="完成工资结算、社保转移和工作交接",
                actions=[
                    "结清工资（含未结工资、年假补偿、报销等）",
                    "支付经济补偿金",
                    "办理社保、公积金停缴/转移手续",
                    "收回公司财产（电脑、工牌、门禁等）",
                    "出具《离职证明》",
                    "办理档案转移（如适用）",
                ],
                documents=["离职证明", "社保减员表", "工资结算单", "财产归还确认书"],
                legal_basis=[
                    "《劳动合同法》第50条（15日内办理档案和社保转移）",
                    "《工资支付暂行规定》第9条（解除合同时一次付清工资）",
                ],
                warnings=[
                    "补偿金须在办理交接手续时支付，不得拖延",
                    "离职证明不得含有对劳动者不利的内容",
                    "保存所有文件签收记录至少2年（仲裁时效）",
                ],
                prerequisites=["已送达通知并取得签收"],
                estimated_days=5,
            ),
        ],
    },

    # =============================================
    # 2. 工伤处理流程
    # =============================================
    "work_injury": {
        "title": "工伤处理合规流程向导",
        "description": "从事故发生到赔偿到位的全流程指引",
        "steps": [
            WizardStep(
                step_id=1, name="事故处理与报告",
                description="事故发生后的紧急处理和报告",
                actions=[
                    "立即将伤者送医救治",
                    "保护事故现场、收集证据（照片、视频、证人联系方式）",
                    "24小时内向人社局报告工伤事故",
                    "内部记录事故经过",
                ],
                documents=["事故报告表", "现场照片/视频", "证人证言"],
                legal_basis=["《工伤保险条例》第17条（30日内申请工伤认定）"],
                warnings=["超过30天未申报的，期间费用由用人单位承担"],
                estimated_days=1,
            ),
            WizardStep(
                step_id=2, name="工伤认定申请",
                description="向人社局提交工伤认定申请",
                actions=[
                    "用人单位在事故发生后30日内提交申请",
                    "如单位未申请，职工或近亲属可在1年内申请",
                    "准备工伤认定所需全部材料",
                    "等待人社局审核（一般60日内出结果）",
                ],
                documents=[
                    "工伤认定申请表",
                    "劳动合同（或事实劳动关系证明）",
                    "医疗诊断证明",
                    "事故调查报告",
                    "目击证人证词",
                ],
                legal_basis=[
                    "《工伤保险条例》第14条（应当认定为工伤的情形）",
                    "《工伤保险条例》第17条（申请时限）",
                    "《工伤保险条例》第20条（60日内作出认定决定）",
                ],
                warnings=["用人单位超过30日未申请的，期间费用自行承担"],
                prerequisites=["已完成事故处理和报告"],
                estimated_days=60,
            ),
            WizardStep(
                step_id=3, name="劳动能力鉴定",
                description="伤情稳定后申请伤残等级鉴定",
                actions=[
                    "确认伤情稳定（或治疗终结）",
                    "向设区的市级劳动能力鉴定委员会申请",
                    "参加鉴定（一般60日内出结果，最长90日）",
                    "对鉴定结果有异议可在15日内申请再次鉴定",
                ],
                documents=["劳动能力鉴定申请表", "工伤认定决定书", "完整医疗资料"],
                legal_basis=[
                    "《工伤保险条例》第21-26条（劳动能力鉴定）",
                ],
                prerequisites=["已取得工伤认定决定书", "伤情稳定"],
                estimated_days=90,
            ),
            WizardStep(
                step_id=4, name="赔偿计算与支付",
                description="根据伤残等级计算并支付各项赔偿",
                actions=[
                    "根据伤残等级计算一次性伤残补助金",
                    "确认停工留薪期工资（原工资福利不变）",
                    "核算医疗费、护理费、交通食宿费",
                    "如解除合同：计算一次性工伤医疗补助金和就业补助金",
                    "申请工伤保险基金支付",
                ],
                documents=["赔偿计算明细表", "医疗费发票汇总", "工伤保险基金支付申请"],
                legal_basis=[
                    "《工伤保险条例》第30-37条（各项工伤保险待遇）",
                ],
                warnings=[
                    "未缴纳工伤保险的，全部费用由用人单位承担",
                    "停工留薪期一般不超过12个月，经确认可延长",
                ],
                prerequisites=["已取得劳动能力鉴定结论"],
                estimated_days=30,
            ),
        ],
    },

    # =============================================
    # 3. 合同违约处理流程
    # =============================================
    "contract_breach": {
        "title": "合同违约处理流程向导",
        "description": "从发现乙方违约到最终解决的完整流程",
        "steps": [
            WizardStep(
                step_id=1, name="违约认定与证据固定",
                description="确认违约事实并固定关键证据",
                actions=[
                    "对照合同条款逐项确认违约行为",
                    "收集违约证据（合同、付款记录、沟通记录、验收报告等）",
                    "评估违约程度（根本违约 vs 一般违约）",
                    "计算已造成的损失金额",
                    "检查合同中的违约责任条款和争议解决方式",
                ],
                documents=["违约事实确认书", "证据清单", "损失计算明细"],
                legal_basis=[
                    "《民法典》第577条（违约责任）",
                    "《民法典》第584条（损失赔偿范围）",
                    "《民法典》第585条（违约金条款）",
                ],
                warnings=[
                    "注意检查合同有无免责条款或不可抗力条款",
                    "电子证据（微信/邮件）需注意保全，防止删除",
                ],
                estimated_days=3,
            ),
            WizardStep(
                step_id=2, name="发送催告/律师函",
                description="正式通知对方违约，要求限期整改或赔偿",
                actions=[
                    "起草催告函/律师函",
                    "明确要求对方在限定期限内的具体行为（继续履行/赔偿/解除合同）",
                    "通过EMS/公证邮寄送达（保留快递单号和签收回执）",
                    "设定合理期限（一般15-30天）",
                ],
                documents=["律师函/催告函", "EMS快递单", "公证送达记录（如需要）"],
                legal_basis=[
                    "《民法典》第563条第3款（催告后合理期限内仍不履行可解除合同）",
                    "《民法典》第565条（合同解除通知）",
                ],
                warnings=[
                    "律师函措辞要准确，避免给对方留下反诉把柄",
                    "务必保留送达证据（EMS签收单/公证）",
                ],
                prerequisites=["已完成违约认定和证据固定"],
                estimated_days=5,
            ),
            WizardStep(
                step_id=3, name="协商/调解",
                description="尝试通过协商或第三方调解解决争议",
                actions=[
                    "与对方进行正式协商谈判",
                    "记录协商过程和结果",
                    "如协商成功，签署补充协议/和解协议",
                    "如协商不成，考虑行业调解或人民调解",
                    "评估诉讼的成本收益（诉讼费+律师费+时间成本 vs 和解方案）",
                ],
                documents=["协商记录", "和解协议/补充协议（如协商成功）"],
                legal_basis=[
                    "《民法典》第233条（协商解决纠纷）",
                    "《人民调解法》（调解协议具有合同效力）",
                ],
                warnings=["和解协议也是合同，条款需严谨避免二次纠纷"],
                prerequisites=["已发送催告函且超过限定期限"],
                estimated_days=15,
            ),
            WizardStep(
                step_id=4, name="提起诉讼/仲裁",
                description="协商不成时，通过法律途径解决",
                actions=[
                    "确认管辖法院或仲裁机构（看合同约定）",
                    "准备起诉材料（起诉状、证据清单、授权委托书等）",
                    "计算诉讼请求金额（本金+违约金+损失+利息）",
                    "评估是否需要申请财产保全",
                    "缴纳诉讼费/仲裁费",
                    "如果紧急，先申请行为保全或财产保全",
                ],
                documents=[
                    "起诉状/仲裁申请书",
                    "证据清单及全部证据副本",
                    "授权委托书",
                    "财产保全申请书（如需要）",
                ],
                legal_basis=[
                    "《民事诉讼法》第122条（起诉条件）",
                    "《民事诉讼法》第103条（财产保全）",
                ],
                warnings=[
                    "注意诉讼时效（一般3年，从知道权利受侵害之日起算）",
                    "财产保全需提供等额担保",
                ],
                prerequisites=["协商/调解未成功"],
                estimated_days=180,
            ),
            WizardStep(
                step_id=5, name="执行与回款",
                description="判决生效后的执行和款项追回",
                actions=[
                    "判决生效后对方未履行的，申请强制执行",
                    "提供被执行人财产线索",
                    "配合法院执行措施（查封、扣押、冻结）",
                    "如对方无财产可供执行，申请纳入失信名单",
                ],
                documents=["强制执行申请书", "被执行人财产线索报告"],
                legal_basis=[
                    "《民事诉讼法》第249条（申请执行期限2年）",
                    "《最高法关于限制被执行人高消费的若干规定》",
                ],
                warnings=["申请执行期限为判决书生效后2年内，逾期丧失申请权"],
                prerequisites=["已取得生效判决/裁定/调解书"],
                estimated_days=90,
            ),
        ],
    },

    # =============================================
    # 4. 公司设立流程
    # =============================================
    "company_formation": {
        "title": "公司设立登记流程向导",
        "description": "从核名到拿照的完整创业设立流程",
        "steps": [
            WizardStep(
                step_id=1, name="企业核名",
                description="在市场监管局网上平台进行名称预核准",
                actions=[
                    "确定公司类型（有限责任公司 / 股份有限公司 / 个人独资 / 合伙）",
                    "准备3-5个备选名称",
                    "登录国家企业信用信息公示系统查询名称是否可用",
                    "在当地市场监管局网站提交名称预核准申请",
                ],
                documents=["名称预核准申请书"],
                legal_basis=["《公司法》第5条（公司名称）", "《企业名称登记管理规定》"],
                estimated_days=3,
            ),
            WizardStep(
                step_id=2, name="制定章程与协议",
                description="起草公司章程和股东协议",
                actions=[
                    "确定注册资本、出资方式、出资比例",
                    "确定股东会/董事会/监事会架构",
                    "起草公司章程（股东共同签署）",
                    "如有多个股东，建议签署股东协议（补充章程未覆盖的事项）",
                    "确定经营范围（参照《国民经济行业分类》）",
                ],
                documents=["公司章程", "股东协议（如需要）", "出资协议"],
                legal_basis=[
                    "《公司法》第25条（有限公司章程应当载明的事项）",
                    "《公司法》第26条（注册资本认缴制）",
                ],
                warnings=["章程是公司的'宪法'，务必重视表决权、分红权、退出机制等条款"],
                prerequisites=["已通过名称预核准"],
                estimated_days=3,
            ),
            WizardStep(
                step_id=3, name="设立登记",
                description="向市场监管局提交设立登记申请",
                actions=[
                    "准备全部登记材料",
                    "线上或线下提交设立登记申请",
                    "领取营业执照",
                ],
                documents=[
                    "设立登记申请书",
                    "公司章程",
                    "股东身份证明",
                    "住所使用证明（房产证/租赁合同）",
                    "法定代表人任职文件和身份证明",
                ],
                legal_basis=["《公司登记管理条例》第20-25条"],
                prerequisites=["已制定公司章程"],
                estimated_days=5,
            ),
            WizardStep(
                step_id=4, name="后续事项",
                description="领照后的必要手续",
                actions=[
                    "刻制公章、财务章、法人章、发票章",
                    "银行开立基本户",
                    "税务登记（国税+地税，现合并为税务局）",
                    "社保开户",
                    "公积金开户",
                    "特殊行业办理许可证（如需要）",
                ],
                documents=["印章备案证明", "银行开户许可证", "税务登记证"],
                legal_basis=[
                    "《税收征管法》第15条（30日内办理税务登记）",
                    "《社会保险法》第57条（30日内办理社保登记）",
                ],
                warnings=["营业执照领取后30日内必须办理税务登记，逾期有罚款风险"],
                prerequisites=["已领取营业执照"],
                estimated_days=10,
            ),
        ],
    },
}


class ProcedureWizardService:
    """流程向导服务"""

    def __init__(self) -> None:
        self._instances: dict[str, WizardInstance] = {}

    def get_available_wizards(self) -> list[dict[str, Any]]:
        """获取所有可用流程向导"""
        return [
            {
                "type": key,
                "title": defn["title"],
                "description": defn["description"],
                "total_steps": len(defn["steps"]),
                "total_days": sum(s.estimated_days for s in defn["steps"]),
            }
            for key, defn in WIZARD_DEFINITIONS.items()
        ]

    def start_wizard(self, wizard_type: str, context: dict[str, Any] | None = None) -> WizardInstance:
        """启动流程向导"""
        if wizard_type not in WIZARD_DEFINITIONS:
            raise ValueError(f"不支持的流程类型: {wizard_type}，可用: {list(WIZARD_DEFINITIONS.keys())}")

        defn = WIZARD_DEFINITIONS[wizard_type]
        import copy
        steps = copy.deepcopy(defn["steps"])
        steps[0].status = "current"

        instance = WizardInstance(
            wizard_id=str(uuid.uuid4())[:12] if 'uuid' in dir() else datetime.now().strftime("%y%m%d%H%M%S"),
            wizard_type=wizard_type,
            title=defn["title"],
            steps=steps,
            current_step=1,
            context=context or {},
        )
        self._instances[instance.wizard_id] = instance
        return instance

    def advance_step(self, wizard_id: str) -> WizardInstance:
        """推进到下一步"""
        instance = self._instances.get(wizard_id)
        if not instance:
            raise ValueError(f"向导实例不存在: {wizard_id}")

        if instance.current_step <= instance.total_steps:
            instance.steps[instance.current_step - 1].status = "done"

        instance.current_step += 1
        if instance.current_step <= instance.total_steps:
            instance.steps[instance.current_step - 1].status = "current"
        else:
            instance.status = "completed"

        return instance

    def get_current_step_guide(self, wizard_id: str) -> str:
        """获取当前步骤的 Markdown 指引"""
        instance = self._instances.get(wizard_id)
        if not instance:
            return "向导实例不存在"
        return instance.to_markdown()

    def get_instance(self, wizard_id: str) -> WizardInstance | None:
        return self._instances.get(wizard_id)

    def get_wizard_overview_markdown(self, wizard_type: str) -> str:
        """获取流程向导的全景概览（不启动实例）"""
        if wizard_type not in WIZARD_DEFINITIONS:
            return f"不支持的流程类型: {wizard_type}"

        defn = WIZARD_DEFINITIONS[wizard_type]
        lines = [
            f"## {defn['title']}",
            f"{defn['description']}\n",
            f"**总步骤**：{len(defn['steps'])} 步",
            f"**预估总耗时**：约 {sum(s.estimated_days for s in defn['steps'])} 个工作日\n",
            "### 流程概览\n",
        ]

        for step in defn["steps"]:
            lines.append(f"**第{step.step_id}步：{step.name}**（约{step.estimated_days}天）")
            lines.append(f"  {step.description}")
            if step.documents:
                docs = " / ".join(step.documents[:3])
                lines.append(f"  📄 文件：{docs}")
            lines.append("")

        return "\n".join(lines)


import uuid  # noqa: E402

# 全局实例
procedure_wizard_service = ProcedureWizardService()
