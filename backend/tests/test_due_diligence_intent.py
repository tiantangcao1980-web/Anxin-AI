from src.services.due_diligence_service import (
    detect_company_due_diligence_request,
    extract_company_name_from_text,
    format_due_diligence_chat_response,
)


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
