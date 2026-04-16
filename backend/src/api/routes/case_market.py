# -*- coding: utf-8 -*-
"""
案源市场 API (V2 架构)

需求方端：发布需求、查看投标、选择律师
服务方端：浏览案源、提交投标、查看接单记录
"""

from typing import Optional, List
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.core.responses import UnifiedResponse
from src.models.user import User
from src.models.case_market import CaseRequest, LawyerBid, RequestStatus, BidStatus

router = APIRouter(prefix="/case-market", tags=["案源市场"])


# ===== 请求模型 =====

class PublishRequestBody(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    legal_area: str = Field(..., min_length=1, max_length=50)
    urgency: str = Field("normal", pattern=r"^(urgent|normal|flexible)$")
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    location: Optional[str] = None
    is_anonymous: bool = True
    tags: Optional[List[str]] = None


class SubmitBidBody(BaseModel):
    proposal: str = Field(..., min_length=10)
    quoted_price: Optional[float] = None
    estimated_days: Optional[int] = Field(None, ge=1)


class RatingBody(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


# ===== 需求方端 API =====

@router.post("/requests")
async def publish_request(
    body: PublishRequestBody,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """发布法律需求到案源市场"""
    req = CaseRequest(
        user_id=user.id,
        org_id=getattr(user, 'org_id', None),
        title=body.title,
        description=body.description,
        legal_area=body.legal_area,
        urgency=body.urgency,
        budget_min=body.budget_min,
        budget_max=body.budget_max,
        location=body.location,
        is_anonymous=body.is_anonymous,
        tags=body.tags,
        status=RequestStatus.PUBLISHED,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(req)
    await db.flush()
    await db.commit()
    return UnifiedResponse.success(data={"id": str(req.id), "message": "需求已发布"})


@router.get("/requests/mine")
async def list_my_requests(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """查看我发布的需求列表"""
    query = select(CaseRequest).where(CaseRequest.user_id == user.id)
    if status:
        query = query.where(CaseRequest.status == status)
    query = query.order_by(CaseRequest.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    items = result.scalars().all()

    count_q = select(func.count()).select_from(CaseRequest).where(CaseRequest.user_id == user.id)
    total = (await db.execute(count_q)).scalar() or 0

    return UnifiedResponse.success(data={
        "items": [_request_to_dict(r) for r in items],
        "total": total,
    })


@router.get("/requests/{request_id}/bids")
async def list_bids_for_request(
    request_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """查看某个需求收到的投标"""
    req = await db.get(CaseRequest, request_id)
    if not req:
        raise HTTPException(404, "需求不存在")
    if req.user_id != user.id:
        raise HTTPException(403, "无权查看")

    result = await db.execute(
        select(LawyerBid)
        .where(LawyerBid.case_request_id == request_id)
        .order_by(LawyerBid.created_at.desc())
    )
    bids = result.scalars().all()
    return UnifiedResponse.success(data=[_bid_to_dict(b) for b in bids])


@router.post("/requests/{request_id}/accept-bid/{bid_id}")
async def accept_bid(
    request_id: str,
    bid_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """接受律师投标"""
    req = await db.get(CaseRequest, request_id)
    if not req or req.user_id != user.id:
        raise HTTPException(403, "无权操作")

    bid = await db.get(LawyerBid, bid_id)
    if not bid or bid.case_request_id != request_id:
        raise HTTPException(404, "投标不存在")

    # 接受该投标
    bid.status = BidStatus.ACCEPTED
    req.status = RequestStatus.MATCHED
    req.matched_lawyer_id = bid.lawyer_id

    # 拒绝其他投标
    other_bids = await db.execute(
        select(LawyerBid).where(
            and_(
                LawyerBid.case_request_id == request_id,
                LawyerBid.id != bid_id,
                LawyerBid.status == BidStatus.PENDING,
            )
        )
    )
    for ob in other_bids.scalars().all():
        ob.status = BidStatus.REJECTED

    await db.commit()
    return UnifiedResponse.success(message="已接受投标，律师将与您联系")


# ===== 服务方端 API =====

@router.get("/market")
async def browse_market(
    legal_area: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    urgency: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """浏览案源市场（服务方端）"""
    query = select(CaseRequest).where(
        and_(
            CaseRequest.status == RequestStatus.PUBLISHED,
            CaseRequest.visible_to_market == True,
            or_(CaseRequest.expires_at == None, CaseRequest.expires_at > datetime.now(timezone.utc)),
        )
    )
    if legal_area:
        query = query.where(CaseRequest.legal_area == legal_area)
    if location:
        query = query.where(CaseRequest.location.ilike(f"%{location}%"))
    if urgency:
        query = query.where(CaseRequest.urgency == urgency)

    query = query.order_by(CaseRequest.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    # 更新浏览量
    for item in items:
        item.view_count = (item.view_count or 0) + 1
    await db.flush()

    return UnifiedResponse.success(data={
        "items": [_request_to_dict(r, anonymous=True) for r in items],
    })


@router.post("/market/{request_id}/bid")
async def submit_bid(
    request_id: str,
    body: SubmitBidBody,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """律师提交投标"""
    req = await db.get(CaseRequest, request_id)
    if not req or req.status != RequestStatus.PUBLISHED:
        raise HTTPException(404, "需求不存在或已关闭")

    # 检查是否已投标
    existing = await db.execute(
        select(LawyerBid).where(
            and_(
                LawyerBid.case_request_id == request_id,
                LawyerBid.lawyer_id == user.id,
                LawyerBid.status != BidStatus.WITHDRAWN,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "您已经对此需求投标")

    # V2: 利益冲突检查
    conflict_warning = None
    try:
        from src.services.conflict_check_service import ConflictCheckService
        conflict_svc = ConflictCheckService(db)
        # 从需求标题/描述中提取当事人名称（简化：用 tags 或标题）
        party_names = (req.tags or []) + [req.title]
        conflict_result = await conflict_svc.check_conflict(
            lawyer_id=user.id,
            party_names=party_names,
            org_id=getattr(user, 'org_id', None),
        )
        if conflict_result.has_conflict:
            conflict_warning = conflict_result.to_dict()
    except Exception as e:
        pass  # 冲突检查失败不阻断投标

    bid = LawyerBid(
        case_request_id=request_id,
        lawyer_id=user.id,
        proposal=body.proposal,
        quoted_price=body.quoted_price,
        estimated_days=body.estimated_days,
        status=BidStatus.PENDING,
    )
    db.add(bid)
    req.bid_count = (req.bid_count or 0) + 1
    await db.commit()

    response_data = {"id": str(bid.id), "message": "投标已提交"}
    if conflict_warning:
        response_data["conflict_warning"] = conflict_warning
        response_data["message"] = "投标已提交，但检测到潜在利益冲突，请注意审查"
    return UnifiedResponse.success(data=response_data)


@router.get("/bids/mine")
async def list_my_bids(
    status: Optional[str] = Query(None),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """查看我的投标记录（律师端）"""
    query = select(LawyerBid).where(LawyerBid.lawyer_id == user.id)
    if status:
        query = query.where(LawyerBid.status == status)
    query = query.order_by(LawyerBid.created_at.desc())

    result = await db.execute(query)
    bids = result.scalars().all()
    return UnifiedResponse.success(data=[_bid_to_dict(b) for b in bids])


@router.post("/bids/{bid_id}/rate")
async def rate_service(
    bid_id: str,
    body: RatingBody,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """双向评价"""
    bid = await db.get(LawyerBid, bid_id)
    if not bid:
        raise HTTPException(404, "投标不存在")

    req = await db.get(CaseRequest, bid.case_request_id)
    if req and req.user_id == user.id:
        bid.client_rating = body.rating
        bid.client_comment = body.comment
    elif bid.lawyer_id == user.id:
        bid.lawyer_rating = body.rating
        bid.lawyer_comment = body.comment
    else:
        raise HTTPException(403, "无权评价")

    await db.commit()
    return UnifiedResponse.success(message="评价已提交")


# ===== 辅助函数 =====

def _request_to_dict(r: CaseRequest, anonymous: bool = False) -> dict:
    d = {
        "id": str(r.id),
        "title": r.title,
        "description": r.description[:200] + ("..." if len(r.description) > 200 else ""),
        "legal_area": r.legal_area,
        "urgency": r.urgency,
        "budget_min": r.budget_min,
        "budget_max": r.budget_max,
        "location": r.location,
        "status": r.status.value if hasattr(r.status, 'value') else r.status,
        "tags": r.tags,
        "view_count": r.view_count,
        "bid_count": r.bid_count,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "expires_at": r.expires_at.isoformat() if r.expires_at else None,
    }
    if not anonymous:
        d["user_id"] = str(r.user_id)
    return d


def _bid_to_dict(b: LawyerBid) -> dict:
    return {
        "id": str(b.id),
        "case_request_id": str(b.case_request_id),
        "lawyer_id": str(b.lawyer_id),
        "proposal": b.proposal,
        "quoted_price": b.quoted_price,
        "estimated_days": b.estimated_days,
        "status": b.status.value if hasattr(b.status, 'value') else b.status,
        "client_rating": b.client_rating,
        "lawyer_rating": b.lawyer_rating,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }
