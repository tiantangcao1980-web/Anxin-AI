"""知识库路由"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user, get_current_user_required
from src.core.responses import UnifiedResponse
from src.services.knowledge_service import KnowledgeService
from src.models.user import User

router = APIRouter()


class KnowledgeBaseCreate(BaseModel):
    """创建知识库"""
    name: str
    knowledge_type: str = "other"
    description: Optional[str] = None
    is_public: bool = False


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""
    id: str
    name: str
    knowledge_type: str
    description: Optional[str] = None
    doc_count: int
    is_public: bool
    created_at: datetime


class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应"""
    items: List[KnowledgeBaseResponse]
    total: int
    page: int
    page_size: int


class DocumentCreate(BaseModel):
    """添加文档"""
    title: str
    content: str
    source: Optional[str] = None
    source_url: Optional[str] = None
    tags: Optional[list] = None
    law_category: Optional[str] = None
    effective_date: Optional[str] = None
    issuing_authority: Optional[str] = None


class KnowledgeDocumentResponse(BaseModel):
    """知识库文档响应"""
    id: str
    title: str
    source: Optional[str] = None
    summary: Optional[str] = None
    is_processed: bool
    tags: Optional[list] = None
    created_at: datetime


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str
    kb_ids: Optional[List[str]] = None
    top_k: int = 10
    use_vector: bool = True  # 是否使用向量搜索
    hybrid: bool = False  # 是否使用混合搜索


class SearchResultItem(BaseModel):
    """搜索结果项"""
    id: str
    title: str
    content: str
    source: Optional[str] = None
    score: float
    match_type: Optional[str] = None  # vector / text / hybrid


class RAGQueryRequest(BaseModel):
    """RAG 智能问答请求"""
    query: str  # 用户问题
    kb_ids: Optional[List[str]] = None  # 限制搜索的知识库
    top_k: Optional[int] = 5  # 检索的文档数量
    include_sources: bool = True  # 是否返回来源信息
    system_prompt: Optional[str] = None  # 自定义系统提示词


class RAGQueryResponse(BaseModel):
    """RAG 智能问答响应"""
    answer: str  # 生成的答案
    sources: List[dict] = []  # 引用的来源
    context_used: bool = True  # 是否使用了检索上下文
    chunks_used: Optional[int] = None  # 使用的分块数量
    error: Optional[str] = None  # 错误信息


class IndexDocumentRequest(BaseModel):
    """索引文档请求"""
    title: str  # 文档标题
    content: str  # 文档内容
    source: Optional[str] = None  # 文档来源
    metadata: Optional[dict] = None  # 额外元数据
    chunk_size: Optional[int] = None  # 分块大小（可选）
    chunk_overlap: Optional[int] = None  # 分块重叠（可选）


class IndexDocumentResponse(BaseModel):
    """索引文档响应"""
    success: bool
    doc_id: Optional[str] = None
    chunk_count: int = 0  # 分块数量
    indexed_count: int = 0  # 成功索引的分块数量
    error: Optional[str] = None


class SemanticSearchRequest(BaseModel):
    """语义搜索请求"""
    query: str  # 搜索查询
    kb_id: Optional[str] = None  # 知识库 ID
    top_k: Optional[int] = 10  # 返回结果数量


class DeepResearchRequest(BaseModel):
    """深度研究请求"""
    topic: str
    kb_ids: Optional[List[str]] = None


