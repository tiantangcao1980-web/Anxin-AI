"""
法律引用溯源服务

提供法律条文引用的解析、验证和链接生成能力。
使Agent输出的法律引用可追溯、可验证。
"""

import re
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class LegalCitation:
    """法律引用结构"""
    law_name: str           # 法律名称，如"中华人民共和国民法典"
    article: str            # 条文编号，如"第496条"
    paragraph: str | None = None  # 款，如"第二款"
    item: str | None = None       # 项，如"第（三）项"
    content_preview: str | None = None  # 条文内容摘要
    url: str | None = None         # 国家法律数据库链接
    verified: bool = False             # 是否验证通过
    confidence: float = 0.0            # 引用置信度

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_display(self) -> str:
        """生成显示文本"""
        parts = [f"《{self.law_name}》{self.article}"]
        if self.paragraph:
            parts.append(self.paragraph)
        if self.item:
            parts.append(self.item)
        return "".join(parts)


# ==================== 法律引用模式库 ====================

# 核心法律简称→全称映射
LAW_NAME_MAP = {
    "民法典": "中华人民共和国民法典",
    "合同法": "中华人民共和国合同法",  # 已被民法典合同编替代
    "劳动合同法": "中华人民共和国劳动合同法",
    "劳动法": "中华人民共和国劳动法",
    "公司法": "中华人民共和国公司法",
    "刑法": "中华人民共和国刑法",
    "民事诉讼法": "中华人民共和国民事诉讼法",
    "刑事诉讼法": "中华人民共和国刑事诉讼法",
    "行政诉讼法": "中华人民共和国行政诉讼法",
    "消费者权益保护法": "中华人民共和国消费者权益保护法",
    "反不正当竞争法": "中华人民共和国反不正当竞争法",
    "数据安全法": "中华人民共和国数据安全法",
    "个人信息保护法": "中华人民共和国个人信息保护法",
    "网络安全法": "中华人民共和国网络安全法",
    "招标投标法": "中华人民共和国招标投标法",
    "物权法": "中华人民共和国物权法",  # 已被民法典物权编替代
    "担保法": "中华人民共和国担保法",  # 已被民法典替代
    "保险法": "中华人民共和国保险法",
    "证券法": "中华人民共和国证券法",
    "知识产权法": "中华人民共和国知识产权法",
    "专利法": "中华人民共和国专利法",
    "商标法": "中华人民共和国商标法",
    "著作权法": "中华人民共和国著作权法",
}

# 国家法律法规数据库基础URL
FLKG_BASE_URL = "https://flk.npc.gov.cn/detail2.html"

# 引用模式正则（覆盖常见格式）
CITATION_PATTERNS = [
    # 《法律名称》第XXX条（第X款/第X项）
    r'《([^》]+)》第(\d+)条(?:第([一二三四五六七八九十\d]+)款)?(?:第[（(]([一二三四五六七八九十\d]+)[)）]项)?',
    # 法律简称第XXX条
    r'(?:依据|根据|参照|依照)?\s*(?:《([^》]+)》|([^\s，。,\.]+?法[^，。,\.\s]*?))\s*第(\d+)[-至到]?(\d*)条',
    # 民法典第XXX-XXX条
    r'(民法典|劳动合同法|公司法|消费者权益保护法|数据安全法|个人信息保护法)\s*第(\d+)[-至到](\d+)条',
    # 第XXX条规定
    r'第(\d+)条(?:之(\d+))?(?:的?规定)?',
]


