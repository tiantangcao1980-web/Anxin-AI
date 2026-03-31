"""
高风险法律任务护栏

用于在合同审查、文书起草等高风险专业任务中，
先检查关键信息是否充足，再决定是否继续走通用智能体流程。
"""

from typing import Dict, Any
import re


_CONTRACT_REVIEW_PATTERNS = [
    re.compile(r"(审[查阅看核].{0,8}合同)"),
    re.compile(r"(合同.{0,8}审[查阅看核])"),
    re.compile(r"(审核.{0,8}(协议|条款))"),
    re.compile(r"(帮我看.{0,8}(合同|协议))"),
]

_DOCUMENT_DRAFT_PATTERNS = [
    re.compile(r"(起草|草拟|写一份|拟一份|生成).{0,10}(律师函|协议|合同|起诉状|答辩状|授权委托书|法律意见书|催款函|通知书)"),
    re.compile(r"(律师函|起诉状|答辩状|授权委托书|法律意见书|催款函).{0,8}(怎么写|起草|模板)"),
]

_CONTRACT_MATERIAL_MARKERS = [
    "甲方", "乙方", "第一条", "第1条", "合同编号", "签署日期",
    "违约责任", "争议解决", "保密条款", "付款方式", "合同期限",
]

_DOCUMENT_TYPE_MARKERS = [
    "律师函", "协议", "合同", "起诉状", "答辩状", "授权委托书", "法律意见书", "催款函", "通知书",
]

_PARTY_MARKERS = ["甲方", "乙方", "原告", "被告", "委托人", "受托人", "对方", "收函方", "发函方"]
_FACT_MARKERS = ["因为", "由于", "未支付", "违约", "欠款", "争议", "金额", "时间", "日期", "事实"]


def detect_high_risk_guardrail(message: str) -> Dict[str, Any]:
    text = (message or "").strip()
    if not text:
        return {"matched": False}

    if _matches_any(text, _CONTRACT_REVIEW_PATTERNS):
        if not _has_contract_material(text):
            return {
                "matched": True,
                "intent": "contract_review",
                "response_text": (
                    "我已识别到您要做合同审查，但当前还没有足够的合同材料。"
                    "请直接上传合同文件，或把合同全文/关键条款粘贴过来；如果您有特别关注点，也可以一并说明，例如违约责任、付款条款、保密条款或争议解决。"
                ),
            }
        return {"matched": False}

    if _matches_any(text, _DOCUMENT_DRAFT_PATTERNS):
        if not _has_document_drafting_minimum_info(text):
            return {
                "matched": True,
                "intent": "document_drafting",
                "response_text": (
                    "我已识别到您要起草法律文书，但当前关键信息还不够。"
                    "请补充以下内容中的至少 3 项：文书类型、双方主体、核心事实、诉求/目的、涉及金额或期限。"
                    "例如：帮我起草一份催款律师函，发函方是甲公司，收函方是乙公司，拖欠 50 万货款已超过 30 天，要求 7 日内付款。"
                ),
            }
        return {"matched": False}

    return {"matched": False}


def _matches_any(text: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _has_contract_material(text: str) -> bool:
    if len(text) >= 300:
        return True
    return any(marker in text for marker in _CONTRACT_MATERIAL_MARKERS)


def _has_document_drafting_minimum_info(text: str) -> bool:
    score = 0
    if any(marker in text for marker in _DOCUMENT_TYPE_MARKERS):
        score += 1
    if any(marker in text for marker in _PARTY_MARKERS):
        score += 1
    if any(marker in text for marker in _FACT_MARKERS):
        score += 1
    if re.search(r"\d+\s*(元|万元|万|天|日|月|年)", text):
        score += 1
    if len(text) >= 60:
        score += 1
    return score >= 3
