"""合同审查路由"""

from datetime import date, datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import json
import asyncio

from src.core.config import settings
from src.core.responses import UnifiedResponse
from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.services.contract_service import ContractService
from src.services.document_parser import parse_contract_document, contract_analyzer
from src.models.user import User
from src.agents.workforce import get_workforce

router = APIRouter()


class ContractCreate(BaseModel):
    """创建合同"""
    title: str
    contract_type: str
    party_a: Optional[dict] = None
    party_b: Optional[dict] = None
    amount: Optional[float] = None
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None


class ContractResponse(BaseModel):
    """合同响应"""
    id: str
    contract_number: Optional[str] = None
    title: str
    contract_type: str
    status: str
    risk_level: Optional[str] = None
    risk_score: Optional[float] = None
    amount: Optional[float] = None
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime


class ContractListResponse(BaseModel):
    """合同列表响应"""
    items: List[ContractResponse]
    total: int
    page: int
    page_size: int


class ContractReviewRequest(BaseModel):
    """合同审查请求"""
    contract_text: str


class ContractReviewResponse(BaseModel):
    """合同审查响应"""
    contract_id: str
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    summary: str
    risks: list = []
    suggestions: list = []
    key_terms: dict = {}


class ContractRiskResponse(BaseModel):
    """合同风险响应"""
    id: str
    risk_type: str
    risk_level: str
    title: str
    description: str
    related_clause: Optional[str] = None
    suggestion: Optional[str] = None
    is_resolved: bool


@router.get("/", response_model=UnifiedResponse)
async def list_contracts(
    status: Optional[str] = None,
    contract_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
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
):
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
):
    """获取合同模板列表"""
    data = {
        "templates": [
            {"id": "1", "name": "采购合同模板", "type": "purchase"},
            {"id": "2", "name": "服务协议模板", "type": "service"},
            {"id": "3", "name": "劳动合同模板", "type": "labor"},
            {"id": "4", "name": "租赁合同模板", "type": "lease"},
            {"id": "5", "name": "保密协议模板", "type": "nda"},
        ]
    }
    return UnifiedResponse.success(data=data)


# ============ 动态路径路由 ============


