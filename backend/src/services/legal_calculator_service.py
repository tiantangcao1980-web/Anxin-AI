"""
法律计算器服务 — 精确法律数值计算

P0 能力：
1. 经济补偿金计算器（N/N+1/2N）
2. 诉讼费计算器（标的额→诉讼费）
3. 诉讼时效计算器（事由→时效期限→截止日期）
4. 加班费计算器（工作日/休息日/法定假日）
5. 工伤赔偿计算器（伤残等级→赔偿项目）

核心原则：
- 所有计算基于中国现行法律法规，精确到分
- 输出明确的法条依据
- 区分城市/地区差异（最低工资、社平工资）
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from loguru import logger

# ========== 2024-2025 年各主要城市最低工资标准（月，元） ==========
MINIMUM_WAGE: dict[str, int] = {
    "北京": 2420, "上海": 2690, "深圳": 2360, "广州": 2300,
    "杭州": 2280, "南京": 2280, "苏州": 2280, "成都": 2100,
    "武汉": 2010, "重庆": 2100, "天津": 2180, "西安": 2160,
    "长沙": 1930, "郑州": 2000, "青岛": 2100, "大连": 1980,
    "厦门": 2030, "福州": 2030, "合肥": 2060, "济南": 2100,
    "沈阳": 1910, "哈尔滨": 1860, "石家庄": 2200, "昆明": 1990,
    "南昌": 1850, "贵阳": 1890, "南宁": 1810, "兰州": 1820,
    "太原": 1980, "长春": 1880, "呼和浩特": 1980, "海口": 1830,
    "银川": 1900, "西宁": 1880, "乌鲁木齐": 1900, "拉萨": 1850,
    "默认": 2000,
}

# ========== 2023-2024 年各主要城市社平工资（月，元） ==========
AVERAGE_WAGE: dict[str, int] = {
    "北京": 13930, "上海": 13050, "深圳": 13730, "广州": 12100,
    "杭州": 11600, "南京": 11500, "苏州": 11200, "成都": 9500,
    "武汉": 9600, "重庆": 9100, "天津": 10200, "西安": 9200,
    "长沙": 9300, "郑州": 8800, "青岛": 9500, "大连": 9200,
    "厦门": 10500, "福州": 9800, "合肥": 9300, "济南": 9600,
    "默认": 10000,
}


@dataclass
class CalculationResult:
    """计算结果"""
    calculator_name: str
    total_amount: float
    breakdown: list[dict[str, Any]] = field(default_factory=list)
    legal_basis: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    raw_params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "calculator": self.calculator_name,
            "total_amount": round(self.total_amount, 2),
            "total_display": f"¥{self.total_amount:,.2f}",
            "breakdown": self.breakdown,
            "legal_basis": self.legal_basis,
            "warnings": self.warnings,
            "notes": self.notes,
        }

    def to_markdown(self) -> str:
        lines = [f"## {self.calculator_name}\n"]
        lines.append(f"**计算结果：¥{self.total_amount:,.2f}**\n")

        if self.breakdown:
            lines.append("### 明细")
            lines.append("| 项目 | 金额 | 说明 |")
            lines.append("|------|------|------|")
            for item in self.breakdown:
                amt = item.get("amount", 0)
                lines.append(f"| {item.get('item', '')} | ¥{amt:,.2f} | {item.get('note', '')} |")
            lines.append("")

        if self.legal_basis:
            lines.append("### 法律依据")
            for basis in self.legal_basis:
                lines.append(f"- {basis}")
            lines.append("")

        if self.warnings:
            lines.append("### ⚠️ 注意事项")
            for w in self.warnings:
                lines.append(f"- {w}")
            lines.append("")

        if self.notes:
            lines.append("### 补充说明")
            for n in self.notes:
                lines.append(f"- {n}")

        return "\n".join(lines)


class LegalCalculatorService:
    """法律计算器统一服务"""

    # ========== 1. 经济补偿金计算器 ==========

    def calc_severance(
        self,
        monthly_salary: float,
        work_years: float,
        termination_type: str = "N",
        city: str = "默认",
        is_illegal: bool = False,
    ) -> CalculationResult:
        """
        经济补偿金计算（N / N+1 / 2N）

        Args:
            monthly_salary: 离职前12个月平均工资
            work_years: 工作年限（年，支持小数如 2.5）
            termination_type: "N"=协商/经济性裁员, "N+1"=无过失辞退未提前通知, "2N"=违法辞退
            city: 城市（用于判断社平工资上限）
            is_illegal: 是否违法辞退（强制 2N）
        """
        if is_illegal:
            termination_type = "2N"

        avg_wage = AVERAGE_WAGE.get(city, AVERAGE_WAGE["默认"])
        salary_cap = avg_wage * 3  # 三倍社平封顶

        # 月工资封顶处理
        capped = False
        effective_salary = monthly_salary
        if monthly_salary > salary_cap:
            effective_salary = salary_cap
            capped = True

        # 计算 N（补偿月数）
        if work_years <= 0.5:
            n_months = 0.5
        else:
            # 每满一年支付一个月，不满半年按半个月，满半年不满一年按一个月
            full_years = int(work_years)
            remaining = work_years - full_years
            if remaining >= 0.5:
                n_months = full_years + 1
            else:
                n_months = full_years + 0.5

        # 高薪员工年限封顶12年
        year_cap_applied = False
        if capped and n_months > 12:
            n_months = 12
            year_cap_applied = True

        base_amount = effective_salary * n_months
        breakdown = []

        if termination_type == "N":
            total = base_amount
            breakdown.append({
                "item": f"经济补偿金 (N={n_months}个月)",
                "amount": total,
                "note": f"月工资 ¥{effective_salary:,.0f} × {n_months} 个月",
            })
        elif termination_type == "N+1":
            notice_pay = monthly_salary  # 代通知金按实际工资（不封顶）
            total = base_amount + notice_pay
            breakdown.append({
                "item": f"经济补偿金 (N={n_months}个月)",
                "amount": base_amount,
                "note": f"月工资 ¥{effective_salary:,.0f} × {n_months} 个月",
            })
            breakdown.append({
                "item": "代通知金 (+1个月)",
                "amount": notice_pay,
                "note": f"按实际月工资 ¥{monthly_salary:,.0f}（代通知金不受三倍封顶）",
            })
        elif termination_type == "2N":
            total = base_amount * 2
            breakdown.append({
                "item": f"赔偿金 (2N={n_months * 2}个月)",
                "amount": total,
                "note": f"月工资 ¥{effective_salary:,.0f} × {n_months} × 2",
            })
        else:
            total = base_amount
            breakdown.append({
                "item": f"经济补偿金 (N={n_months}个月)",
                "amount": total,
                "note": f"月工资 ¥{effective_salary:,.0f} × {n_months} 个月",
            })

        result = CalculationResult(
            calculator_name="经济补偿金计算器",
            total_amount=total,
            breakdown=breakdown,
            legal_basis=[
                "《劳动合同法》第四十七条：经济补偿按劳动者在本单位工作的年限，每满一年支付一个月工资的标准向劳动者支付",
                "《劳动合同法》第四十条：无过失性辞退未提前三十日书面通知的，额外支付一个月工资（N+1）",
                "《劳动合同法》第四十八条、第八十七条：违法解除/终止的，按经济补偿标准的二倍支付赔偿金（2N）",
                f"《劳动合同法》第四十七条第二款：月工资高于用人单位所在地区上年度职工月平均工资三倍的（{city}标准：¥{salary_cap:,.0f}/月），按三倍支付，年限最高不超过十二年",
            ],
        )

        if capped:
            result.warnings.append(
                f"月工资 ¥{monthly_salary:,.0f} 超过{city}社平工资三倍（¥{salary_cap:,.0f}），已按封顶标准计算"
            )
        if year_cap_applied:
            result.warnings.append("高薪员工补偿年限已封顶12年")

        result.notes.append("月工资是指劳动者在劳动合同解除或终止前十二个月的平均工资（含奖金、津贴等）")
        result.notes.append("经济补偿金无需缴纳个人所得税的部分：当地上年职工平均工资3倍以内的数额")

        return result

    # ========== 2. 诉讼费计算器 ==========

    def calc_litigation_cost(
        self,
        amount: float,
        case_type: str = "civil_property",
        is_simplified: bool = False,
        is_appeal: bool = False,
    ) -> CalculationResult:
        """
        诉讼费计算

        Args:
            amount: 标的额/诉讼请求金额（元）
            case_type: 案件类型
                - "civil_property": 财产案件（含合同纠纷、侵权纠纷等）
                - "labor": 劳动争议
                - "divorce": 离婚案件
                - "ip": 知识产权案件
                - "administrative": 行政案件
            is_simplified: 是否适用简易程序（减半）
            is_appeal: 是否二审（按一审标准收取）
        """
        breakdown: list[dict[str, Any]] = []
        fee: float
        legal_basis = [
            "《诉讼费用交纳办法》（国务院令第481号）"
        ]

        if case_type == "labor":
            # 劳动争议案件：每件10元
            fee = 10
            breakdown.append({"item": "劳动争议案件受理费", "amount": 10, "note": "每件10元"})
            legal_basis.append("《诉讼费用交纳办法》第十三条第（四）项：劳动争议案件每件交纳10元")

        elif case_type == "divorce":
            # 离婚案件：每件50-300元；涉及财产分割超20万的部分按0.5%
            fee = 300  # 取中间值
            breakdown.append({"item": "离婚案件受理费", "amount": 300, "note": "每件50-300元（取300元）"})
            if amount > 200000:
                extra = (amount - 200000) * 0.005
                fee += extra
                breakdown.append({
                    "item": "财产分割超20万部分",
                    "amount": extra,
                    "note": f"(¥{amount:,.0f} - ¥200,000) × 0.5%",
                })
            legal_basis.append("《诉讼费用交纳办法》第十三条第（二）项")

        elif case_type == "administrative":
            # 行政案件：50元/件（商标、专利100元）
            fee = 50
            breakdown.append({"item": "行政案件受理费", "amount": 50, "note": "每件50元"})

        else:
            # 财产案件（含合同纠纷、侵权、IP 等）：阶梯费率
            fee = self._calc_property_case_fee(amount)
            breakdown.append({
                "item": "财产案件受理费",
                "amount": fee,
                "note": f"标的额 ¥{amount:,.0f} 的阶梯费率",
            })
            legal_basis.append("《诉讼费用交纳办法》第十三条第（一）项：财产案件阶梯费率")

        # 简易程序减半
        if is_simplified:
            fee = fee / 2
            breakdown.append({"item": "简易程序减半", "amount": -fee, "note": "适用简易程序，受理费减半"})
            legal_basis.append("《诉讼费用交纳办法》第十六条：适用简易程序审理的案件减半交纳案件受理费")

        result = CalculationResult(
            calculator_name="诉讼费计算器",
            total_amount=fee,
            breakdown=breakdown,
            legal_basis=legal_basis,
        )

        result.notes.append("案件受理费由原告预交，判决后由败诉方承担")
        result.notes.append("当事人申请财产保全的，另交保全费（保全金额的1%，最低不少于100元）")
        if amount > 0:
            lawyer_estimate_low = max(5000, amount * 0.03)
            lawyer_estimate_high = max(10000, amount * 0.08)
            result.notes.append(
                f"律师费参考（非固定）：约 ¥{lawyer_estimate_low:,.0f} - ¥{lawyer_estimate_high:,.0f}（按标的3%-8%估算，具体以委托合同为准）"
            )

        if is_appeal:
            result.notes.append("二审案件按照一审案件标准交纳受理费")

        return result

    def _calc_property_case_fee(self, amount: float) -> float:
        """财产案件阶梯费率（《诉讼费用交纳办法》第十三条）"""
        if amount <= 0:
            return 50  # 最低50元
        elif amount <= 10000:
            return 50
        elif amount <= 100000:
            return (amount - 10000) * 0.025 + 50
        elif amount <= 200000:
            return (amount - 100000) * 0.02 + 2300
        elif amount <= 500000:
            return (amount - 200000) * 0.015 + 4300
        elif amount <= 1000000:
            return (amount - 500000) * 0.01 + 8800
        elif amount <= 2000000:
            return (amount - 1000000) * 0.009 + 13800
        elif amount <= 5000000:
            return (amount - 2000000) * 0.008 + 22800
        elif amount <= 10000000:
            return (amount - 5000000) * 0.007 + 46800
        elif amount <= 20000000:
            return (amount - 10000000) * 0.006 + 81800
        else:
            return (amount - 20000000) * 0.005 + 141800

    # ========== 3. 诉讼时效计算器 ==========

    def calc_statute_of_limitations(
        self,
        cause_of_action: str,
        trigger_date: str,
        is_interrupted: bool = False,
        interruption_date: str | None = None,
    ) -> CalculationResult:
        """
        诉讼时效计算

        Args:
            cause_of_action: 案由类型
                - "general": 一般民事纠纷（3年）
                - "labor_arbitration": 劳动仲裁（1年）
                - "personal_injury": 人身损害（3年，原1年已修改）
                - "product_liability": 产品质量（2年+最长不超10年）
                - "environmental": 环境侵权（3年）
                - "subrogation": 债权人撤销权（1年知道+5年绝对）
                - "defect_warranty": 瑕疵担保（验收后合理期间，最长2年）
                - "international_trade": 国际贸易（4年）
                - "insurance": 保险理赔（2年）
            trigger_date: 知道或应当知道权利被侵害的日期 (YYYY-MM-DD)
            is_interrupted: 是否发生中断
            interruption_date: 中断日期 (YYYY-MM-DD)
        """
        # 案由 → (时效年数, 法条依据)
        sol_map = {
            "general": (3, "《民法典》第一百八十八条：向人民法院请求保护民事权利的诉讼时效期间为三年"),
            "labor_arbitration": (1, "《劳动争议调解仲裁法》第二十七条：劳动争议申请仲裁的时效期间为一年"),
            "personal_injury": (3, "《民法典》第一百八十八条：人身损害赔偿诉讼时效为三年（原《民法通则》1年已废止）"),
            "product_liability": (2, "《民法典》第一百八十八条+第五百九十五条：产品质量诉讼时效2年"),
            "environmental": (3, "《民法典》第一百八十八条：环境侵权诉讼时效三年"),
            "subrogation": (1, "《民法典》第五百四十一条：债权人撤销权自知道之日起一年内行使"),
            "international_trade": (4, "《民法典》第五百九十四条：国际货物买卖合同和技术进出口合同诉讼时效为四年"),
            "insurance": (2, "《保险法》第二十六条：人寿保险5年，其他保险2年"),
        }

        years, basis = sol_map.get(cause_of_action, sol_map["general"])

        try:
            trigger = datetime.strptime(trigger_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return CalculationResult(
                calculator_name="诉讼时效计算器",
                total_amount=0,
                warnings=["日期格式错误，请使用 YYYY-MM-DD 格式"],
            )

        # 计算到期日
        if is_interrupted and interruption_date:
            try:
                interrupt = datetime.strptime(interruption_date, "%Y-%m-%d").date()
                # 中断后时效重新计算
                deadline = date(interrupt.year + years, interrupt.month, interrupt.day)
                trigger = interrupt
            except (ValueError, TypeError):
                deadline = date(trigger.year + years, trigger.month, trigger.day)
        else:
            try:
                deadline = date(trigger.year + years, trigger.month, trigger.day)
            except ValueError:
                # 处理2月29日等特殊情况
                deadline = date(trigger.year + years, trigger.month, 28)

        today = date.today()
        remaining_days = (deadline - today).days

        expired = remaining_days < 0
        urgent = 0 < remaining_days <= 90

        result = CalculationResult(
            calculator_name="诉讼时效计算器",
            total_amount=remaining_days if remaining_days > 0 else 0,
            breakdown=[
                {"item": "时效期间", "amount": years, "note": f"{years}年"},
                {"item": "起算日期", "amount": 0, "note": str(trigger)},
                {"item": "届满日期", "amount": 0, "note": str(deadline)},
                {"item": "剩余天数", "amount": remaining_days, "note": f"{'已过期' if expired else f'{remaining_days}天'}"},
            ],
            legal_basis=[
                basis,
                "《民法典》第一百九十五条：诉讼时效中断事由：权利人提起诉讼、申请仲裁、提出请求、义务人同意履行等",
                "《民法典》第一百九十二条：诉讼时效期间届满，义务人可以提出不履行的抗辩（丧失胜诉权，实体权利不消灭）",
            ],
        )

        if expired:
            result.warnings.append(f"⚠️ 诉讼时效已于 {deadline} 届满（超期 {abs(remaining_days)} 天），可能丧失胜诉权")
            result.warnings.append("但如果义务人同意履行，法院仍予支持；或可寻找中断/中止事由")
        elif urgent:
            result.warnings.append(f"⚠️ 诉讼时效将于 {deadline} 届满（仅剩 {remaining_days} 天），请尽快采取法律行动")
            result.warnings.append("建议：立即发送催告函（保留证据）或提起诉讼/仲裁以中断时效")

        if is_interrupted:
            result.notes.append(f"时效已发生中断（中断日期：{interruption_date}），从中断事由消除之日起重新计算")

        result.notes.append("最长保护期：自权利受到损害之日起超过20年的，法院不予保护（特殊情况可申请延长）")

        return result

    # ========== 4. 加班费计算器 ==========

    def calc_overtime_pay(
        self,
        monthly_salary: float,
        overtime_hours_workday: float = 0,
        overtime_hours_weekend: float = 0,
        overtime_hours_holiday: float = 0,
        monthly_work_days: float = 21.75,
        daily_work_hours: float = 8,
    ) -> CalculationResult:
        """
        加班费计算

        Args:
            monthly_salary: 月工资
            overtime_hours_workday: 工作日加班小时数
            overtime_hours_weekend: 休息日加班小时数（未安排补休）
            overtime_hours_holiday: 法定假日加班小时数
            monthly_work_days: 月计薪天数（默认21.75）
            daily_work_hours: 日标准工时（默认8小时）
        """
        hourly_wage = monthly_salary / monthly_work_days / daily_work_hours

        # 150% 工作日加班
        workday_pay = hourly_wage * 1.5 * overtime_hours_workday
        # 200% 休息日加班
        weekend_pay = hourly_wage * 2.0 * overtime_hours_weekend
        # 300% 法定假日加班
        holiday_pay = hourly_wage * 3.0 * overtime_hours_holiday

        total = workday_pay + weekend_pay + holiday_pay

        return CalculationResult(
            calculator_name="加班费计算器",
            total_amount=total,
            breakdown=[
                {
                    "item": f"工作日加班 ({overtime_hours_workday}小时 × 150%)",
                    "amount": workday_pay,
                    "note": f"¥{hourly_wage:.2f}/时 × 1.5 × {overtime_hours_workday}h",
                },
                {
                    "item": f"休息日加班 ({overtime_hours_weekend}小时 × 200%)",
                    "amount": weekend_pay,
                    "note": f"¥{hourly_wage:.2f}/时 × 2.0 × {overtime_hours_weekend}h",
                },
                {
                    "item": f"法定假日加班 ({overtime_hours_holiday}小时 × 300%)",
                    "amount": holiday_pay,
                    "note": f"¥{hourly_wage:.2f}/时 × 3.0 × {overtime_hours_holiday}h",
                },
            ],
            legal_basis=[
                "《劳动法》第四十四条：工作日加班150%、休息日加班200%（未补休）、法定假日加班300%",
                f"月计薪天数 = (365-104) / 12 = 21.75天，小时工资 = ¥{monthly_salary:,.0f} / 21.75 / 8 = ¥{hourly_wage:.2f}",
            ],
            notes=[
                "休息日加班优先安排补休，无法补休的按200%支付",
                "法定假日加班不能用补休替代，必须支付300%加班费",
            ],
        )

    # ========== 5. 工伤赔偿计算器 ==========

    def calc_work_injury(
        self,
        disability_level: int,
        monthly_salary: float,
        city: str = "默认",
        age: int | None = None,
    ) -> CalculationResult:
        """
        工伤赔偿计算（一次性伤残补助金 + 一次性工伤医疗补助金 + 一次性伤残就业补助金）

        Args:
            disability_level: 伤残等级 (1-10)
            monthly_salary: 本人工资（受伤前12个月平均）
            city: 城市
            age: 年龄（影响部分地区补助金标准）
        """
        avg_wage = AVERAGE_WAGE.get(city, AVERAGE_WAGE["默认"])

        # 一次性伤残补助金标准（月工资×月数）
        disability_months = {
            1: 27, 2: 25, 3: 23, 4: 21,
            5: 18, 6: 16, 7: 13, 8: 11, 9: 9, 10: 7,
        }

        if disability_level not in disability_months:
            return CalculationResult(
                calculator_name="工伤赔偿计算器",
                total_amount=0,
                warnings=["伤残等级应为1-10级"],
            )

        months = disability_months[disability_level]
        lump_sum = monthly_salary * months

        breakdown = [{
            "item": f"{disability_level}级伤残补助金",
            "amount": lump_sum,
            "note": f"本人工资 ¥{monthly_salary:,.0f} × {months} 个月",
        }]

        # 5-10级解除/终止合同时的一次性医疗补助金和就业补助金
        # 这些标准各省不同，这里给出通用参考
        if disability_level >= 5:
            # 参考值：医疗补助金和就业补助金各为社平工资的若干月
            medical_months = {5: 18, 6: 15, 7: 12, 8: 9, 9: 6, 10: 3}
            employ_months = {5: 18, 6: 15, 7: 12, 8: 9, 9: 6, 10: 3}

            med_months = medical_months.get(disability_level, 6)
            emp_months = employ_months.get(disability_level, 6)
            med_amount = avg_wage * med_months
            emp_amount = avg_wage * emp_months

            breakdown.append({
                "item": "一次性工伤医疗补助金（参考值）",
                "amount": med_amount,
                "note": f"社平工资 ¥{avg_wage:,.0f} × {med_months} 个月（各省标准不同）",
            })
            breakdown.append({
                "item": "一次性伤残就业补助金（参考值）",
                "amount": emp_amount,
                "note": f"社平工资 ¥{avg_wage:,.0f} × {emp_months} 个月（各省标准不同）",
            })
            total = lump_sum + med_amount + emp_amount
        else:
            total = lump_sum

        result = CalculationResult(
            calculator_name="工伤赔偿计算器",
            total_amount=total,
            breakdown=breakdown,
            legal_basis=[
                "《工伤保险条例》第三十五至三十七条：伤残补助金标准",
                "一次性工伤医疗补助金和就业补助金：各省、自治区、直辖市人民政府规定",
            ],
        )

        if disability_level <= 4:
            result.notes.append(f"{disability_level}级伤残保留劳动关系，按月领取伤残津贴（{[90, 85, 80, 75][disability_level-1]}%工资）")
        else:
            result.notes.append("5-10级伤残解除/终止劳动合同时，由工伤保险基金支付医疗补助金，由用人单位支付就业补助金")
            result.notes.append("⚠️ 医疗/就业补助金标准各省差异大，以上为参考值，请查阅当地规定")

        result.notes.append("另外可主张的项目：医疗费（实报实销）、停工留薪期工资、护理费、交通食宿费等")

        return result

    # ========== 统一入口 ==========

    def calculate(self, calc_type: str, params: dict[str, Any]) -> CalculationResult:
        """
        统一计算入口

        Args:
            calc_type: 计算器类型
            params: 计算参数（dict）
        """
        dispatch: dict[str, Callable[..., CalculationResult]] = {
            "severance": self.calc_severance,
            "litigation_cost": self.calc_litigation_cost,
            "statute_of_limitations": self.calc_statute_of_limitations,
            "overtime_pay": self.calc_overtime_pay,
            "work_injury": self.calc_work_injury,
        }

        if calc_type not in dispatch:
            return CalculationResult(
                calculator_name="未知计算器",
                total_amount=0,
                warnings=[f"不支持的计算器类型: {calc_type}，可用类型: {', '.join(dispatch.keys())}"],
            )

        try:
            return dispatch[calc_type](**params)
        except TypeError as e:
            return CalculationResult(
                calculator_name=calc_type,
                total_amount=0,
                warnings=[f"参数错误: {e}"],
            )
        except Exception as e:
            logger.error(f"计算器 {calc_type} 执行失败: {e}")
            return CalculationResult(
                calculator_name=calc_type,
                total_amount=0,
                warnings=[f"计算失败: {e}"],
            )


# 全局实例
legal_calculator_service = LegalCalculatorService()
