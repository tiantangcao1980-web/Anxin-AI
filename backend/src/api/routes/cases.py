"""案件管理路由"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user, get_current_user_required
from src.core.responses import UnifiedResponse
from src.services.case_service import CaseService
from src.models.user import User
from src.agents.workforce import get_workforce

router = APIRouter()


class CaseCreate(BaseModel):
    """创建案件"""
    title: str
    case_type: str
    description: Optional[str] = None
    priority: str = "medium"
    parties: Optional[dict] = None
    deadline: Optional[datetime] = None


class CaseUpdate(BaseModel):
    """更新案件"""
    title: Optional[str] = None
    case_type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[str] = None


class CaseResponse(BaseModel):
    """案件响应"""
    id: str
    case_number: Optional[str] = None
    title: str
    case_type: str
    status: str
    priority: str
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    risk_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class CaseListResponse(BaseModel):
    """案件列表响应"""
    items: List[CaseResponse]
    total: int
    page: int
    page_size: int


class CaseEventResponse(BaseModel):
    """案件事件响应"""
    id: str
    event_type: str
    title: str
    description: Optional[str] = None
    event_time: datetime
    created_at: datetime


class CaseDocumentResponse(BaseModel):
    """案件文档响应"""
    id: str
    name: str
    doc_type: str
    file_size: int
    ai_summary: Optional[str] = None
    created_at: datetime


class LinkDocumentRequest(BaseModel):
    """关联文档请求"""
    document_id: str


class LegalBriefingResponse(BaseModel):
    """案件简报响应"""
    briefing: str
    key_points: List[str]
    risk_list: List[dict]
    action_items: List[str]
    generated_at: datetime


@router.get("/")
async def list_cases(
    status: Optional[str] = None,
    case_type: Optional[str] = None,
    priority: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取案件列表"""
    service = CaseService(db)

    # V2 架构：律所内部分级数据可见性
    # 合伙人(partner)/管理员(org_admin/admin/super_admin) 看全部
    # 律师(lawyer)/入驻律师(platform_lawyer) 只看自己负责的
    # 助理(paralegal) 只看自己负责的
    _scope_user_id = None
    if user.role in ("lawyer", "platform_lawyer", "paralegal"):
        _scope_user_id = user.id

    cases, total = await service.list_cases(
        org_id=user.org_id,
        assignee_id=_scope_user_id,
        status=status,
        case_type=case_type,
        priority=priority,
        page=page,
        page_size=page_size,
    )
    
    data = CaseListResponse(
        items=[
            CaseResponse(
                id=c.id,
                case_number=c.case_number,
                title=c.title,
                case_type=c.case_type.value,
                status=c.status.value,
                priority=c.priority.value,
                description=c.description,
                assignee_id=c.assignee_id,
                risk_score=c.risk_score,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in cases
        ],
        total=total,
        page=page,
        page_size=page_size
    )
    return UnifiedResponse.success(data=data)


@router.post("/")
async def create_case(
    case: CaseCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """创建案件"""
    service = CaseService(db)
    
    created_case = await service.create_case(
        title=case.title,
        case_type=case.case_type,
        description=case.description,
        priority=case.priority,
        org_id=user.org_id,
        created_by=user.id,
        parties=case.parties,
        deadline=case.deadline,
    )
    
    data = CaseResponse(
        id=created_case.id,
        case_number=created_case.case_number,
        title=created_case.title,
        case_type=created_case.case_type.value,
        status=created_case.status.value,
        priority=created_case.priority.value,
        description=created_case.description,
        created_at=created_case.created_at,
        updated_at=created_case.updated_at,
    )
    return UnifiedResponse.success(data=data)



# ============ 固定路径路由 — 必须在 /{case_id} 之前 ============

@router.get("/statistics/overview")
async def get_cases_statistics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取案件统计概览"""
    service = CaseService(db)
    stats = await service.get_case_statistics(org_id=user.org_id)
    return UnifiedResponse.success(data=stats)


@router.get("/events/recent")
async def get_recent_events(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取最近的案件事件"""
    service = CaseService(db)
    events = await service.get_recent_events(org_id=user.org_id, limit=limit)
    data = []
    for event, case in events:
        data.append({
            "id": event.id,
            "case_id": case.id,
            "case_number": case.case_number,
            "case_title": case.title,
            "event_type": event.event_type,
            "title": event.title,
            "description": event.description,
            "event_time": event.event_time,
            "created_at": event.created_at,
        })
    return UnifiedResponse.success(data=data)


@router.get("/alerts")
async def get_alerts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取系统预警"""
    service = CaseService(db)
    alerts = await service.get_alerts(org_id=user.org_id)
    return UnifiedResponse.success(data=alerts)


@router.get("/statistics/compliance")
async def get_compliance_score(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取合规健康分"""
    service = CaseService(db)
    score_data = await service.get_compliance_score(org_id=user.org_id)
    return UnifiedResponse.success(data=score_data)


# ============ 动态路径路由 ============

@router.get("/{case_id}")
async def get_case(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required)
):
    """获取案件详情"""
    service = CaseService(db)
    case = await service.get_case(case_id)
    
    if not case:
        return JSONResponse(
            status_code=404,
            content=UnifiedResponse.error(code=404, message="案件不存在"),
        )
    
    # 简单的越权检查
    if case.org_id != user.org_id:
        return JSONResponse(
            status_code=403,
            content=UnifiedResponse.error(code=403, message="无权访问该案件"),
        )
    
    data = CaseResponse(
        id=case.id,
        case_number=case.case_number,
        title=case.title,
        case_type=case.case_type.value,
        status=case.status.value,
        priority=case.priority.value,
        description=case.description,
        assignee_id=case.assignee_id,
        risk_score=case.risk_score,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )
    return UnifiedResponse.success(data=data)


@router.put("/{case_id}")
async def update_case(
    case_id: str,
    case: CaseUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """更新案件"""
    service = CaseService(db)
    
    # 先检查权限
    existing_case = await service.get_case(case_id)
    if not existing_case:
        return UnifiedResponse.error(code=404, message="案件不存在")
    if existing_case.org_id != user.org_id:
        return UnifiedResponse.error(code=403, message="无权修改该案件")
    
    updated_case = await service.update_case(
        case_id=case_id,
        **case.model_dump(exclude_unset=True)
    )
    
    data = CaseResponse(
        id=updated_case.id,
        case_number=updated_case.case_number,
        title=updated_case.title,
        case_type=updated_case.case_type.value,
        status=updated_case.status.value,
        priority=updated_case.priority.value,
        description=updated_case.description,
        assignee_id=updated_case.assignee_id,
        risk_score=updated_case.risk_score,
        created_at=updated_case.created_at,
        updated_at=updated_case.updated_at,
    )
    return UnifiedResponse.success(data=data)


@router.delete("/{case_id}")
async def delete_case(
    case_id: str, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required)
):
    """删除案件"""
    service = CaseService(db)
    
    # 先检查权限
    existing_case = await service.get_case(case_id)
    if not existing_case:
        return UnifiedResponse.error(code=404, message="案件不存在")
    if existing_case.org_id != user.org_id:
        return UnifiedResponse.error(code=403, message="无权删除该案件")
        
    success = await service.delete_case(case_id)
    return UnifiedResponse.success(message="案件已删除")


@router.get("/{case_id}/timeline")
async def get_case_timeline(
    case_id: str, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required)
):
    """获取案件时间线"""
    service = CaseService(db)
    
    # 权限检查
    case = await service.get_case(case_id)
    if not case or case.org_id != user.org_id:
        return UnifiedResponse.error(code=404, message="案件不存在")
        
    events = await service.get_timeline(case_id)
    
    data = [
        CaseEventResponse(
            id=e.id,
            event_type=e.event_type,
            title=e.title,
            description=e.description,
            event_time=e.event_time,
            created_at=e.created_at,
        )
        for e in events
    ]
    return UnifiedResponse.success(data=data)


