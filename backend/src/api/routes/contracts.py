"""合同审查路由"""

import asyncio
import io
import json
import urllib.parse
from collections.abc import AsyncIterator
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.workforce import get_workforce
from src.api.routes.upload_validation import read_validated_upload_file
from src.core.config import settings
from src.core.database import get_db
from src.core.deps import get_current_user_required, rate_limit_upload
from src.core.responses import UnifiedResponse
from src.models.audit import AuditAction, ResourceType
from src.models.contract import ContractStatus
from src.models.user import User
from src.services.audit_service import AuditService
from src.services.contract_lifecycle_service import IllegalStateTransition
from src.services.contract_review_lock import (
    ContractReviewAlreadyRunning,
    ContractReviewLockUnavailable,
)
from src.services.contract_service import (
    ContractReviewExecutionError,
    ContractReviewTimeoutError,
    ContractService,
)
from src.services.document_parser import contract_analyzer, parse_contract_document
from src.services.object_storage_service import ObjectStorageError

router = APIRouter()


class ContractCreate(BaseModel):
    """创建合同"""
    title: str
    contract_type: str
    party_a: dict[str, Any] | None = None
    party_b: dict[str, Any] | None = None
    amount: float | None = None
    effective_date: date | None = None
    expiry_date: date | None = None


class ContractResponse(BaseModel):
    """合同响应"""
    id: str
    contract_number: str | None = None
    title: str
    contract_type: str
    status: str
    risk_level: str | None = None
    risk_score: float | None = None
    amount: float | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    created_at: datetime
    updated_at: datetime


class ContractListResponse(BaseModel):
    """合同列表响应"""
    items: list[ContractResponse]
    total: int
    page: int
    page_size: int


class ContractReviewRequest(BaseModel):
    """合同审查请求"""
    contract_text: str


class ContractReviewResponse(BaseModel):
    """合同审查响应"""
    contract_id: str
    risk_score: float | None = None
    risk_level: str | None = None
    summary: str
    risks: list[dict[str, Any]] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    key_terms: dict[str, Any] = Field(default_factory=dict)


class ContractRiskResponse(BaseModel):
    """合同风险响应"""
    id: str
    risk_type: str
    risk_level: str
    title: str
    description: str
    related_clause: str | None = None
    suggestion: str | None = None
    is_resolved: bool


class ContractTransitionRequest(BaseModel):
    """合同状态转换请求"""
    status: str
    reason: str | None = Field(default=None, max_length=500)


class ContractRollbackRequest(BaseModel):
    """合同版本回滚请求"""
    reason: str | None = Field(default=None, max_length=500)


class TemplateRenderRequest(BaseModel):
    """合同模板渲染请求"""
    variables: dict[str, Any] = Field(default_factory=dict)


def _normalize_review_payload(review_data: Any) -> dict[str, Any]:
    if isinstance(review_data, str):
        import re

        json_match = re.search(r'\{[\s\S]*\}', review_data)
        if json_match:
            try:
                review_data = json.loads(json_match.group())
            except json.JSONDecodeError:
                review_data = {}
        else:
            review_data = {}

    if not isinstance(review_data, dict):
        review_data = {}

    risks = review_data.get("risks")
    key_risks = review_data.get("key_risks")

    if not isinstance(risks, list):
        risks = key_risks if isinstance(key_risks, list) else []
    if not isinstance(key_risks, list):
        key_risks = risks

    suggestions = review_data.get("suggestions")
    key_terms = review_data.get("key_terms")
    missing_clauses = review_data.get("missing_clauses")

    return {
        **review_data,
        "summary": review_data.get("summary", "审查完成"),
        "risk_level": review_data.get("risk_level", "medium"),
        "risk_score": float(review_data.get("risk_score", 0.5)),
        "risks": risks,
        "key_risks": key_risks,
        "suggestions": suggestions if isinstance(suggestions, list) else [],
        "key_terms": key_terms if isinstance(key_terms, dict) else {},
        "missing_clauses": missing_clauses if isinstance(missing_clauses, list) else [],
    }


