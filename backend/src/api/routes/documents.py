"""文档管理路由"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File, Form, Body, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.core.config import settings
from src.core.responses import UnifiedResponse
from src.core.database import get_db
from src.core.deps import get_current_user
from src.services.document_service import DocumentService
from src.models.user import User

router = APIRouter()


class DocumentResponse(BaseModel):
    """文档响应"""
    id: str
    name: str
    doc_type: str
    description: Optional[str] = None
    file_size: int
    mime_type: Optional[str] = None
    version: int
    ai_summary: Optional[str] = None
    extracted_text: Optional[str] = None # 支持在线编辑
    tags: Optional[list] = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentUpdate(BaseModel):
    """更新文档元数据"""
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list] = None


class DocumentContentUpdate(BaseModel):
    """更新文档内容"""
    content: str
    change_summary: Optional[str] = None


class TextDocumentCreate(BaseModel):
    """创建文本文档"""
    name: str
    content: str
    doc_type: str = "other"
    description: Optional[str] = None
    case_id: Optional[str] = None
    tags: Optional[List[str]] = None


class DocumentGenerateRequest(BaseModel):
    """文档生成请求"""
    doc_type: str
    scenario: str
    requirements: Dict[str, Any] # 动态参数
    case_id: Optional[str] = None


@router.get("/", response_model=UnifiedResponse)
async def list_documents(
    case_id: Optional[str] = None,
    doc_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """获取文档列表"""
    service = DocumentService(db)
    
    documents, total = await service.list_documents(
        org_id=user.org_id if user else None,
        case_id=case_id,
        doc_type=doc_type,
        page=page,
        page_size=page_size,
    )
    
    data = DocumentListResponse(
        items=[
            DocumentResponse(
                id=d.id,
                name=d.name,
                doc_type=d.doc_type.value,
                description=d.description,
                file_size=d.file_size,
                mime_type=d.mime_type,
                version=d.version,
                ai_summary=d.ai_summary,
                extracted_text=d.extracted_text, # 返回文本内容
                tags=d.tags,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in documents
        ],
        total=total,
        page=page,
        page_size=page_size
    )
    return UnifiedResponse.success(data=data)


@router.post("/", response_model=UnifiedResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("other"),
    description: Optional[str] = Form(None),
    case_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON字符串
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """上传文档"""
    service = DocumentService(db)

    # 读取文件内容
    file_content = await file.read()

    # 文件大小校验
    if len(file_content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过限制（最大 {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB）"
        )
    
    # 解析tags
    parsed_tags = None
    if tags:
        import json
        try:
            parsed_tags = json.loads(tags)
        except:
            parsed_tags = [t.strip() for t in tags.split(",")]
    
    document = await service.upload_document(
        name=file.filename or "未命名文档",
        file_content=file_content,
        mime_type=file.content_type or "application/octet-stream",
        doc_type=doc_type,
        org_id=user.org_id if user else None,
        case_id=case_id,
        created_by=user.id if user else None,
        description=description,
        tags=parsed_tags,
    )
    
    data = DocumentResponse(
        id=document.id,
        name=document.name,
        doc_type=document.doc_type.value,
        description=document.description,
        file_size=document.file_size,
        mime_type=document.mime_type,
        version=document.version,
        tags=document.tags,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
    return UnifiedResponse.success(data=data)


@router.post("/text", response_model=UnifiedResponse)
async def create_text_document(
    request: TextDocumentCreate,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """创建在线文本文档"""
    service = DocumentService(db)
    
    document = await service.create_text_document(
        name=request.name,
        content=request.content,
        doc_type=request.doc_type,
        org_id=user.org_id if user else None,
        case_id=request.case_id,
        created_by=user.id if user else None,
        description=request.description,
        tags=request.tags,
    )
    
    data = DocumentResponse(
        id=document.id,
        name=document.name,
        doc_type=document.doc_type.value,
        description=document.description,
        file_size=document.file_size,
        mime_type=document.mime_type,
        version=document.version,
        extracted_text=document.extracted_text, # 这里应该有了
        tags=document.tags,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
    return UnifiedResponse.success(data=data)


@router.post("/generate", response_model=UnifiedResponse)
async def generate_document(
    request: DocumentGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """AI 生成文档"""
    from src.agents.workforce import get_workforce
    
    workforce = get_workforce()
    
    # 构建 Prompt
    prompt = f"""
    请作为一名专业律师，起草一份【{request.doc_type}】。
    
    场景背景：
    {request.scenario}
    
    具体要求与参数：
    {request.requirements}
    
    输出要求：
    1. 格式规范，条款清晰。
    2. 使用 Markdown 格式输出。
    3. 包含必要的法律声明。
    """
    
    try:
        # 调用 DocumentDrafter Agent
        generated_content = await workforce.chat(prompt, agent_name="document_drafter")
        
        # 自动保存为文档
        service = DocumentService(db)
        doc_name = f"{request.doc_type}_{datetime.now().strftime('%Y%m%d%H%M')}.md"
        
        document = await service.create_text_document(
            name=doc_name,
            content=generated_content,
            doc_type="contract" if "合同" in request.doc_type else "legal_opinion", # 简单映射
            org_id=user.org_id if user else None,
            case_id=request.case_id,
            created_by=user.id if user else None,
            description=f"AI自动生成: {request.scenario[:50]}...",
            tags=["AI生成", request.doc_type]
        )
        
        data = DocumentResponse(
            id=document.id,
            name=document.name,
            doc_type=document.doc_type.value,
            description=document.description,
            file_size=document.file_size,
            mime_type=document.mime_type,
            version=document.version,
            extracted_text=document.extracted_text,
            tags=document.tags,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
        return UnifiedResponse.success(data=data)
        
    except Exception as e:
        logger.error(f"文档生成失败: {e}")
        return UnifiedResponse.error(code=500, message=f"生成失败: {str(e)}")


@router.get("/{document_id}", response_model=UnifiedResponse)
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """获取文档详情"""
    service = DocumentService(db)
    document = await service.get_document(document_id)
    
    if not document:
        return UnifiedResponse.error(code=404, message="文档不存在")
    
    data = DocumentResponse(
        id=document.id,
        name=document.name,
        doc_type=document.doc_type.value,
        description=document.description,
        file_size=document.file_size,
        mime_type=document.mime_type,
        version=document.version,
        ai_summary=document.ai_summary,
        extracted_text=document.extracted_text,
        tags=document.tags,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
    return UnifiedResponse.success(data=data)


@router.put("/{document_id}", response_model=UnifiedResponse)
async def update_document(
    document_id: str,
    update: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新文档元数据"""
    service = DocumentService(db)
    
    document = await service.update_document(
        document_id=document_id,
        name=update.name,
        description=update.description,
        tags=update.tags,
    )
    
    if not document:
        return UnifiedResponse.error(code=404, message="文档不存在")
    
    data = DocumentResponse(
        id=document.id,
        name=document.name,
        doc_type=document.doc_type.value,
        description=document.description,
        file_size=document.file_size,
        mime_type=document.mime_type,
        version=document.version,
        ai_summary=document.ai_summary,
        extracted_text=document.extracted_text,
        tags=document.tags,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
    return UnifiedResponse.success(data=data)


@router.patch("/{document_id}/content", response_model=UnifiedResponse)
async def update_document_content(
    document_id: str,
    update: DocumentContentUpdate,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """更新文档内容（创建新版本）"""
    service = DocumentService(db)
    
    document = await service.update_document_content(
        document_id=document_id,
        content=update.content,
        updated_by=user.id if user else None,
        change_summary=update.change_summary
    )
    
    if not document:
        return UnifiedResponse.error(code=404, message="文档不存在")
        
    data = DocumentResponse(
        id=document.id,
        name=document.name,
        doc_type=document.doc_type.value,
        description=document.description,
        file_size=document.file_size,
        mime_type=document.mime_type,
        version=document.version,
        ai_summary=document.ai_summary,
        extracted_text=document.extracted_text,
        tags=document.tags,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
    return UnifiedResponse.success(data=data)


@router.delete("/{document_id}", response_model=UnifiedResponse)
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """删除文档"""
    service = DocumentService(db)
    success = await service.delete_document(document_id)
    
    if not success:
        return UnifiedResponse.error(code=404, message="文档不存在")
    
    return UnifiedResponse.success(message="文档已删除")


@router.get("/{document_id}/versions", response_model=UnifiedResponse)
async def get_document_versions(document_id: str, db: AsyncSession = Depends(get_db)):
    """获取文档版本历史"""
    service = DocumentService(db)
    versions = await service.get_versions(document_id)
    
    data = {
        "versions": [
            {
                "id": v.id,
                "version": v.version,
                "file_size": v.file_size,
                "change_summary": v.change_summary,
                "created_at": v.created_at.isoformat(),
            }
            for v in versions
        ]
    }
    return UnifiedResponse.success(data=data)
