"""
RAG (检索增强生成) 核心服务

整合检索、重排序、上下文构建、生成回答的完整 RAG 流程

主要功能：
1. 知识检索：从向量数据库检索相关文档
2. 结果重排序：使用 Reranker 提高相关性
3. 上下文构建：将检索结果组织成 LLM 上下文
4. 答案生成：调用 LLM 生成最终回答
5. 引用追踪：返回答案的来源引用
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple
from enum import Enum
from loguru import logger

from src.core.config import settings
from src.services.vector_store import vector_store, multi_collection_search
from src.services.reranker_service import reranker_service, RerankResult
from src.services.graph_service import graph_service


class RAGMode(str, Enum):
    """RAG 模式"""
    SIMPLE = "simple"           # 简单模式：直接检索 + 生成
    RERANK = "rerank"           # 重排序模式：检索 + 重排序 + 生成
    HYBRID = "hybrid"           # 混合模式：向量 + 关键词检索 + 重排序
    MULTI_QUERY = "multi_query" # 多查询模式：查询扩展 + 合并结果
    GRAPH = "graph"             # 图谱模式：结合知识图谱检索 (GraphRAG)


@dataclass
class RAGContext:
    """RAG 上下文"""
    query: str                              # 用户查询
    retrieved_chunks: List[Dict[str, Any]]  # 检索到的分块
    reranked_chunks: List[RerankResult]     # 重排序后的分块
    context_text: str                       # 构建的上下文文本
    sources: List[Dict[str, Any]]           # 来源引用
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "chunk_count": len(self.retrieved_chunks),
            "context_length": len(self.context_text),
            "sources": self.sources,
        }


@dataclass
class RAGResponse:
    """RAG 响应"""
    answer: str                             # 生成的回答
    context: RAGContext                     # RAG 上下文
    sources: List[Dict[str, Any]]           # 来源引用
    confidence: float                       # 置信度
    tokens_used: int                        # 使用的 Token 数
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "sources": self.sources,
            "confidence": self.confidence,
            "tokens_used": self.tokens_used,
            "context_info": self.context.to_dict(),
        }


# 法律领域专用系统提示
LEGAL_RAG_SYSTEM_PROMPT = """你是一位专业的超级AI法律顾问助手，拥有极其严谨的逻辑分析能力。
请基于提供的法律知识库参考资料回答用户问题。

回答准则：
1. 【有据可查】：回答必须严格基于参考资料。如果资料中包含具体法条（如《民法典》第X条），必须准确引用。
2. 【严谨性】：若参考资料不足以回答问题，请直白告知用户“根据当前知识库资料，无法完整回答该问题”，并尝试给出基于现有资料的风险提示。
3. 【结构化输出】：
   - 核心结论：首先给出简洁明了的法律结论。
   - 法律依据：详细列出参考资料中的相关条款。
   - 详细分析：结合案情或问题进行法理分析。
   - 风险建议：给出专业的操作建议或避坑指南。
