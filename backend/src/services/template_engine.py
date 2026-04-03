# -*- coding: utf-8 -*-
"""
智能条件合同模板引擎

核心功能：
1. 条件分支渲染（根据用户输入动态生成条款）
2. 变量插值（自动填充合同要素）
3. 地区司法差异适配
4. 行业惯例自动适用
"""

import re
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class FieldType(str, Enum):
    """模板字段类型"""
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    SELECT = "select"
    MULTISELECT = "multiselect"
    BOOLEAN = "boolean"
    TEXTAREA = "textarea"
    MONEY = "money"         # 金额（自动生成大写）
    PARTY = "party"         # 当事方信息（名称+代码+代表人+地址+联系方式）
    PERCENTAGE = "percentage"


@dataclass
class TemplateField:
    """模板字段定义"""
    key: str                        # 字段标识符
    label: str                      # 显示标签
    field_type: FieldType           # 字段类型
    required: bool = True           # 是否必填
    default: Any = None             # 默认值
    placeholder: str = ""           # 占位提示
    options: List[Dict[str, str]] = field(default_factory=list)  # 选项（select/multiselect）
    validation: Optional[str] = None  # 验证规则
    group: str = "基本信息"          # 分组
    help_text: str = ""             # 帮助文本
    condition: Optional[str] = None  # 条件表达式（仅当条件满足时显示）


@dataclass
class ConditionalClause:
    """条件条款"""
    id: str                         # 条款标识
    title: str                      # 条款标题
    content: str                    # 条款内容模板（支持变量插值）
    condition: Optional[str] = None  # 条件表达式
    required: bool = True           # 是否必选
    order: int = 0                  # 排序


@dataclass
class ContractTemplate:
    """合同模板定义"""
    id: str
    name: str                       # 模板名称
    category: str                   # 分类（买卖/租赁/劳动/服务等）
    description: str                # 描述
    fields: List[TemplateField]     # 可填字段
    clauses: List[ConditionalClause]  # 条件条款
    version: str = "1.0"
    applicable_regions: List[str] = field(default_factory=lambda: ["全国"])


# ==================== 数字转大写 ====================

def number_to_chinese(num: float) -> str:
    """将阿拉伯数字金额转换为大写中文"""
    digits = "零壹贰叁肆伍陆柒捌玖"
    units = ["", "拾", "佰", "仟"]
    big_units = ["", "万", "亿", "万亿"]

    if num == 0:
        return "零元整"

    # 分离整数和小数部分
    integer_part = int(num)
    decimal_part = round((num - integer_part) * 100)

    result = ""

    if integer_part > 0:
        str_int = str(integer_part)
        length = len(str_int)
        groups = []

        # 按4位分组
        while str_int:
            groups.insert(0, str_int[-4:])
            str_int = str_int[:-4]

        for gi, group in enumerate(groups):
            group_str = ""
            has_zero = False
            for di, d in enumerate(group):
                n = int(d)
                pos = len(group) - 1 - di
                if n == 0:
                    has_zero = True
                else:
                    if has_zero:
                        group_str += "零"
                        has_zero = False
                    group_str += digits[n] + units[pos]

            if group_str:
                big_idx = len(groups) - 1 - gi
                result += group_str + big_units[min(big_idx, len(big_units) - 1)]

        result += "元"
    else:
        result = "零元"

    if decimal_part > 0:
        jiao = decimal_part // 10
        fen = decimal_part % 10
        if jiao > 0:
            result += digits[jiao] + "角"
        if fen > 0:
            result += digits[fen] + "分"
    else:
        result += "整"

    return result


# ==================== 模板渲染引擎 ====================

