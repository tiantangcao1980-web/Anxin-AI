# -*- coding: utf-8 -*-
"""
律所内部管理 API 路由

提供团队管理、工时管理、账单管理接口。
"""

from datetime import date as DateType
from typing import Literal, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.core.database import get_db
from src.core.deps import get_current_user_required, require_permission, Permission
from src.core.responses import UnifiedResponse
from src.models.user import User
from src.services.team_service import TeamService
from src.services.timesheet_service import TimesheetService
from src.services.billing_service import BillingService

router = APIRouter(prefix="/firm", tags=["律所管理"])


# ========== 请求模型 ==========


class CreateTeamRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="团队名称")
    description: Optional[str] = Field(None, description="团队描述")
    leader_id: Optional[str] = Field(None, description="团队负责人ID")


class UpdateTeamRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    leader_id: Optional[str] = None


class AddMemberRequest(BaseModel):
    user_id: str = Field(..., description="用户ID")
    role: str = Field("member", description="角色: leader | member")


class CreateTimeEntryRequest(BaseModel):
    date: DateType = Field(..., description="工时日期")
    minutes: int = Field(..., gt=0, le=1440, description="工时（分钟），最大1440（24小时）")
    description: Optional[str] = Field(None, max_length=500, description="工时说明")
    billable: bool = Field(True, description="是否可计费")
    rate: Optional[float] = Field(None, ge=0, description="费率（元/小时）")
    case_id: Optional[str] = Field(None, description="关联案件ID")


class EntryIdsRequest(BaseModel):
    entry_ids: List[str] = Field(..., min_length=1, description="工时记录ID列表")


class InvoiceItem(BaseModel):
    """发票明细项"""
    description: str = Field(..., min_length=1, max_length=500, description="明细描述")
    hours: float = Field(..., gt=0, description="工时小时数")
    rate: float = Field(..., ge=0, description="费率（元/小时）")
    amount: float = Field(..., ge=0, description="金额")


class CreateInvoiceRequest(BaseModel):
    client_name: str = Field(..., min_length=1, max_length=200, description="客户名称")
    items: List[InvoiceItem] = Field(..., min_length=1, description="发票明细")
    case_id: Optional[str] = Field(None, description="关联案件ID")
    due_date: Optional[DateType] = Field(None, description="到期日")
    notes: Optional[str] = Field(None, description="备注")


class UpdateInvoiceStatusRequest(BaseModel):
    status: Literal["draft", "sent", "paid", "overdue", "cancelled"] = Field(
        ..., description="状态: draft | sent | paid | overdue | cancelled"
    )


# ========== 团队管理 ==========