4. 【禁止幻觉】：严禁捏造法律名称、文号或判例。
5. 【免责声明】：回答末尾请统一附带：“注：以上回答仅供参考，不构成正式法律意见。复杂案件建议咨询专业律师。”
"""


@dataclass
class RAGConfig:
    """RAG 配置"""
    mode: RAGMode = RAGMode.RERANK
    
    # 检索配置
    top_k: int = 10                         # 初始检索数量
    rerank_top_k: int = 5                   # 重排序后保留数量
    score_threshold: float = 0.5            # 相似度阈值
    
    # 上下文配置
    max_context_length: int = 4000          # 最大上下文长度
    chunk_separator: str = "\n\n---\n\n"    # 分块分隔符
    include_metadata: bool = True           # 是否包含元数据
    
    # 生成配置
    system_prompt: str = ""                 # 系统提示（可选）
    temperature: float = 0.7                # 生成温度
    max_tokens: int = 2000                  # 最大生成 Token
    
    # 多查询配置
    multi_query_count: int = 3              # 查询扩展数量


class RAGService:
    """RAG 核心服务"""
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self.llm_client = None
        self._init_llm_client()
    
    def _is_local_model_api(self) -> bool:
        """判断是否为本地模型服务"""
        return "/api/v1/chat" in (settings.LLM_BASE_URL or "")

    def _init_llm_client(self):
        """初始化 LLM 客户端"""
        try:
            if self._is_local_model_api():
                # 本地模型服务使用 httpx
                import httpx
                self.llm_client = True  # 标记为可用
                self._httpx_client = httpx.Client(timeout=60.0)
                logger.info(f"RAG LLM 客户端初始化成功 (本地模型: {settings.LLM_BASE_URL})")
            else:
                from openai import OpenAI
                self.llm_client = OpenAI(
                    api_key=settings.LLM_API_KEY,
                    base_url=settings.LLM_BASE_URL,
                )
                self._httpx_client = None
                logger.info("RAG LLM 客户端初始化成功")

        except Exception as e:
            logger.error(f"RAG LLM 客户端初始化失败: {e}")

    def _call_local_llm(self, messages: list, temperature: float = 0.7, max_tokens: int = 4096) -> str:
        """调用本地模型服务"""
        # 将 messages 转为 input 文本
        input_text = ""
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                input_text += f"[系统指令] {content}\n\n"
            elif role == "user":
                input_text += f"{content}\n"
            elif role == "assistant":
                input_text += f"[助手回复] {content}\n"

        url = settings.LLM_BASE_URL.rstrip("/")
        headers = {
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.LLM_MODEL,
            "input": input_text.strip(),
            "stream": False,
        }

        resp = self._httpx_client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

        # 解析本地模型响应: {"output": [{"type": "message", "content": "..."}], ...}
        output_list = data.get("output", [])
        content = ""
        for item in output_list:
            if isinstance(item, dict) and item.get("content"):
                content += item["content"]
        if not content:
            # 兜底：尝试 choices 格式
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", str(data))
            else:
                content = str(data)
        return content
    
    @property
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.llm_client is not None and vector_store.is_available
    
    async def get_graph_a2ui_data(self, query: str) -> Optional[Dict[str, Any]]:
        """获取图谱的 A2UI 格式数据"""
        entities = await self._extract_entities(query)
        if not entities:
            return None
            
        all_relations = []
        for entity in entities:
            relations = graph_service.get_related_entities(entity, depth=1)
            all_relations.extend(relations)
            
        if not all_relations:
            return None
            
        # 转换为 A2UI graph 格式
        nodes = []
        edges = []
        seen_nodes = set()
        
        # 添加查询节点
        query_node_id = "query_node"
        nodes.append({
            "id": query_node_id,
            "label": f"查询: {query[:20]}...",
            "type": "query"
        })
        seen_nodes.add(query_node_id)
        
        for rel in all_relations:
            source = rel['source']
            target = rel['target']
            relation = rel['relation']
            
            # 确定节点类型 (简单猜测)
            def get_type(name):
                if any(k in name for k in ['法', '条', '意见']): return 'law'
                if any(k in name for k in ['司', '院', '局']): return 'entity'
                return 'entity'
            
            if source not in seen_nodes:
                nodes.append({"id": source, "label": source, "type": get_type(source)})
                seen_nodes.add(source)
            if target not in seen_nodes:
                nodes.append({"id": target, "label": target, "type": get_type(target)})
                seen_nodes.add(target)
                
            edges.append({
                "source": source,
                "target": target,
                "relation": relation,
                "label": relation
            })
            
            # 连接查询到第一个匹配的实体
            if source in entities:
                edges.append({
                    "source": query_node_id,
                    "target": source,
                    "relation": "EXTRACT",
                    "label": "提取实体"
                })

        return {
            "components": [
                {
                    "id": "knowledge_graph",
                    "type": "graph",
                    "props": {
                        "data": {
                            "nodes": nodes,
                            "edges": edges
                        }
                    }
                }
            ]
        }

    async def retrieve(
        self,
        query: str,
        collection_names: List[str],
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            collection_names: 要搜索的集合列表
            top_k: 返回结果数
            filters: 过滤条件
            
        Returns:
            检索结果列表
        """
        top_k = top_k or self.config.top_k
        
        if len(collection_names) == 1:
            # 单集合搜索
            results = await vector_store.search(
                collection_name=collection_names[0],
                query=query,
                top_k=top_k,
                score_threshold=self.config.score_threshold,
                filter_conditions=filters,
            )
        else:
            # 多集合搜索
            results = await multi_collection_search(
                collection_names=collection_names,
                query=query,
                top_k=top_k,
                score_threshold=self.config.score_threshold,
            )
        
        logger.debug(f"检索到 {len(results)} 个相关文档")
        return results
    
    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[RerankResult]:
        """
        重排序文档
        
        Args:
            query: 查询文本
            documents: 文档列表
            top_k: 返回结果数
            
        Returns:
            重排序结果
        """
        if not documents:
            return []
        
        top_k = top_k or self.config.rerank_top_k
        
        if reranker_service.is_available:
            results = await reranker_service.rerank(query, documents, top_k)
            logger.debug(f"重排序完成，返回 {len(results)} 个结果")
            return results
        else:
            # 降级：使用原始分数排序
            logger.warning("Reranker 不可用，使用原始分数排序")
            sorted_docs = sorted(
                documents, 
                key=lambda x: x.get("score", 0), 
                reverse=True
            )[:top_k]
            return [
                RerankResult(
                    id=doc.get("id", ""),
                    content=doc.get("content", ""),
                    original_score=doc.get("score", 0),
                    rerank_score=doc.get("score", 0),
                    final_score=doc.get("score", 0),
                    metadata=doc.get("metadata", {}),
                )
                for doc in sorted_docs
            ]
    
    def build_context(
        self,
        query: str,
        chunks: List[RerankResult],
    ) -> RAGContext:
        """
        构建 RAG 上下文
        
        Args:
            query: 查询文本
            chunks: 重排序后的分块
            
        Returns:
            RAG 上下文
        """
        context_parts = []
        sources = []
        current_length = 0
        
        for i, chunk in enumerate(chunks):
            # 构建分块文本
            chunk_text = f"【参考资料 {i+1}】\n"
            
            if self.config.include_metadata and chunk.metadata:
                # 添加元数据
                if chunk.metadata.get("title"):
                    chunk_text += f"标题：{chunk.metadata['title']}\n"
                if chunk.metadata.get("source"):
                    chunk_text += f"来源：{chunk.metadata['source']}\n"
                if chunk.metadata.get("article"):
                    chunk_text += f"条款：{chunk.metadata['article']}\n"
            
            chunk_text += f"内容：{chunk.content}\n"
            
            # 检查长度限制
            if current_length + len(chunk_text) > self.config.max_context_length:
                logger.debug(f"上下文长度达到限制，截断于第 {i} 个分块")
                break
            
            context_parts.append(chunk_text)
            current_length += len(chunk_text)
            
            # 记录来源
            sources.append({
                "index": i + 1,
                "id": chunk.id,
                "title": chunk.metadata.get("title", ""),
                "source": chunk.metadata.get("source", ""),
                "score": chunk.final_score,
            })
        
        context_text = self.config.chunk_separator.join(context_parts)
        
        return RAGContext(
            query=query,
            retrieved_chunks=[],  # 原始检索结果（可选保留）
            reranked_chunks=chunks,
            context_text=context_text,
            sources=sources,
        )
    
    async def generate(
        self,
        query: str,
        context: RAGContext,
        system_prompt: Optional[str] = None,
    ) -> Tuple[str, int]:
        """
        生成回答
        
        Args:
            query: 用户查询
            context: RAG 上下文
            system_prompt: 系统提示（可选）
            
        Returns:
            (生成的回答, 使用的 token 数)
        """
        if not self.llm_client:
            return "抱歉，AI 服务暂时不可用。", 0
        
        # 构建系统提示
        system = system_prompt or self.config.system_prompt or LEGAL_RAG_SYSTEM_PROMPT
        
        # 构建用户消息
        user_message = f"""请基于以下参考资料回答用户问题。

{context.context_text}

---

用户问题：{query}

请根据上述参考资料，提供专业、准确的回答。如果参考资料不足以回答问题，请说明。"""
        
        try:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ]
            if self._is_local_model_api():
                answer = self._call_local_llm(messages, self.config.temperature, self.config.max_tokens)
                return answer, 0
            else:
                response = self.llm_client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                answer = response.choices[0].message.content
                tokens_used = response.usage.total_tokens if response.usage else 0
                return answer, tokens_used

        except Exception as e:
            logger.error(f"RAG 生成失败: {e}")
            return f"生成回答时遇到错误: {str(e)}", 0
    
    async def expand_query(self, query: str) -> List[str]:
        """
        查询扩展
        
        生成多个相关查询以提高检索覆盖率
        
        Args:
            query: 原始查询
            
        Returns:
            扩展后的查询列表
        """
        if not self.llm_client:
            return [query]
        
        try:
            prompt = f"""请为以下法律问题生成 {self.config.multi_query_count} 个相关但不同角度的查询，用于知识库检索。

原始问题：{query}

要求：
1. 每个查询从不同角度描述同一问题
2. 包含可能的同义词或相关概念
3. 直接输出查询，每行一个，不要编号

查询："""
            
            messages = [{"role": "user", "content": prompt}]
            if self._is_local_model_api():
                content = self._call_local_llm(messages, 0.7, 200)
            else:
                response = self.llm_client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=200,
                )
                content = response.choices[0].message.content

            expanded = content.strip().split("\n")
            queries = [q.strip() for q in expanded if q.strip()]
            
            # 确保包含原始查询
            if query not in queries:
                queries.insert(0, query)
            
            return queries[:self.config.multi_query_count + 1]
            
        except Exception as e:
            logger.error(f"查询扩展失败: {e}")
            return [query]

    async def _extract_entities(self, query: str) -> List[str]:
        """从查询中提取实体，用于图谱检索"""
        if not self.llm_client:
            return []
            
        try:
            prompt = f"""请从以下法律咨询问题中提取核心实体（如人名、公司名、法院名、关键法律条文等）。
直接输出实体名称，多个实体用逗号分隔。如果没有实体，输出“无”。

问题：{query}

实体："""
            messages = [{"role": "user", "content": prompt}]
            if self._is_local_model_api():
                content = self._call_local_llm(messages, 0, 100).strip()
            else:
                response = self.llm_client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=messages,
                    temperature=0,
                    max_tokens=100,
                )
                content = response.choices[0].message.content.strip()
            if content == "无":
                return []
            return [e.strip() for e in content.split(",") if e.strip()]
        except Exception as e:
            logger.error(f"提取实体失败: {e}")
            return []

    async def query(
        self,
        query: str,
        collection_names: List[str],
        system_prompt: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> RAGResponse:
        """
        执行完整的 RAG 流程
        
        Args:
            query: 用户查询
            collection_names: 知识库集合列表
            system_prompt: 系统提示（可选）
            filters: 检索过滤条件
            
        Returns:
            RAG 响应
        """
        # 1. 检索向量数据
        retrieved_docs = await self.retrieve(
            query=query,
            collection_names=collection_names,
            filters=filters,
        )
        
        # 2. 如果是 GRAPH 模式，额外检索图谱数据
        graph_context = ""
        if self.config.mode == RAGMode.GRAPH:
            entities = await self._extract_entities(query)
            if entities:
                graph_context = graph_service.get_context_from_graph(entities)
                logger.debug(f"从图谱中提取到上下文，长度: {len(graph_context)}")
        
        if not retrieved_docs and not graph_context:
            return RAGResponse(
                answer="抱歉，未能在知识库中找到与您问题相关的内容。请尝试换一种方式描述您的问题，或者联系人工法务顾问。",
                context=RAGContext(
                    query=query,
                    retrieved_chunks=[],
                    reranked_chunks=[],
                    context_text="",
                    sources=[],
                ),
                sources=[],
                confidence=0.0,
                tokens_used=0,
            )
        
        # 3. 重排序 (仅针对向量检索结果)
        if retrieved_docs:
            if self.config.mode in [RAGMode.RERANK, RAGMode.HYBRID, RAGMode.GRAPH]:
                reranked_chunks = await self.rerank(query, retrieved_docs)
            else:
                reranked_chunks = [
                    RerankResult(
                        id=doc.get("id", ""),
                        content=doc.get("content", ""),
                        original_score=doc.get("score", 0),
                        rerank_score=doc.get("score", 0),
                        final_score=doc.get("score", 0),
                        metadata=doc.get("metadata", {}),
                    )
                    for doc in retrieved_docs[:self.config.rerank_top_k]
                ]
        else:
            reranked_chunks = []
        
        # 4. 构建上下文 (合并向量和图谱上下文)
        context = self.build_context(query, reranked_chunks)
        context.retrieved_chunks = retrieved_docs
        
        if graph_context:
            context.context_text = graph_context + "\n\n" + context.context_text
        
        # 5. 生成回答
        answer, tokens_used = await self.generate(
            query=query,
            context=context,
            system_prompt=system_prompt,
        )
        
        # 计算置信度
        if reranked_chunks:
            avg_score = sum(c.final_score for c in reranked_chunks) / len(reranked_chunks)
            confidence = min(avg_score, 1.0)
        elif graph_context:
            confidence = 0.8  # 如果只有图谱数据，给予一个基础置信度
        else:
            confidence = 0.0
        
        return RAGResponse(
            answer=answer,
            context=context,
            sources=context.sources,
            confidence=confidence,
            tokens_used=tokens_used,
        )

    async def stream_query(
        self,
        query: str,
        collection_names: List[str],
        system_prompt: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式 RAG 查询
        """
        # 1. 检索与实体提取
        yield {"type": "status", "content": "正在检索相关知识..."}
        
        # 并行执行向量检索和实体提取（如果需要）
        tasks = [self.retrieve(query, collection_names, filters=filters)]
        if self.config.mode == RAGMode.GRAPH:
            tasks.append(self._extract_entities(query))
            
        task_results = await asyncio.gather(*tasks)
        retrieved_docs = task_results[0]
        entities = task_results[1] if len(task_results) > 1 else []
        
        # 2. 处理图谱上下文
        graph_context = ""
        if entities:
            yield {"type": "status", "content": f"提取到实体: {', '.join(entities)}，正在查询图谱..."}
            graph_context = graph_service.get_context_from_graph(entities)
            
        if not retrieved_docs and not graph_context:
            yield {"type": "answer", "content": "抱歉，未能在知识库中找到与您问题相关的内容。"}
            yield {"type": "done", "sources": []}
            return
            
        # 3. 重排序
        reranked_chunks = []
        if retrieved_docs:
            yield {"type": "status", "content": f"找到 {len(retrieved_docs)} 条向量记录，正在重排序..."}
            reranked_chunks = await self.rerank(query, retrieved_docs)
            
        # 4. 构建上下文
        context = self.build_context(query, reranked_chunks)
        if graph_context:
            context.context_text = graph_context + "\n\n" + context.context_text
            
        # 5. 生成回答
        yield {"type": "status", "content": "正在生成回答..."}
        
        if not self.llm_client:
            yield {"type": "answer", "content": "抱歉，AI 服务暂时不可用。"}
            yield {"type": "done", "sources": context.sources}
            return
            
        system = system_prompt or self.config.system_prompt or LEGAL_RAG_SYSTEM_PROMPT
        user_message = f"""请基于以下参考资料回答用户问题。

{context.context_text}

---

用户问题：{query}

请根据上述参考资料，提供专业、准确的回答。"""
        
        try:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ]
            if self._is_local_model_api():
                # 本地模型不支持流式，一次性返回
                answer = self._call_local_llm(messages, self.config.temperature, self.config.max_tokens)
                yield {"type": "answer", "content": answer}
            else:
                stream = self.llm_client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    stream=True,
                )
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield {"type": "answer", "content": chunk.choices[0].delta.content}

            yield {"type": "done", "sources": context.sources}

        except Exception as e:
            logger.error(f"RAG 流式生成失败: {e}")
            yield {"type": "error", "content": f"生成回答时遇到错误: {str(e)}"}
    
    async def multi_query_rag(
        self,
        query: str,
        collection_names: List[str],
        system_prompt: Optional[str] = None,
    ) -> RAGResponse:
        """
        多查询 RAG
        
        使用查询扩展提高检索覆盖率
        """
        # 1. 查询扩展
        queries = await self.expand_query(query)
        logger.debug(f"扩展查询: {queries}")
        
        # 2. 并行检索
        all_results = []
        for q in queries:
            results = await self.retrieve(q, collection_names)
            all_results.extend(results)
        
        # 3. 去重（基于 ID）
        seen_ids = set()
        unique_results = []
        for r in all_results:
            if r.get("id") not in seen_ids:
                seen_ids.add(r.get("id"))
                unique_results.append(r)
        
        # 4. 重排序（使用原始查询）
        reranked_chunks = await self.rerank(query, unique_results)
        
        # 5. 构建上下文和生成
        context = self.build_context(query, reranked_chunks)
        answer, tokens_used = await self.generate(query, context, system_prompt)
        
        # 计算置信度
        if reranked_chunks:
            avg_score = sum(c.final_score for c in reranked_chunks) / len(reranked_chunks)
            confidence = min(avg_score, 1.0)
        else:
            confidence = 0.0
        
        return RAGResponse(
            answer=answer,
            context=context,
            sources=context.sources,
            confidence=confidence,
            tokens_used=tokens_used,
        )


# 创建默认实例
rag_config = RAGConfig(
    mode=RAGMode.RERANK,
    top_k=settings.RAG_TOP_K,
    max_context_length=settings.RAG_CONTEXT_MAX_LENGTH,
    score_threshold=settings.RAG_SCORE_THRESHOLD,
)
rag_service = RAGService(rag_config)


# 便捷函数
async def rag_query(
    query: str,
    collection_names: List[str],
    system_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    执行 RAG 查询
    
    Args:
        query: 用户查询
        collection_names: 知识库集合列表
        system_prompt: 系统提示
        
    Returns:
        RAG 响应字典
    """
    response = await rag_service.query(query, collection_names, system_prompt)
    return response.to_dict()


async def legal_rag_query(
    query: str,
    kb_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    法律领域 RAG 查询
    
    Args:
        query: 法律问题
        kb_ids: 知识库 ID 列表（可选）
        
    Returns:
        RAG 响应
    """
    # 如果没有指定知识库，使用默认集合
    if kb_ids:
        collection_names = [f"kb_{kb_id}" for kb_id in kb_ids]
    else:
        collection_names = [settings.QDRANT_COLLECTION_NAME]
    
    response = await rag_service.query(
        query=query,
        collection_names=collection_names,
        system_prompt=LEGAL_RAG_SYSTEM_PROMPT,
    )
    return response.to_dict()