class TemplateEngine:
    """合同模板渲染引擎"""

    @classmethod
    def evaluate_condition(cls, condition: str, variables: Dict[str, Any]) -> bool:
        """
        评估条件表达式

        支持的表达式：
        - "has_ip == true"  (布尔判断)
        - "amount > 100000" (数值比较)
        - "contract_type == '技术开发'" (字符串相等)
        - "region in ['北京','上海']"  (包含判断)
        """
        if not condition:
            return True

        try:
            # 简单安全的条件评估（不使用eval）
            condition = condition.strip()

            # Boolean check: "field == true/false"
            bool_match = re.match(r'^(\w+)\s*==\s*(true|false)$', condition, re.IGNORECASE)
            if bool_match:
                field_name = bool_match.group(1)
                expected = bool_match.group(2).lower() == "true"
                return bool(variables.get(field_name)) == expected

            # Numeric comparison: "field > 100000"
            num_match = re.match(r'^(\w+)\s*([><=!]+)\s*([\d.]+)$', condition)
            if num_match:
                field_name = num_match.group(1)
                operator = num_match.group(2)
                threshold = float(num_match.group(3))
                value = float(variables.get(field_name, 0))

                if operator == ">":
                    return value > threshold
                elif operator == ">=":
                    return value >= threshold
                elif operator == "<":
                    return value < threshold
                elif operator == "<=":
                    return value <= threshold
                elif operator in ("==", "="):
                    return value == threshold
                elif operator == "!=":
                    return value != threshold

            # String equality: "field == 'value'"
            str_match = re.match(r"^(\w+)\s*==\s*'([^']*)'$", condition)
            if str_match:
                field_name = str_match.group(1)
                expected = str_match.group(2)
                return str(variables.get(field_name, "")) == expected

            # In check: "field in ['a','b','c']"
            in_match = re.match(r"^(\w+)\s+in\s+\[([^\]]+)\]$", condition)
            if in_match:
                field_name = in_match.group(1)
                items = [s.strip().strip("'\"") for s in in_match.group(2).split(",")]
                return str(variables.get(field_name, "")) in items

            # Not empty check: "field"
            if re.match(r'^\w+$', condition):
                return bool(variables.get(condition))

            logger.warning(f"无法解析的条件表达式: {condition}")
            return True

        except Exception as e:
            logger.warning(f"条件表达式评估失败: {condition}, 错误: {e}")
            return True

    @classmethod
    def render_template(
        cls,
        template: ContractTemplate,
        variables: Dict[str, Any],
    ) -> str:
        """
        渲染合同模板

        1. 评估每个条款的条件
        2. 对满足条件的条款进行变量插值
        3. 组装为完整合同文本
        """
        output_parts = []

        # 渲染标题区
        title = cls._interpolate(template.name, variables)
        output_parts.append(f"# {title}\n")

        # 渲染合同编号
        output_parts.append(f"合同编号：【    】\n")

        # 渲染当事方信息
        party_a = variables.get("party_a", {})
        party_b = variables.get("party_b", {})
        if isinstance(party_a, dict):
            output_parts.append(cls._render_party("甲方", party_a))
        if isinstance(party_b, dict):
            output_parts.append(cls._render_party("乙方", party_b))

        output_parts.append("")

        # 渲染条款
        clause_num = 0
        sorted_clauses = sorted(template.clauses, key=lambda c: c.order)

        for clause in sorted_clauses:
            # 评估条件
            if clause.condition and not cls.evaluate_condition(clause.condition, variables):
                continue

            clause_num += 1
            rendered_content = cls._interpolate(clause.content, variables)
            rendered_title = cls._interpolate(clause.title, variables)

            output_parts.append(f"## 第{cls._num_to_chinese(clause_num)}条 {rendered_title}\n")
            output_parts.append(f"{rendered_content}\n")

        # 签署区
        output_parts.append("\n（以下无正文）\n")
        output_parts.append("**甲方（盖章）：**                    **乙方（盖章）：**\n")
        output_parts.append("法定代表人/授权代表：              法定代表人/授权代表：\n")
        output_parts.append("签字：                            签字：\n")
        output_parts.append("日期：    年    月    日           日期：    年    月    日\n")

        return "\n".join(output_parts)

    @classmethod
    def _interpolate(cls, text: str, variables: Dict[str, Any]) -> str:
        """变量插值：将 {{variable}} 替换为实际值"""
        def replace_var(match):
            var_name = match.group(1).strip()

            # 支持管道符格式化：{{amount|money}}
            if "|" in var_name:
                var_name, fmt = var_name.split("|", 1)
                var_name = var_name.strip()
                fmt = fmt.strip()
                value = variables.get(var_name, f"【{var_name}】")

                if fmt == "money" and isinstance(value, (int, float)):
                    return f"人民币{value:,.2f}元（大写：{number_to_chinese(value)}）"
                elif fmt == "date":
                    return str(value) if value else "【    年    月    日】"
                elif fmt == "percentage":
                    return f"{value}%"

            value = variables.get(var_name)
            if value is None:
                return f"【{var_name}】"
            return str(value)

        return re.sub(r'\{\{([^}]+)\}\}', replace_var, text)

    @classmethod
    def _render_party(cls, role: str, info: Dict[str, Any]) -> str:
        """渲染当事方信息"""
        name = info.get("name", f"【{role}全称】")
        code = info.get("code", "【    】")
        rep = info.get("representative", "【    】")
        address = info.get("address", "【    】")
        contact = info.get("contact", "【    】")

        return (
            f"**{role}（全称）：** {name}\n"
            f"统一社会信用代码/身份证号：{code}\n"
            f"法定代表人：{rep}\n"
            f"住所/地址：{address}\n"
            f"联系方式：{contact}\n"
        )

    @staticmethod
    def _num_to_chinese(num: int) -> str:
        """数字转中文（1-30）"""
        chinese_nums = [
            "", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
            "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
            "二十一", "二十二", "二十三", "二十四", "二十五", "二十六", "二十七", "二十八", "二十九", "三十",
        ]
        if 0 < num < len(chinese_nums):
            return chinese_nums[num]
        return str(num)

    @classmethod
    def get_applicable_fields(
        cls,
        template: ContractTemplate,
        current_variables: Dict[str, Any],
    ) -> List[TemplateField]:
        """
        获取当前需要展示的字段列表
        （根据已填写的变量值，动态显示/隐藏条件字段）
        """
        result = []
        for f in template.fields:
            if f.condition:
                if cls.evaluate_condition(f.condition, current_variables):
                    result.append(f)
            else:
                result.append(f)
        return result


