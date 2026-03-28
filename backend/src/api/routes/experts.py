# -*- coding: utf-8 -*-
"""
律师精英路由
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.core.responses import UnifiedResponse
from src.models.user import User
from src.services.expert_service import ExpertService

router = APIRouter()


class ExpertCreate(BaseModel):
    name: str
    title: Optional[str] = None
    specialty: Optional[List[str]] = None
    yearsOfExperience: int = 0
    rating: float = 0.0
    casesHandled: int = 0
    description: Optional[str] = None
    achievements: Optional[List[str]] = None


class ExpertUpdate(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    specialty: Optional[List[str]] = None
    yearsOfExperience: Optional[int] = None
    rating: Optional[float] = None
    casesHandled: Optional[int] = None
    description: Optional[str] = None
    achievements: Optional[List[str]] = None


class ExpertResponse(BaseModel):
    id: str
    name: str
    title: Optional[str] = None
    specialty: List[str] = []
    yearsOfExperience: int = 0
    rating: float = 0.0
    casesHandled: int = 0
    description: Optional[str] = None
    achievements: List[str] = []


def expert_to_response(expert) -> ExpertResponse:
    return ExpertResponse(
        id=expert.id,
        name=expert.name,
        title=expert.title,
        specialty=expert.specialty or [],
        yearsOfExperience=expert.years_of_experience,
        rating=expert.rating,
        casesHandled=expert.cases_handled,
        description=expert.description,
        achievements=expert.achievements or [],
    )


@router.get("/")
async def list_experts(
    specialty: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    service = ExpertService(db)
    experts, total = await service.list_experts(
        org_id=user.org_id,
        specialty=specialty,
        page=page,
        page_size=page_size,
    )
    return UnifiedResponse.success(data={
        "items": [expert_to_response(e) for e in experts],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/")
async def create_expert(
    data: ExpertCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    service = ExpertService(db)
    expert = await service.create_expert(
        name=data.name,
        title=data.title,
        specialty=data.specialty or [],
        years_of_experience=data.yearsOfExperience,
        rating=data.rating,
        cases_handled=data.casesHandled,
        description=data.description,
        achievements=data.achievements or [],
        org_id=user.org_id,
    )
    return UnifiedResponse.success(data=expert_to_response(expert))


@router.get("/{expert_id}")
async def get_expert(
    expert_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    service = ExpertService(db)
    expert = await service.get_expert(expert_id)
    if not expert:
        return UnifiedResponse.error(code=404, message="律师不存在")
    return UnifiedResponse.success(data=expert_to_response(expert))


@router.put("/{expert_id}")
async def update_expert(
    expert_id: str,
    data: ExpertUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    service = ExpertService(db)
    update_data = {}
    if data.name is not None:
        update_data["name"] = data.name
    if data.title is not None:
        update_data["title"] = data.title
    if data.specialty is not None:
        update_data["specialty"] = data.specialty
    if data.yearsOfExperience is not None:
        update_data["years_of_experience"] = data.yearsOfExperience
    if data.rating is not None:
        update_data["rating"] = data.rating
    if data.casesHandled is not None:
        update_data["cases_handled"] = data.casesHandled
    if data.description is not None:
        update_data["description"] = data.description
    if data.achievements is not None:
        update_data["achievements"] = data.achievements

    expert = await service.update_expert(expert_id, org_id=user.org_id, **update_data)
    if not expert:
        return UnifiedResponse.error(code=404, message="律师不存在")
    return UnifiedResponse.success(data=expert_to_response(expert))


@router.delete("/{expert_id}")
async def delete_expert(
    expert_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    service = ExpertService(db)
    success = await service.delete_expert(expert_id, org_id=user.org_id)
    if not success:
        return UnifiedResponse.error(code=404, message="律师不存在")
    return UnifiedResponse.success(message="删除成功")
