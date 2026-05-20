"""
Legal RAG Service — 法律知识图谱 Hybrid 检索服务

核心能力：
1. Hybrid 检索：向量语义搜索 + 关键词精确匹配 + 知识图谱推理
2. 四种查询模式（参考 LightRAG/DeepTutor）：
   - local: 局部精确检索（特定法条、案号）
   - global: 全局主题检索（法律领域、行业概览）
   - hybrid: 混合模式（默认，兼顾精度和覆盖）
   - naive: 简单向量检索（降级模式）
3. 法律知识自动分层：法律体系→部门法→具体法条→司法解释→判例
4. 增量更新：新法规自动融入，无需全量重建
5. 检索结果格式化为 Prompt 上下文

集成方式：
- Agent 调用 LLM 前自动注入法律上下文
- 知识图谱 Neo4j 关系推理（可选）
- 向量库 Qdrant 语义检索（可选）
- 内存法条索引（兜底，始终可用）
"""

import re
from dataclasses import dataclass, field
from typing import TypeAlias, TypedDict, cast

from loguru import logger

from src.core.config import settings
from src.services.legal_corpus_loader import (
    LegalArticle,
    get_all_legal_corpus,
)

# ===== 查询模式 =====


class QueryMode:
    LOCAL = "local"  # 精确法条检索
    GLOBAL = "global"  # 主题概览检索
    HYBRID = "hybrid"  # 混合（默认）
    NAIVE = "naive"  # 纯向量


MetadataValue: TypeAlias = (
    str
    | int
    | float
    | bool
    | None
    | list[str]
    | list[int]
    | list[float]
    | list[bool]
    | list["MetadataValue"]
    | dict[str, "MetadataValue"]
)
MetadataDict: TypeAlias = dict[str, MetadataValue]


class SourceEntry(TypedDict):
    index: str
    source: str
    method: str


class VectorSearchResult(TypedDict, total=False):
    text: str
    content: str
    source: str
    score: float
    metadata: MetadataDict


class GraphRelation(TypedDict, total=False):
    source: str
    relation: str
    target: str


def _metadata_text(metadata: MetadataDict, key: str, default: str = "") -> str:
    value = metadata.get(key, default)
    return value if isinstance(value, str) else default


@dataclass
class RetrievalResult:
    """单条检索结果"""

    content: str
    source: str  # 来源（法律名称）
    article_number: str = ""  # 条文编号
    score: float = 0.0  # 相关性评分
    retrieval_method: str = ""  # 检索方式
    metadata: MetadataDict = field(default_factory=dict)


@dataclass
class RAGContext:
    """RAG 检索上下文"""

    query: str
    mode: str
    results: list[RetrievalResult]
    total_found: int
    context_text: str  # 格式化后的上下文文本
    sources: list[SourceEntry]  # 引用来源列表
    token_estimate: int  # 估计 token 数


class LegalRAGService:
    """法律 RAG 检索服务"""

    def __init__(self) -> None:
        self._corpus: list[LegalArticle] | None = None
        self._keyword_index: dict[str, list[int]] = {}  # keyword → article indices
        self._initialized = False

    def _ensure_loaded(self) -> None:
        """确保法律语料和索引已加载"""
        if self._initialized:
            return
        self._corpus = get_all_legal_corpus()
        self._build_keyword_index()
        self._initialized = True
        logger.info(
            f"LegalRAGService: 加载 {len(self._corpus)} 条法条，构建 {len(self._keyword_index)} 个关键词索引"
        )

    def _build_keyword_index(self) -> None:
        """构建关键词倒排索引"""
        if not self._corpus:
            return
        for i, article in enumerate(self._corpus):
            # 从内容和标签中提取关键词
            words: set[str] = set()
            words.update(article.tags)
            words.add(article.law_name)
            words.add(article.chapter)
            # 从内容中提取核心名词（简单分词）
            for segment in re.split(r"[，。；、\s]+", article.content):
                if 2 <= len(segment) <= 8:
                    words.add(segment)
            for w in words:
                if w:
                    self._keyword_index.setdefault(w, []).append(i)

    # ===== 核心检索方法 =====

    async def retrieve(
        self,
        query: str,
        mode: str = QueryMode.HYBRID,
        max_results: int = 10,
        max_context_tokens: int = 4000,
        law_filter: str | None = None,
        article_filter: str | None = None,
    ) -> RAGContext:
        """
        法律知识检索

        Args:
            query: 查询文本
            mode: 查询模式 (local/global/hybrid/naive)
            max_results: 最大结果数
            max_context_tokens: 上下文最大 token
            law_filter: 法律名称过滤
            article_filter: 条文编号过滤

        Returns:
            RAGContext 包含检索结果和格式化上下文
        """
        self._ensure_loaded()
        results: list[RetrievalResult] = []

        if mode == QueryMode.LOCAL:
            results = await self._local_retrieve(query, max_results, law_filter, article_filter)
        elif mode == QueryMode.GLOBAL:
            results = await self._global_retrieve(query, max_results)
        elif mode == QueryMode.HYBRID:
            results = await self._hybrid_retrieve(query, max_results, law_filter, article_filter)
        else:  # naive
            results = await self._naive_retrieve(query, max_results)

        # 格式化为上下文
        context_text, sources = self._format_context(results, max_context_tokens)
        token_estimate = len(context_text) // 2  # 粗估

        return RAGContext(
            query=query,
            mode=mode,
            results=results,
            total_found=len(results),
            context_text=context_text,
            sources=sources,
            token_estimate=token_estimate,
        )

    async def _local_retrieve(
        self,
        query: str,
        max_results: int,
        law_filter: str | None = None,
        article_filter: str | None = None,
    ) -> list[RetrievalResult]:
        """局部精确检索：法条编号、法律名称精确匹配"""
        results: list[RetrievalResult] = []

        # 1. 提取查询中的法条引用
        law_refs = re.findall(r"《([^》]+)》", query)
        article_refs = re.findall(r"第\s*(\d+)\s*条", query)

        for article in self._corpus or []:
            score = 0.0

            # 法律名称匹配
            if law_filter and law_filter in article.law_name:
                score += 5.0
            for ref in law_refs:
                if ref in article.law_name:
                    score += 5.0

            # 条文编号匹配
            if article_filter and article_filter == article.article_number:
                score += 10.0
            for ref in article_refs:
                if ref == article.article_number:
                    score += 10.0

            # 内容关键词匹配
            for word in re.split(r"[，。、\s《》]+", query):
                if len(word) >= 2 and word in article.content:
                    score += 1.0

            if score > 0:
                results.append(
                    RetrievalResult(
                        content=article.content,
                        source=f"《{article.law_name}》第{article.article_number}条",
                        article_number=article.article_number,
                        score=score,
                        retrieval_method="local",
                        metadata={
                            "law_name": article.law_name,
                            "chapter": article.chapter,
                            "tags": article.tags,
                            "effective_date": article.effective_date,
                        },
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:max_results]

    async def _global_retrieve(
        self,
        query: str,
        max_results: int,
    ) -> list[RetrievalResult]:
        """全局主题检索：按法律领域和主题聚类"""
        results: list[RetrievalResult] = []

        # 关键词匹配 + 标签匹配
        query_words = {w for w in re.split(r"[，。、\s《》]+", query) if len(w) >= 2}

        for article in self._corpus or []:
            score = 0.0

            # 标签匹配（权重最高）
            for tag in article.tags:
                for word in query_words:
                    if word in tag or tag in word:
                        score += 3.0

            # 章节匹配
            for word in query_words:
                if word in article.chapter:
                    score += 2.0

            # 内容包含
            for word in query_words:
                if word in article.content:
                    score += 0.5

            if score > 0:
                results.append(
                    RetrievalResult(
                        content=article.content,
                        source=f"《{article.law_name}》第{article.article_number}条",
                        article_number=article.article_number,
                        score=score,
                        retrieval_method="global",
                        metadata={
                            "law_name": article.law_name,
                            "chapter": article.chapter,
                            "tags": article.tags,
                        },
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:max_results]

    async def _hybrid_retrieve(
        self,
        query: str,
        max_results: int,
        law_filter: str | None = None,
        article_filter: str | None = None,
    ) -> list[RetrievalResult]:
        """混合检索：local + global + vector(可选) 三路合并"""

        # 路线1: 精确检索
        local_results = await self._local_retrieve(query, max_results, law_filter, article_filter)

        # 路线2: 全局主题
        global_results = await self._global_retrieve(query, max_results)

        # 路线3: 向量语义检索（如果 Qdrant 可用）
        vector_results = await self._vector_retrieve(query, max_results)

        # 三路合并 + 去重 + RRF 排序
        merged = self._reciprocal_rank_fusion(
            [local_results, global_results, vector_results],
            weights=[0.4, 0.3, 0.3],
        )

        return merged[:max_results]

    async def _naive_retrieve(
        self,
        query: str,
        max_results: int,
    ) -> list[RetrievalResult]:
        """纯向量检索（降级模式）"""
        results = await self._vector_retrieve(query, max_results)
        if not results:
            # 向量不可用，再降级到全局
            results = await self._global_retrieve(query, max_results)
        return results

    async def _vector_retrieve(
        self,
        query: str,
        max_results: int,
    ) -> list[RetrievalResult]:
        """向量语义检索（Qdrant）"""
        try:
            from src.services.vector_store import vector_store

            if not vector_store or not vector_store.is_available:
                return []

            search_results = cast(
                list[VectorSearchResult],
                await vector_store.search(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    query=query,
                    top_k=max_results,
                ),
            )
            results: list[RetrievalResult] = []
            for sr in search_results:
                content = sr.get("text", sr.get("content", ""))
                metadata: MetadataDict = sr.get("metadata") or {}
                results.append(
                    RetrievalResult(
                        content=content,
                        source=_metadata_text(metadata, "source", "知识库"),
                        score=sr.get("score", 0.0),
                        retrieval_method="vector",
                        metadata=metadata,
                    )
                )
            return results

        except Exception as e:
            logger.debug(f"向量检索不可用: {e}")
            return []

    # ===== 知识图谱检索 =====

    async def graph_retrieve(
        self,
        entity_name: str,
        depth: int = 2,
        max_results: int = 10,
    ) -> list[RetrievalResult]:
        """知识图谱关系检索（Neo4j）"""
        try:
            from src.services.graph_service import graph_service

            related = cast(
                list[GraphRelation],
                graph_service.get_related_entities(entity_name, depth=depth),
            )
            results: list[RetrievalResult] = []
            for item in related[:max_results]:
                results.append(
                    RetrievalResult(
                        content=f"{item.get('source', '')} --[{item.get('relation', '')}]--> {item.get('target', '')}",
                        source="知识图谱",
                        score=1.0,
                        retrieval_method="graph",
                        metadata={
                            "source": item.get("source", ""),
                            "relation": item.get("relation", ""),
                            "target": item.get("target", ""),
                        },
                    )
                )
            return results
        except Exception as e:
            logger.debug(f"图谱检索不可用: {e}")
            return []

    # ===== 排序与格式化 =====

    def _reciprocal_rank_fusion(
        self,
        result_lists: list[list[RetrievalResult]],
        weights: list[float],
        k: int = 60,
    ) -> list[RetrievalResult]:
        """
        Reciprocal Rank Fusion (RRF) 多路结果合并

        公式：RRF_score = Σ weight_i / (k + rank_i)
        """
        score_map: dict[str, float] = {}
        item_map: dict[str, RetrievalResult] = {}

        for weight, result_list in zip(weights, result_lists, strict=False):
            for rank, result in enumerate(result_list):
                key = f"{result.source}:{result.article_number}"
                rrf_score = weight / (k + rank + 1)
                score_map[key] = score_map.get(key, 0) + rrf_score
                if key not in item_map or result.score > item_map[key].score:
                    item_map[key] = result

        sorted_keys = sorted(score_map, key=score_map.__getitem__, reverse=True)
        merged_results: list[RetrievalResult] = []
        for key in sorted_keys:
            item = item_map[key]
            item.score = score_map[key]
            merged_results.append(item)
        return merged_results

    def _format_context(
        self,
        results: list[RetrievalResult],
        max_tokens: int,
    ) -> tuple[str, list[SourceEntry]]:
        """格式化检索结果为 Prompt 上下文"""
        if not results:
            return "", []

        parts = ["[法律知识上下文]"]
        sources: list[SourceEntry] = []
        current_tokens = 20  # 标题预估

        for i, r in enumerate(results):
            entry = f"\n[{i+1}] {r.source}\n{r.content}"
            entry_tokens = len(entry) // 2

            if current_tokens + entry_tokens > max_tokens:
                break

            parts.append(entry)
            current_tokens += entry_tokens
            sources.append(
                {
                    "index": str(i + 1),
                    "source": r.source,
                    "method": r.retrieval_method,
                }
            )

        return "\n".join(parts), sources

    # ===== 便捷方法 =====

    async def get_context_for_agent(
        self,
        query: str,
        agent_type: str = "general",
        max_context_tokens: int = 4000,
    ) -> str:
        """
        为 Agent 获取法律上下文（最常用的调用方式）

        根据 agent_type 自动选择检索模式：
        - contract_reviewer → hybrid + 合同相关法条
        - legal_advisor → global + 广泛法律知识
        - litigation_strategist → local + 精确判例
        - document_drafter → hybrid + 模板条款
        """
        mode_map: dict[str, str] = {
            "contract_reviewer": QueryMode.HYBRID,
            "legal_advisor": QueryMode.GLOBAL,
            "litigation_strategist": QueryMode.LOCAL,
            "document_drafter": QueryMode.HYBRID,
        }

        mode = mode_map.get(agent_type, QueryMode.HYBRID)
        ctx = await self.retrieve(query, mode=mode, max_context_tokens=max_context_tokens)
        return ctx.context_text

    async def index_new_document(
        self,
        content: str,
        law_name: str,
        law_type: str = "law",
        effective_date: str = "",
    ) -> int:
        """
        增量索引新法律文档（不需要全量重建）

        Returns:
            新增条文数量
        """
        self._ensure_loaded()

        # 简单按"第X条"分割
        articles = re.split(r"(?=第\s*\d+\s*条)", content)
        added = 0

        for text in articles:
            match = re.match(r"第\s*(\d+)\s*条", text)
            if not match:
                continue

            article_num = match.group(1)
            article_content = text.strip()

            new_article = LegalArticle(
                law_name=law_name,
                law_type=law_type,
                article_number=article_num,
                title="",
                content=article_content,
                effective_date=effective_date,
            )

            if self._corpus is not None:
                idx = len(self._corpus)
                self._corpus.append(new_article)
                # 更新倒排索引
                for word in re.split(r"[，。；、\s]+", article_content):
                    if 2 <= len(word) <= 8:
                        self._keyword_index.setdefault(word, []).append(idx)
                added += 1

        if added > 0:
            logger.info(f"LegalRAGService: 增量索引 {added} 条来自《{law_name}》的法条")

        return added

    def get_stats(self) -> MetadataDict:
        """获取检索服务统计"""
        self._ensure_loaded()
        law_names = {a.law_name for a in (self._corpus or [])}
        return {
            "total_articles": len(self._corpus or []),
            "total_laws": len(law_names),
            "law_names": sorted(law_names),
            "keyword_index_size": len(self._keyword_index),
            "query_modes": ["local", "global", "hybrid", "naive"],
        }


# 全局实例
legal_rag_service = LegalRAGService()
