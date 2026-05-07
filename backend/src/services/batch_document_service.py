"""
批量文件生成服务

核心场景：
1. 物业公司：上传欠费名单 → 批量生成个性化催费律师函（含业主名、房号、金额、法律依据）
2. 企业催收：上传欠款清单 → 批量生成催款函/律师函
3. HR批量操作：批量生成劳动合同/解除通知/调岗通知

设计理念：
- 一次上传 → 批量渲染 → 逐份预览 → 打包下载
- 每份文件都是独立的、个性化的、法律上可用的
- 支持 Markdown / DOCX / PDF 三种输出格式
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from loguru import logger


@dataclass
class DocumentItem:
    """单份生成文件"""
    id: str = ""
    recipient_name: str = ""      # 收件人/对象名
    recipient_info: dict[str, Any] = field(default_factory=dict)  # 收件人详细信息
    content: str = ""             # 生成的文件内容（Markdown）
    status: str = "pending"       # pending / generating / done / error
    error: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())[:8]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "recipient_name": self.recipient_name,
            "content": self.content,
            "status": self.status,
            "error": self.error,
        }


@dataclass
class BatchJob:
    """批量生成任务"""
    job_id: str = ""
    template_type: str = ""       # demand_letter / labor_contract / termination_notice / etc.
    total: int = 0
    completed: int = 0
    items: list[DocumentItem] = field(default_factory=list)
    common_context: dict[str, Any] = field(default_factory=dict)  # 各份文件共用的上下文
    status: str = "created"       # created / processing / done / error
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.job_id:
            self.job_id = str(uuid.uuid4())[:12]
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    @property
    def progress(self) -> float:
        return self.completed / self.total if self.total > 0 else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "template_type": self.template_type,
            "total": self.total,
            "completed": self.completed,
            "progress": f"{self.progress:.0%}",
            "status": self.status,
            "items": [i.to_dict() for i in self.items],
        }


# ========== 文件模板 ==========

DOCUMENT_TEMPLATES: dict[str, dict[str, Any]] = {
    # 物业催费律师函
    "property_demand_letter": {
        "name": "物业催费律师函",
        "required_fields": ["owner_name", "unit_number", "overdue_amount", "overdue_period"],
        "optional_fields": ["property_company", "property_address", "deadline_days", "contact_phone"],
        "template": """# 律师函

**致：{owner_name}**

**关于催缴 {unit_number} 物业服务费的律师函**

{owner_name}：

受 {property_company} 委托，本律师就您拖欠物业服务费事宜致函如下：

## 一、基本事实

您系 {property_address}{unit_number} 的业主。根据您与 {property_company} 签订的《物业服务合同》约定，您应按时缴纳物业服务费。

截至本函发出之日，您已拖欠 {overdue_period} 的物业服务费，累计欠款金额为 **人民币 {overdue_amount} 元**。{property_company} 已多次催缴，但您至今未予缴纳。

## 二、法律依据

根据以下法律规定，您有义务缴纳物业服务费：

1. 《中华人民共和国民法典》第九百四十四条：业主应当按照约定向物业服务人支付物业费。业主违反约定逾期不支付物业费的，物业服务人可以催告其在合理期限内支付；合理期限届满仍不支付的，物业服务人可以提起诉讼或者申请仲裁。
2. 《物业管理条例》第四十一条：业主应当根据物业服务合同的约定交纳物业服务费用。

## 三、律师意见

请您在收到本函之日起 **{deadline_days}日内**，向 {property_company} 缴清全部欠款 **人民币 {overdue_amount} 元**。

逾期未缴纳的，{property_company} 将依法向人民法院提起诉讼，届时您除需承担上述欠款本金外，还需承担：
- 逾期违约金（按合同约定）
- 案件受理费
- 律师代理费
- 其他因诉讼产生的合理费用

请您慎重考虑，及时缴纳。

**联系方式**：{contact_phone}

此致

{property_company}
委托律师：___________
日期：{date}
""",
        "defaults": {
            "property_company": "____物业管理有限公司",
            "property_address": "____小区",
            "deadline_days": "15",
            "contact_phone": "____",
            "date": "",
        },
    },

    # 企业催款律师函
    "business_demand_letter": {
        "name": "企业催款律师函",
        "required_fields": ["debtor_name", "debt_amount", "contract_info", "overdue_date"],
        "optional_fields": ["creditor_name", "goods_or_service", "deadline_days", "contract_number"],
        "template": """# 律师函

