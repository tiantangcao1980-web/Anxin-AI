"""
Citation Tracker — 精确引文追踪系统

灵感来源：DeepTutor 精确引文系统
- 法律咨询必须引用具体法条、司法解释
- 每个回答追踪引用来源（法条 → 节 → 条 → 款 → 项）
- 支持引文验证和交叉引用

功能：
1. 从文本中提取法律引用（法条、司法解释、判例）
2. 验证引用的准确性（查知识库确认）
3. 构建引用关系图谱
4. 追踪引文链路（A引用B，B引用C）
"""

import os
import re
from typing import Any

from loguru import logger

from src.core.config import settings
from src.services.pii_service import pii_service

MAX_CITATION_FIELD_LENGTH = 120


def _safe_citation_text(value: str, max_length: int = MAX_CITATION_FIELD_LENGTH) -> str:
    """Mask PII and bound citation fields before returning or sinking to graph."""
    scrubbed = str(pii_service.scrub_for_output(value or ""))
    if len(scrubbed) <= max_length:
        return scrubbed
    return scrubbed[: max_length - 3] + "..."


class Citation:
    """单条引文"""

    def __init__(
        self,
        text: str,
        source_type: str,  # law / regulation / case / interpretation / article
        source_name: str,
        article: str | None = None,  # 第X条
        paragraph: str | None = None,  # 第X款
        item: str | None = None,  # 第X项
        confidence: float = 1.0,
        verified: bool = False,
    ):
        self.text = text
        self.source_type = source_type
        self.source_name = source_name
        self.article = article
        self.paragraph = paragraph
        self.item = item
        self.confidence = confidence
        self.verified = verified

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": _safe_citation_text(self.text),
            "source_type": self.source_type,
            "source_name": _safe_citation_text(self.source_name),
            "article": self.article,
            "paragraph": self.paragraph,
            "item": self.item,
            "confidence": self.confidence,
            "verified": self.verified,
            "reference": _safe_citation_text(self.full_reference, max_length=200),
        }

    @property
    def full_reference(self) -> str:
        """完整引用格式"""
        parts = [f"《{self.source_name}》"]
        if self.article:
            parts.append(f"第{self.article}条")
        if self.paragraph:
            parts.append(f"第{self.paragraph}款")
        if self.item:
            parts.append(f"第{self.item}项")
        return "".join(parts)


