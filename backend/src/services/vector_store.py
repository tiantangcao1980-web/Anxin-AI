"""
向量存储服务

使用 Qdrant 进行向量存储和检索
支持文档向量化、相似度搜索
支持 OpenAI API 和本地 sentence-transformers 两种 Embedding 方式
"""

import hashlib
from typing import Any, cast

from loguru import logger

from src.core.config import settings


class VectorStoreService:
    """
    向量存储服务
    
    支持两种 Embedding 模式：
    1. OpenAI API（或兼容的 API）
    2. 本地 sentence-transformers 模型
    """

    def __init__(self) -> None:
        self.client: Any | None = None  # Qdrant 客户端
        self.embedding_model: str | None = None  # Embedding 模型名称
        self.openai_client: Any | None = None  # OpenAI 客户端（API 模式）
        self.local_model: Any | None = None  # 本地 sentence-transformers 模型
        self.embedding_dim = 1536  # 向量维度
        self.use_local_embedding = settings.USE_LOCAL_EMBEDDING  # 是否使用本地模型

        self._init_client()
        self._init_embedding()

    def _init_client(self) -> None:
        """初始化 Qdrant 客户端连接"""
        try:
            from qdrant_client import QdrantClient

            # 优先使用 URL 配置，其次使用 HOST:PORT 配置
            qdrant_url = settings.QDRANT_URL

            if qdrant_url and qdrant_url.startswith("http"):
                # 使用 URL 连接
                self.client = QdrantClient(
                    url=qdrant_url,
                    api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
                    timeout=30,
                )
                logger.info(f"Qdrant 客户端初始化成功 (URL模式): {qdrant_url}")
            elif settings.QDRANT_HOST:
                # 使用 HOST:PORT 连接
                self.client = QdrantClient(
                    host=settings.QDRANT_HOST,
                    port=settings.QDRANT_PORT,
                    api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
                    timeout=30,
                )
                logger.info(f"Qdrant 客户端初始化成功 (HOST模式): {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
            else:
                # 内存模式（用于测试）
                self.client = QdrantClient(path=":memory:")
                logger.warning("Qdrant 使用内存模式，数据不会持久化")

        except ImportError:
            logger.warning("qdrant-client 未安装，向量存储功能不可用")
            self.client = None
        except Exception as e:
            logger.error(f"Qdrant 客户端初始化失败: {e}")
            self.client = None

    def _init_embedding(self) -> None:
        """
        初始化 Embedding 模型
        
        根据配置选择使用本地 sentence-transformers 模型或 OpenAI API
        """
        if self.use_local_embedding:
            self._init_local_embedding()
        else:
            self._init_openai_embedding()

    def _init_local_embedding(self) -> None:
        """初始化本地 sentence-transformers Embedding 模型"""
        try:
            from sentence_transformers import SentenceTransformer

            model_name = settings.LOCAL_EMBEDDING_MODEL
            self.local_model = SentenceTransformer(model_name)
            self.embedding_model = model_name

            # 获取模型的向量维度
            self.embedding_dim = self.local_model.get_sentence_embedding_dimension()

            logger.info(f"本地 Embedding 模型初始化成功: {model_name} (维度: {self.embedding_dim})")

        except ImportError:
            logger.warning("sentence-transformers 未安装，尝试回退到 OpenAI API")
            self.use_local_embedding = False
            self._init_openai_embedding()
        except Exception as e:
            logger.error(f"本地 Embedding 模型初始化失败: {e}")
            logger.info("尝试回退到 OpenAI API")
            self.use_local_embedding = False
            self._init_openai_embedding()

    def _init_openai_embedding(self) -> None:
        """初始化 OpenAI API Embedding"""
        try:
            from openai import OpenAI

            # 优先使用 Embedding 专用配置，否则回退到 LLM 配置
            api_key = settings.EMBEDDING_API_KEY or settings.LLM_API_KEY
            base_url = settings.EMBEDDING_BASE_URL or settings.LLM_BASE_URL

            if not api_key:
                logger.warning("未配置 Embedding API Key，向量化功能不可用")
                return

            self.openai_client = OpenAI(
                api_key=api_key,
                base_url=base_url,
            )
            self.embedding_model = settings.EMBEDDING_MODEL or "text-embedding-3-small"
            self.embedding_dim = settings.EMBEDDING_DIMENSIONS or 1536

            logger.info(f"OpenAI Embedding 模型初始化成功: {self.embedding_model} (维度: {self.embedding_dim})")

        except ImportError:
            logger.warning("openai 未安装，向量化功能不可用")
        except Exception as e:
            logger.error(f"OpenAI Embedding 模型初始化失败: {e}")

    @property
    def is_available(self) -> bool:
        """检查服务是否可用"""
        has_embedding = (
            self.local_model is not None if self.use_local_embedding
            else self.openai_client is not None
        )
        return self.client is not None and has_embedding

    @property
    def embedding_info(self) -> dict[str, Any]:
        """获取当前 Embedding 配置信息"""
        return {
            "model": self.embedding_model,
            "dimensions": self.embedding_dim,
            "type": "local" if self.use_local_embedding else "api",
            "available": self.is_available,
        }

    async def create_collection(
        self,
        collection_name: str,
        recreate: bool = False,
    ) -> bool:
        """创建向量集合"""
        if not self.client:
            return False

        try:
            import asyncio

            from qdrant_client.models import Distance, VectorParams
            client = cast(Any, self.client)

            # 检查集合是否存在
            collections = await asyncio.to_thread(
                lambda: client.get_collections().collections
            )
            exists = any(c.name == collection_name for c in collections)
            need_create = False

            if exists:
                if recreate:
                    await asyncio.to_thread(client.delete_collection, collection_name)
                    logger.info(f"已删除旧集合: {collection_name} (recreate=True)")
                    need_create = True
                else:
                    # 检查已有集合的向量维度是否与当前配置一致
                    try:
                        info = await asyncio.to_thread(
                            self.client.get_collection, collection_name
                        )
                        existing_dim = info.config.params.vectors.size
                        if existing_dim != self.embedding_dim:
                            logger.warning(
                                f"集合 {collection_name} 维度不匹配: "
                                f"已有 {existing_dim}, 当前配置 {self.embedding_dim}，自动重建"
                            )
                            await asyncio.to_thread(
                                client.delete_collection, collection_name
                            )
                            need_create = True
                        else:
                            return True
                    except Exception:
                        return True
            else:
                need_create = True

            if need_create:
                # 删除后等待 Qdrant 释放资源，避免紧接着 create 超时
                if exists:
                    await asyncio.sleep(2.0)

                await asyncio.to_thread(
                    lambda: client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=self.embedding_dim,
                            distance=Distance.COSINE,
                        ),
                    )
                )
                logger.info(f"向量集合创建成功: {collection_name} (维度: {self.embedding_dim})")

            return True

        except Exception as e:
            logger.error(f"创建向量集合失败: {e}")
            return False

    async def get_embedding(self, text: str) -> list[float] | None:
        """
        获取文本的向量表示
        
        根据配置自动选择本地模型或 API
        
        Args:
            text: 需要向量化的文本
            
        Returns:
            向量列表，失败返回 None
        """
        if not text or not text.strip():
            return None

        # 清理文本
        text = text.strip()

        if self.use_local_embedding:
            return await self._get_local_embedding(text)
        else:
            return await self._get_api_embedding(text)

    async def _get_local_embedding(self, text: str) -> list[float] | None:
        """使用本地 sentence-transformers 模型获取向量"""
        if not self.local_model:
            return None

        try:
            # 截断过长的文本（sentence-transformers 通常限制 512 tokens）
            max_length = 8000
            if len(text) > max_length:
                text = text[:max_length]

            # sentence-transformers 是同步的，但速度很快
            embedding = self.local_model.encode(text, normalize_embeddings=True)

            return cast(list[float], embedding.tolist())

        except Exception as e:
            logger.error(f"本地 Embedding 获取失败: {e}")
            return None

    async def _get_api_embedding(self, text: str) -> list[float] | None:
        """使用 OpenAI API 获取向量"""
        if not self.openai_client:
            return None

        try:
            # 截断过长的文本
            max_tokens = 8000
            if len(text) > max_tokens * 4:  # 粗略估计（1 token ≈ 4 字符）
                text = text[:max_tokens * 4]

            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )

            return cast(list[float], response.data[0].embedding)

        except Exception as e:
            logger.error(f"API Embedding 获取失败: {e}")
            return None

    async def get_embeddings_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
    ) -> list[list[float] | None]:
        """
        批量获取文本向量
        
        Args:
            texts: 文本列表
            batch_size: 批处理大小
            
        Returns:
            向量列表
        """
        if not texts:
            return []

        if self.use_local_embedding and self.local_model:
            # 本地模型支持批量处理
            try:
                cleaned_texts = [t.strip()[:8000] if t else "" for t in texts]
                embeddings = self.local_model.encode(
                    cleaned_texts,
                    normalize_embeddings=True,
                    batch_size=batch_size,
                    show_progress_bar=False,
                )
                return [e.tolist() for e in embeddings]
            except Exception as e:
                logger.error(f"批量 Embedding 失败: {e}")
                return [None] * len(texts)
        else:
            # API 模式逐个处理
            results = []
            for text in texts:
                embedding = await self.get_embedding(text)
                results.append(embedding)
            return results

    async def add_documents(
        self,
        collection_name: str,
        documents: list[dict[str, Any]],
    ) -> int:
        """
        添加文档到向量集合
        
        Args:
            collection_name: 集合名称
            documents: 文档列表，每个文档包含 id, content, metadata
            
        Returns:
            成功添加的文档数量
        """
        if not self.is_available:
            return 0

        try:
            from qdrant_client.models import PointStruct

            # 确保集合存在
            await self.create_collection(collection_name)

            points = []
            for doc in documents:
                # 获取向量
                embedding = await self.get_embedding(doc.get("content", ""))
                if not embedding:
                    continue

                # 生成数值 ID
                doc_id = doc.get("id", "")
                point_id = int(hashlib.md5(doc_id.encode()).hexdigest()[:8], 16)

                points.append(PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "doc_id": doc_id,
                        "title": doc.get("title", ""),
                        "content": doc.get("content", "")[:1000],  # 存储部分内容
                        "source": doc.get("source", ""),
                        **doc.get("metadata", {}),
                    }
                ))

            if points:
                client = cast(Any, self.client)
                client.upsert(
                    collection_name=collection_name,
                    points=points,
                )
                logger.info(f"添加 {len(points)} 个文档到集合 {collection_name}")

            return len(points)

        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return 0

    async def search(
        self,
        collection_name: str,
        query: str,
        top_k: int | None = None,
        score_threshold: float | None = None,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        向量相似度搜索
        
        Args:
            collection_name: 集合名称
            query: 查询文本
            top_k: 返回结果数量，默认使用配置值
            score_threshold: 最低相似度阈值，默认使用配置值
            filter_conditions: 过滤条件
            
        Returns:
            搜索结果列表
        """
        if not self.is_available:
            return []

        # 使用配置的默认值
        if top_k is None:
            top_k = settings.RAG_TOP_K
        if score_threshold is None:
            score_threshold = settings.RAG_SCORE_THRESHOLD

        try:
            # 获取查询向量
            query_embedding = await self.get_embedding(query)
            if not query_embedding:
                return []

            # 检查集合是否存在
            client = cast(Any, self.client)
            collections = client.get_collections().collections
            if not any(c.name == collection_name for c in collections):
                logger.warning(f"向量集合不存在: {collection_name}")
                return []

            # 构建过滤器
            query_filter = None
            if filter_conditions:
                from qdrant_client.models import FieldCondition, Filter, MatchValue

                must_conditions: list[Any] = []
                for key, value in filter_conditions.items():
                    must_conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )
                query_filter = Filter(must=must_conditions)

            # 执行搜索（qdrant-client >= 1.12 使用 query_points 替代 search）
            response = client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                limit=top_k,
                query_filter=query_filter,
                score_threshold=score_threshold,
            )

            return [
                {
                    "id": hit.payload.get("doc_id", ""),
                    "title": hit.payload.get("title", ""),
                    "content": hit.payload.get("content", ""),
                    "source": hit.payload.get("source", ""),
                    "score": hit.score,
                    "metadata": {k: v for k, v in hit.payload.items()
                               if k not in ["doc_id", "title", "content", "source"]},
                }
                for hit in response.points
            ]

        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []

    async def delete_documents(
        self,
        collection_name: str,
        doc_ids: list[str],
    ) -> bool:
        """删除文档"""
        if not self.client:
            return False

        try:
            from qdrant_client.models import FieldCondition, Filter, MatchAny

            self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="doc_id",
                            match=MatchAny(any=doc_ids),
                        )
                    ]
                ),
            )

            logger.info(f"删除 {len(doc_ids)} 个文档")
            return True

        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    async def get_collection_info(self, collection_name: str) -> dict[str, Any] | None:
        """获取集合信息"""
        if not self.client:
            return None

        try:
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status.name,
            }
        except Exception:
            return None

    async def add_chunks(
        self,
        collection_name: str,
        doc_id: str,
        chunks: list[dict[str, Any]],
    ) -> int:
        """
        批量添加文档分块到向量集合
        
        Args:
            collection_name: 集合名称
            doc_id: 原始文档 ID
            chunks: 分块列表，每个分块包含 chunk_id, content, chunk_index 等
            
        Returns:
            成功添加的分块数量
        """
        if not self.is_available or not chunks:
            return 0

        try:
            from qdrant_client.models import PointStruct

            # 确保集合存在
            await self.create_collection(collection_name)

            # 批量获取向量
            contents = [chunk.get("content", "") for chunk in chunks]
            embeddings = await self.get_embeddings_batch(contents)

            points = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=False)):
                if not embedding:
                    continue

                chunk_id = chunk.get("chunk_id", f"{doc_id}_{i}")
                point_id = int(hashlib.md5(chunk_id.encode()).hexdigest()[:8], 16)

                points.append(PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "doc_id": doc_id,
                        "chunk_id": chunk_id,
                        "chunk_index": chunk.get("chunk_index", i),
                        "title": chunk.get("title", ""),
                        "content": chunk.get("content", ""),
                        "source": chunk.get("source", ""),
                        **chunk.get("metadata", {}),
                    }
                ))

            if points:
                client = cast(Any, self.client)
                client.upsert(
                    collection_name=collection_name,
                    points=points,
                )
                logger.info(f"添加 {len(points)} 个分块到集合 {collection_name}")

            return len(points)

        except Exception as e:
            logger.error(f"添加分块失败: {e}")
            return 0

    async def delete_collection(self, collection_name: str) -> bool:
        """删除向量集合"""
        if not self.client:
            return False

        try:
            self.client.delete_collection(collection_name)
            logger.info(f"删除向量集合: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"删除向量集合失败: {e}")
            return False

    async def list_collections(self) -> list[str]:
        """列出所有向量集合"""
        if not self.client:
            return []

        try:
            collections = self.client.get_collections().collections
            return [c.name for c in collections]
        except Exception as e:
            logger.error(f"获取集合列表失败: {e}")
            return []


# 创建全局实例
vector_store = VectorStoreService()


# 便捷函数
async def embed_and_store_document(
    collection_name: str,
    doc_id: str,
    title: str,
    content: str,
    source: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """向量化并存储单个文档"""
    result = await vector_store.add_documents(
        collection_name=collection_name,
        documents=[{
            "id": doc_id,
            "title": title,
            "content": content,
            "source": source,
            "metadata": metadata or {},
        }],
    )
    return result > 0


async def semantic_search(
    collection_name: str,
    query: str,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """语义搜索"""
    return await vector_store.search(
        collection_name=collection_name,
        query=query,
        top_k=top_k,
    )


async def multi_collection_search(
    collection_names: list[str],
    query: str,
    top_k: int = 10,
    score_threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """
    多集合搜索
    
    在多个向量集合中搜索，合并结果并按分数排序
    
    Args:
        collection_names: 集合名称列表
        query: 查询文本
        top_k: 每个集合返回的结果数
        score_threshold: 相似度阈值
        
    Returns:
        合并后的搜索结果
    """
    all_results = []

    for collection_name in collection_names:
        try:
            results = await vector_store.search(
                collection_name=collection_name,
                query=query,
                top_k=top_k,
                score_threshold=score_threshold,
            )
            # 添加集合来源标记
            for r in results:
                r["collection"] = collection_name
            all_results.extend(results)
        except Exception as e:
            logger.warning(f"搜索集合 {collection_name} 失败: {e}")

    # 按分数排序
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)

    return all_results[:top_k]


async def search_with_filter(
    collection_name: str,
    query: str,
    filters: dict[str, Any],
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """
    带过滤条件的搜索
    
    Args:
        collection_name: 集合名称
        query: 查询文本
        filters: 过滤条件字典
        top_k: 返回结果数
        
    Returns:
        过滤后的搜索结果
    """
    return await vector_store.search(
        collection_name=collection_name,
        query=query,
        top_k=top_k,
        filter_conditions=filters,
    )


async def get_similar_chunks(
    collection_name: str,
    chunk_id: str,
    top_k: int = 5,
    exclude_same_doc: bool = True,
) -> list[dict[str, Any]]:
    """
    获取相似分块
    
    根据已有分块找到相似的其他分块
    
    Args:
        collection_name: 集合名称
        chunk_id: 分块 ID
        top_k: 返回结果数
        exclude_same_doc: 是否排除同一文档的分块
        
    Returns:
        相似分块列表
    """
    if not vector_store.client:
        return []

    try:
        # 获取原分块的向量
        point_id = int(hashlib.md5(chunk_id.encode()).hexdigest()[:8], 16)

        points = vector_store.client.retrieve(
            collection_name=collection_name,
            ids=[point_id],
            with_vectors=True,
        )

        if not points:
            return []

        original_vector = points[0].vector
        original_doc_id = points[0].payload.get("doc_id", "")

        # 搜索相似向量
        results = vector_store.client.search(
            collection_name=collection_name,
            query_vector=original_vector,
            limit=top_k + 10,  # 多取一些用于过滤
        )

        # 过滤和格式化结果
        formatted_results = []
        for hit in results:
            # 跳过自己
            if hit.id == point_id:
                continue

            # 可选：跳过同一文档
            if exclude_same_doc and hit.payload.get("doc_id") == original_doc_id:
                continue

            formatted_results.append({
                "id": hit.payload.get("chunk_id", ""),
                "doc_id": hit.payload.get("doc_id", ""),
                "title": hit.payload.get("title", ""),
                "content": hit.payload.get("content", ""),
                "score": hit.score,
                "metadata": {k: v for k, v in hit.payload.items()
                           if k not in ["doc_id", "chunk_id", "title", "content"]},
            })

            if len(formatted_results) >= top_k:
                break

        return formatted_results

    except Exception as e:
        logger.error(f"获取相似分块失败: {e}")
        return []
