# -*- coding: utf-8 -*-
"""
案源管理路由
"""

from typing import List, Literal, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.core.responses import UnifiedResponse
from src.models.user import User
from src.services.lead_service import LeadService

router = APIRouter()


class LeadCreate(BaseModel):
    clientName: str = Field(..., min_length=1, max_length=100, description="客户名称")
    contactInfo: Optional[str] = Field(None, max_length=500, description="联系方式")
    source: Optional[str] = Field(None, max_length=100, description="来源渠道")
    caseType: Optional[str] = Field(None, max_length=100, description="案件类型")
    estimatedAmount: float = Field(default=0.0, ge=0, description="预估金额")
    stage: Literal["new", "contacted", "qualified", "proposal", "won", "lost"] = Field(
        default="new", description="阶段"
    )
    assignee: Optional[str] = Field(None, description="负责人")


class LeadUpdate(BaseModel):
    clientName: Optional[str] = Field(None, min_length=1, max_length=100, description="客户名称")
    contactInfo: Optional[str] = Field(None, max_length=500, description="联系方式")
    source: Optional[str] = Field(None, max_length=100, description="来源渠道")
    caseType: Optional[str] = Field(None, max_length=100, description="案件类型")
    estimatedAmount: Optional[float] = Field(None, ge=0, description="预估金额")
    stage: Optional[Literal["new", "contacted", "qualified", "proposal", "won", "lost"]] = Field(
        None, description="阶段"
    )


class FollowUpCreate(BaseModel):
    date: str
    content: str
    type: str  # 电话, 面谈, 邮件, 微信


class LeadResponse(BaseModel):
    id: str
    clientName: str
    contactInfo: Optional[str] = None
    source: Optional[str] = None
    caseType: Optional[str] = None
    estimatedAmount: float = 0.0
    stage: str
    assignee: Optional[str] = None
    followUps: list = []
    createdAt: Optional[str] = None


def lead_to_response(lead) -> LeadResponse:
    return LeadResponse(
        id=lead.id,
        clientName=lead.client_name,
        contactInfo=lead.contact_info,
        source=lead.source,
        caseType=lead.case_type,
        estimatedAmount=lead.estimated_amount,
        stage=lead.stage,
        assignee=None,
        followUps=lead.follow_ups or [],
        createdAt=lead.created_at.isoformat() if lead.created_at else None,
    )


@router.get("/")
async def list_leads(
    stage: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    service = LeadService(db)
    leads, total = await service.list_leads(
        org_id=user.org_id,
        stage=stage,
        page=page,
        page_size=page_size,
    )
    return UnifiedResponse.success(data={
        "items": [lead_to_response(l) for l in leads],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/")
async def create_lead(
    data: LeadCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    service = LeadService(db)
    lead = await service.create_lead(
        client_name=data.clientName,
        contact_info=data.contactInfo,
        source=data.source,
        case_type=data.caseType,
        estimated_amount=data.estimatedAmount,
        stage=data.stage,
        created_by=user.id,
        org_id=user.org_id,
    )
    return UnifiedResponse.success(data=lead_to_response(lead))


@router.put("/{lead_id}")
async def update_lead(
    lead_id: str,
    data: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    service = LeadService(db)
    update_data = {}
    if data.clientName is not None:
        update_data["client_name"] = data.clientName
    if data.contactInfo is not None:
        update_data["contact_info"] = data.contactInfo
    if data.source is not None:
        update_data["source"] = data.source
    if data.caseType is not None:
        update_data["case_type"] = data.caseType
    if data.estimatedAmount is not None:
        update_data["estimated_amount"] = data.estimatedAmount
    if data.stage is not None:
        update_data["stage"] = data.stage

    lead = await service.update_lead(lead_id, org_id=user.org_id, **update_data)
    if not lead:
        return UnifiedResponse.error(code=404, message="线索不存在")
    return UnifiedResponse.success(data=lead_to_response(lead))


@router.patch("/{lead_id}/stage")
async def update_lead_stage(
    lead_id: str,
    stage: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    service = LeadService(db)
    lead = await service.update_stage(lead_id, stage, org_id=user.org_id)
    if not lead:
        return UnifiedResponse.error(code=404, message="线索不存在")
    return UnifiedResponse.success(data=lead_to_response(lead))


@router.post("/{lead_id}/follow-ups")
async def add_follow_up(
    lead_id: str,
    data: FollowUpCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    service = LeadService(db)
    lead = await service.add_follow_up(
        lead_id,
        {"date": data.date, "content": data.content, "type": data.type},
        org_id=user.org_id,
    )
    if not lead:
        return UnifiedResponse.error(code=404, message="线索不存在")
    return UnifiedResponse.success(data=lead_to_response(lead))


@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    service = LeadService(db)
    success = await service.delete_lead(lead_id, org_id=user.org_id)
    if not success:
        return UnifiedResponse.error(code=404, message="线索不存在")
    return UnifiedResponse.success(message="删除成功")
