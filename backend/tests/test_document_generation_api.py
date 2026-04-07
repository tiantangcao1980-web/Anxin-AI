from unittest.mock import AsyncMock

import pytest

from .conftest import create_auth_headers


@pytest.mark.asyncio
async def test_generate_document_uses_shared_generation_service(client, test_user, monkeypatch):
    generated = {
        "content": "# 服务合同\n\n## 第一条 定义与解释\n1.1 ...\n\n---\n## 起草说明\n...",
        "draft_mode": "高可用草案",
        "validation_score": 0.86,
        "missing_fields": [
            {
                "key": "合同金额与付款安排",
                "label": "合同金额与付款安排",
                "severity": "high",
                "group": "交易条件",
                "suggestion": "建议补充：明确合同总价、付款节点、付款条件",
            }
        ],
    }

    service = AsyncMock()
    service.generate.return_value = generated
    monkeypatch.setattr("src.api.routes.documents.DocumentGenerationService", lambda db: service)

    response = await client.post(
        "/api/v1/documents/generate",
        headers=create_auth_headers(test_user),
        json={
            "doc_type": "服务合同",
            "scenario": "甲方委托乙方提供驻场运维服务",
            "requirements": {
                "client": "甲公司",
                "target": "乙公司",
                "details": "需要约定驻场服务、响应时效、付款节点",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert payload["data"]["name"].endswith(".md")
    assert payload["data"]["extracted_text"].startswith("# 服务合同")
    assert "高可用草案" in payload["data"]["description"]
    assert payload["data"]["ai_metadata"]["draft_mode"] == "高可用草案"
    assert payload["data"]["ai_metadata"]["missing_fields"][0]["label"] == "合同金额与付款安排"
    assert service.generate.await_count == 1


@pytest.mark.asyncio
async def test_generate_paragraph_uses_shared_generation_service(client, test_user, monkeypatch):
    service = AsyncMock()
    service.generate_missing_field_paragraph.return_value = {
        "title": "AI补写段落：法律后果提示",
        "content": "若贵方逾期未履行付款义务，我方将依法提起诉讼并主张违约责任。",
    }
    monkeypatch.setattr("src.api.routes.documents.DocumentGenerationService", lambda db: service)

    response = await client.post(
        "/api/v1/documents/generate-paragraph",
        headers=create_auth_headers(test_user),
        json={
            "doc_type": "律师函",
            "document_title": "催款律师函",
            "current_content": "# 催款律师函\n\n一、基本事实\n...",
            "missing_field": {
                "key": "法律后果提示",
                "label": "法律后果提示",
                "severity": "medium",
                "group": "风险控制",
                "suggestion": "建议补充：说明逾期不履行将面临的诉讼、仲裁或其他法律后果",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert payload["data"]["title"] == "AI补写段落：法律后果提示"
    assert "诉讼" in payload["data"]["content"]
    assert service.generate_missing_field_paragraph.await_count == 1