@router.get("/teams")
async def list_teams(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user: User = Depends(require_permission(Permission.MANAGE_CRM)),
    db: AsyncSession = Depends(get_db),
):
    """获取团队列表"""
    service = TeamService(db)
    teams = await service.list_teams(user.org_id)
    total = len(teams)
    start = (page - 1) * page_size
    items = teams[start: start + page_size]
    return UnifiedResponse.success(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/teams")
async def create_team(
    req: CreateTeamRequest,
    user: User = Depends(require_permission(Permission.MANAGE_CRM)),
    db: AsyncSession = Depends(get_db),
):
    """创建团队"""
    service = TeamService(db)
    team = await service.create_team(
        org_id=user.org_id,
        name=req.name,
        description=req.description,
        leader_id=req.leader_id,
    )
    return UnifiedResponse.success(data=team, message="团队创建成功")


@router.put("/teams/{team_id}")
async def update_team(
    team_id: str,
    req: UpdateTeamRequest,
    user: User = Depends(require_permission(Permission.MANAGE_CRM)),
    db: AsyncSession = Depends(get_db),
):
    """更新团队"""
    service = TeamService(db)
    data = req.model_dump(exclude_none=True)
    team = await service.update_team(team_id, data)
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    return UnifiedResponse.success(data=team, message="团队更新成功")


@router.delete("/teams/{team_id}")
async def delete_team(
    team_id: str,
    user: User = Depends(require_permission(Permission.MANAGE_CRM)),
    db: AsyncSession = Depends(get_db),
):
    """删除团队"""
    service = TeamService(db)
    ok = await service.delete_team(team_id)
    if not ok:
        raise HTTPException(status_code=404, detail="团队不存在")
    return UnifiedResponse.success(message="团队删除成功")


@router.post("/teams/{team_id}/members")
async def add_team_member(
    team_id: str,
    req: AddMemberRequest,
    user: User = Depends(require_permission(Permission.MANAGE_CRM)),
    db: AsyncSession = Depends(get_db),
):
    """添加团队成员"""
    service = TeamService(db)
    try:
        member = await service.add_member(team_id, req.user_id, req.role)
        return UnifiedResponse.success(data=member, message="成员添加成功")
    except Exception as e:
        logger.warning(f"添加团队成员失败: {e}")
        raise HTTPException(status_code=400, detail="成员已存在或参数错误")


@router.delete("/teams/{team_id}/members/{member_user_id}")
async def remove_team_member(
    team_id: str,
    member_user_id: str,
    user: User = Depends(require_permission(Permission.MANAGE_CRM)),
    db: AsyncSession = Depends(get_db),
):
    """移除团队成员"""
    service = TeamService(db)
    ok = await service.remove_member(team_id, member_user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="成员不存在")
    return UnifiedResponse.success(message="成员移除成功")


# ========== 工时管理 ==========


@router.get("/timesheet")
async def list_timesheet(
    user_id: Optional[str] = Query(None, description="用户ID"),
    date_from: Optional[DateType] = Query(None, description="开始日期"),
    date_to: Optional[DateType] = Query(None, description="结束日期"),
    status: Optional[str] = Query(None, description="状态"),
    case_id: Optional[str] = Query(None, description="案件ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user: User = Depends(require_permission(Permission.MANAGE_TIMESHEET)),
    db: AsyncSession = Depends(get_db),
):
    """查询工时记录"""
    service = TimesheetService(db)
    entries = await service.list_entries(
        user_id=user_id or user.id,
        date_from=date_from,
        date_to=date_to,
        status=status,
        case_id=case_id,
    )
    total = len(entries)
    start = (page - 1) * page_size
    items = entries[start: start + page_size]
    return UnifiedResponse.success(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/timesheet")
async def create_time_entry(
    req: CreateTimeEntryRequest,
    user: User = Depends(require_permission(Permission.MANAGE_TIMESHEET)),
    db: AsyncSession = Depends(get_db),
):
    """创建工时记录"""
    service = TimesheetService(db)
    entry = await service.create_entry(
        user_id=user.id,
        entry_date=req.date,
        minutes=req.minutes,
        description=req.description,
        billable=req.billable,
        rate=req.rate,
        case_id=req.case_id,
    )
    return UnifiedResponse.success(data=entry, message="工时记录创建成功")


@router.post("/timesheet/submit")
async def submit_time_entries(
    req: EntryIdsRequest,
    user: User = Depends(require_permission(Permission.MANAGE_TIMESHEET)),
    db: AsyncSession = Depends(get_db),
):
    """批量提交工时记录"""
    service = TimesheetService(db)
    count = await service.submit_entries(req.entry_ids, user.id)
    return UnifiedResponse.success(data={"submitted": count}, message=f"已提交 {count} 条记录")


@router.post("/timesheet/approve")
async def approve_time_entries(
    req: EntryIdsRequest,
    user: User = Depends(require_permission(Permission.MANAGE_TIMESHEET)),
    db: AsyncSession = Depends(get_db),
):
    """批量审批工时记录"""
    service = TimesheetService(db)
    count = await service.approve_entries(req.entry_ids, user.id)
    return UnifiedResponse.success(data={"approved": count}, message=f"已审批 {count} 条记录")


@router.post("/timesheet/reject")
async def reject_time_entries(
    req: EntryIdsRequest,
    user: User = Depends(require_permission(Permission.MANAGE_TIMESHEET)),
    db: AsyncSession = Depends(get_db),
):
    """批量拒绝工时记录"""
    service = TimesheetService(db)
    count = await service.reject_entries(req.entry_ids, user.id)
    return UnifiedResponse.success(data={"rejected": count}, message=f"已拒绝 {count} 条记录")


@router.get("/timesheet/summary")
async def get_timesheet_summary(
    date_from: Optional[DateType] = Query(None, description="开始日期"),
    date_to: Optional[DateType] = Query(None, description="结束日期"),
    user: User = Depends(require_permission(Permission.MANAGE_TIMESHEET)),
    db: AsyncSession = Depends(get_db),
):
    """获取工时汇总"""
    service = TimesheetService(db)
    summary = await service.get_summary(
        org_id=user.org_id,
        date_from=date_from,
        date_to=date_to,
    )
    return UnifiedResponse.success(data=summary)


# ========== 账单管理 ==========


@router.get("/invoices")
async def list_invoices(
    status: Optional[Literal["draft", "sent", "paid", "overdue", "cancelled"]] = Query(
        None, description="状态过滤"
    ),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user: User = Depends(require_permission(Permission.MANAGE_BILLING)),
    db: AsyncSession = Depends(get_db),
):
    """查询发票列表"""
    service = BillingService(db)
    invoices = await service.list_invoices(org_id=user.org_id, status=status)
    total = len(invoices)
    start = (page - 1) * page_size
    items = invoices[start: start + page_size]
    return UnifiedResponse.success(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/invoices")
async def create_invoice(
    req: CreateInvoiceRequest,
    user: User = Depends(require_permission(Permission.MANAGE_BILLING)),
    db: AsyncSession = Depends(get_db),
):
    """创建发票"""
    service = BillingService(db)
    invoice = await service.create_invoice(
        org_id=user.org_id,
        client_name=req.client_name,
        items=[item.model_dump() for item in req.items],
        case_id=req.case_id,
        due_date=req.due_date,
        notes=req.notes,
    )
    return UnifiedResponse.success(data=invoice, message="发票创建成功")


@router.put("/invoices/{invoice_id}/status")
async def update_invoice_status(
    invoice_id: str,
    req: UpdateInvoiceStatusRequest,
    user: User = Depends(require_permission(Permission.MANAGE_BILLING)),
    db: AsyncSession = Depends(get_db),
):
    """更新发票状态"""
    service = BillingService(db)
    invoice = await service.update_invoice_status(invoice_id, req.status)
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    return UnifiedResponse.success(data=invoice, message="发票状态更新成功")


@router.get("/revenue-report")
async def get_revenue_report(
    date_from: Optional[DateType] = Query(None, description="开始日期"),
    date_to: Optional[DateType] = Query(None, description="结束日期"),
    user: User = Depends(require_permission(Permission.MANAGE_BILLING)),
    db: AsyncSession = Depends(get_db),
):
    """获取收入报表"""
    service = BillingService(db)
    report = await service.get_revenue_report(
        org_id=user.org_id,
        date_from=date_from,
        date_to=date_to,
    )
    return UnifiedResponse.success(data=report)