@router.post("/{case_id}/analyze")
async def analyze_case(
    case_id: str, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required)
):
    """AI分析案件"""
    service = CaseService(db)
    
    # 权限检查
    case = await service.get_case(case_id)
    if not case or case.org_id != user.org_id:
        return UnifiedResponse.error(code=404, message="案件不存在")
        
    try:
        result = await service.analyze_case(case_id)
        return UnifiedResponse.success(data=result)
    except ValueError as e:
        return UnifiedResponse.error(code=404, message=str(e))


@router.post("/{case_id}/briefing")
async def generate_case_briefing(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required)
):
    """生成案件简报 (Legal Briefing)"""
    service = CaseService(db)
    case = await service.get_case(case_id)
    
    if not case or case.org_id != user.org_id:
        return UnifiedResponse.error(code=404, message="案件不存在")
        
    # 获取案件时间线和相关文档摘要
    timeline = await service.get_timeline(case_id)
    documents = await service.get_case_documents(case_id, org_id=user.org_id)
    
    # 构建上下文
    context = f"案件标题: {case.title}\n案件类型: {case.case_type.value}\n描述: {case.description}\n"
    context += "\n[关键时间节点]:\n" + "\n".join([f"- {e.event_time.date()}: {e.title}" for e in timeline])
    context += "\n[关键文档]:\n" + "\n".join([f"- {d.name}: {d.ai_summary or '暂无摘要'}" for d in documents])
    
    # 调用 Workforce 生成简报
    workforce = get_workforce()
    prompt = f"""
    请为律师生成一份专业的【案件简报 (Legal Briefing)】。
    
    案情上下文：
    {context}
    
    要求：
    1. 语言简练，直击要害，符合法律文书规范。
    2. 结构清晰：案情摘要、争议焦点、风险清单、行动建议。
    3. 重点提示截止日期 (Deadline) 和程序性事项。
    """
    
    try:
        # 这里可以直接调用 legal_advisor，或者专门的 document_drafter
        briefing_text = await workforce.chat(prompt, agent_name="document_drafter")
        
        # 简单解析（实际生产中应使用 Structured Output）
        # 这里为了演示，我们假设 LLM 返回了 Markdown，我们直接返回 Text
        # 前端负责渲染 Markdown
        
        return UnifiedResponse.success(data={
            "briefing": briefing_text,
            "generated_at": datetime.now()
        })
        
    except Exception as e:
        return UnifiedResponse.error(code=500, message=f"生成简报失败: {str(e)}")