# ==================== 预置模板库 ====================

def get_builtin_templates() -> List[ContractTemplate]:
    """获取预置合同模板库"""
    templates = []

    # ===== 1. 买卖合同 =====
    templates.append(ContractTemplate(
        id="sale_purchase",
        name="{{goods_name}}买卖合同",
        category="买卖合同",
        description="适用于货物买卖交易，涵盖标的物、价款、交付、验收、违约责任等核心条款",
        fields=[
            TemplateField(key="goods_name", label="商品/货物名称", field_type=FieldType.TEXT, group="标的信息"),
            TemplateField(key="goods_spec", label="规格型号", field_type=FieldType.TEXT, group="标的信息"),
            TemplateField(key="quantity", label="数量", field_type=FieldType.NUMBER, group="标的信息"),
            TemplateField(key="unit", label="单位", field_type=FieldType.TEXT, default="件", group="标的信息"),
            TemplateField(key="unit_price", label="单价(元)", field_type=FieldType.MONEY, group="价款"),
            TemplateField(key="total_amount", label="总金额(元)", field_type=FieldType.MONEY, group="价款"),
            TemplateField(key="payment_method", label="付款方式", field_type=FieldType.SELECT, group="价款",
                          options=[{"value": "full", "label": "一次性付清"}, {"value": "installment", "label": "分期付款"}, {"value": "advance", "label": "预付款+尾款"}]),
            TemplateField(key="installment_count", label="分期期数", field_type=FieldType.NUMBER, group="价款",
                          condition="payment_method == 'installment'"),
            TemplateField(key="advance_ratio", label="预付款比例(%)", field_type=FieldType.PERCENTAGE, group="价款",
                          condition="payment_method == 'advance'", default=30),
            TemplateField(key="delivery_date", label="交货日期", field_type=FieldType.DATE, group="交付"),
            TemplateField(key="delivery_place", label="交货地点", field_type=FieldType.TEXT, group="交付"),
            TemplateField(key="warranty_period", label="质保期(月)", field_type=FieldType.NUMBER, default=12, group="售后"),
            TemplateField(key="has_ip_clause", label="是否涉及知识产权", field_type=FieldType.BOOLEAN, default=False, group="特别条款"),
            TemplateField(key="dispute_method", label="争议解决方式", field_type=FieldType.SELECT, group="争议解决",
                          options=[{"value": "court", "label": "诉讼"}, {"value": "arbitration", "label": "仲裁"}]),
            TemplateField(key="court_name", label="管辖法院", field_type=FieldType.TEXT, group="争议解决",
                          condition="dispute_method == 'court'"),
            TemplateField(key="arbitration_name", label="仲裁机构", field_type=FieldType.TEXT, group="争议解决",
                          condition="dispute_method == 'arbitration'"),
        ],
        clauses=[
            ConditionalClause(
                id="definition", title="定义与解释", order=1,
                content="1.1 \"标的物\"是指本合同约定的{{goods_name}}，规格型号为{{goods_spec}}。\n\n1.2 本合同中的标题仅为方便阅读之目的，不影响本合同的解释。",
            ),
            ConditionalClause(
                id="subject", title="合同标的", order=2,
                content="2.1 甲方向乙方购买{{goods_name}}，规格型号：{{goods_spec}}。\n\n2.2 数量：{{quantity}}{{unit}}。\n\n2.3 质量标准：符合国家标准及行业标准，具体以双方确认的技术规格书为准。",
            ),
            ConditionalClause(
                id="price_full", title="合同价款及支付", order=3,
                condition="payment_method == 'full'",
                content="3.1 合同总价款为{{total_amount|money}}。\n\n3.2 乙方应在收到甲方交付的标的物并验收合格后【  】个工作日内一次性付清全部货款。\n\n3.3 付款方式：银行转账。",
            ),
            ConditionalClause(
                id="price_installment", title="合同价款及支付", order=3,
                condition="payment_method == 'installment'",
                content="3.1 合同总价款为{{total_amount|money}}。\n\n3.2 付款方式：分{{installment_count}}期支付，每期支付金额为总价款的{{installment_count}}分之一。\n\n3.3 首期款项在合同签订后【  】个工作日内支付，后续款项每【  】支付一期。",
            ),
            ConditionalClause(
                id="price_advance", title="合同价款及支付", order=3,
                condition="payment_method == 'advance'",
                content="3.1 合同总价款为{{total_amount|money}}。\n\n3.2 预付款：乙方应在合同签订后【  】个工作日内支付合同总价款的{{advance_ratio}}%作为预付款。\n\n3.3 尾款：剩余款项在标的物验收合格后【  】个工作日内付清。",
            ),
            ConditionalClause(
                id="delivery", title="交付与验收", order=4,
                content="4.1 交货日期：{{delivery_date|date}}。\n\n4.2 交货地点：{{delivery_place}}。\n\n4.3 验收标准：乙方应在收到标的物后【7】个工作日内完成验收。验收合格的，乙方应出具验收确认书；验收不合格的，乙方应在【3】个工作日内书面通知甲方，说明不合格原因。",
            ),
            ConditionalClause(
                id="warranty", title="质量保证", order=5,
                content="5.1 质保期：自标的物验收合格之日起{{warranty_period}}个月。\n\n5.2 质保期内，因标的物本身质量问题导致的故障或损坏，甲方应免费维修或更换。\n\n5.3 因乙方使用不当造成的损坏不在质保范围内。",
            ),
            ConditionalClause(
                id="ip", title="知识产权", order=6,
                condition="has_ip_clause == true",
                content="6.1 标的物涉及的知识产权归属甲方所有。\n\n6.2 甲方保证其交付的标的物不侵犯任何第三方的知识产权。如因此发生纠纷，甲方应承担全部责任。\n\n6.3 乙方不得对标的物进行反向工程、反编译或其他形式的技术分析。",
            ),
            ConditionalClause(
                id="confidentiality", title="保密条款", order=7,
                content="7.1 双方在合同履行过程中知悉的对方商业秘密和保密信息，应当严格保密。\n\n7.2 保密期限：自本合同签订之日起至合同终止后【2】年止。\n\n7.3 违反保密义务的一方应赔偿对方因此遭受的全部损失。",
            ),
            ConditionalClause(
                id="breach", title="违约责任", order=8,
                content="8.1 甲方违约：\n（1）甲方逾期交货的，每逾期一日，应按合同总价款的0.5‰向乙方支付违约金。\n（2）甲方交付的标的物不符合质量要求的，乙方有权要求退换货或减少价款。\n\n8.2 乙方违约：\n（1）乙方逾期付款的，每逾期一日，应按逾期金额的0.5‰向甲方支付违约金。\n（2）乙方无正当理由拒绝验收的，视为验收合格。\n\n8.3 违约金不足以弥补实际损失的，违约方还应赔偿差额部分，但赔偿总额不超过合同总价款的30%。",
            ),
            ConditionalClause(
                id="termination", title="合同的变更和解除", order=9,
                content="9.1 经双方协商一致，可以变更或解除本合同。变更或解除合同应采用书面形式。\n\n9.2 有下列情形之一的，一方可以书面通知另一方解除本合同：\n（1）因不可抗力致使合同目的不能实现的；\n（2）一方迟延履行主要义务，经催告后在合理期限内仍未履行的；\n（3）一方明确表示或以自己的行为表明不履行主要义务的。",
            ),
            ConditionalClause(
                id="force_majeure", title="不可抗力", order=10,
                content="10.1 不可抗力是指不能预见、不能避免且不能克服的客观情况。\n\n10.2 因不可抗力不能履行合同的，根据不可抗力的影响，部分或全部免除责任。\n\n10.3 遭受不可抗力的一方应在事件发生后【15】日内书面通知对方，并在【30】日内提供相关证明文件。",
            ),
            ConditionalClause(
                id="dispute_court", title="争议解决", order=11,
                condition="dispute_method == 'court'",
                content="11.1 因本合同引起的或与本合同有关的任何争议，双方应首先通过友好协商解决。\n\n11.2 协商不成的，任何一方均有权向{{court_name}}人民法院提起诉讼。",
            ),
            ConditionalClause(
                id="dispute_arbitration", title="争议解决", order=11,
                condition="dispute_method == 'arbitration'",
                content="11.1 因本合同引起的或与本合同有关的任何争议，双方应首先通过友好协商解决。\n\n11.2 协商不成的，提交{{arbitration_name}}按其仲裁规则进行仲裁。仲裁裁决是终局的，对双方均有约束力。",
            ),
            ConditionalClause(
                id="general", title="附则", order=12,
                content="12.1 本合同自双方签字（盖章）之日起生效。\n\n12.2 本合同一式【  】份，甲方持【  】份，乙方持【  】份，具有同等法律效力。\n\n12.3 本合同的附件为本合同不可分割的组成部分，与本合同具有同等法律效力。\n\n12.4 本合同未尽事宜，双方可另行签订补充协议。",
            ),
        ],
    ))

    # ===== 2. 房屋租赁合同 =====
    templates.append(ContractTemplate(
        id="house_lease",
        name="房屋租赁合同",
        category="租赁合同",
        description="适用于住宅或商业房屋租赁，涵盖租金、押金、装修、优先续租权等条款",
        fields=[
            TemplateField(key="property_address", label="房屋地址", field_type=FieldType.TEXT, group="房屋信息"),
            TemplateField(key="property_area", label="建筑面积(平方米)", field_type=FieldType.NUMBER, group="房屋信息"),
            TemplateField(key="property_use", label="房屋用途", field_type=FieldType.SELECT, group="房屋信息",
                          options=[{"value": "residential", "label": "居住"}, {"value": "commercial", "label": "商业办公"}, {"value": "mixed", "label": "商住两用"}]),
            TemplateField(key="monthly_rent", label="月租金(元)", field_type=FieldType.MONEY, group="租金"),
            TemplateField(key="deposit_months", label="押金(月数)", field_type=FieldType.NUMBER, default=2, group="租金"),
            TemplateField(key="payment_cycle", label="付款周期", field_type=FieldType.SELECT, group="租金",
                          options=[{"value": "monthly", "label": "月付"}, {"value": "quarterly", "label": "季付"}, {"value": "yearly", "label": "年付"}]),
            TemplateField(key="lease_start", label="租赁起始日", field_type=FieldType.DATE, group="期限"),
            TemplateField(key="lease_end", label="租赁终止日", field_type=FieldType.DATE, group="期限"),
            TemplateField(key="allow_sublease", label="是否允许转租", field_type=FieldType.BOOLEAN, default=False, group="特别条款"),
            TemplateField(key="allow_decoration", label="是否允许装修改造", field_type=FieldType.BOOLEAN, default=False, group="特别条款"),
            TemplateField(key="has_furniture", label="是否含家具家电", field_type=FieldType.BOOLEAN, default=False, group="特别条款",
                          condition="property_use == 'residential'"),
        ],
        clauses=[
            ConditionalClause(id="subject", title="租赁房屋", order=1,
                content="1.1 甲方将位于{{property_address}}的房屋出租给乙方使用。\n\n1.2 建筑面积：{{property_area}}平方米。\n\n1.3 房屋用途：仅限于{{property_use}}用途，未经甲方书面同意，乙方不得擅自改变房屋用途。"),
            ConditionalClause(id="term", title="租赁期限", order=2,
                content="2.1 租赁期限自{{lease_start|date}}起至{{lease_end|date}}止。\n\n2.2 租赁期满，乙方如需续租，应在租赁期满前【30】日书面通知甲方，经甲方同意后双方另行签订租赁合同。\n\n2.3 在同等条件下，乙方享有优先续租权（依据民法典第734条）。"),
            ConditionalClause(id="rent", title="租金及支付", order=3,
                content="3.1 月租金为{{monthly_rent|money}}。\n\n3.2 押金为【{{deposit_months}}】个月租金。\n\n3.3 付款方式：{{payment_cycle}}，乙方应在每期首日前【5】个工作日内支付。\n\n3.4 甲方收取押金后应向乙方出具收据。租赁期满且乙方无违约行为的，甲方应在交还房屋后【15】日内退还押金。"),
            ConditionalClause(id="sublease", title="转租", order=4,
                condition="allow_sublease == true",
                content="4.1 经甲方书面同意，乙方可以将租赁房屋的部分或全部转租给第三人。\n\n4.2 转租期限不得超过原租赁合同的剩余期限。\n\n4.3 乙方转租的，原租赁合同继续有效。"),
            ConditionalClause(id="no_sublease", title="转租限制", order=4,
                condition="allow_sublease == false",
                content="4.1 未经甲方书面同意，乙方不得将租赁房屋的部分或全部转租给第三人。\n\n4.2 乙方擅自转租的，甲方有权解除本合同并要求乙方承担违约责任。"),
            ConditionalClause(id="decoration", title="装修改造", order=5,
                condition="allow_decoration == true",
                content="5.1 经甲方书面同意，乙方可以对租赁房屋进行装修改造。\n\n5.2 装修方案须经甲方书面确认，不得影响房屋结构安全。\n\n5.3 租赁期满或合同解除时，可拆除的装修由乙方自行拆除恢复原状；不可拆除的装修归甲方所有，双方可协商补偿。"),
            ConditionalClause(id="maintenance", title="房屋维修", order=6,
                content="6.1 甲方负责房屋主体结构和公共设施的维修。\n\n6.2 乙方负责因使用不当造成的房屋及设施损坏的维修费用。\n\n6.3 甲方应在接到乙方维修通知后【7】日内进行维修，逾期不维修的，乙方可自行维修，费用由甲方承担。"),
            ConditionalClause(id="breach", title="违约责任", order=7,
                content="7.1 甲方违约：\n（1）甲方逾期交付房屋的，每逾期一日按月租金的1%支付违约金。\n（2）甲方擅自收回房屋的，应退还剩余租金及押金，并支付【2】个月租金的违约金。\n\n7.2 乙方违约：\n（1）乙方逾期支付租金的，每逾期一日按欠缴金额的1‰支付违约金。\n（2）乙方逾期支付租金超过【30】日的，甲方有权解除合同并没收押金。"),
            ConditionalClause(id="termination", title="合同解除", order=8,
                content="8.1 经双方协商一致，可以解除本合同。\n\n8.2 有下列情形之一的，甲方有权解除合同：\n（1）乙方未经同意擅自改变房屋用途的；\n（2）乙方逾期支付租金超过30日的；\n（3）乙方擅自转租的（未约定允许转租的情况下）。\n\n8.3 有下列情形之一的，乙方有权解除合同：\n（1）甲方未按约定交付房屋的；\n（2）交付的房屋不符合约定条件且严重影响使用的。"),
            ConditionalClause(id="general", title="附则", order=9,
                content="9.1 本合同自双方签字（盖章）之日起生效。\n\n9.2 本合同一式两份，甲乙双方各执一份。\n\n9.3 因本合同引起的争议，双方协商不成的，任何一方可向房屋所在地人民法院提起诉讼。"),
        ],
    ))

    # 还可以继续添加：劳动合同、服务合同、借款合同、保密协议等
    # 为简洁起见此处省略，可按相同模式扩展

    return templates


# 全局模板库
_builtin_templates: Optional[List[ContractTemplate]] = None


def get_template_library() -> List[ContractTemplate]:
    """获取模板库（懒加载）"""
    global _builtin_templates
    if _builtin_templates is None:
        _builtin_templates = get_builtin_templates()
    return _builtin_templates


def get_template_by_id(template_id: str) -> Optional[ContractTemplate]:
    """根据ID获取模板"""
    for t in get_template_library():
        if t.id == template_id:
            return t
    return None
