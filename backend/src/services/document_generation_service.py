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
    ) -> dict[str, Any]:
        task = {
            "description": scenario or f"起草一份{doc_type}",
            "context": {
                "doc_type": doc_type,
                "scenario": scenario,
                "requirements": requirements,
            },
        }
        response = await self.agent.process(task)
        validation = DocumentValidator.validate_document(response.content, doc_type)
        return {
            "content": response.content,
            "draft_mode": response.metadata.get("draft_mode")
            or self._extract_draft_mode(response.reasoning),
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