class CitationTracker:
    """引文追踪器"""

    # 法律引用正则
    RE_LAW_REF = re.compile(
        r"《([^》]{2,30})》"
        r"(?:\s*第?\s*(\d+)\s*条)?"
        r"(?:\s*第?\s*(\d+)\s*款)?"
        r"(?:\s*第?\s*(\d+)\s*项)?"
    )
    # 案号引用
    RE_CASE_REF = re.compile(r"[（(](\d{4})[）)]([^，,。\s]{2,20}?)第?\s*(\d+)\s*号")
    # 司法解释引用
    RE_INTERPRETATION = re.compile(
        r"(?:最高人民法院|最高人民检察院|两高)(?:关于[^的]{2,30}的)?"
        r"(?:解释|规定|意见|批复|通知)"
    )

    def extract_citations(self, text: str) -> list[Citation]:
        """从文本中提取所有法律引用"""
        citations = []

        # 1. 法律法规引用
        for match in self.RE_LAW_REF.finditer(text):
            name = match.group(1)
            article = match.group(2)
            paragraph = match.group(3)
            item = match.group(4)

            source_type = self._classify_source(name)
            citations.append(
                Citation(
                    text=match.group(0),
                    source_type=source_type,
                    source_name=name,
                    article=article,
                    paragraph=paragraph,
                    item=item,
                )
            )

        # 2. 案号引用
        for match in self.RE_CASE_REF.finditer(text):
            year = match.group(1)
            court = match.group(2)
            number = match.group(3)
            case_no = f"({year}){court}{number}号"
            citations.append(
                Citation(
                    text=match.group(0),
                    source_type="case",
                    source_name=case_no,
                )
            )

        # 3. 司法解释引用
        for match in self.RE_INTERPRETATION.finditer(text):
            citations.append(
                Citation(
                    text=match.group(0),
                    source_type="interpretation",
                    source_name=match.group(0),
                )
            )

        return citations

    def _classify_source(self, name: str) -> str:
        """分类法律来源"""
        if any(kw in name for kw in ["法", "条例", "规定"]):
            return "law"
        if any(kw in name for kw in ["解释", "意见", "批复"]):
            return "interpretation"
        if any(kw in name for kw in ["标准", "规范", "办法"]):
            return "regulation"
        return "law"

    async def verify_citations(
        self,
        citations: list[Citation],
    ) -> list[Citation]:
        """
        验证引文准确性（查知识库）

        将每条引用与知识库中的法规文本进行匹配验证
        """
        try:
            # 尝试在知识库中查找引用的法规
            for citation in citations:
                try:
                    # 语义搜索验证
                    from src.services.vector_store import vector_store

                    if vector_store and vector_store.is_available:
                        results = await vector_store.search(
                            collection_name=settings.QDRANT_COLLECTION_NAME,
                            query=citation.full_reference,
                            top_k=1,
                        )
                        if results and len(results) > 0:
                            score = results[0].get("score", 0)
                            citation.verified = score > 0.7
                            citation.confidence = min(1.0, score)
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"引文验证跳过: {e}")

        return citations

    def build_citation_graph(
        self,
        citations: list[Citation],
    ) -> dict[str, Any]:
        """
        构建引文关系图

        Returns:
            {nodes: [...], edges: [...]} 格式的图数据
        """
        nodes = []
        edges = []
        seen = set()

        for citation in citations:
            node_id = _safe_citation_text(citation.source_name)
            if node_id not in seen:
                seen.add(node_id)
                nodes.append(
                    {
                        "id": node_id,
                        "name": node_id,
                        "type": citation.source_type,
                        "verified": citation.verified,
                    }
                )

        # 相同类型的引文之间建立"共引"关系
        source_names = [_safe_citation_text(c.source_name) for c in citations]
        for i in range(len(source_names)):
            for j in range(i + 1, len(source_names)):
                if source_names[i] != source_names[j]:
                    edges.append(
                        {
                            "source": source_names[i],
                            "target": source_names[j],
                            "relation": "共引",
                        }
                    )

        return {"nodes": nodes, "edges": edges}

    async def track_and_enrich(
        self,
        text: str,
        auto_sink_to_graph: bool = True,
    ) -> dict[str, Any]:
        """
        完整的引文追踪流程

        1. 提取引文
        2. 验证准确性
        3. 构建引文图
        4. 可选：将引文实体沉淀到知识图谱

        Returns:
            {citations: [...], graph: {...}, sunk_count: int}
        """
        if os.environ.get("PYTEST_CURRENT_TEST"):
            auto_sink_to_graph = False

        # 提取
        citations = self.extract_citations(text)
        if not citations:
            return {"citations": [], "graph": {"nodes": [], "edges": []}, "sunk_count": 0}

        # 验证
        citations = await self.verify_citations(citations)

        # 构建引文图
        graph = self.build_citation_graph(citations)

        # 沉淀到知识图谱
        sunk_count = 0
        if auto_sink_to_graph:
            sunk_count = await self._sink_to_knowledge_graph(citations)

        return {
            "citations": [c.to_dict() for c in citations],
            "citation_count": len(citations),
            "verified_count": sum(1 for c in citations if c.verified),
            "graph": graph,
            "sunk_count": sunk_count,
        }

    async def _sink_to_knowledge_graph(self, citations: list[Citation]) -> int:
        """将引文实体沉淀到知识图谱"""
        sunk = 0
        try:
            from src.services.graph_service import graph_service

            for citation in citations:
                try:
                    source_name = _safe_citation_text(citation.source_name)
                    await graph_service.create_entity(
                        name=source_name,
                        entity_type=citation.source_type,
                        properties={
                            "source": "citation_tracker",
                            "article": citation.article or "",
                            "verified": str(citation.verified),
                        },
                    )
                    sunk += 1
                except Exception:
                    pass  # 实体可能已存在

            # 创建共引关系
            names = list({_safe_citation_text(c.source_name) for c in citations})
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    try:
                        await graph_service.create_relation(
                            subject=names[i],
                            predicate="CITED_WITH",
                            obj=names[j],
                        )
                    except Exception:
                        pass

        except Exception as e:
            logger.debug(f"引文沉淀到图谱跳过: {e}")

        return sunk


# 全局实例
citation_tracker = CitationTracker()
