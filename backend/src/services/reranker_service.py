"""
Reranker 重排序服务

使用交叉编码器对检索结果进行重排序，提高检索准确性

支持多种重排序方式：
1. 本地模型（sentence-transformers CrossEncoder）
2. API 调用（如 Cohere Rerank、Jina Reranker）
3. LLM 重排序（使用 GPT 等大模型）
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from loguru import logger

from src.core.config import settings


class RerankerType(str, Enum):
    """重排序器类型"""
    LOCAL = "local"           # 本地 CrossEncoder 模型
    COHERE = "cohere"         # Cohere Rerank API
    JINA = "jina"             # Jina Reranker API
    LLM = "llm"               # 使用 LLM 重排序
    NONE = "none"             # 不使用重排序


@dataclass
class RerankResult:
    """重排序结果"""
    id: str
    content: str
    original_score: float     # 原始向量搜索分数
    rerank_score: float       # 重排序分数
    final_score: float        # 最终分数
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "original_score": self.original_score,
            "rerank_score": self.rerank_score,
            "final_score": self.final_score,
            "metadata": self.metadata,
        }


@dataclass
class RerankerConfig:
    """重排序配置"""
    reranker_type: RerankerType = RerankerType.LOCAL
    model_name: str = "BAAI/bge-reranker-base"  # 本地模型名称
    api_key: str | None = None               # API 密钥
    api_base_url: str | None = None          # API 基础 URL
    top_k: int = 5                              # 重排序后返回的结果数
    score_threshold: float = 0.0                # 重排序分数阈值
    weight_original: float = 0.3                # 原始分数权重
    weight_rerank: float = 0.7                  # 重排序分数权重


class RerankerService:
    """重排序服务"""

    def __init__(self, config: RerankerConfig | None = None) -> None:
        self.config = config or RerankerConfig()
        self.cross_encoder = None
        self._init_reranker()

    def _init_reranker(self) -> None:
        """初始化重排序器"""
        if self.config.reranker_type == RerankerType.LOCAL:
            self._init_local_reranker()
        elif self.config.reranker_type == RerankerType.COHERE:
            self._init_cohere_client()
        elif self.config.reranker_type == RerankerType.JINA:
            self._init_jina_client()

    def _init_local_reranker(self) -> None:
        """初始化本地 CrossEncoder 模型"""
        try:
            from sentence_transformers import CrossEncoder

            model_name = self.config.model_name
            self.cross_encoder = CrossEncoder(model_name)

            logger.info(f"本地 Reranker 模型初始化成功: {model_name}")

        except ImportError:
            logger.warning("sentence-transformers 未安装，本地重排序不可用")
        except Exception as e:
            logger.error(f"本地 Reranker 初始化失败: {e}")

    def _init_cohere_client(self) -> None:
        """初始化 Cohere 客户端"""
        try:
            import cohere

            api_key = self.config.api_key or getattr(settings, 'COHERE_API_KEY', None)
            if api_key:
                self.cohere_client = cohere.Client(api_key)
                logger.info("Cohere Reranker 客户端初始化成功")
            else:
                logger.warning("未配置 Cohere API Key")

        except ImportError:
            logger.warning("cohere 未安装")
        except Exception as e:
            logger.error(f"Cohere 客户端初始化失败: {e}")

    def _init_jina_client(self) -> None:
        """初始化 Jina 客户端"""
        # Jina Reranker 使用 HTTP API
        self.jina_api_key = self.config.api_key or getattr(settings, 'JINA_API_KEY', None)
        if self.jina_api_key:
            logger.info("Jina Reranker 配置成功")
        else:
            logger.warning("未配置 Jina API Key")

    @property
    def is_available(self) -> bool:
        """检查重排序服务是否可用"""
        if self.config.reranker_type == RerankerType.LOCAL:
            return self.cross_encoder is not None
        elif self.config.reranker_type == RerankerType.COHERE:
            return hasattr(self, 'cohere_client') and self.cohere_client is not None
        elif self.config.reranker_type == RerankerType.JINA:
            return hasattr(self, 'jina_api_key') and self.jina_api_key is not None
        elif self.config.reranker_type == RerankerType.LLM:
            return True  # LLM 重排序始终可用（依赖外部 LLM 服务）
        return False

    async def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int | None = None,
    ) -> list[RerankResult]:
        """
        对文档进行重排序
        
        Args:
            query: 查询文本
            documents: 文档列表，每个文档需包含 id, content, score
            top_k: 返回结果数（可选）
            
        Returns:
            重排序后的结果列表
        """
        if not documents:
            return []

        top_k = top_k or self.config.top_k

        # 根据类型选择重排序方法
        if self.config.reranker_type == RerankerType.LOCAL:
            results = await self._rerank_local(query, documents)
        elif self.config.reranker_type == RerankerType.COHERE:
            results = await self._rerank_cohere(query, documents)
        elif self.config.reranker_type == RerankerType.JINA:
            results = await self._rerank_jina(query, documents)
        elif self.config.reranker_type == RerankerType.LLM:
            results = await self._rerank_llm(query, documents)
        else:
            # 不使用重排序，保持原顺序
            results = self._convert_to_results(documents)

        # 按最终分数排序
        results.sort(key=lambda x: x.final_score, reverse=True)

        # 过滤低分结果
        if self.config.score_threshold > 0:
            results = [r for r in results if r.final_score >= self.config.score_threshold]

        return results[:top_k]

    async def _rerank_local(
        self,
        query: str,
        documents: list[dict[str, Any]],
    ) -> list[RerankResult]:
        """使用本地 CrossEncoder 重排序"""
        if not self.cross_encoder:
            return self._convert_to_results(documents)

        try:
            # 准备查询-文档对
            pairs = [(query, doc.get("content", "")) for doc in documents]

            # 获取重排序分数
            scores = self.cross_encoder.predict(pairs)

            # 归一化分数到 0-1 范围
            min_score = min(scores)
            max_score = max(scores)
            if max_score > min_score:
                normalized_scores = [(s - min_score) / (max_score - min_score) for s in scores]
            else:
                normalized_scores = [0.5] * len(scores)

            # 构建结果
            results = []
            for doc, rerank_score in zip(documents, normalized_scores, strict=False):
                original_score = doc.get("score", 0.5)
                final_score = (
                    original_score * self.config.weight_original +
                    rerank_score * self.config.weight_rerank
                )

                results.append(RerankResult(
                    id=doc.get("id", ""),
                    content=doc.get("content", ""),
                    original_score=original_score,
                    rerank_score=rerank_score,
                    final_score=final_score,
                    metadata=doc.get("metadata", {}),
                ))

            return results

        except Exception as e:
            logger.error(f"本地重排序失败: {e}")
            return self._convert_to_results(documents)

    async def _rerank_cohere(
        self,
        query: str,
        documents: list[dict[str, Any]],
    ) -> list[RerankResult]:
        """使用 Cohere Rerank API"""
        if not hasattr(self, 'cohere_client'):
            return self._convert_to_results(documents)

        try:
            # 准备文档列表
            doc_texts = [doc.get("content", "") for doc in documents]

            # 调用 Cohere Rerank API
            response = self.cohere_client.rerank(
                model="rerank-multilingual-v2.0",
                query=query,
                documents=doc_texts,
                top_n=len(documents),
            )

            # 构建结果映射
            rerank_scores = {r.index: r.relevance_score for r in response.results}

            results = []
            for i, doc in enumerate(documents):
                original_score = doc.get("score", 0.5)
                rerank_score = rerank_scores.get(i, 0.5)
                final_score = (
                    original_score * self.config.weight_original +
                    rerank_score * self.config.weight_rerank
                )

                results.append(RerankResult(
                    id=doc.get("id", ""),
                    content=doc.get("content", ""),
                    original_score=original_score,
                    rerank_score=rerank_score,
                    final_score=final_score,
                    metadata=doc.get("metadata", {}),
                ))

            return results

        except Exception as e:
            logger.error(f"Cohere 重排序失败: {e}")
            return self._convert_to_results(documents)

    async def _rerank_jina(
        self,
        query: str,
        documents: list[dict[str, Any]],
    ) -> list[RerankResult]:
        """使用 Jina Reranker API"""
        if not hasattr(self, 'jina_api_key') or not self.jina_api_key:
            return self._convert_to_results(documents)

        try:
            import httpx

            # 准备请求数据
            doc_texts = [doc.get("content", "") for doc in documents]

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.jina.ai/v1/rerank",
                    headers={
                        "Authorization": f"Bearer {self.jina_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "jina-reranker-v1-base-en",
                        "query": query,
                        "documents": doc_texts,
                        "top_n": len(documents),
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

            # 构建结果映射
            rerank_scores = {r["index"]: r["relevance_score"] for r in data["results"]}

            results = []
            for i, doc in enumerate(documents):
                original_score = doc.get("score", 0.5)
                rerank_score = rerank_scores.get(i, 0.5)
                final_score = (
                    original_score * self.config.weight_original +
                    rerank_score * self.config.weight_rerank
                )

                results.append(RerankResult(
                    id=doc.get("id", ""),
                    content=doc.get("content", ""),
                    original_score=original_score,
                    rerank_score=rerank_score,
                    final_score=final_score,
                    metadata=doc.get("metadata", {}),
                ))

            return results

        except Exception as e:
            logger.error(f"Jina 重排序失败: {e}")
            return self._convert_to_results(documents)

    async def _rerank_llm(
        self,
        query: str,
        documents: list[dict[str, Any]],
    ) -> list[RerankResult]:
        """使用 LLM 进行重排序"""
        try:
            # 构建重排序提示
            doc_list = "\n".join([
                f"[{i+1}] {doc.get('content', '')[:500]}"
                for i, doc in enumerate(documents)
            ])

            prompt = f"""请根据查询与文档的相关性，对以下文档进行排序。
