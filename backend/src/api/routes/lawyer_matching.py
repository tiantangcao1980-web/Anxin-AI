# -*- coding: utf-8 -*-
"""
找律师 API 路由

核心流程（滴滴模式）：
1. POST /consultations — 用户发起咨询请求
2. POST /consultations/{id}/match — AI 匹配律师
3. POST /consultations/{id}/accept — 律师接单
4. POST /consultations/{id}/delegate — 一键委托
5. GET  /lawyers — 律师列表（公开信息）
6. GET  /lawyers/hall — 入驻律师接单大厅
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel, Field
from datetime import datetime
from loguru import logger

from src.core.database import get_db
from src.core.deps import get_current_user_required, require_permission, Permission
from src.models.user import User
from src.models.lawyer_matching import (
    LawyerProfile, Consultation, Delegation,
    ConsultationStatus, UrgencyLevel, PrivacyLevel, DelegationStatus
)

router = APIRouter(prefix="/lawyer", tags=["找律师"])


# ===== 请求/响应模型 =====

class CreateConsultationRequest(BaseModel):
    """发起咨询请求"""
    description: str = Field(..., min_length=10, max_length=5000, description="问题描述")
    legal_domain: Optional[str] = Field(None, description="法律领域（可选，AI 会自动识别）")
    urgency: str = Field("medium", description="紧急程度: low/medium/high/urgent")


class LawyerProfileResponse(BaseModel):
    """律师公开信息（不含敏感数据）"""
    id: str
    real_name: str
    license_number: str
    law_firm: Optional[str]
    years_of_practice: int
    city: Optional[str]
    specializations: list
    bio: Optional[str]
    avatar_url: Optional[str]
    rating: float
    total_cases: int
    success_cases: int
    hourly_rate_min: Optional[int]
    hourly_rate_max: Optional[int]
    is_online: bool
    is_verified: bool


class CreateDelegationRequest(BaseModel):
    """一键委托"""
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    service_type: str = Field("instant", description="即时咨询/预约咨询/案件委托")


# ===== 用户端接口 =====

@router.post("/consultations")
async def create_consultation(
    req: CreateConsultationRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """发起咨询请求 — AI 预分析并生成匿名摘要"""
    from src.services.lawyer_matching_service import lawyer_matching_service

    # AI 案情分析：领域识别 + 脱敏 + 要素提取
    analysis = await lawyer_matching_service.analyze_case(
        description=req.description,
        user_domain=req.legal_domain,
    )

    consultation = Consultation(
        user_id=user.id,
        original_description=req.description,
        anonymous_summary=analysis["anonymous_summary"],
        legal_domain=analysis["legal_domain"],
        legal_tags=analysis.get("recommended_specializations", []),
        urgency=req.urgency,
        status=ConsultationStatus.PENDING.value,
        privacy_level=PrivacyLevel.ANONYMOUS.value,
    )
    db.add(consultation)
    await db.commit()
    await db.refresh(consultation)

    logger.info(f"用户 {user.id} 发起咨询请求 {consultation.id}，领域={analysis['domain_label']}，风险={analysis['risk_level']}")

    return {
        "consultation_id": consultation.id,
        "status": consultation.status,
        "anonymous_summary": consultation.anonymous_summary,
        "legal_domain": consultation.legal_domain,
        "domain_label": analysis["domain_label"],
        "domain_confidence": analysis["domain_confidence"],
        "risk_level": analysis["risk_level"],
        "legal_elements": analysis.get("legal_elements", {}),
        "message": "AI 已完成案情分析，正在为您匹配律师",
    }


@router.get("/consultations")
async def list_consultations(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """查询我的咨询记录"""
    query = select(Consultation).where(Consultation.user_id == user.id)
    if status:
        query = query.where(Consultation.status == status)
    query = query.order_by(Consultation.created_at.desc())

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    consultations = result.scalars().all()

    return {
        "items": [
            {
                "id": c.id,
                "anonymous_summary": c.anonymous_summary,
                "legal_domain": c.legal_domain,
                "urgency": c.urgency,
                "status": c.status,
                "privacy_level": c.privacy_level,
                "matched_at": c.matched_at.isoformat() if c.matched_at else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in consultations
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/consultations/{consultation_id}/delegate")
async def create_delegation(
    consultation_id: str,
    req: CreateDelegationRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """一键委托 — 创建委托记录"""
    consultation = await db.get(Consultation, consultation_id)
    if not consultation or consultation.user_id != user.id:
        raise HTTPException(status_code=404, detail="咨询记录不存在")
    if not consultation.matched_lawyer_id:
        raise HTTPException(status_code=400, detail="尚未匹配律师，无法委托")

    delegation = Delegation(
        consultation_id=consultation_id,
        client_id=user.id,
        lawyer_id=consultation.matched_lawyer_id,
        title=req.title,
        description=req.description,
        service_type=req.service_type,
        status=DelegationStatus.DRAFT.value,
    )
    db.add(delegation)

    # 更新咨询状态
    consultation.status = ConsultationStatus.DELEGATION.value
    consultation.privacy_level = PrivacyLevel.DELEGATED.value

    await db.commit()
    await db.refresh(delegation)

    return {
        "delegation_id": delegation.id,
        "status": delegation.status,
        "message": "委托已创建，请确认并签署委托协议",
    }


# ===== 律师公开接口 =====

@router.get("/lawyers")
async def list_lawyers(
    domain: Optional[str] = None,
    city: Optional[str] = None,
    min_rating: float = Query(0, ge=0, le=5),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """律师列表 — 支持智能匹配排序"""
    from src.services.lawyer_matching_service import lawyer_matching_service

    # 如果指定了领域，使用智能匹配
    if domain:
        matched = await lawyer_matching_service.match_lawyers(
            db=db,
            domain=domain,
            city=city,
            limit=page_size,
        )
        return {
            "items": matched,
            "total": len(matched),
        }

    # 通用列表查询
    query = select(LawyerProfile).where(
        LawyerProfile.is_verified == True
    )
    if city:
        query = query.where(LawyerProfile.city == city)
    if min_rating > 0:
        query = query.where(LawyerProfile.rating >= min_rating)

    query = query.order_by(LawyerProfile.rating.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    lawyers = result.scalars().all()

    return {
        "items": [
            {
                "id": lp.id,
                "real_name": lp.real_name,
                "license_number": lp.license_number,
                "law_firm": lp.law_firm,
                "years_of_practice": lp.years_of_practice,
                "city": lp.city,
                "specializations": lp.specializations or [],
                "bio": lp.bio,
                "avatar_url": lp.avatar_url,
                "rating": lp.rating,
                "total_cases": lp.total_cases,
                "success_cases": lp.success_cases,
                "hourly_rate_min": lp.hourly_rate_min,
                "hourly_rate_max": lp.hourly_rate_max,
                "is_online": lp.is_online,
                "is_verified": lp.is_verified,
            }
            for lp in lawyers
        ],
        "total": total,
    }


# ===== 入驻律师接口 =====

@router.get("/hall")
async def lawyer_hall(
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """接单大厅 — 入驻律师查看待接单的匿名咨询"""
    # 验证是入驻律师
    profile = await db.execute(
        select(LawyerProfile).where(LawyerProfile.user_id == user.id)
    )
    lawyer_profile = profile.scalar_one_or_none()
    if not lawyer_profile:
        raise HTTPException(status_code=403, detail="仅入驻律师可访问接单大厅")

    # 查询待匹配的咨询（仅展示匿名摘要）
    result = await db.execute(
        select(Consultation).where(
            Consultation.status == ConsultationStatus.PENDING.value
        ).order_by(Consultation.created_at.desc()).limit(50)
    )
    consultations = result.scalars().all()

    return {
        "items": [
            {
                "id": c.id,
                "anonymous_summary": c.anonymous_summary,
                "legal_domain": c.legal_domain,
                "urgency": c.urgency,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in consultations
        ],
    }


@router.post("/hall/{consultation_id}/accept")
async def accept_consultation(
    consultation_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """律师接单"""
    # 验证是入驻律师
    profile = await db.execute(
        select(LawyerProfile).where(LawyerProfile.user_id == user.id)
    )
    if not profile.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="仅入驻律师可接单")

    consultation = await db.get(Consultation, consultation_id)
    if not consultation:
        raise HTTPException(status_code=404, detail="咨询记录不存在")
    if consultation.status != ConsultationStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="该咨询已被其他律师接单")

    consultation.matched_lawyer_id = user.id
    consultation.matched_at = datetime.utcnow()
    consultation.status = ConsultationStatus.IN_PROGRESS.value

    await db.commit()

    return {"message": "接单成功，可以开始匿名咨询"}


# ===== 评价相关接口 =====


class CreateReviewRequest(BaseModel):
    """提交评价"""
    rating: int = Field(..., ge=1, le=5, description="评分 1-5 星")
    content: Optional[str] = Field(None, max_length=2000, description="评价内容")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    is_anonymous: bool = Field(False, description="是否匿名评价")
    consultation_id: Optional[str] = Field(None, description="关联的咨询 ID")
    delegation_id: Optional[str] = Field(None, description="关联的委托 ID")


class ReplyReviewRequest(BaseModel):
    """律师回复评价"""
    content: str = Field(..., min_length=1, max_length=2000, description="回复内容")


@router.get("/lawyers/{profile_id}/reviews")
async def list_lawyer_reviews(
    profile_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """获取律师评价列表"""
    from src.services.review_service import ReviewService
    service = ReviewService(db)
    data = await service.list_reviews(
        lawyer_profile_id=profile_id,
        page=page,
        page_size=page_size,
    )
    return data


@router.post("/lawyers/{profile_id}/reviews")
async def create_lawyer_review(
    profile_id: str,
    req: CreateReviewRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """提交律师评价"""
    from src.services.review_service import ReviewService
    service = ReviewService(db)
    try:
        review = await service.create_review(
            reviewer_id=user.id,
            lawyer_profile_id=profile_id,
            rating=req.rating,
            content=req.content,
            tags=req.tags,
            is_anonymous=req.is_anonymous,
            consultation_id=req.consultation_id,
            delegation_id=req.delegation_id,
        )
        return {
            "id": review.id,
            "rating": review.rating,
            "message": "评价提交成功",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/lawyers/reviews/{review_id}/reply")
async def reply_to_review(
    review_id: str,
    req: ReplyReviewRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """律师回复评价"""
    from src.services.review_service import ReviewService
    service = ReviewService(db)
    try:
        review = await service.reply_to_review(
            review_id=review_id,
            lawyer_user_id=user.id,
            content=req.content,
        )
        return {
            "id": review.id,
            "reply_content": review.reply_content,
            "message": "回复成功",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/lawyers/{profile_id}/review-stats")
async def get_lawyer_review_stats(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取律师评价统计"""
    from src.services.review_service import ReviewService
    service = ReviewService(db)
    data = await service.get_review_stats(lawyer_profile_id=profile_id)
    return data
