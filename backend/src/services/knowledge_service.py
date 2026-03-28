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
    
    async def get_knowledge_base(self, kb_id: str) -> Optional[KnowledgeBase]:
        """获取知识库"""
        result = await self.db.execute(
            select(KnowledgeBase)
            .options(selectinload(KnowledgeBase.documents))
            .where(KnowledgeBase.id == kb_id)
        )
        return result.scalar_one_or_none()

    async def list_knowledge_bases(
        self,
        org_id: Optional[str] = None,
        knowledge_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[KnowledgeBase], int]:
        """获取知识库列表"""
        query = select(KnowledgeBase)
        count_query = select(func.count(KnowledgeBase.id))
        
        conditions = []
        if org_id:
            conditions.append(KnowledgeBase.org_id == org_id)
        if knowledge_type:
            conditions.append(KnowledgeBase.knowledge_type == KnowledgeType(knowledge_type))
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
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
    ) -> tuple[List[KnowledgeDocument], int]:
        """获取知识库文档列表"""
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

    async def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        result = await self.db.execute(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            return False
        
        # 尝试从向量库删除
        kb = await self.get_knowledge_base(doc.knowledge_base_id)
        if kb and vector_store.is_available:
            await vector_store.delete_documents(kb.vector_collection, [doc_id])
            
        await self.db.delete(doc)
        if kb:
            kb.doc_count = max(0, kb.doc_count - 1)
            
        return True

    async def semantic_search_simple(self, query: str, kb_id: Optional[str] = None, top_k: int = 10) -> List[dict]:
        """简单语义搜索"""
        kb_ids = [kb_id] if kb_id else None
        return await self.search(query, kb_ids=kb_ids, top_k=top_k)

    async def hybrid_search(self, query: str, kb_ids: Optional[List[str]] = None, top_k: int = 10) -> List[dict]:
        """混合搜索 (结合语义搜索与关键词搜索)"""
        # 1. 语义搜索结果
        vector_results = await self.search(query, kb_ids=kb_ids, top_k=top_k * 2)
        
        # 2. 关键词搜索结果 (PostgreSQL)
        keyword_results = []
        try:
            db_query = select(KnowledgeDocument).where(
                or_(
                    KnowledgeDocument.title.ilike(f"%{query}%"),
                    KnowledgeDocument.content.ilike(f"%{query}%")
                )
            )
            if kb_ids:
                db_query = db_query.where(KnowledgeDocument.knowledge_base_id.in_(kb_ids))
            
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
    ) -> Dict[str, Any]:
        """
        索引文档：集成分块与向量化流程
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
        text_chunks = chunking_service.chunk_text(
            text=content,
            strategy=ChunkingStrategy.RECURSIVE,
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
        **kwargs
    ) -> Dict[str, Any]:
        """
        RAG 智能问答：统一转发给高级 RAG 服务
        """
        if not kb_ids:
            collection_names = [settings.QDRANT_COLLECTION_NAME]
        else:
            kbs_result = await self.db.execute(select(KnowledgeBase).where(KnowledgeBase.id.in_(kb_ids)))
            collection_names = [kb.vector_collection for kb in kbs_result.scalars().all()]

        response = await rag_service.query(
            query=query,
            collection_names=collection_names,
            system_prompt=system_prompt,
        )
        return response.to_dict()

    async def search(self, query: str, kb_ids: Optional[List[str]] = None, top_k: int = 10) -> List[dict]:
        """语义搜索转发"""
        if kb_ids:
            kbs_result = await self.db.execute(select(KnowledgeBase).where(KnowledgeBase.id.in_(kb_ids)))
            collection_names = [kb.vector_collection for kb in kbs_result.scalars().all()]
        else:
            collection_names = [settings.QDRANT_COLLECTION_NAME]
            
        return await vector_store.search(
            collection_name=collection_names[0], 
            query=query, 
            top_k=top_k
        )

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