@router.post("/{contract_id}/apply-suggestions")
async def apply_suggestions(
    contract_id: str,
    body: dict,  # {"accepted_risk_ids": ["id1", "id2"]}
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """应用用户接受的修改建议"""
    service = ContractService(db)
    accepted_ids = body.get("accepted_risk_ids", [])
    modified_text = await service.apply_suggestions(contract_id, accepted_ids)
    return UnifiedResponse.success(data={"modified_text": modified_text})


@router.post("/{contract_id}/save-file")
async def save_contract_file(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """保存合同文件到服务器"""
    service = ContractService(db)
    file_path = await service.save_contract_file(
        contract_id, user_id=user.id
    )
    return UnifiedResponse.success(data={"file_path": file_path}, message="合同已保存")


@router.get("/{contract_id}/download")
async def download_contract(
    contract_id: str,
    format: str = Query("docx", pattern="^(pdf|docx)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """下载合同文件（PDF 或 DOCX）"""
    service = ContractService(db)
    contract = await service.get_contract(contract_id)
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

    from src.services.document_export import ContractExportService

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

    import urllib.parse
    encoded_filename = urllib.parse.quote(filename)

    return StreamingResponse(
        output,
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
):
    """获取合同详情"""
    service = ContractService(db)
    contract = await service.get_contract(contract_id)
    
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
):
    """AI审查合同"""
    service = ContractService(db)
    
    try:
        result = await service.review_contract(
            contract_id=contract_id,
            contract_text=request.contract_text,
            reviewed_by=user.id,
        )
        return UnifiedResponse.success(data=ContractReviewResponse(**result))
    except ValueError as e:
        return UnifiedResponse.error(code=404, message=str(e))


@router.get("/{contract_id}/risks", response_model=UnifiedResponse)
async def get_contract_risks(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取合同风险点"""
    service = ContractService(db)
    risks = await service.get_risks(contract_id)
    
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
    resolution_note: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """标记风险已解决"""
    service = ContractService(db)
    success = await service.resolve_risk(risk_id, resolution_note)
    
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
    key_info: dict = {}
    structure: dict = {}
    error: Optional[str] = None


class QuickReviewRequest(BaseModel):
    """快速审查请求"""
    text: str
    contract_type: Optional[str] = None


class QuickReviewResponse(BaseModel):
    """快速审查响应"""
    summary: str
    risk_level: str
    risk_score: float
    key_risks: List[dict]
    suggestions: List[str]
    key_terms: dict


@router.post("/parse", response_model=DocumentParseResponse)
async def parse_contract_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user_required),
):
    """
    解析合同文档
    
    支持格式: PDF, Word (.docx), TXT, Markdown
    """
    try:
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件大小超过限制（最大 {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB）"
            )
        result = await parse_contract_document(
            file_content=content,
            file_name=file.filename,
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
):
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
        
        # 调用合同审查智能体
        review_prompt = f"""
请快速审查以下合同文本，识别关键风险点：

合同类型：{contract_type}

合同内容：
{request.text[:8000]}

请以JSON格式返回：
{{
    "summary": "审查总结（100字以内）",
    "risk_level": "low/medium/high/critical",
    "risk_score": 0.0-1.0,
    "key_risks": [
        {{"type": "风险类型", "title": "风险标题", "level": "等级", "description": "描述", "suggestion": "建议"}}
    ],
    "suggestions": ["建议1", "建议2"],
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
        review_data = result.get("final_result", {})
        if isinstance(review_data, str):
            import re
            json_match = re.search(r'\{[\s\S]*\}', review_data)
            if json_match:
                try:
                    review_data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    review_data = {}
        
        # 合并高风险词检测结果
        high_risk_terms = key_info.get("high_risk_terms", [])
        if high_risk_terms and "key_risks" in review_data:
            review_data["key_risks"].append({
                "type": "高风险条款",
                "title": "检测到高风险关键词",
                "level": "high",
                "description": f"文本中包含以下高风险表述：{', '.join(high_risk_terms)}",
                "suggestion": "请仔细审查这些条款的具体内容"
            })
        
        return QuickReviewResponse(
            summary=review_data.get("summary", "审查完成"),
            risk_level=review_data.get("risk_level", "medium"),
            risk_score=float(review_data.get("risk_score", 0.5)),
            key_risks=review_data.get("key_risks", []),
            suggestions=review_data.get("suggestions", []),
            key_terms=review_data.get("key_terms", {}),
        )
        
    except Exception as e:
        logger.error(f"快速审查失败: {e}")
        raise HTTPException(status_code=500, detail=f"审查失败: {str(e)}")


@router.post("/review-stream")
async def stream_review_contract(
    file: UploadFile = File(None),
    text: str = Form(None),
    user: User = Depends(get_current_user_required),
):
    """
    流式合同审查（SSE）
    
    支持上传文件或直接传入文本
    """
    
    async def generate_stream():
        workforce = get_workforce()
        
        # 发送开始事件
        yield f"data: {json.dumps({'type': 'start', 'message': '开始处理合同...'})}\n\n"
        await asyncio.sleep(0.1)
        
        try:
            # 解析文档
            if file:
                yield f"data: {json.dumps({'type': 'parsing', 'message': '正在解析文档...'})}\n\n"
                content = await file.read()
                if len(content) > settings.MAX_UPLOAD_SIZE:
                    yield f"data: {json.dumps({'type': 'error', 'message': f'文件大小超过限制（最大 {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB）'})}\n\n"
                    return
                parse_result = await parse_contract_document(
                    file_content=content,
                    file_name=file.filename,
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
            
            # 调用智能体
            result = await workforce.process_task(
                task_description=f"请审查以下{contract_type}：\n\n{contract_text[:8000]}",
                task_type="contract_review",
            )
            
            review_data = result.get("final_result", {})
            
            # 发送审查结果
            yield f"data: {json.dumps({'type': 'risks', 'data': review_data.get('risks', [])})}\n\n"
            yield f"data: {json.dumps({'type': 'suggestions', 'data': review_data.get('suggestions', [])})}\n\n"
            
            # 完成
            yield f"data: {json.dumps({'type': 'done', 'summary': review_data.get('summary', '审查完成'), 'risk_level': review_data.get('risk_level', 'medium'), 'risk_score': review_data.get('risk_score', 0.5)})}\n\n"
            
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
    title: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """
    上传合同文件并进行完整审查
    
    1. 解析文档
    2. 创建合同记录
    3. AI审查
    4. 保存风险点
    """
    try:
        # 解析文档
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件大小超过限制（最大 {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB）"
            )
        parse_result = await parse_contract_document(
            file_content=content,
            file_name=file.filename,
        )
        
        if parse_result.get("error"):
            raise HTTPException(status_code=400, detail=parse_result.get("error"))
        
        contract_text = parse_result.get("text", "")
        contract_type = parse_result.get("contract_type", "通用合同")
        key_info = parse_result.get("key_info", {})
        
        # 创建合同记录
        service = ContractService(db)
        contract = await service.create_contract(
            title=title or file.filename or "未命名合同",
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传审查失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")