@router.post("/deep-research")
async def deep_research(
    request: DeepResearchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """
    深度法律研究报告生成
    """
    service = KnowledgeService(db)
    result = await service.deep_research(
        topic=request.topic,
        kb_ids=request.kb_ids
    )
    return UnifiedResponse.success(data=result)


@router.get("/bases")
async def list_knowledge_bases(
    knowledge_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取知识库列表"""
    service = KnowledgeService(db)
    
    kbs, total = await service.list_knowledge_bases(
        org_id=user.org_id,
        knowledge_type=knowledge_type,
        page=page,
        page_size=page_size,
    )
    
    data = KnowledgeBaseListResponse(
        items=[
            KnowledgeBaseResponse(
                id=kb.id,
                name=kb.name,
                knowledge_type=kb.knowledge_type.value,
                description=kb.description,
                doc_count=kb.doc_count,
                is_public=kb.is_public,
                created_at=kb.created_at,
            )
            for kb in kbs
        ],
        total=total,
        page=page,
        page_size=page_size
    )
    return UnifiedResponse.success(data=data)


@router.post("/bases")
async def create_knowledge_base(
    kb: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """创建知识库"""
    service = KnowledgeService(db)
    
    created_kb = await service.create_knowledge_base(
        name=kb.name,
        knowledge_type=kb.knowledge_type,
        description=kb.description,
        org_id=user.org_id,
        created_by=user.id,
        is_public=kb.is_public,
    )
    
    data = KnowledgeBaseResponse(
        id=created_kb.id,
        name=created_kb.name,
        knowledge_type=created_kb.knowledge_type.value,
        description=created_kb.description,
        doc_count=created_kb.doc_count,
        is_public=created_kb.is_public,
        created_at=created_kb.created_at,
    )
    return UnifiedResponse.success(data=data)


@router.get("/bases/{kb_id}")
async def get_knowledge_base(
    kb_id: str, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required)
):
    """获取知识库详情"""
    service = KnowledgeService(db)
    kb = await service.get_knowledge_base(kb_id)
    
    if not kb:
        return UnifiedResponse.error(code=404, message="知识库不存在")
    
    data = KnowledgeBaseResponse(
        id=kb.id,
        name=kb.name,
        knowledge_type=kb.knowledge_type.value,
        description=kb.description,
        doc_count=kb.doc_count,
        is_public=kb.is_public,
        created_at=kb.created_at,
    )
    return UnifiedResponse.success(data=data)


@router.get("/bases/{kb_id}/documents")
async def list_kb_documents(
    kb_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取知识库文档列表"""
    service = KnowledgeService(db)
    
    docs, total = await service.list_documents(kb_id, page, page_size)
    
    data = {
        "items": [
            KnowledgeDocumentResponse(
                id=d.id,
                title=d.title,
                source=d.source,
                summary=d.summary,
                is_processed=d.is_processed,
                tags=d.tags,
                created_at=d.created_at,
            )
            for d in docs
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }
    return UnifiedResponse.success(data=data)


@router.post("/bases/{kb_id}/documents")
async def add_document_to_kb(
    kb_id: str,
    doc: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """添加文档到知识库"""
    service = KnowledgeService(db)
    
    # 检查知识库是否存在
    kb = await service.get_knowledge_base(kb_id)
    if not kb:
        return UnifiedResponse.error(code=404, message="知识库不存在")
    
    created_doc = await service.add_document(
        kb_id=kb_id,
        title=doc.title,
        content=doc.content,
        source=doc.source,
        source_url=doc.source_url,
        tags=doc.tags,
        law_category=doc.law_category,
        effective_date=doc.effective_date,
        issuing_authority=doc.issuing_authority,
    )
    
    data = KnowledgeDocumentResponse(
        id=created_doc.id,
        title=created_doc.title,
        source=created_doc.source,
        summary=created_doc.summary,
        is_processed=created_doc.is_processed,
        tags=created_doc.tags,
        created_at=created_doc.created_at,
    )
    return UnifiedResponse.success(data=data)


@router.post("/search")
async def search_knowledge(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """
    搜索知识库
    
    支持三种搜索模式：
    - 向量语义搜索 (use_vector=True, hybrid=False)
    - 关键词文本搜索 (use_vector=False, hybrid=False)
    - 混合搜索 (hybrid=True)
    """
    service = KnowledgeService(db)
    
    if request.hybrid:
        results = await service.hybrid_search(
            query=request.query,
            kb_ids=request.kb_ids,
            top_k=request.top_k,
        )
    else:
        results = await service.search(
            query=request.query,
            kb_ids=request.kb_ids,
            top_k=request.top_k,
            use_vector=request.use_vector,
        )
    
    data = [
        SearchResultItem(
            id=r.get("id", ""),
            title=r.get("title", ""),
            content=r.get("content", ""),
            source=r.get("source"),
            score=r.get("score", 0) or r.get("final_score", 0),
            match_type=r.get("match_type", "vector" if request.use_vector else "text"),
        )
        for r in results
    ]
    return UnifiedResponse.success(data=data)


@router.get("/search/status")
async def get_vector_status(user: User = Depends(get_current_user_required)):
    """获取向量搜索服务状态"""
    from src.services.vector_store import vector_store
    
    data = {
        "available": vector_store.is_available,
        "embedding_model": vector_store.embedding_model if vector_store.is_available else None,
    }
    return UnifiedResponse.success(data=data)


@router.delete("/documents/{doc_id}")
async def delete_kb_document(
    doc_id: str, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required)
):
    """删除知识库文档"""
    service = KnowledgeService(db)
    success = await service.delete_document(doc_id)
    
    if not success:
        return UnifiedResponse.error(code=404, message="文档不存在")
    
    return UnifiedResponse.success(message="文档已删除")


# ==================== RAG 增强功能 API ====================


@router.post("/rag-query")
async def rag_query(
    request: RAGQueryRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """
    RAG 智能问答
    """
    service = KnowledgeService(db)
    
    result = await service.rag_query(
        query=request.query,
        kb_ids=request.kb_ids,
        top_k=request.top_k,
        include_sources=request.include_sources,
        system_prompt=request.system_prompt,
    )
    
    data = RAGQueryResponse(
        answer=result.get("answer", ""),
        sources=result.get("sources", []),
        context_used=result.get("context_used", False),
        chunks_used=result.get("chunks_used"),
        error=result.get("error"),
    )
    return UnifiedResponse.success(data=data)


@router.post("/bases/{kb_id}/index")
async def index_document(
    kb_id: str,
    request: IndexDocumentRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """
    索引文档到知识库
    """
    service = KnowledgeService(db)
    
    # 检查知识库是否存在
    kb = await service.get_knowledge_base(kb_id)
    if not kb:
        return UnifiedResponse.error(code=404, message="知识库不存在")
    
    result = await service.index_document(
        kb_id=kb_id,
        title=request.title,
        content=request.content,
        source=request.source,
        metadata=request.metadata,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
    )
    
    data = IndexDocumentResponse(
        success=result.get("success", False),
        doc_id=result.get("doc_id"),
        chunk_count=result.get("chunk_count", 0),
        indexed_count=result.get("indexed_count", 0),
        error=result.get("error"),
    )
    return UnifiedResponse.success(data=data)


@router.post("/bases/{kb_id}/upload")
async def upload_document_to_kb(
    kb_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """
    上传文件并索引到知识库
    """
    service = KnowledgeService(db)
    
    # 检查知识库是否存在
    kb = await service.get_knowledge_base(kb_id)
    if not kb:
        return UnifiedResponse.error(code=404, message="知识库不存在")
    
    content = await file.read()
    
    result = await service.index_file(
        kb_id=kb_id,
        file_content=content,
        file_name=file.filename,
        metadata={"uploaded_by": user.id}
    )
    
    if not result.get("success"):
        return UnifiedResponse.error(message=result.get("error", "上传并索引失败"))
    
    return UnifiedResponse.success(data=result, message="文件已上传并开始处理")


@router.get("/semantic-search")
async def semantic_search(
    query: str = Query(..., description="搜索查询"),
    kb_id: Optional[str] = Query(None, description="知识库 ID"),
    top_k: int = Query(10, ge=1, le=50, description="返回结果数量"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """
    语义搜索
    """
    service = KnowledgeService(db)
    
    results = await service.semantic_search_simple(
        query=query,
        kb_id=kb_id,
        top_k=top_k,
    )
    
    data = [
        SearchResultItem(
            id=r.get("id", ""),
            title=r.get("title", ""),
            content=r.get("content", ""),
            source=r.get("source"),
            score=r.get("score", 0),
            match_type="vector",
        )
        for r in results
    ]
    return UnifiedResponse.success(data=data)


@router.get("/vector-store/info")
async def get_vector_store_info(user: User = Depends(get_current_user_required)):
    """
    获取向量存储服务详细信息
    """
    from src.services.vector_store import vector_store
    
    collections = await vector_store.list_collections() if vector_store.is_available else []
    
    data = {
        "available": vector_store.is_available,
        "embedding": vector_store.embedding_info,
        "collections": collections,
    }
    return UnifiedResponse.success(data=data)