def _serialize_attachment(attachment: Any) -> dict[str, Any]:
    return {
        "id": attachment.id,
        "contract_id": attachment.contract_id,
        "filename": attachment.original_filename,
        "content_type": attachment.content_type,
        "file_size": attachment.file_size,
        "file_hash": attachment.file_hash,
        "storage_backend": attachment.storage_backend,
        "object_key": attachment.object_key,
        "uploaded_by": attachment.uploaded_by,
        "created_at": attachment.created_at.isoformat() if attachment.created_at else None,
        "updated_at": attachment.updated_at.isoformat() if attachment.updated_at else None,
    }


@router.get("/", response_model=UnifiedResponse)
async def list_contracts(
    status: str | None = None,
    contract_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取合同列表"""
    service = ContractService(db)

    contracts, total = await service.list_contracts(
        org_id=user.org_id,
        status=status,
        contract_type=contract_type,
        page=page,
        page_size=page_size,
    )

    data = ContractListResponse(
        items=[
            ContractResponse(
                id=c.id,
                contract_number=c.contract_number,
                title=c.title,
                contract_type=c.contract_type,
                status=c.status.value,
                risk_level=c.risk_level.value if c.risk_level else None,
                risk_score=c.risk_score,
                amount=c.amount,
                effective_date=c.effective_date,
                expiry_date=c.expiry_date,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in contracts
        ],
        total=total,
        page=page,
        page_size=page_size
    )
    return UnifiedResponse.success(data=data)


@router.post("/", response_model=UnifiedResponse)
async def create_contract(
    contract: ContractCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """创建合同"""
    service = ContractService(db)

    created_contract = await service.create_contract(
        title=contract.title,
        contract_type=contract.contract_type,
        org_id=user.org_id,
        party_a=contract.party_a,
        party_b=contract.party_b,
        amount=contract.amount,
        effective_date=contract.effective_date,
        expiry_date=contract.expiry_date,
    )

    data = ContractResponse(
        id=created_contract.id,
        contract_number=created_contract.contract_number,
        title=created_contract.title,
        contract_type=created_contract.contract_type,
        status=created_contract.status.value,
        amount=created_contract.amount,
        effective_date=created_contract.effective_date,
        expiry_date=created_contract.expiry_date,
        created_at=created_contract.created_at,
        updated_at=created_contract.updated_at,
    )
    return UnifiedResponse.success(data=data)


# ============ 固定路径路由（必须在 /{contract_id} 之前） ============

@router.get("/templates", response_model=UnifiedResponse)
async def get_contract_templates(
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取合同模板列表（含智能条件模板）"""
    from src.services.template_engine import get_template_library

    templates = []
    for t in get_template_library():
        templates.append({
            "id": t.id,
            "name": t.name.replace("{{", "").replace("}}", "").replace("goods_name", ""),
            "type": t.category,
            "description": t.description,
            "field_count": len(t.fields),
            "clause_count": len(t.clauses),
            "regions": t.applicable_regions,
        })

    return UnifiedResponse.success(data={"templates": templates})


@router.get("/templates/{template_id}", response_model=UnifiedResponse)
async def get_template_detail(
    template_id: str,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取模板详情（含字段定义和条款结构）"""
    from dataclasses import asdict

    from src.services.template_engine import get_template_by_id

    template = get_template_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    return UnifiedResponse.success(data={
        "id": template.id,
        "name": template.name,
        "category": template.category,
        "description": template.description,
        "version": template.version,
        "fields": [asdict(f) for f in template.fields],
        "clauses": [{"id": c.id, "title": c.title, "required": c.required, "condition": c.condition} for c in template.clauses],
    })


@router.post("/templates/{template_id}/render", response_model=UnifiedResponse)
async def render_template(
    template_id: str,
    body: TemplateRenderRequest,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """渲染合同模板（根据用户填写的变量生成合同文本）"""
    from src.services.template_engine import TemplateEngine, get_template_by_id

    template = get_template_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    variables = body.variables
    validation_errors = TemplateEngine.validate_variables(template, variables)
    if validation_errors:
        raise HTTPException(status_code=422, detail=validation_errors)

    try:
        rendered = TemplateEngine.render_template(template, variables)
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    return UnifiedResponse.success(data={
        "template_id": template_id,
        "rendered_text": rendered,
        "word_count": len(rendered.replace(" ", "")),
    })


# ============ 动态路径路由 ============


@router.post("/{contract_id}/apply-suggestions")
async def apply_suggestions(
    contract_id: str,
    body: dict[str, Any],  # {"accepted_risk_ids": ["id1", "id2"]}
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """应用用户接受的修改建议"""
    service = ContractService(db)
    accepted_ids = body.get("accepted_risk_ids", [])
    try:
        modified_text = await service.apply_suggestions(
            contract_id, accepted_ids, org_id=user.org_id
        )
    except ValueError as e:
        return UnifiedResponse.error(code=404, message=str(e))

    return UnifiedResponse.success(data={"modified_text": modified_text})


@router.post("/{contract_id}/save-file")
async def save_contract_file(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """保存合同文件到服务器"""
    service = ContractService(db)
    try:
        file_path = await service.save_contract_file(
            contract_id, user_id=user.id, org_id=user.org_id
        )
    except ValueError as e:
        return UnifiedResponse.error(code=404, message=str(e))

    return UnifiedResponse.success(data={"file_path": file_path}, message="合同已保存")


@router.post("/{contract_id}/attachments", response_model=UnifiedResponse)
async def upload_contract_attachment(
    request: Request,
    contract_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
    _: None = Depends(rate_limit_upload),
) -> dict[str, Any]:
    """上传合同附件并写入对象存储。"""
    service = ContractService(db)
    content, filename, content_type = await read_validated_upload_file(file)
    try:
        attachment = await service.upload_attachment(
            contract_id,
            filename=filename,
            content=content,
            content_type=content_type,
            org_id=user.org_id,
            actor_id=user.id,
        )
    except ValueError as exc:
        return UnifiedResponse.error(code=404, message=str(exc))

    await AuditService(db).log_from_request(
        request,
        action=AuditAction.CONTRACT_ATTACHMENT_UPLOAD.value,
        resource_type=ResourceType.CONTRACT.value,
        resource_id=contract_id,
        user=user,
        new_value=_serialize_attachment(attachment),
    )
    return UnifiedResponse.success(data=_serialize_attachment(attachment), message="合同附件已上传")


@router.get("/{contract_id}/attachments", response_model=UnifiedResponse)
async def list_contract_attachments(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """列出合同附件。"""
    service = ContractService(db)
    try:
        attachments = await service.list_attachments(contract_id, org_id=user.org_id)
    except ValueError as exc:
        return UnifiedResponse.error(code=404, message=str(exc))

    return UnifiedResponse.success(data={
        "contract_id": contract_id,
        "attachments": [_serialize_attachment(item) for item in attachments],
    })


@router.get("/{contract_id}/attachments/{attachment_id}/download")
async def download_contract_attachment(
    contract_id: str,
    attachment_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> StreamingResponse:
    """下载合同附件。"""
    service = ContractService(db)
    try:
        attachment, content = await service.get_attachment_content(
            contract_id,
            attachment_id,
            org_id=user.org_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ObjectStorageError as exc:
        raise HTTPException(status_code=404, detail="附件文件不存在或不可用") from exc

    await AuditService(db).log_from_request(
        request,
        action=AuditAction.CONTRACT_ATTACHMENT_DOWNLOAD.value,
        resource_type=ResourceType.CONTRACT.value,
        resource_id=contract_id,
        user=user,
        extra_data={"attachment_id": attachment.id, "filename": attachment.original_filename},
    )

    encoded_filename = urllib.parse.quote(attachment.original_filename)
    return StreamingResponse(
        io.BytesIO(content),
        media_type=attachment.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
        },
    )


@router.get("/{contract_id}/attachments/{attachment_id}/download-url", response_model=UnifiedResponse)
async def get_contract_attachment_download_url(
    contract_id: str,
    attachment_id: str,
    request: Request,
    expires_seconds: int = Query(3600, ge=60, le=86400),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取合同附件对象存储下载 URL。"""
    service = ContractService(db)
    try:
        attachment, url = await service.get_attachment_download_url(
            contract_id,
            attachment_id,
            org_id=user.org_id,
            expires_seconds=expires_seconds,
        )
    except ValueError as exc:
        return UnifiedResponse.error(code=404, message=str(exc))
    except ObjectStorageError as exc:
        raise HTTPException(status_code=404, detail="附件文件不存在或不可用") from exc

    await AuditService(db).log_from_request(
        request,
        action=AuditAction.CONTRACT_ATTACHMENT_DOWNLOAD.value,
        resource_type=ResourceType.CONTRACT.value,
        resource_id=contract_id,
        user=user,
        extra_data={"attachment_id": attachment.id, "filename": attachment.original_filename, "presigned": True},
    )
    return UnifiedResponse.success(data={
        "attachment": _serialize_attachment(attachment),
        "download_url": url,
        "expires_seconds": expires_seconds,
    })


@router.delete("/{contract_id}/attachments/{attachment_id}", response_model=UnifiedResponse)
async def delete_contract_attachment(
    contract_id: str,
    attachment_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """删除合同附件对象和数据库记录。"""
    service = ContractService(db)
    try:
        attachment = await service.delete_attachment(
            contract_id,
            attachment_id,
            org_id=user.org_id,
        )
    except ValueError as exc:
        return UnifiedResponse.error(code=404, message=str(exc))
    except ObjectStorageError as exc:
        raise HTTPException(status_code=503, detail="附件存储不可用，删除未完成") from exc

    serialized = _serialize_attachment(attachment)
    await AuditService(db).log_from_request(
        request,
        action=AuditAction.CONTRACT_ATTACHMENT_DELETE.value,
        resource_type=ResourceType.CONTRACT.value,
        resource_id=contract_id,
        user=user,
        old_value=serialized,
    )
    return UnifiedResponse.success(data={"deleted": True, "attachment": serialized}, message="合同附件已删除")


@router.post("/{contract_id}/transition", response_model=UnifiedResponse)
async def transition_contract_status(
    contract_id: str,
    body: ContractTransitionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """按合同生命周期矩阵转换状态"""
    try:
        target_status = ContractStatus(body.status)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="不支持的合同状态") from exc

    service = ContractService(db)
    try:
        contract = await service.transition_status(
            contract_id,
            target_status,
            actor_id=user.id,
            reason=body.reason,
            org_id=user.org_id,
        )
    except IllegalStateTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        return UnifiedResponse.error(code=404, message=str(exc))

    return UnifiedResponse.success(data={
        "contract_id": contract.id,
        "status": contract.status.value,
    })


@router.get("/{contract_id}/versions", response_model=UnifiedResponse)
async def list_contract_versions(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取合同版本时间线"""
    service = ContractService(db)
    try:
        versions = await service.get_contract_versions(contract_id, org_id=user.org_id)
    except ValueError as exc:
        return UnifiedResponse.error(code=404, message=str(exc))

    return UnifiedResponse.success(data={
        "contract_id": contract_id,
        "versions": [
            {
                "id": version.id,
                "version": version.version,
                "source": version.source,
                "description": version.description,
                "created_at": version.created_at.isoformat() if version.created_at else None,
                "created_by": version.created_by,
            }
            for version in versions
        ],
    })


@router.get("/{contract_id}/versions/diff", response_model=UnifiedResponse)
async def diff_contract_versions(
    contract_id: str,
    from_version: int = Query(..., ge=1),
    to_version: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """按段落对比两个合同版本"""
    service = ContractService(db)
    try:
        diff = await service.get_version_diff(
            contract_id,
            from_version,
            to_version,
            org_id=user.org_id,
        )
    except ValueError as exc:
        return UnifiedResponse.error(code=404, message=str(exc))

    return UnifiedResponse.success(data=diff)


@router.post("/{contract_id}/versions/{version}/rollback", response_model=UnifiedResponse)
async def rollback_contract_version(
    contract_id: str,
    version: int,
    body: ContractRollbackRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """回滚到指定合同版本，状态变更必须通过生命周期矩阵"""
    service = ContractService(db)
    try:
        contract = await service.rollback_to_version(
            contract_id,
            version,
            actor_id=user.id,
            reason=body.reason if body else None,
            org_id=user.org_id,
        )
    except IllegalStateTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        return UnifiedResponse.error(code=404, message=str(exc))

    return UnifiedResponse.success(data={
        "contract_id": contract.id,
        "status": contract.status.value,
        "version": contract.version,
        "text": contract.modified_text or contract.original_text or "",
    })


@router.get("/{contract_id}/download")
async def download_contract(
    contract_id: str,
    format: str = Query("docx", pattern="^(pdf|docx)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> StreamingResponse:
    """下载合同文件（PDF 或 DOCX）"""
    service = ContractService(db)
    contract = await service.get_contract(contract_id, org_id=user.org_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    text = contract.modified_text or contract.original_text
    if not text:
        raise HTTPException(status_code=400, detail="没有可下载的合同内容")

    # 获取风险列表
    risks_data = []
    for r in contract.risks:
        risks_data.append({
            "title": r.title,
            "risk_type": r.risk_type,
            "risk_level": r.risk_level.value if r.risk_level else "medium",
            "description": r.description,
            "suggestion": r.suggestion,
            "is_resolved": r.is_resolved,
        })

    from src.services.document_export import ContractExportService, ExportSizeLimitError

    try:
        if format == "docx":
            output = ContractExportService.export_docx(
                title=contract.title,
                text=text,
                contract_number=contract.contract_number,
                risk_level=contract.risk_level.value if contract.risk_level else None,
                risk_score=contract.risk_score,
                review_summary=contract.review_summary,
                risks=risks_data,
            )
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = f"{contract.title}.docx"
        else:
            output = ContractExportService.export_pdf(
                title=contract.title,
                text=text,
                contract_number=contract.contract_number,
                risk_level=contract.risk_level.value if contract.risk_level else None,
                risk_score=contract.risk_score,
                review_summary=contract.review_summary,
                risks=risks_data,
            )
            media_type = "application/pdf"
            filename = f"{contract.title}.pdf"
    except ExportSizeLimitError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    import urllib.parse
    encoded_filename = urllib.parse.quote(filename)

    return StreamingResponse(
        ContractExportService.iter_bytes(output),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
        },
    )


@router.get("/{contract_id}", response_model=UnifiedResponse)
async def get_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取合同详情"""
    service = ContractService(db)
    contract = await service.get_contract(contract_id, org_id=user.org_id)

    if not contract:
        return UnifiedResponse.error(code=404, message="合同不存在")

    data = ContractResponse(
        id=contract.id,
        contract_number=contract.contract_number,
        title=contract.title,
        contract_type=contract.contract_type,
        status=contract.status.value,
        risk_level=contract.risk_level.value if contract.risk_level else None,
        risk_score=contract.risk_score,
        amount=contract.amount,
        effective_date=contract.effective_date,
        expiry_date=contract.expiry_date,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )
    return UnifiedResponse.success(data=data)


@router.post("/{contract_id}/review", response_model=UnifiedResponse)
async def review_contract(
    contract_id: str,
    request: ContractReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """AI审查合同"""
    service = ContractService(db)

    try:
        result = await service.review_contract(
            contract_id=contract_id,
            contract_text=request.contract_text,
            reviewed_by=user.id,
            org_id=user.org_id,
        )
        return UnifiedResponse.success(data=ContractReviewResponse(**result))
    except ContractReviewAlreadyRunning as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ContractReviewLockUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ContractReviewTimeoutError as e:
        await db.commit()
        raise HTTPException(status_code=504, detail=str(e)) from e
    except ContractReviewExecutionError as e:
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e)) from e
    except IllegalStateTransition as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        return UnifiedResponse.error(code=404, message=str(e))


@router.get("/{contract_id}/risks", response_model=UnifiedResponse)
async def get_contract_risks(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """获取合同风险点"""
    service = ContractService(db)
    contract = await service.get_contract(contract_id, org_id=user.org_id)
    if not contract:
        return UnifiedResponse.error(code=404, message="合同不存在")

    risks = await service.get_risks(contract_id, org_id=user.org_id)

    data = [
        ContractRiskResponse(
            id=r.id,
            risk_type=r.risk_type,
            risk_level=r.risk_level.value,
            title=r.title,
            description=r.description,
            related_clause=r.related_clause,
            suggestion=r.suggestion,
            is_resolved=r.is_resolved,
        )
        for r in risks
    ]
    return UnifiedResponse.success(data=data)


@router.post("/{contract_id}/risks/{risk_id}/resolve", response_model=UnifiedResponse)
async def resolve_risk(
    contract_id: str,
    risk_id: str,
    resolution_note: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """标记风险已解决"""
    service = ContractService(db)
    success = await service.resolve_risk(
        risk_id,
        resolution_note,
        contract_id=contract_id,
        org_id=user.org_id,
    )

    if not success:
        return UnifiedResponse.error(code=404, message="风险点不存在")

    return UnifiedResponse.success(message="风险已标记为已解决")


# ============ 文档解析和智能审查 ============

class DocumentParseResponse(BaseModel):
    """文档解析响应"""
    success: bool
    text: str = ""
    char_count: int = 0
    word_count: int = 0
    contract_type: str = ""
    key_info: dict[str, Any] = Field(default_factory=dict)
    structure: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class QuickReviewRequest(BaseModel):
    """快速审查请求"""
    text: str
    contract_type: str | None = None


class QuickReviewResponse(BaseModel):
    """快速审查响应"""
    summary: str
    risk_level: str
    risk_score: float
    key_risks: list[dict[str, Any]]
    suggestions: list[str]
    key_terms: dict[str, Any]


@router.post("/parse", response_model=DocumentParseResponse)
async def parse_contract_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user_required),
) -> DocumentParseResponse:
    """
    解析合同文档
    
    支持格式: PDF, Word (.docx), TXT, Markdown
    """
    try:
        content, filename, _content_type = await read_validated_upload_file(file)
        result = await parse_contract_document(
            file_content=content,
            file_name=filename,
        )

        if result.get("error"):
            return DocumentParseResponse(
                success=False,
                error=result.get("error"),
            )

        return DocumentParseResponse(
            success=True,
            text=result.get("text", ""),
            char_count=result.get("char_count", 0),
            word_count=result.get("word_count", 0),
            contract_type=result.get("contract_type", ""),
            key_info=result.get("key_info", {}),
            structure=result.get("structure", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档解析失败: {e}")
        return DocumentParseResponse(
            success=False,
            error=str(e),
        )


@router.post("/quick-review", response_model=QuickReviewResponse)
async def quick_review_contract(
    request: QuickReviewRequest,
    user: User = Depends(get_current_user_required),
) -> QuickReviewResponse:
    """
    快速审查合同文本
    
    无需创建合同记录，直接返回审查结果
    """
    try:
        workforce = get_workforce()

        # 自动检测合同类型
        contract_type = request.contract_type
        if not contract_type:
            contract_type = contract_analyzer.analyze_contract_type(request.text)

        # 提取关键信息
        key_info = contract_analyzer.extract_key_info(request.text)

        # 调用合同审查智能体（增强版）
        review_prompt = f"""请对以下合同进行专业审查，识别关键风险点并引用法律依据：

合同类型：{contract_type}

合同内容：
{request.text[:8000]}

请以JSON格式返回：
{{
    "summary": "审查总结（200字以上，概述合同类型、主要内容和核心风险）",
    "risk_level": "low/medium/high/critical",
    "risk_score": 0.0-1.0,
    "key_risks": [
        {{"type": "风险类型", "title": "风险标题", "level": "等级", "description": "描述（引用法律依据）", "legal_basis": "相关法条", "suggestion": "建议", "suggested_text": "修改后文本"}}
    ],
    "missing_clauses": ["缺少的重要条款1", "缺少的重要条款2"],
    "suggestions": ["建议1", "建议2", "建议3"],
    "key_terms": {{
        "parties": "合同主体",
        "amount": "金额",
        "term": "期限"
    }}
}}
"""

        result = await workforce.process_task(
            task_description=review_prompt,
            task_type="contract_review",
        )

        # 解析结果
        review_data = _normalize_review_payload(result.get("final_result", {}))

        # 合并高风险词检测结果
        high_risk_terms = key_info.get("high_risk_terms", [])
        if high_risk_terms:
            review_data["key_risks"].append({
                "type": "高风险条款",
                "title": "检测到高风险关键词",
                "level": "high",
                "description": f"文本中包含以下高风险表述：{', '.join(high_risk_terms)}",
                "suggestion": "请仔细审查这些条款的具体内容"
            })
            review_data["risks"] = review_data["key_risks"]

        return QuickReviewResponse(
            summary=review_data["summary"],
            risk_level=review_data["risk_level"],
            risk_score=review_data["risk_score"],
            key_risks=review_data["key_risks"],
            suggestions=review_data["suggestions"],
            key_terms=review_data["key_terms"],
        )

    except Exception as e:
        logger.error(f"快速审查失败: {e}")
        raise HTTPException(status_code=500, detail=f"审查失败: {str(e)}") from e


@router.post("/review-stream")
async def stream_review_contract(
    file: UploadFile = File(None),
    text: str = Form(None),
    user: User = Depends(get_current_user_required),
) -> StreamingResponse:
    """
    流式合同审查（SSE）
    
    支持上传文件或直接传入文本
    """

    async def generate_stream() -> AsyncIterator[str]:
        workforce = get_workforce()

        # 发送开始事件
        yield f"data: {json.dumps({'type': 'start', 'message': '开始处理合同...'})}\n\n"
        await asyncio.sleep(0.1)

        try:
            # 解析文档
            if file:
                yield f"data: {json.dumps({'type': 'parsing', 'message': '正在解析文档...'})}\n\n"
                try:
                    content, filename, _content_type = await read_validated_upload_file(file)
                except HTTPException as exc:
                    yield f"data: {json.dumps({'type': 'error', 'message': exc.detail}, ensure_ascii=False)}\n\n"
                    return
                parse_result = await parse_contract_document(
                    file_content=content,
                    file_name=filename,
                )

                if parse_result.get("error"):
                    yield f"data: {json.dumps({'type': 'error', 'message': parse_result.get('error')})}\n\n"
                    return

                contract_text = parse_result.get("text", "")
                contract_type = parse_result.get("contract_type", "通用合同")

                yield f"data: {json.dumps({'type': 'parsed', 'contract_type': contract_type, 'char_count': len(contract_text)})}\n\n"

            elif text:
                contract_text = text
                contract_type = contract_analyzer.analyze_contract_type(text)
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': '请提供合同文件或文本'})}\n\n"
                return

            # 预分析
            yield f"data: {json.dumps({'type': 'analyzing', 'agent': '合同审查Agent', 'message': '正在提取关键信息...'})}\n\n"
            await asyncio.sleep(0.2)

            key_info = contract_analyzer.extract_key_info(contract_text)
            yield f"data: {json.dumps({'type': 'key_info', 'data': key_info})}\n\n"

            # 智能体审查
            yield f"data: {json.dumps({'type': 'reviewing', 'agent': '风险评估Agent', 'message': '正在识别风险条款...'})}\n\n"

            # 调用智能体（增强版提示）
            result = await workforce.process_task(
                task_description=f"请对以下{contract_type}进行全面、系统的专业审查，按照三层审查框架逐一检查，引用具体法律条文，列出缺失条款：\n\n{contract_text[:10000]}",
                task_type="contract_review",
                context={
                    "contract_type": contract_type,
                }
            )

            review_data = _normalize_review_payload(result.get("final_result", {}))

            # 发送审查结果
            yield f"data: {json.dumps({'type': 'risks', 'data': review_data['risks']}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'suggestions', 'data': review_data['suggestions']}, ensure_ascii=False)}\n\n"

            # 发送缺失条款（新增）
            missing = review_data["missing_clauses"]
            if missing:
                yield f"data: {json.dumps({'type': 'missing_clauses', 'data': missing}, ensure_ascii=False)}\n\n"

            # 发送关键条款（新增）
            key_terms = review_data["key_terms"]
            if key_terms:
                yield f"data: {json.dumps({'type': 'key_terms', 'data': key_terms}, ensure_ascii=False)}\n\n"

            # 完成
            yield f"data: {json.dumps({'type': 'done', 'summary': review_data['summary'], 'risk_level': review_data['risk_level'], 'risk_score': review_data['risk_score']}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"流式审查失败: {e}", exc_info=True)
            error_msg = "审查过程中发生错误，请稍后重试" if settings.ENVIRONMENT == "production" else str(e)
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/upload-and-review")
async def upload_and_review_contract(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """
    上传合同文件并进行完整审查
    
    1. 解析文档
    2. 创建合同记录
    3. AI审查
    4. 保存风险点
    """
    try:
        # 解析文档
        content, filename, _content_type = await read_validated_upload_file(file)
        parse_result = await parse_contract_document(
            file_content=content,
            file_name=filename,
        )

        if parse_result.get("error"):
            raise HTTPException(status_code=400, detail=parse_result.get("error"))

        contract_text = parse_result.get("text", "")
        contract_type = parse_result.get("contract_type", "通用合同")
        key_info = parse_result.get("key_info", {})

        # 创建合同记录
        service = ContractService(db)
        contract = await service.create_contract(
            title=title or filename,
            contract_type=contract_type,
            org_id=user.org_id,
        )

        # 保存原始合同文本
        contract.original_text = contract_text

        # 执行AI审查
        review_result = await service.review_contract(
            contract_id=contract.id,
            contract_text=contract_text,
            reviewed_by=user.id,
            org_id=user.org_id,
        )

        return {
            "contract_id": contract.id,
            "contract_number": contract.contract_number,
            "title": contract.title,
            "contract_type": contract_type,
            "parse_result": {
                "char_count": parse_result.get("char_count", 0),
                "word_count": parse_result.get("word_count", 0),
                "key_info": key_info,
            },
            "review_result": review_result,
        }

    except ContractReviewAlreadyRunning as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ContractReviewLockUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ContractReviewTimeoutError as e:
        await db.commit()
        raise HTTPException(status_code=504, detail=str(e)) from e
    except ContractReviewExecutionError as e:
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e)) from e
    except IllegalStateTransition as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传审查失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}") from e
