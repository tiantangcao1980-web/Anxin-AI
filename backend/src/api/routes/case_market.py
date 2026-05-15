"""
案源市场 API (V2 架构)

需求方端：发布需求、查看投标、选择律师
服务方端：浏览案源、提交投标、查看接单记录
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.core.responses import UnifiedResponse
from src.models.case_market import BidStatus, CaseRequest, LawyerBid, RequestStatus
from src.models.user import User

router = APIRouter(prefix="/case-market", tags=["案源市场"])


def _reject_local_market_mode(request: Request) -> None:
    mode = (request.headers.get("X-Privacy-Mode") or "").lower()
    if mode == "local":
        raise HTTPException(
            status_code=403,
            detail="本地模式不支持案源市场，请切换到 hybrid/cloud 模式后重试",
        )


def _extract_conflict_party_names(req: CaseRequest) -> list[str]:
    names: list[str] = []
    for tag in req.tags or []:
        if isinstance(tag, str):
            names.append(tag)
    extra = req.extra_data or {}
    if isinstance(extra, dict):
        for item in extra.get("parties", []):
            if isinstance(item, dict) and item.get("name"):
                names.append(str(item["name"]))
            elif isinstance(item, str):
                names.append(item)
    names.append(req.title)
    return [name.strip() for name in names if isinstance(name, str) and name.strip()]


# ===== 请求模型 =====


class PublishRequestBody(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    legal_area: str = Field(..., min_length=1, max_length=50)
    urgency: str = Field("normal", pattern=r"^(urgent|normal|flexible)$")
    budget_min: float | None = None
    budget_max: float | None = None
    location: str | None = None
    is_anonymous: bool = True
    tags: list[str] | None = None


class SubmitBidBody(BaseModel):
    proposal: str = Field(..., min_length=10)
    quoted_price: float | None = None
    estimated_days: int | None = Field(None, ge=1)


class RatingBody(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None


# ===== 需求方端 API =====


@router.post("/requests")
async def publish_request(
    body: PublishRequestBody,
    request: Request,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """发布法律需求到案源市场"""
    _reject_local_market_mode(request)
    req = CaseRequest(
        user_id=user.id,
        org_id=getattr(user, "org_id", None),
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
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db.add(req)
    await db.flush()
    await db.commit()
    return UnifiedResponse.success(data={"id": str(req.id), "message": "需求已发布"})


@router.get("/requests/mine")
async def list_my_requests(
    status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """查看我发布的需求列表"""
    query = select(CaseRequest).where(CaseRequest.user_id == user.id)
    if status:
        query = query.where(CaseRequest.status == status)
    query = query.order_by(CaseRequest.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    items = result.scalars().all()

    count_q = select(func.count()).select_from(CaseRequest).where(CaseRequest.user_id == user.id)
    total = (await db.execute(count_q)).scalar() or 0

    return UnifiedResponse.success(
        data={
            "items": [_request_to_dict(r) for r in items],
            "total": total,
        }
    )


@router.get("/requests/{request_id}/bids")
async def list_bids_for_request(
    request_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
    request: Request,
    legal_area: str | None = Query(None),
    location: str | None = Query(None),
    urgency: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """浏览案源市场（服务方端）"""
    _reject_local_market_mode(request)
    query = select(CaseRequest).where(
        and_(
            CaseRequest.status == RequestStatus.PUBLISHED,
            CaseRequest.visible_to_market == True,
            or_(CaseRequest.expires_at.is_(None), CaseRequest.expires_at > datetime.now(UTC)),
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

    return UnifiedResponse.success(
        data={
            "items": [_request_to_dict(r, anonymous=True) for r in items],
        }
    )


@router.post("/market/{request_id}/bid")
async def submit_bid(
    request_id: str,
    body: SubmitBidBody,
    request: Request,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """律师提交投标"""
    _reject_local_market_mode(request)
    req = await db.get(CaseRequest, request_id)
    if not req or req.status != RequestStatus.PUBLISHED:
        raise HTTPException(404, "需求不存在或已关闭")
    if req.user_id == user.id:
        raise HTTPException(403, "不能对自己发布的需求投标")

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

    from src.services.conflict_check_service import ConflictCheckService

    conflict_svc = ConflictCheckService(db)
    conflict_result = await conflict_svc.check_conflict(
        lawyer_id=user.id,
        party_names=_extract_conflict_party_names(req),
        org_id=getattr(user, "org_id", None),
    )
    if conflict_result.has_conflict:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "检测到潜在利益冲突，已阻止投标，请走人工复核",
                "conflict": conflict_result.to_dict(),
            },
        )

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

    return UnifiedResponse.success(data={"id": str(bid.id), "message": "投标已提交"})


@router.get("/bids/mine")
async def list_my_bids(
    status: str | None = Query(None),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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


def _request_to_dict(r: CaseRequest, anonymous: bool = False) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": str(r.id),
        "title": r.title,
        "description": r.description[:200] + ("..." if len(r.description) > 200 else ""),
        "legal_area": r.legal_area,
        "urgency": r.urgency,
        "budget_min": r.budget_min,
        "budget_max": r.budget_max,
        "location": r.location,
        "status": r.status.value if hasattr(r.status, "value") else r.status,
        "tags": r.tags,
        "view_count": r.view_count,
        "bid_count": r.bid_count,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "expires_at": r.expires_at.isoformat() if r.expires_at else None,
    }
    if not anonymous:
        d["user_id"] = str(r.user_id)
    return d


def _bid_to_dict(b: LawyerBid) -> dict[str, Any]:
    return {
        "id": str(b.id),
        "case_request_id": str(b.case_request_id),
        "lawyer_id": str(b.lawyer_id),
        "proposal": b.proposal,
        "quoted_price": b.quoted_price,
        "estimated_days": b.estimated_days,
        "status": b.status.value if hasattr(b.status, "value") else b.status,
        "client_rating": b.client_rating,
        "lawyer_rating": b.lawyer_rating,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }
