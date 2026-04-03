# -*- coding: utf-8 -*-
"""
Agent RAG增强服务

为所有法律Agent提供统一的RAG检索接口。
Agent在调用LLM之前，先检索相关的法律知识作为上下文注入。

使用方式：
    from src.services.agent_rag_service import AgentRAGService

    rag = AgentRAGService()
    context = await rag.get_legal_context("合同违约金是否可以调整？")
    # 将context注入到agent的prompt中
"""

from typing import Optional, List, Dict, Any
from loguru import logger

from src.services.legal_corpus_loader import (
    get_all_legal_corpus,
    LegalArticle,
    format_articles_for_rag_context,
)
from src.services.legal_citation import LegalCitationService


class AgentRAGService:
    """Agent RAG增强服务 — 为Agent提供法律知识检索"""

    # 内存法条索引（轻量级，用于无Qdrant环境）
    _corpus: Optional[List[LegalArticle]] = None
    _initialized: bool = False

    @classmethod
    def _ensure_loaded(cls):
        """确保法律语料已加载到内存"""
        if not cls._initialized:
            cls._corpus = get_all_legal_corpus()
            cls._initialized = True
            logger.info(f"AgentRAGService: 加载 {len(cls._corpus)} 条法律条文到内存")

    @classmethod
    async def get_legal_context(
        cls,
        query: str,
        contract_type: Optional[str] = None,
        max_articles: int = 8,
        max_context_length: int = 4000,
    ) -> str:
        """
        根据查询获取相关法律条文作为RAG上下文

        优先使用Qdrant向量检索，降级为内存关键词匹配。

        Args:
            query: 查询文本（合同内容/用户问题）
            contract_type: 合同类型（用于过滤）
            max_articles: 最大返回条文数
            max_context_length: 上下文最大字符数

        Returns:
            格式化的法律条文上下文文本
        """
        # 尝试向量检索
        try:
            return await cls._vector_search(query, contract_type, max_articles, max_context_length)
        except Exception as e:
            logger.debug(f"向量检索不可用({e})，降级为关键词匹配")

        # 降级为内存关键词匹配
        return cls._keyword_search(query, contract_type, max_articles, max_context_length)

    @classmethod
    async def _vector_search(
        cls,
        query: str,
        contract_type: Optional[str],
        max_articles: int,
        max_context_length: int,
    ) -> str:
        """通过Qdrant向量检索"""
        from src.services.vector_store import semantic_search
        from src.core.config import get_settings

        settings = get_settings()

        results = await semantic_search(
            query=query,
            collection_name=settings.QDRANT_COLLECTION_NAME,
            top_k=max_articles,
            score_threshold=settings.RAG_SCORE_THRESHOLD,
        )

        if not results:
            # 向量库为空或无匹配，降级
            raise ValueError("向量检索无结果")

        context_parts = []
        total_len = 0
        for result in results:
            payload = result.get("payload", {})
            text = payload.get("content", payload.get("text", ""))
            source = payload.get("source", "")
            score = result.get("score", 0)

            entry = f"【{source}】(相关度: {score:.2f})\n{text}\n"
            if total_len + len(entry) > max_context_length:
                break
            context_parts.append(entry)
            total_len += len(entry)

        return "\n".join(context_parts)

    @classmethod
    def _keyword_search(
        cls,
        query: str,
        contract_type: Optional[str],
        max_articles: int,
        max_context_length: int,
    ) -> str:
        """内存关键词匹配（降级方案，零外部依赖）"""
        cls._ensure_loaded()
        if not cls._corpus:
            return ""

        # 提取查询关键词
        keywords = cls._extract_keywords(query)
        if contract_type:
            keywords.extend(cls._extract_keywords(contract_type))

        # 对每个法条计算匹配分数
        scored_articles = []
        for article in cls._corpus:
            score = cls._calculate_relevance(article, keywords)
            if score > 0:
                scored_articles.append((score, article))

        # 按分数排序，取top-k
        scored_articles.sort(key=lambda x: x[0], reverse=True)
        top_articles = [art for _, art in scored_articles[:max_articles]]

        return format_articles_for_rag_context(top_articles, max_context_length)

    @classmethod
    def _extract_keywords(cls, text: str) -> List[str]:
        """提取搜索关键词"""
        # 法律相关关键词
        legal_terms = [
            "违约", "赔偿", "解除", "终止", "不可抗力", "免责", "格式条款",
            "违约金", "损害", "瑕疵", "担保", "保证", "抵押", "质押",
            "租赁", "买卖", "劳动", "雇佣", "服务", "委托", "借款",
            "保密", "竞业", "知识产权", "著作权", "专利", "商标",
            "试用期", "工资", "社保", "经济补偿", "辞职", "解雇",
            "风险转移", "验收", "交付", "付款", "发票",
            "诉讼", "仲裁", "管辖", "时效", "举证",
            "合同成立", "合同生效", "合同效力", "无效", "可撤销",
            "股权", "投资", "对赌", "分红", "公司章程",
            "个人信息", "数据安全", "隐私", "消费者",
        ]

        keywords = []
        for term in legal_terms:
            if term in text:
                keywords.append(term)

        # 也提取法条编号引用
        import re
        article_refs = re.findall(r'第(\d+)条', text)
        for ref in article_refs:
            keywords.append(f"第{ref}条")

        return keywords

    @classmethod
    def _calculate_relevance(cls, article: LegalArticle, keywords: List[str]) -> float:
        """计算法条与关键词的相关性分数"""
        score = 0.0
        searchable = f"{article.title} {article.content} {' '.join(article.tags)}"

        for keyword in keywords:
            if keyword in searchable:
                # 标题匹配权重更高
                if keyword in article.title:
                    score += 3.0
                # 标签匹配
                elif keyword in article.tags:
                    score += 2.0
                # 内容匹配
                else:
                    score += 1.0

            # 条文编号精确匹配
            if keyword.startswith("第") and keyword == article.article_number:
                score += 5.0

        return score

    @classmethod
    def build_rag_prompt_section(cls, context: str, task_type: str = "review") -> str:
        """
        构建RAG上下文的Prompt片段

        Args:
            context: 检索到的法律条文
            task_type: 任务类型（review/draft/consult）

        Returns:
            可直接插入Prompt的上下文片段
        """
        if not context:
            return ""

        headers = {
            "review": "以下是与本合同相关的法律条文，请在审查时引用：",
            "draft": "以下是与本文书相关的法律条文，请在起草时参考并引用：",
            "consult": "以下是与本问题相关的法律条文，请在回答时引用：",
        }

        header = headers.get(task_type, headers["consult"])

        return f"""
【RAG检索到的法律依据】
{header}

{context}

注意：请在回答中引用上述法条时使用"《法律名称》第XXX条"的标准格式。
"""
