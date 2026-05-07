"""文档管理路由"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.upload_validation import read_validated_upload_file
from src.core.database import get_db
from src.core.deps import get_current_user_required, rate_limit_upload
from src.core.responses import UnifiedResponse
from src.models.user import User
from src.services.document_generation_service import DocumentGenerationService
from src.services.document_service import DocumentService

router = APIRouter()


class DocumentResponse(BaseModel):
    """文档响应"""
    id: str
    name: str
    doc_type: str
    description: str | None = None
    file_size: int
    mime_type: str | None = None
    version: int
    ai_summary: str | None = None
    ai_metadata: dict[str, Any] | None = None
    extracted_text: str | None = None # 支持在线编辑
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentUpdate(BaseModel):
    """更新文档元数据"""
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None


class DocumentContentUpdate(BaseModel):
    """更新文档内容"""
    content: str
    change_summary: str | None = None


class TextDocumentCreate(BaseModel):
    """创建文本文档"""
    name: str
    content: str
    doc_type: str = "other"
    description: str | None = None
    case_id: str | None = None
    tags: list[str] | None = None


class DocumentGenerateRequest(BaseModel):
    """文档生成请求"""
    doc_type: str
    scenario: str
    requirements: dict[str, Any] # 动态参数
    case_id: str | None = None


class ParagraphGenerateRequest(BaseModel):
    """补写段落生成请求"""
    doc_type: str
    document_title: str
    current_content: str
    missing_field: dict[str, Any]


class ParagraphGenerateResponse(BaseModel):
    """补写段落生成响应"""
    title: str
    content: str


@router.get("/", response_model=UnifiedResponse)
async def list_documents(
    case_id: str | None = None,
    doc_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
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
                ai_metadata=None,
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
    description: str | None = Form(None),
    case_id: str | None = Form(None),
    tags: str | None = Form(None),  # JSON字符串
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
    _: None = Depends(rate_limit_upload),
) -> dict[str, Any]:
    """上传文档"""
    service = DocumentService(db)

    file_content, filename, content_type = await read_validated_upload_file(file)

    # 解析tags
    parsed_tags = None
    if tags:
        import json
        try:
            parsed_tags = json.loads(tags)
        except Exception:
            parsed_tags = [t.strip() for t in tags.split(",")]

    document = await service.upload_document(
        name=filename,
        file_content=file_content,
        mime_type=content_type,
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
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
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
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """AI 生成文档"""
    try:
        generation_service = DocumentGenerationService(db)
        generated = await generation_service.generate(
            doc_type=request.doc_type,
            scenario=request.scenario,
            requirements=request.requirements or {},
        )

        service = DocumentService(db)
        doc_name = f"{request.doc_type}_{datetime.now().strftime('%Y%m%d%H%M')}.md"

        document = await service.create_text_document(
            name=doc_name,
            content=generated["content"],
            doc_type="contract" if "合同" in request.doc_type else "legal_opinion",
            org_id=user.org_id if user else None,
            case_id=request.case_id,
            created_by=user.id if user else None,
            description=f"AI自动生成（{generated['draft_mode']}）: {request.scenario[:50]}...",
            tags=["AI生成", request.doc_type, generated["draft_mode"]],
        )

        data = DocumentResponse(
            id=document.id,
            name=document.name,
            doc_type=document.doc_type.value,
            description=document.description,
            file_size=document.file_size,
            mime_type=document.mime_type,
            version=document.version,
            ai_metadata={
                "draft_mode": generated["draft_mode"],
                "validation_score": generated["validation_score"],
                "completeness_score": generated.get("completeness_score"),
                "missing_fields": generated.get("missing_fields", []),
            },
            extracted_text=document.extracted_text,
            tags=document.tags,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
        return UnifiedResponse.success(data=data)

    except Exception as e:
        logger.error(f"文档生成失败: {e}")
        return UnifiedResponse.error(code=500, message=f"生成失败: {str(e)}")


@router.post("/generate-paragraph", response_model=UnifiedResponse)
async def generate_paragraph(
    request: ParagraphGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """AI 生成补写段落"""
    try:
        generation_service = DocumentGenerationService(db)
        generated = await generation_service.generate_missing_field_paragraph(
            doc_type=request.doc_type,
            document_title=request.document_title,
            current_content=request.current_content,
            missing_field=request.missing_field,
        )
        data = ParagraphGenerateResponse(
            title=generated["title"],
            content=generated["content"],
        )
        return UnifiedResponse.success(data=data)
    except Exception as e:
        logger.error(f"补写段落生成失败: {e}")
        return UnifiedResponse.error(code=500, message=f"生成失败: {str(e)}")


@router.get("/{document_id}", response_model=UnifiedResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取文档详情"""
    service = DocumentService(db)
    document = await service.get_document(document_id, org_id=user.org_id)

    if not document:
        return UnifiedResponse.error(code=404, message="文档不存在")

    data = DocumentResponse(
        id=document.id,
        name=document.name,
        doc_type=document.doc_type.value,
        description=document.description,
        file_size=document.file_size,
        mime_type=document.mime_type,
        ai_metadata=None,
        version=document.version,
        ai_summary=document.ai_summary,
        extracted_text=document.extracted_text,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
    return UnifiedResponse.success(data=data)


@router.put("/{document_id}", response_model=UnifiedResponse)
async def update_document(
    document_id: str,
    update: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """更新文档元数据"""
    service = DocumentService(db)

    document = await service.update_document(
        document_id=document_id,
        org_id=user.org_id,
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
        ai_metadata=None,
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
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """更新文档内容（创建新版本）"""
    service = DocumentService(db)

    document = await service.update_document_content(
        document_id=document_id,
        content=update.content,
        org_id=user.org_id,
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
            ai_metadata=None,
        extracted_text=document.extracted_text,
        tags=document.tags,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
    return UnifiedResponse.success(data=data)


@router.post("/{document_id}/analyze", response_model=UnifiedResponse)
async def analyze_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """AI 分析文档"""
    service = DocumentService(db)

    try:
        data = await service.analyze_document(document_id, org_id=user.org_id)
    except ValueError as e:
        return UnifiedResponse.error(code=404, message=str(e))

    return UnifiedResponse.success(data=data)


@router.delete("/{document_id}", response_model=UnifiedResponse)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """删除文档"""
    service = DocumentService(db)
    success = await service.delete_document(document_id, org_id=user.org_id)

    if not success:
        return UnifiedResponse.error(code=404, message="文档不存在")

    return UnifiedResponse.success(message="文档已删除")


@router.get("/{document_id}/versions", response_model=UnifiedResponse)
async def get_document_versions(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取文档版本历史"""
    service = DocumentService(db)
    document = await service.get_document(document_id, org_id=user.org_id)
    if not document:
        return UnifiedResponse.error(code=404, message="文档不存在")

    versions = await service.get_versions(document_id, org_id=user.org_id)

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