**致：{debtor_name}**

**关于催收合同欠款的律师函**

{debtor_name}：

受 {creditor_name}（以下简称"委托人"）委托，就贵方拖欠货款/服务费事宜致函如下：

## 一、基本事实

{creditor_name} 与贵方于 {contract_info} 签订合同（合同编号：{contract_number}），约定由委托人向贵方提供 {goods_or_service}。

委托人已按合同约定履行完毕全部义务。根据合同约定，贵方应于 {overdue_date} 前支付款项 **人民币 {debt_amount} 元**。截至本函发出之日，贵方仍未支付上述款项。

## 二、法律依据

1. 《民法典》第五百零九条：当事人应当按照约定全面履行自己的义务。
2. 《民法典》第五百七十七条：当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。
3. 《民法典》第五百八十四条：当事人一方不履行合同义务或者履行合同义务不符合约定，造成对方损失的，损失赔偿额应当相当于因违约所造成的损失。

## 三、律师意见

请贵方在收到本函之日起 **{deadline_days}日内**，向委托人支付全部欠款 **人民币 {debt_amount} 元**。

逾期未付的，委托人将依法采取以下措施：
1. 向人民法院提起诉讼，主张欠款本金及逾期利息
2. 申请财产保全，冻结贵方银行账户及其他资产
3. 将贵方列入失信名单（如执行阶段拒不履行）

望贵方审慎对待，及时清偿。

此致

{creditor_name}
委托律师：___________
日期：{date}
""",
        "defaults": {
            "creditor_name": "____有限公司",
            "goods_or_service": "货物/服务",
            "deadline_days": "15",
            "contract_number": "____",
            "date": "",
        },
    },

    # 解除劳动合同通知书
    "termination_notice": {
        "name": "解除劳动合同通知书",
        "required_fields": ["employee_name", "entry_date", "termination_reason", "termination_type"],
        "optional_fields": ["company_name", "position", "last_work_date", "severance_amount"],
        "template": """# 解除劳动合同通知书

**{employee_name}**：

您于 {entry_date} 入职 {company_name}，担任 {position} 职务。

经公司研究决定，依据《中华人民共和国劳动合同法》相关规定，因 {termination_reason}，现通知如下：

## 一、解除决定

公司决定于 **{last_work_date}** 与您解除劳动合同。解除类型为：{termination_type}。

## 二、经济补偿

根据《劳动合同法》第四十七条规定，公司将向您支付经济补偿金 **人民币 {severance_amount} 元**（税前）。该款项将在办理完离职手续后 15 个工作日内支付至您的工资账户。

## 三、离职手续

请您在 {last_work_date} 前完成以下事项：
1. 完成工作交接（移交文件、物品、权限等）
2. 归还公司财产（电脑、工牌、钥匙等）
3. 结清借款及报销
4. 办理社保、公积金转移手续

## 四、权利告知

1. 公司将依法为您出具解除劳动合同证明书
2. 您可在解除后依法申请失业保险金
3. 如您对本决定有异议，可依法申请劳动仲裁

特此通知。

{company_name}（盖章）
日期：{date}

**签收确认**

本人已收到上述通知，并知悉全部内容。

签收人：_____________ 日期：_____________
""",
        "defaults": {
            "company_name": "____有限公司",
            "position": "____",
            "last_work_date": "____年____月____日",
            "severance_amount": "____",
            "date": "",
        },
    },

    # 调岗通知书
    "transfer_notice": {
        "name": "调岗通知书",
        "required_fields": ["employee_name", "original_position", "new_position", "reason"],
        "optional_fields": ["company_name", "effective_date", "salary_change"],
        "template": """# 调岗通知书

**{employee_name}**：

经公司研究决定，基于 {reason}，现对您的工作岗位进行调整：

| 项目 | 调整前 | 调整后 |
|------|--------|--------|
| 岗位 | {original_position} | {new_position} |
| 薪资 | {salary_change} | |
| 生效日期 | {effective_date} | |