class LegalCitationService:
    """法律引用溯源服务"""

    @classmethod
    def extract_citations(cls, text: str) -> list[LegalCitation]:
        """
        从文本中提取所有法律引用

        支持以下格式：
        - 《民法典》第496条
        - 民法典第496条第二款
        - 依据《劳动合同法》第19-21条
        - 根据个人信息保护法第XXX条规定
        """
        citations = []
        seen = set()

        # Pattern 1: 《法律名称》第XXX条（带款项）
        for match in re.finditer(
            r'《([^》]+)》\s*第(\d+)条(?:\s*第([一二三四五六七八九十百零\d]+)款)?(?:\s*第[（(]([一二三四五六七八九十\d]+)[)）]项)?',
            text
        ):
            law_name = match.group(1).strip()
            article = f"第{match.group(2)}条"
            paragraph = f"第{match.group(3)}款" if match.group(3) else None
            item = f"第（{match.group(4)}）项" if match.group(4) else None

            key = f"{law_name}_{article}"
            if key not in seen:
                seen.add(key)
                full_name = LAW_NAME_MAP.get(law_name, law_name)
                citations.append(LegalCitation(
                    law_name=full_name,
                    article=article,
                    paragraph=paragraph,
                    item=item,
                    url=cls._generate_law_url(full_name, match.group(2)),
                    confidence=0.9,
                ))

        # Pattern 2: 法律简称 + 第XXX条（无书名号）
        for match in re.finditer(
            r'(?:依据|根据|参照|依照|参见)\s*(民法典|劳动合同法|劳动法|公司法|刑法|消费者权益保护法|数据安全法|个人信息保护法|网络安全法|招标投标法|保险法|证券法|专利法|商标法|著作权法)\s*第(\d+)(?:[-至到](\d+))?条',
            text
        ):
            law_short = match.group(1).strip()
            article_num = match.group(2)
            article_end = match.group(3)

            full_name = LAW_NAME_MAP.get(law_short, law_short)

            if article_end:
                article = f"第{article_num}-{article_end}条"
            else:
                article = f"第{article_num}条"

            key = f"{full_name}_{article}"
            if key not in seen:
                seen.add(key)
                citations.append(LegalCitation(
                    law_name=full_name,
                    article=article,
                    url=cls._generate_law_url(full_name, article_num),
                    confidence=0.85,
                ))

        # Pattern 3: 最高法司法解释
        for match in re.finditer(
            r'《(最高人民法院关于[^》]+)》\s*第(\d+)条',
            text
        ):
            interp_name = match.group(1).strip()
            article = f"第{match.group(2)}条"
            key = f"{interp_name}_{article}"
            if key not in seen:
                seen.add(key)
                citations.append(LegalCitation(
                    law_name=interp_name,
                    article=article,
                    confidence=0.8,
                ))

        return citations

    @classmethod
    def _generate_law_url(cls, law_name: str, article_num: str) -> str | None:
        """生成国家法律法规数据库链接"""
        # 国家法律法规数据库 (flk.npc.gov.cn) 的链接需要法律ID
        # 这里返回搜索链接作为近似
        return f"https://flk.npc.gov.cn/detail2.html?ZmY=&flfg_id=&keyword={law_name}+第{article_num}条"

    @classmethod
    def enrich_review_result(cls, review_result: dict[str, Any]) -> dict[str, Any]:
        """
        增强审查结果的法律引用信息

        为每个风险点解析并附加结构化的法律引用
        """
        risks = review_result.get("risks", [])

        for risk in risks:
            # 从description和legal_basis中提取引用
            text_to_scan = " ".join(filter(None, [
                risk.get("description", ""),
                risk.get("legal_basis", ""),
                risk.get("suggestion", ""),
            ]))

            citations = cls.extract_citations(text_to_scan)
            if citations:
                risk["citations"] = [c.to_dict() for c in citations]
                risk["citation_display"] = [c.to_display() for c in citations]

        # 从suggestions中提取引用
        suggestions = review_result.get("suggestions", [])
        all_citations = []
        for suggestion in suggestions:
            if isinstance(suggestion, str):
                all_citations.extend(cls.extract_citations(suggestion))

        # 去重并添加到review_result
        seen_keys = set()
        unique_citations = []
        for c in all_citations:
            key = f"{c.law_name}_{c.article}"
            if key not in seen_keys:
                seen_keys.add(key)
                unique_citations.append(c.to_dict())

        if unique_citations:
            review_result["all_citations"] = unique_citations

        return review_result

    @classmethod
    def format_citation_summary(cls, citations: list[LegalCitation]) -> str:
        """格式化引用摘要"""
        if not citations:
            return ""

        lines = ["**引用法律依据：**"]
        for i, citation in enumerate(citations, 1):
            lines.append(f"{i}. {citation.to_display()}")

        return "\n".join(lines)
