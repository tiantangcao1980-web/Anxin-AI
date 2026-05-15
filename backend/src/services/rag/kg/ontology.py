"""
法律领域本体（轻量级）

仅在抽取/分类层使用——不依赖外部本体库（OWL/RDF）。
覆盖任务卡列出的 11 类实体 + 7 类关系；后续可平滑迁移到 KG 三方平台。
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from src.services.rag.kg.base import EntityType

# ---------------------------------------------------------------------------
# 当事人 / 主体
# ---------------------------------------------------------------------------

LEGAL_PARTY_KEYWORDS: tuple[str, ...] = (
    "甲方",
    "乙方",
    "丙方",
    "丁方",
    "买方",
    "卖方",
    "出租方",
    "承租方",
    "委托方",
    "受托方",
    "发包方",
    "承包方",
    "供方",
    "需方",
    "出借人",
    "借款人",
    "担保方",
    "本公司",
    "对方",
)


# ---------------------------------------------------------------------------
# 义务 / 权利动词触发词
# ---------------------------------------------------------------------------

LEGAL_OBLIGATION_KEYWORDS: tuple[str, ...] = (
    "应当",
    "须",
    "必须",
    "应",
    "负责",
    "承担",
    "履行",
    "支付",
    "交付",
    "保证",
    "确保",
    "不得",
    "不应",
    "禁止",
)

LEGAL_RIGHT_KEYWORDS: tuple[str, ...] = (
    "有权",
    "享有",
    "可以",
    "得",
    "保留权利",
    "授权",
    "授予",
    "可向",
)


# ---------------------------------------------------------------------------
# 法规引用模式
# ---------------------------------------------------------------------------

# 形如《民法典》、《公司法》、《XX 法》、《XX 规定》、《XX 办法》、《XX 条例》
LEGAL_REGULATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"《[^》]{2,40}(?:法|条例|规定|办法|意见|通知|解释|实施细则|公约|协定)》"),
    re.compile(r"《中华人民共和国[^》]{1,30}》"),
)

# 第 N 章 / 第 N 条 / 第 N 款 / 第 N 项
ARTICLE_REGEX = re.compile(
    r"第[一二三四五六七八九十百零〇0-9]+(?:章|节|条|款|项|目)"
)


# ---------------------------------------------------------------------------
# 金额 / 日期
# ---------------------------------------------------------------------------

AMOUNT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"[0-9]+(?:[,，][0-9]{3})*(?:\.[0-9]+)?\s*(?:元|万元|亿元|美元|欧元|RMB|USD|CNY)"),
    re.compile(r"人民币\s*[0-9]+(?:[,，][0-9]{3})*(?:\.[0-9]+)?\s*(?:元|万元|亿元)"),
)

DATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日"),
    re.compile(r"\d{4}-\d{1,2}-\d{1,2}"),
    re.compile(r"\d{4}/\d{1,2}/\d{1,2}"),
)


# ---------------------------------------------------------------------------
# Modality → 默认实体类型映射（图章/签字/表格的快速归类）
# ---------------------------------------------------------------------------

MODALITY_DEFAULT_TYPE: dict[str, EntityType] = {
    "seal": EntityType.SEAL,
    "signature": EntityType.SIGNATURE,
    "table": EntityType.TABLE_DATA,
    "formula": EntityType.GENERIC,
    "image": EntityType.GENERIC,
}


# ---------------------------------------------------------------------------
# 简单分类器
# ---------------------------------------------------------------------------


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(kw in text for kw in keywords)


def classify_entity(name: str, modality: str = "text") -> EntityType:
    """根据实体名 + 所在 modality 推断 EntityType。

    优先级：
    1. modality 默认（seal/signature/table 直接归类）
    2. 法规模式（《XX法》、第 N 条）
    3. 当事人/义务/权利关键词
    4. 金额/日期正则
    5. 兜底 GENERIC
    """
    if modality in MODALITY_DEFAULT_TYPE and modality != "text":
        return MODALITY_DEFAULT_TYPE[modality]

    if any(p.search(name) for p in LEGAL_REGULATION_PATTERNS):
        return EntityType.REGULATION
    if ARTICLE_REGEX.search(name):
        return EntityType.REGULATION

    if name in LEGAL_PARTY_KEYWORDS or _contains_any(name, LEGAL_PARTY_KEYWORDS):
        return EntityType.LEGAL_PARTY

    if _contains_any(name, LEGAL_OBLIGATION_KEYWORDS):
        return EntityType.OBLIGATION
    if _contains_any(name, LEGAL_RIGHT_KEYWORDS):
        return EntityType.RIGHT

    if any(p.search(name) for p in AMOUNT_PATTERNS):
        return EntityType.AMOUNT
    if any(p.search(name) for p in DATE_PATTERNS):
        return EntityType.DATE

    return EntityType.GENERIC


__all__ = [
    "LEGAL_PARTY_KEYWORDS",
    "LEGAL_OBLIGATION_KEYWORDS",
    "LEGAL_RIGHT_KEYWORDS",
    "LEGAL_REGULATION_PATTERNS",
    "ARTICLE_REGEX",
    "AMOUNT_PATTERNS",
    "DATE_PATTERNS",
    "MODALITY_DEFAULT_TYPE",
    "classify_entity",
]
