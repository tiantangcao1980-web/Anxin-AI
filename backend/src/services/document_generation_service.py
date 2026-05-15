from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.document_drafter import DocumentDraftAgent
from src.services.document_validator import DocumentValidator


class DocumentGenerationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.agent = DocumentDraftAgent()

    async def generate(
        self,
        *,
        doc_type: str,
        scenario: str,
        requirements: dict[str, Any],
        subject: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """生成法律文书草稿。

        如调用方传入 ``subject``（含 ``id / role / tenant_id / clearance /
        primary_jurisdiction``），自动走治理 PDP + 审计；否则走原 ``process``
        以保持向后兼容。

        高敏文书（律师函 / 起诉状）默认 ``data-classification=L4``；普通模板
        合同 / 协议为 L3。
        """
        task = {
            "description": scenario or f"起草一份{doc_type}",
            "context": {
                "doc_type": doc_type,
                "scenario": scenario,
                "requirements": requirements,
            },
        }
        if subject:
            classification = _classification_for_doc_type(doc_type)
            response = await self.agent.process_governed(
                task,
                subject=subject,
                action="agent.document_drafter.generate",
                resource={
                    "type": "agent",
                    "id": "DocumentDraftAgent",
                    "classification": classification,
                    "jurisdiction": subject.get("primary_jurisdiction") or "CN",
                },
                context={
                    "trace_id": subject.get("trace_id"),
                    "mfa_recent": bool(subject.get("mfa_recent")),
                    "doc_type": doc_type,
                },
            )
        else:
            response = await self.agent.process(task)
        validation = DocumentValidator.validate_document(response.content, doc_type)
        return {
            "content": response.content,
            "draft_mode": response.metadata.get("draft_mode") or self._extract_draft_mode(response.reasoning),
            "validation_score": validation.score,
            "completeness_score": response.metadata.get("completeness_score"),
            "missing_fields": response.metadata.get("missing_fields", []),
            "reasoning": response.reasoning,
        }

    async def generate_missing_field_paragraph(
        self,
        *,
        doc_type: str,
        document_title: str,
        current_content: str,
        missing_field: dict[str, Any],
    ) -> dict[str, str]:
        field_label = missing_field.get("label", "待确认事项")
        suggestion = missing_field.get("suggestion", "")
        prompt = f"""请为以下法律文书补写一个可以直接纳入正文的专业段落。

【文书类型】{doc_type}
【文书标题】{document_title}
【待补写字段】{field_label}
【补写要求】{suggestion}
【现有文书内容】
{current_content}

请严格输出中文 Markdown，格式如下：
## AI补写段落：{field_label}
[仅输出可直接纳入正文的完整段落，不要解释，不要写提示语]
"""
        content = await self.agent.chat(prompt)
        return {
            "title": f"AI补写段落：{field_label}",
            "content": content.strip(),
        }

    @staticmethod
    def _extract_draft_mode(reasoning: str | None) -> str:
        if not reasoning:
            return "高可用草案"
        for mode in ("成稿", "高可用草案", "结构化草稿"):
            if mode in reasoning:
                return mode
        return "高可用草案"


# 文书类型 → 数据分级映射；用于 _call PDP 时传入正确的 resource.classification
_HIGH_RISK_DOC_TYPES = {
    "demand_letter",         # 律师函
    "complaint",             # 起诉状
    "settlement_agreement",  # 和解协议
    "investigation_report",  # 调查报告
    "internal_audit_report", # 内审报告
    "privileged_memo",       # 律师备忘
}


def _classification_for_doc_type(doc_type: str | None) -> str:
    """律师函 / 起诉状 / 和解 等高敏文书 → L4；其它 → L3。"""
    if not doc_type:
        return "L3"
    if any(k in doc_type.lower() for k in _HIGH_RISK_DOC_TYPES):
        return "L4"
    return "L3"