# ============ 文档关联 ============

@router.get("/{case_id}/documents")
async def get_case_documents(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """获取案件关联的文档"""
    service = CaseService(db)
    
    # 权限检查
    case = await service.get_case(case_id)
    if not case or case.org_id != user.org_id:
        return UnifiedResponse.error(code=404, message="案件不存在")
        
    documents = await service.get_case_documents(case_id)
    
    data = [
        CaseDocumentResponse(
            id=doc.id,
            name=doc.name,
            doc_type=doc.doc_type.value if hasattr(doc.doc_type, 'value') else str(doc.doc_type),
            file_size=doc.file_size or 0,
            ai_summary=doc.ai_summary,
            created_at=doc.created_at,
        )
        for doc in documents
    ]
    return UnifiedResponse.success(data=data)


@router.post("/{case_id}/documents")
async def link_document_to_case(
    case_id: str,
    request: LinkDocumentRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """关联文档到案件"""
    service = CaseService(db)
    
    # 权限检查
    case = await service.get_case(case_id)
    if not case or case.org_id != user.org_id:
        return UnifiedResponse.error(code=404, message="案件不存在")
        
    success = await service.link_document(
        case_id=case_id,
        document_id=request.document_id,
        org_id=user.org_id,
        created_by=user.id,
    )
    
    if not success:
        return UnifiedResponse.error(code=404, message="案件或文档不存在")
    
    await db.commit()
    return UnifiedResponse.success(message="文档已关联到案件")


@router.delete("/{case_id}/documents/{document_id}")
async def unlink_document_from_case(
    case_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    """取消文档与案件的关联"""
    service = CaseService(db)
    
    # 权限检查
    case = await service.get_case(case_id)
    if not case or case.org_id != user.org_id:
        return UnifiedResponse.error(code=404, message="案件不存在")
        
    success = await service.unlink_document(
        case_id=case_id,
        document_id=document_id,
        created_by=user.id,
    )
    
    if not success:
        return UnifiedResponse.error(code=404, message="文档未关联到该案件")
    
    await db.commit()
    return UnifiedResponse.success(message="已取消文档关联")


# (统计路由已移至 /{case_id} 之前，避免路径匹配冲突)
