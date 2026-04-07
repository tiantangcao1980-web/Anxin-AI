from src.services.document_validator import DocumentValidator


def test_contract_short_text_fails_quality_gate():
    text = """# 服务合同

甲方：甲公司
乙方：乙公司

## 第一条 合同标的
乙方向甲方提供服务。

## 第二条 价款
服务费为人民币10000元。
"""

    result = DocumentValidator.validate_contract(text, "服务合同")

    assert result.passed is False
    assert result.score < 0.6
    assert any(issue.level == "critical" for issue in result.issues)
    assert any("条款数量不足" in issue.message or "合同内容过短" in issue.message for issue in result.issues)


def test_lawyer_letter_without_deadline_fails():
    text = """# 律师函

致：某供应商

一、基本事实
贵方存在迟延付款情形。

二、法律分析
贵方行为已构成违约。

三、律师意见
请及时履行付款义务。
"""

    result = DocumentValidator.validate_document(text, "律师函")

    assert result.passed is False
    assert any("履行要求" in issue.message or "期限" in issue.message for issue in result.issues)


def test_legal_opinion_without_conclusion_fails():
    text = """# 法律意见书

致：某公司

## 一、引言
受贵司委托，就本次交易出具法律意见。

## 二、事实概述
交易双方已签署框架协议。

## 三、法律分析
本次交易涉及公司法与民法典相关规则。
"""

    result = DocumentValidator.validate_document(text, "法律意见书")

    assert result.passed is False
    assert any("结论" in issue.message or "法律意见" in issue.message for issue in result.issues)
