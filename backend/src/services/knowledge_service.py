"""
知识库服务

主要职责：
1. 知识库与文档的元数据管理 (PostgreSQL)
2. 协调文档分块 (调用 chunking_service)
3. 协调向量存储 (调用 vector_store)
4. RAG 逻辑转发 (调用 rag_service)
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from loguru import logger

from src.core.config import settings
from src.models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeType
from src.services.vector_store import vector_store, embed_and_store_document, semantic_search
from src.services.chunking_service import chunking_service, ChunkingStrategy
from src.services.rag_service import rag_service
from src.services.document_parser import document_parser


class KnowledgeService:
    """知识库服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_knowledge_base(
        self,
        name: str,
        knowledge_type: str = "other",
        description: Optional[str] = None,
        org_id: Optional[str] = None,
        created_by: Optional[str] = None,
        is_public: bool = False,
    ) -> KnowledgeBase:
        """创建知识库"""
        kb = KnowledgeBase(
            name=name,
            knowledge_type=KnowledgeType(knowledge_type) if knowledge_type in [e.value for e in KnowledgeType] else KnowledgeType.OTHER,
            description=description,
            org_id=org_id,
            created_by=created_by,
            is_public=is_public,
            vector_collection=f"kb_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        )
        self.db.add(kb)
        await self.db.flush()
        logger.info(f"知识库创建成功: {name}")
        return kb
    
    @staticmethod
    def _check_kb_access(kb: 'KnowledgeBase', user_id: Optional[str] = None, org_id: Optional[str] = None) -> bool:
        """检查用户是否有权访问知识库"""
        if kb.is_public:
            return True
        if user_id and str(kb.created_by) == str(user_id):
            return True
        if org_id and kb.org_id and str(kb.org_id) == str(org_id):
            return True
        return False

    async def get_knowledge_base(
        self, kb_id: str, user_id: Optional[str] = None, org_id: Optional[str] = None
    ) -> Optional[KnowledgeBase]:
        """获取知识库（含权限校验）"""
        result = await self.db.execute(
            select(KnowledgeBase)
            .options(selectinload(KnowledgeBase.documents))
            .where(KnowledgeBase.id == kb_id)
        )
        kb = result.scalar_one_or_none()
        if kb and user_id and not self._check_kb_access(kb, user_id, org_id):
            logger.warning(f"用户 {user_id} 无权访问知识库 {kb_id}")
            return None
        return kb

    async def list_knowledge_bases(
        self,
        org_id: Optional[str] = None,
        knowledge_type: Optional[str] = None,
        user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[KnowledgeBase], int]:
        """获取知识库列表（含权限过滤）"""
        query = select(KnowledgeBase)
        count_query = select(func.count(KnowledgeBase.id))

        # 权限过滤：公开 OR 本人创建 OR 同组织
        access_conditions = [KnowledgeBase.is_public == True]
        if user_id:
            access_conditions.append(KnowledgeBase.created_by == user_id)
        if org_id:
            access_conditions.append(KnowledgeBase.org_id == org_id)
        access_filter = or_(*access_conditions)

        type_conditions = []
        if knowledge_type:
            type_conditions.append(KnowledgeBase.knowledge_type == KnowledgeType(knowledge_type))

        if type_conditions:
            combined = and_(access_filter, *type_conditions)
        else:
            combined = access_filter

        query = query.where(combined)
        count_query = count_query.where(combined)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(KnowledgeBase.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def list_documents(
        self,
        kb_id: str,
        page: int = 1,
        page_size: int = 20,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> tuple[List[KnowledgeDocument], int]:
        """获取知识库文档列表"""
        kb = await self.get_knowledge_base(kb_id, user_id=user_id, org_id=org_id)
        if not kb:
            return [], 0
        query = select(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb_id)
        count_query = select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.knowledge_base_id == kb_id)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(KnowledgeDocument.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def add_document(
        self,
        kb_id: str,
        title: str,
        content: str,
        source: Optional[str] = None,
        **kwargs
    ) -> KnowledgeDocument:
        """添加单个文档（不带自动向量化）"""
        doc = KnowledgeDocument(
            knowledge_base_id=kb_id,
            title=title,
            content=content,
            source=source,
            is_processed=False,
            **kwargs
        )
        self.db.add(doc)
        
        # 更新知识库文档计数
        kb = await self.get_knowledge_base(kb_id)
        if kb:
            kb.doc_count += 1
            
        await self.db.flush()
        return doc

    async def delete_document(
        self,
        doc_id: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> bool:
        """删除文档"""
        result = await self.db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            return False
        
        # 尝试从向量库删除
        kb = await self.get_knowledge_base(doc.knowledge_base_id, user_id=user_id, org_id=org_id)
        if not kb:
            return False
        if kb and vector_store.is_available:
            await vector_store.delete_documents(kb.vector_collection, [doc_id])
            
        await self.db.delete(doc)
        if kb:
            kb.doc_count = max(0, kb.doc_count - 1)
            
        return True

    async def semantic_search_simple(
        self,
        query: str,
        kb_id: Optional[str] = None,
        top_k: int = 10,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> List[dict]:
        """简单语义搜索"""
        kb_ids = [kb_id] if kb_id else None
        return await self.search(query, kb_ids=kb_ids, top_k=top_k, user_id=user_id, org_id=org_id)

    async def hybrid_search(
        self,
        query: str,
        kb_ids: Optional[List[str]] = None,
        top_k: int = 10,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> List[dict]:
        """混合搜索 (结合语义搜索与关键词搜索)"""
        # 1. 语义搜索结果
        vector_results = await self.search(
            query,
            kb_ids=kb_ids,
            top_k=top_k * 2,
            user_id=user_id,
            org_id=org_id,
        )

        accessible_kb_ids = kb_ids
        if kb_ids and user_id:
            kbs_result = await self.db.execute(select(KnowledgeBase).where(KnowledgeBase.id.in_(kb_ids)))
            kbs = [kb for kb in kbs_result.scalars().all() if self._check_kb_access(kb, user_id, org_id)]
            accessible_kb_ids = [kb.id for kb in kbs]
            if not accessible_kb_ids:
                return []
        
        # 2. 关键词搜索结果 (PostgreSQL)
        keyword_results = []
        try:
            db_query = select(KnowledgeDocument).where(
                or_(
                    KnowledgeDocument.title.ilike(f"%{query}%"),
                    KnowledgeDocument.content.ilike(f"%{query}%")
                )
            )
            if accessible_kb_ids:
                db_query = db_query.where(KnowledgeDocument.knowledge_base_id.in_(accessible_kb_ids))
            
            db_query = db_query.limit(top_k * 2)
            db_result = await self.db.execute(db_query)
            docs = db_result.scalars().all()
            
            for doc in docs:
                keyword_results.append({
                    "id": doc.id,
                    "title": doc.title,
                    "content": doc.content[:1000],
                    "source": doc.source,
                    "score": 0.8, # 基础权重
                    "metadata": doc.extra_metadata or {}
                })
        except Exception as e:
            logger.error(f"关键词搜索失败: {e}")

        # 3. 结果合并与去重 (Reciprocal Rank Fusion 简化版)
        combined_results = {}
        
        # 处理向量结果 (权重 0.7)
        for i, res in enumerate(vector_results):
            doc_id = res["id"]
            score = 0.7 * (1.0 / (i + 1))
            combined_results[doc_id] = {**res, "combined_score": score}
            
        # 处理关键词结果 (权重 0.3)
        for i, res in enumerate(keyword_results):
            doc_id = res["id"]
            score = 0.3 * (1.0 / (i + 1))
            if doc_id in combined_results:
                combined_results[doc_id]["combined_score"] += score
                # 关键词匹配成功，提升分数
                combined_results[doc_id]["metadata"]["keyword_match"] = True
            else:
                combined_results[doc_id] = {**res, "combined_score": score}
        
        # 按合并分数排序
        sorted_results = sorted(
            combined_results.values(), 
            key=lambda x: x["combined_score"], 
            reverse=True
        )
        
        return sorted_results[:top_k]

    async def index_document(
        self,
        kb_id: str,
        title: str,
        content: str,
        source: Optional[str] = None,
        metadata: Optional[Dict] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        chunking_strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        索引文档：集成分块与向量化流程

        Args:
            chunking_strategy: 分块策略名称，可选值:
                - "legal_article": 按法律条款(第X条)分块，适用于法律法规
                - "paragraph": 按段落分块，适用于合同模板
                - "sentence": 按句子分块
                - "recursive": 递归分块(默认)
                - None: 自动选择(默认 recursive)
        """
        kb = await self.get_knowledge_base(kb_id)
        if not kb:
            return {"success": False, "error": "知识库不存在"}

        doc_id = str(uuid.uuid4())

        # 1. 调用统一的分块引擎
        chunk_kwargs = {}
        if chunk_size is not None:
            chunk_kwargs["chunk_size"] = chunk_size
        if chunk_overlap is not None:
            chunk_kwargs["chunk_overlap"] = chunk_overlap

        # 根据 chunking_strategy 参数或知识库类型选择分块策略
        strategy = ChunkingStrategy.RECURSIVE
        if chunking_strategy:
            strategy_map = {
                "legal_article": ChunkingStrategy.LEGAL_ARTICLE,
                "paragraph": ChunkingStrategy.PARAGRAPH,
                "sentence": ChunkingStrategy.SENTENCE,
                "recursive": ChunkingStrategy.RECURSIVE,
                "fixed_size": ChunkingStrategy.FIXED_SIZE,
            }
            strategy = strategy_map.get(chunking_strategy, ChunkingStrategy.RECURSIVE)
        elif kb.knowledge_type:
            # 根据知识库类型自动选择策略
            type_strategy_map = {
                "law": ChunkingStrategy.LEGAL_ARTICLE,
                "regulation": ChunkingStrategy.LEGAL_ARTICLE,
                "interpretation": ChunkingStrategy.LEGAL_ARTICLE,
                "template": ChunkingStrategy.PARAGRAPH,
                "letter": ChunkingStrategy.PARAGRAPH,
                "litigation": ChunkingStrategy.PARAGRAPH,
            }
            kt = kb.knowledge_type.value if hasattr(kb.knowledge_type, 'value') else str(kb.knowledge_type)
            strategy = type_strategy_map.get(kt, ChunkingStrategy.RECURSIVE)

        text_chunks = chunking_service.chunk_text(
            text=content,
            strategy=strategy,
            **chunk_kwargs,
        )
        
        if not text_chunks:
            return {"success": False, "error": "内容为空"}
        
        # 2. 准备向量化数据
        chunk_docs = [{
            "chunk_id": f"{doc_id}_{i}",
            "chunk_index": i,
            "title": title,
            "content": chunk.content,
            "source": source,
            "metadata": {
                "start_index": chunk.start_char,
                "end_index": chunk.end_char,
                **(metadata or {}),
            },
        } for i, chunk in enumerate(text_chunks)]
        
        # 3. 执行向量索引
        indexed_count = 0
        if vector_store.is_available:
            indexed_count = await vector_store.add_chunks(
                collection_name=kb.vector_collection or f"kb_{kb_id}",
                doc_id=doc_id,
                chunks=chunk_docs,
            )
        
        # 4. 保存元数据到 DB
        doc = KnowledgeDocument(
            id=doc_id,
            knowledge_base_id=kb_id,
            title=title,
            content=content,
            source=source,
            metadata={"chunk_count": len(text_chunks), "indexed_count": indexed_count, **(metadata or {})},
            is_processed=indexed_count > 0,
        )
        self.db.add(doc)
        kb.doc_count += 1
        await self.db.flush()
        
        return {"success": True, "doc_id": doc_id, "chunk_count": len(text_chunks)}

    async def rag_query(
        self,
        query: str,
        kb_ids: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        RAG 智能问答：统一转发给高级 RAG 服务（含权限校验）
        """
        if not kb_ids:
            collection_names = [settings.QDRANT_COLLECTION_NAME]
        else:
            kbs_result = await self.db.execute(select(KnowledgeBase).where(KnowledgeBase.id.in_(kb_ids)))
            kbs = list(kbs_result.scalars().all())
            # 权限过滤：只搜索用户有权访问的知识库
            if user_id:
                kbs = [kb for kb in kbs if self._check_kb_access(kb, user_id, org_id)]
            # 空知识库过滤：跳过没有文档的知识库
            empty_kbs = [kb.name for kb in kbs if kb.doc_count == 0]
            kbs = [kb for kb in kbs if kb.doc_count > 0]
            collection_names = [kb.vector_collection for kb in kbs]
            if not collection_names:
                return {
                    "answer": f"选中的知识库暂无可检索文档。{'（' + '、'.join(empty_kbs) + ' 为空）' if empty_kbs else ''}请先上传文档或选择其他知识库。",
                    "sources": [],
                    "confidence": 0,
                }

        response = await rag_service.query(
            query=query,
            collection_names=collection_names,
            system_prompt=system_prompt,
        )
        return response.to_dict()

    async def search(
        self, query: str, kb_ids: Optional[List[str]] = None, top_k: int = 10,
        user_id: Optional[str] = None, org_id: Optional[str] = None,
    ) -> List[dict]:
        """语义搜索转发（支持多知识库）"""
        if kb_ids:
            kbs_result = await self.db.execute(select(KnowledgeBase).where(KnowledgeBase.id.in_(kb_ids)))
            kbs = list(kbs_result.scalars().all())
            if user_id:
                kbs = [kb for kb in kbs if self._check_kb_access(kb, user_id, org_id)]
            collection_names = [kb.vector_collection for kb in kbs if kb.doc_count > 0]
        else:
            collection_names = [settings.QDRANT_COLLECTION_NAME]

        if not collection_names:
            return []

        if len(collection_names) == 1:
            return await vector_store.search(
                collection_name=collection_names[0],
                query=query,
                top_k=top_k
            )
        else:
            # 多知识库搜索：遍历所有 collection 合并结果
            all_results = []
            for cname in collection_names:
                try:
                    results = await vector_store.search(
                        collection_name=cname, query=query, top_k=top_k
                    )
                    all_results.extend(results)
                except Exception as e:
                    logger.warning(f"搜索 collection {cname} 失败: {e}")
            # 按相关度排序后截取 top_k
            all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
            return all_results[:top_k]

    async def get_kb_stats(self, kb_id: str) -> Dict[str, Any]:
        """获取知识库统计"""
        kb = await self.get_knowledge_base(kb_id)
        if not kb: return {"error": "not found"}
        
        doc_count = await self.db.scalar(select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.knowledge_base_id == kb_id))
        return {
            "kb_id": kb_id,
            "name": kb.name,
            "doc_count": doc_count,
            "vector_collection": kb.vector_collection
        }

    async def deep_research(self, topic: str, kb_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """深度法律研究"""
        from src.agents.legal_researcher import LegalResearchAgent
        
        # 1. 获取背景上下文 (通过混合搜索)
        context_docs = await self.hybrid_search(topic, kb_ids=kb_ids, top_k=5)
        context = {
            "related_documents": [
                {"title": d["title"], "content": d["content"][:500]} 
                for d in context_docs
            ]
        }
        
        # 2. 调用深度研究 Agent
        agent = LegalResearchAgent()
        response = await agent.deep_research(topic, context=context)
        
        return response.to_dict()

    async def index_file(
        self,
        kb_id: str,
        file_path: Optional[str] = None,
        file_content: Optional[bytes] = None,
        file_name: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        从文件索引：集成分析、分块与向量化
        """
        # 1. 解析文件
        parse_result = await document_parser.parse_file(
            file_path=file_path,
            file_content=file_content,
            file_name=file_name
        )
        
        if not parse_result.get("success"):
            return {"success": False, "error": parse_result.get("error", "解析失败")}
        
        content = parse_result["text"]
        title = parse_result.get("file_name", "未命名文档")
        
        # 2. 增强元数据
        doc_metadata = {
            "file_type": parse_result.get("file_type"),
            "char_count": parse_result.get("char_count"),
            "structure": parse_result.get("structure"),
            **(metadata or {})
        }
        
        # 3. 调用索引逻辑
        return await self.index_document(
            kb_id=kb_id,
            title=title,
            content=content,
            source=file_name or file_path,
            metadata=doc_metadata
        )

    async def update_knowledge_base(
        self,
        kb_id: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        **kwargs
    ) -> Optional[KnowledgeBase]:
        """更新知识库"""
        kb = await self.get_knowledge_base(kb_id, user_id=user_id, org_id=org_id)
        if not kb:
            return None
        for key, value in kwargs.items():
            if key == "knowledge_type" and isinstance(value, str):
                value = KnowledgeType(value) if value in [e.value for e in KnowledgeType] else kb.knowledge_type
            if hasattr(kb, key):
                setattr(kb, key, value)
        await self.db.flush()
        return kb

    async def delete_knowledge_base(
        self,
        kb_id: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> bool:
        """删除知识库及其所有文档和向量"""
        kb = await self.get_knowledge_base(kb_id, user_id=user_id, org_id=org_id)
        if not kb:
            return False
        # 删除向量集合
        if kb.vector_collection and vector_store.is_available:
            try:
                await vector_store.delete_collection(kb.vector_collection)
            except Exception as e:
                logger.warning(f"删除向量集合失败: {e}")
        await self.db.delete(kb)
        return True

    async def get_document(
        self,
        doc_id: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> Optional[KnowledgeDocument]:
        """获取文档完整内容"""
        result = await self.db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            return None
        kb = await self.get_knowledge_base(doc.knowledge_base_id, user_id=user_id, org_id=org_id)
        return doc if kb else None

    async def update_document(
        self,
        doc_id: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        **kwargs
    ) -> Optional[KnowledgeDocument]:
        """更新文档"""
        doc = await self.get_document(doc_id, user_id=user_id, org_id=org_id)
        if not doc:
            return None
        for key, value in kwargs.items():
            if hasattr(doc, key):
                setattr(doc, key, value)
        await self.db.flush()
        return doc

    async def get_kb_stats_detail(
        self,
        kb_id: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取知识库详细统计"""
        kb = await self.get_knowledge_base(kb_id, user_id=user_id, org_id=org_id)
        if not kb:
            return {"error": "not found"}

        doc_count = await self.db.scalar(
            select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.knowledge_base_id == kb_id)
        )
        processed_count = await self.db.scalar(
            select(func.count(KnowledgeDocument.id)).where(
                and_(KnowledgeDocument.knowledge_base_id == kb_id, KnowledgeDocument.is_processed == True)
            )
        )
        total_chunks = await self.db.scalar(
            select(func.sum(KnowledgeDocument.chunk_count)).where(KnowledgeDocument.knowledge_base_id == kb_id)
        ) or 0

        # 法律类别分布
        category_result = await self.db.execute(
            select(KnowledgeDocument.law_category, func.count(KnowledgeDocument.id))
            .where(KnowledgeDocument.knowledge_base_id == kb_id)
            .group_by(KnowledgeDocument.law_category)
        )
        categories = {row[0] or "未分类": row[1] for row in category_result.all()}

        return {
            "kb_id": kb_id,
            "name": kb.name,
            "doc_count": doc_count or 0,
            "processed_count": processed_count or 0,
            "total_chunks": total_chunks,
            "categories": categories,
            "vector_collection": kb.vector_collection,
            "embedding_model": kb.embedding_model,
        }

    async def export_knowledge_base(
        self,
        kb_id: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """导出知识库为JSON"""
        kb = await self.get_knowledge_base(kb_id, user_id=user_id, org_id=org_id)
        if not kb:
            return None

        docs_result = await self.db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb_id)
        )
        docs = docs_result.scalars().all()

        return {
            "knowledge_base": {
                "name": kb.name,
                "description": kb.description,
                "knowledge_type": kb.knowledge_type.value,
                "is_public": kb.is_public,
            },
            "documents": [
                {
                    "title": d.title,
                    "content": d.content,
                    "source": d.source,
                    "source_url": d.source_url,
                    "summary": d.summary,
                    "tags": d.tags,
                    "law_category": d.law_category,
                    "effective_date": d.effective_date,
                    "issuing_authority": d.issuing_authority,
                }
                for d in docs
            ],
            "exported_at": datetime.now().isoformat(),
            "total_documents": len(docs),
        }
