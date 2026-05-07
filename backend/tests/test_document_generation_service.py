from __future__ import annotations

from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import AgentResponse
from src.agents.document_drafter import DocumentDraftAgent
from src.services import document_generation_service as generation_module
from src.services.document_generation_service import DocumentGenerationService


class FakeValidation:
    score = 0.91


class FakeDocumentDraftAgent:
    def __init__(self) -> None:
        self.process_calls: list[dict[str, Any]] = []
        self.chat_calls: list[str] = []

    async def process(self, task: dict[str, Any]) -> AgentResponse:
        self.process_calls.append(task)
        return AgentResponse(
            agent_name="fake-drafter",
            content="# Draft",
            reasoning="Generated as a structured draft.",
            actions=[],
            metadata={
                "draft_mode": "structured-draft",
                "completeness_score": 0.72,
                "missing_fields": [{"label": "payment terms"}],
            },
        )

    async def chat(self, prompt: str) -> str:
        self.chat_calls.append(prompt)
        return "  Generated paragraph.  "


@pytest.fixture
def fake_agent(monkeypatch: pytest.MonkeyPatch) -> FakeDocumentDraftAgent:
    agent = FakeDocumentDraftAgent()
    monkeypatch.setattr(generation_module, "DocumentDraftAgent", lambda: agent)
    monkeypatch.setattr(
        generation_module.DocumentValidator,
        "validate_document",
        lambda content, doc_type: FakeValidation(),
    )
    return agent


@pytest.mark.asyncio
async def test_generate_builds_task_and_returns_validation_metadata(
    fake_agent: FakeDocumentDraftAgent,
) -> None:
    service = DocumentGenerationService(cast(AsyncSession, object()))

    result = await service.generate(
        doc_type="service contract",
        scenario="Draft an annual support contract.",
        requirements={"client": "Acme", "target": "Vendor"},
    )

    assert fake_agent.process_calls == [
        {
            "description": "Draft an annual support contract.",
            "context": {
                "doc_type": "service contract",
                "scenario": "Draft an annual support contract.",
                "requirements": {"client": "Acme", "target": "Vendor"},
            },
        }
    ]
    assert result == {
        "content": "# Draft",
        "draft_mode": "structured-draft",
        "validation_score": 0.91,
        "completeness_score": 0.72,
        "missing_fields": [{"label": "payment terms"}],
        "reasoning": "Generated as a structured draft.",
    }


@pytest.mark.asyncio
async def test_generate_missing_field_paragraph_strips_agent_output(
    fake_agent: FakeDocumentDraftAgent,
) -> None:
    service = DocumentGenerationService(cast(AsyncSession, object()))

    result = await service.generate_missing_field_paragraph(
        doc_type="lawyer letter",
        document_title="Demand letter",
        current_content="# Demand letter",
        missing_field={"label": "legal consequence", "suggestion": "Add remedies."},
    )

    assert result == {
        "title": "AI补写段落：legal consequence",
        "content": "Generated paragraph.",
    }
    assert "lawyer letter" in fake_agent.chat_calls[0]
    assert "legal consequence" in fake_agent.chat_calls[0]
    assert "Add remedies." in fake_agent.chat_calls[0]


def test_document_draft_agent_missing_field_items_keep_string_values() -> None:
    agent = DocumentDraftAgent()

    plan = agent._assess_draft_plan(
        doc_type="service contract",
        description="",
        requirements={},
        scenario="",
    )

    assert plan.normalized_doc_type == "contract"
    assert plan.missing_fields
    assert all(
        isinstance(value, str)
        for item in plan.missing_fields
        for value in item.values()
    )
    assert {item["key"] for item in plan.missing_fields} >= {
        "合同金额与付款安排",
        "履行期限与交付节点",
    }
