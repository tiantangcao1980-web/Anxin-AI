import json
from pathlib import Path

import pytest

from src.services.due_diligence_service import (
    DueDiligenceService,
    classify_investigation_request,
    detect_company_due_diligence_request,
    extract_company_name_from_text,
    format_due_diligence_chat_response,
)

EVAL_DATASET = Path(__file__).parent / "eval" / "investigation_routing_eval.jsonl"


def test_detect_due_diligence_request_with_company_name():
    result = detect_company_due_diligence_request("帮我调查一下腾讯公司的背景、诉讼记录和股权结构")

    assert result["matched"] is True
    assert result["company_name"] == "腾讯公司"


def test_detect_due_diligence_request_without_company_name():
    result = detect_company_due_diligence_request("帮我调查一家公司是否可靠，重点看诉讼和工商")

    assert result["matched"] is True
    assert result["company_name"] is None


def test_company_law_question_is_not_misclassified():
    result = detect_company_due_diligence_request("公司法关于股东出资义务是怎么规定的？")

    assert result["matched"] is False


def test_supplier_reliability_phrase_is_classified_as_due_diligence():
    result = detect_company_due_diligence_request("帮我看看这个供应商靠不靠谱，重点看信用和诉讼")

    assert result["matched"] is True
    assert result["company_name"] is None


def test_extract_company_name_prefers_explicit_entity():
    company_name = extract_company_name_from_text("请查一下杭州某某科技有限公司的诉讼记录")

    assert company_name == "杭州某某科技有限公司"


def test_format_due_diligence_response_contains_structured_sections():
    response = format_due_diligence_chat_response(
        "腾讯",
        {
            "basic_info": {
                "name": "腾讯控股有限公司",
                "status": "正常",
                "legal_representative": "马化腾",
                "registered_capital": "待核验",
                "established_date": "1998-11-11",
                "data_source": "公开工商数据",
            },
            "litigation": {
                "plaintiff_cases": 3,
                "defendant_cases": 2,
            },
            "credit": {
                "credit_rating": "A",
            },
            "risk": {
                "overall_rating": "low",
                "operation_risk": 20,
                "litigation_risk": 30,
                "credit_risk": 15,
                "compliance_risk": 35,
                "relation_risk": 20,
                "risk_points": ["存在平台治理相关合规风险"],
                "recommendations": ["建议核查近期监管处罚与整改情况"],
            },
        },
    )

    assert "企业概况" in response
    assert "风险结论" in response
    assert "重点发现" in response
    assert "建议动作" in response
    assert "腾讯控股有限公司" in response


def test_classify_investigation_request_routes_supported_intents():
    cases = [
        ("查一下腾讯公司的工商信息和诉讼记录", "due_diligence"),
        ("搜索腾讯公司的负面新闻和媒体报道", "sentiment"),
        ("监测腾讯公司适用的数据合规新规", "regulatory_monitoring"),
        ("帮我总结一下合同审查流程", "general_search"),
    ]

    for text, intent in cases:
        assert classify_investigation_request(text)["intent"] == intent


def test_investigation_routing_eval_dataset_meets_accuracy_floor():
    rows = [
        json.loads(line)
        for line in EVAL_DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(rows) >= 200

    intent_hits = 0
    company_rows = 0
    company_hits = 0
    for row in rows:
        result = classify_investigation_request(row["text"])
        if result["intent"] == row["intent"]:
            intent_hits += 1
        if row.get("company_name"):
            company_rows += 1
            if result["company_name"] == row["company_name"]:
                company_hits += 1

    assert intent_hits / len(rows) >= 0.85
    assert company_rows >= 100
    assert company_hits / company_rows >= 0.85


@pytest.mark.asyncio
async def test_wenshu_lookup_uses_compliant_crawler(monkeypatch):
    from src.services.crawl4ai_service import crawl4ai_service

    calls: list[str] = []

    async def fake_crawl_url(url: str, timeout: int | None = None):
        calls.append(url)
        return {
            "success": True,
            "content": "腾讯公司 相关结果 共 12 条",
            "error": None,
        }

    monkeypatch.setattr(crawl4ai_service, "crawl_url", fake_crawl_url)

    result = await DueDiligenceService()._fetch_wenshu_info("腾讯公司")

    assert calls == ["https://wenshu.court.gov.cn/"]
    assert result["case_count"] == 12
    assert result["cases"][0]["title"].startswith("腾讯公司")
