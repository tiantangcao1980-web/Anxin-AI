"""
律师精英路由
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.core.responses import UnifiedResponse
from src.core.schemas import CamelModel
from src.models.expert import Expert
from src.models.user import User
from src.services.expert_service import ExpertService

router = APIRouter()


class ExpertCreate(CamelModel):
    name: str
    title: str | None = None
    specialty: list[str] | None = None
    years_of_experience: int = 0
    rating: float = 0.0
    cases_handled: int = 0
    description: str | None = None
    achievements: list[str] | None = None


class ExpertUpdate(CamelModel):
    name: str | None = None
    title: str | None = None
    specialty: list[str] | None = None
    years_of_experience: int | None = None
    rating: float | None = None
    cases_handled: int | None = None
    description: str | None = None
    achievements: list[str] | None = None


class ExpertResponse(CamelModel):
    id: str
    name: str
    title: str | None = None
    specialty: list[str] = []
    years_of_experience: int = 0
    rating: float = 0.0
    cases_handled: int = 0
    description: str | None = None
    achievements: list[str] = []


def expert_to_response(expert: Expert) -> ExpertResponse:
    return ExpertResponse(
        id=expert.id,
        name=expert.name,
        title=expert.title,
        specialty=expert.specialty or [],
        years_of_experience=expert.years_of_experience,
        rating=expert.rating,
        cases_handled=expert.cases_handled,
        description=expert.description,
        achievements=expert.achievements or [],
    )


@router.get("/")
async def list_experts(
    specialty: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
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
) -> dict[str, Any]:
    service = ExpertService(db)
    expert = await service.create_expert(
        name=data.name,
        title=data.title,
        specialty=data.specialty or [],
        years_of_experience=data.years_of_experience,
        rating=data.rating,
        cases_handled=data.cases_handled,
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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
    service = ExpertService(db)
    update_data: dict[str, Any] = {}
    if data.name is not None:
        update_data["name"] = data.name
    if data.title is not None:
        update_data["title"] = data.title
    if data.specialty is not None:
        update_data["specialty"] = data.specialty
    if data.years_of_experience is not None:
        update_data["years_of_experience"] = data.years_of_experience
    if data.rating is not None:
        update_data["rating"] = data.rating
    if data.cases_handled is not None:
        update_data["cases_handled"] = data.cases_handled
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
) -> dict[str, Any]:
    service = ExpertService(db)
    success = await service.delete_expert(expert_id, org_id=user.org_id)
    if not success:
        return UnifiedResponse.error(code=404, message="律师不存在")
    return UnifiedResponse.success(message="删除成功")