返回格式：按相关性从高到低排列的文档编号，用逗号分隔。

查询：{query}

文档列表：
{doc_list}

请直接返回排序后的编号（如：3,1,5,2,4），不要有其他内容。"""

            if "/api/v1/chat" in (settings.LLM_BASE_URL or ""):
                # 本地模型服务
                import httpx
                input_text = prompt
                resp = httpx.post(
                    settings.LLM_BASE_URL.rstrip("/"),
                    headers={
                        "Authorization": f"Bearer {settings.LLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={"model": settings.LLM_MODEL, "input": input_text, "stream": False},
                    timeout=60.0,
                )
                resp.raise_for_status()
                data = resp.json()
                output_list = data.get("output", [])
                order_str = ""
                for item in output_list:
                    if isinstance(item, dict) and item.get("content"):
                        order_str += item["content"]
                if not order_str:
                    choices = data.get("choices", [])
                    if choices:
                        order_str = choices[0].get("message", {}).get("content", "")
                order_str = order_str.strip()
            else:
                from openai import OpenAI
                from openai.types.chat import ChatCompletionUserMessageParam

                client = OpenAI(
                    api_key=settings.LLM_API_KEY,
                    base_url=settings.LLM_BASE_URL,
                )
                messages: list[ChatCompletionUserMessageParam] = [
                    {"role": "user", "content": prompt}
                ]
                response = client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=messages,
                    temperature=0,
                    max_tokens=100,
                )
                content = response.choices[0].message.content
                order_str = content.strip() if content is not None else ""
            order = [int(x.strip()) - 1 for x in order_str.split(",") if x.strip().isdigit()]

            # 计算重排序分数
            results = []
            total = len(documents)
            for rank, idx in enumerate(order):
                if 0 <= idx < len(documents):
                    doc = documents[idx]
                    original_score = doc.get("score", 0.5)
                    # 根据排名计算分数
                    rerank_score = (total - rank) / total
                    final_score = (
                        original_score * self.config.weight_original +
                        rerank_score * self.config.weight_rerank
                    )

                    results.append(RerankResult(
                        id=doc.get("id", ""),
                        content=doc.get("content", ""),
                        original_score=original_score,
                        rerank_score=rerank_score,
                        final_score=final_score,
                        metadata=doc.get("metadata", {}),
                    ))

            # 添加未被排序的文档
            ranked_indices = set(order)
            for i, doc in enumerate(documents):
                if i not in ranked_indices:
                    original_score = doc.get("score", 0.5)
                    results.append(RerankResult(
                        id=doc.get("id", ""),
                        content=doc.get("content", ""),
                        original_score=original_score,
                        rerank_score=0.0,
                        final_score=original_score * self.config.weight_original,
                        metadata=doc.get("metadata", {}),
                    ))

            return results

        except Exception as e:
            logger.error(f"LLM 重排序失败: {e}")
            return self._convert_to_results(documents)

    def _convert_to_results(
        self,
        documents: list[dict[str, Any]],
    ) -> list[RerankResult]:
        """将文档转换为结果格式（不进行重排序）"""
        return [
            RerankResult(
                id=doc.get("id", ""),
                content=doc.get("content", ""),
                original_score=doc.get("score", 0.5),
                rerank_score=doc.get("score", 0.5),
                final_score=doc.get("score", 0.5),
                metadata=doc.get("metadata", {}),
            )
            for doc in documents
        ]


# 创建默认实例
reranker_config = RerankerConfig(
    reranker_type=RerankerType.NONE,
    model_name="BAAI/bge-reranker-base",
)

# 尝试初始化，如果本地模型不可用则降级
try:
    reranker_service = RerankerService(reranker_config)
except Exception:
    reranker_config.reranker_type = RerankerType.NONE
    reranker_service = RerankerService(reranker_config)


# 便捷函数
async def rerank_results(
    query: str,
    documents: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    重排序搜索结果
    
    Args:
        query: 查询文本
        documents: 搜索结果列表
        top_k: 返回结果数
        
    Returns:
        重排序后的结果
    """
    results = await reranker_service.rerank(query, documents, top_k)
    return [r.to_dict() for r in results]