请于 {effective_date} 前完成工作交接并到新岗位报到。

如您对本调岗决定有异议，请在收到通知后5个工作日内向人力资源部书面提出。

特此通知。

{company_name}
日期：{date}

**签收确认**
本人已收到上述通知。 □ 同意 □ 有异议（请书面说明）

签收人：_____________ 日期：_____________
""",
        "defaults": {
            "company_name": "____有限公司",
            "effective_date": "____年____月____日",
            "salary_change": "不变",
            "date": "",
        },
    },
}


class BatchDocumentService:
    """批量文件生成服务"""

    def __init__(self) -> None:
        self._jobs: dict[str, BatchJob] = {}

    def get_available_templates(self) -> list[dict[str, Any]]:
        """获取所有可用模板"""
        return [
            {
                "type": key,
                "name": tpl["name"],
                "required_fields": tpl["required_fields"],
                "optional_fields": tpl.get("optional_fields", []),
            }
            for key, tpl in DOCUMENT_TEMPLATES.items()
        ]

    def create_batch_job(
        self,
        template_type: str,
        recipients: list[dict[str, Any]],
        common_context: dict[str, Any] | None = None,
    ) -> BatchJob:
        """
        创建批量生成任务

        Args:
            template_type: 模板类型（property_demand_letter / business_demand_letter / etc.）
            recipients: 收件人列表 [{"owner_name": "张三", "unit_number": "1-101", "overdue_amount": "5000"}, ...]
            common_context: 所有文件共用的上下文（如公司名、地址、联系方式）
        """
        if template_type not in DOCUMENT_TEMPLATES:
            raise ValueError(f"不支持的模板类型: {template_type}，可用: {list(DOCUMENT_TEMPLATES.keys())}")

        template_def = DOCUMENT_TEMPLATES[template_type]
        items: list[DocumentItem] = []
        for r in recipients:
            name_field = template_def["required_fields"][0]
            items.append(DocumentItem(
                recipient_name=r.get(name_field, r.get("name", "未知")),
                recipient_info=r,
            ))

        job = BatchJob(
            template_type=template_type,
            total=len(items),
            items=items,
            common_context=common_context or {},
        )
        self._jobs[job.job_id] = job
        return job

    async def execute_batch(self, job_id: str) -> BatchJob:
        """执行批量生成"""
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"任务不存在: {job_id}")

        job.status = "processing"
        template_def = DOCUMENT_TEMPLATES[job.template_type]
        template_text = template_def["template"]
        defaults = template_def.get("defaults", {})

        for item in job.items:
            try:
                item.status = "generating"

                # 合并参数：默认值 → 公共上下文 → 个体信息
                params: dict[str, Any] = {**defaults}
                params.update(job.common_context)
                params.update(item.recipient_info)

                # 填充日期
                if not params.get("date"):
                    params["date"] = date.today().strftime("%Y年%m月%d日")

                # 渲染模板
                content = template_text
                for key, value in params.items():
                    content = content.replace(f"{{{key}}}", str(value))

                item.content = content
                item.status = "done"
                job.completed += 1

            except Exception as e:
                item.status = "error"
                item.error = str(e)
                logger.error(f"批量生成失败 [{item.recipient_name}]: {e}")

        job.status = "done"
        return job

    def get_job(self, job_id: str) -> BatchJob | None:
        """获取任务状态"""
        return self._jobs.get(job_id)

    def get_job_results_markdown(self, job_id: str) -> str:
        """获取批量结果的合并 Markdown"""
        job = self._jobs.get(job_id)
        if not job:
            return ""

        parts = [f"# 批量生成结果 — {DOCUMENT_TEMPLATES[job.template_type]['name']}\n"]
        parts.append(f"共 {job.total} 份，成功 {job.completed} 份\n")

        for i, item in enumerate(job.items, 1):
            parts.append(f"\n---\n\n## 第 {i} 份 — {item.recipient_name}\n")
            if item.status == "done":
                parts.append(item.content)
            else:
                parts.append(f"*生成失败: {item.error}*")

        return "\n".join(parts)


# 全局实例
batch_document_service = BatchDocumentService()
