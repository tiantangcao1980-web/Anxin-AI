"""
律师入驻 API 路由

入驻流程：创建档案 -> 提交认证 -> 管理员审核 -> 配置接单 -> 上线
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import (
    Permission,
    get_current_user_required,
    require_permission,
)
from src.core.responses import UnifiedResponse
from src.models.lawyer_matching import LawyerProfile
from src.models.user import User
from src.services.lawyer_onboarding_service import LawyerOnboardingService

router = APIRouter(prefix="/lawyer", tags=["律师入驻"])


# ===== Pydantic 请求模型 =====


class ProfileRequest(BaseModel):
    real_name: str = Field(..., min_length=2, max_length=100, description="真实姓名")
    license_number: str = Field(..., min_length=5, max_length=50, description="执业证号")
    law_firm: str | None = Field(None, max_length=200, description="所在律所")
    years_of_practice: int = Field(0, ge=0, le=60, description="执业年限")
    city: str | None = Field(None, max_length=50, description="城市")
    province: str | None = Field(None, max_length=50, description="省份")
    specializations: list[str] = Field(default_factory=list, description="专业领域")
    bio: str | None = Field(None, max_length=2000, description="个人简介")
    hourly_rate_min: int | None = Field(None, ge=0, description="最低时薪（元）")
    hourly_rate_max: int | None = Field(None, ge=0, description="最高时薪（元）")


class CertificationRequest(BaseModel):
    license_image_url: str = Field(..., max_length=500, description="执业证照片URL")
    id_card_image_url: str | None = Field(None, max_length=500, description="身份证照片URL")
    license_issue_date: date = Field(..., description="执业证签发日期")
    license_expiry_date: date = Field(..., description="执业证到期日期")
    bar_association: str | None = Field(None, max_length=100, description="所属律师协会")


class ServiceConfigRequest(BaseModel):
    service_types: list[str] = Field(
        default_factory=lambda: ["instant_consultation"],
        description="服务类型",
    )
    auto_accept: bool = Field(False, description="是否自动接单")
    max_concurrent_cases: int = Field(10, ge=1, le=100, description="最大并发案件数")
    response_time_hours: int = Field(24, ge=1, le=168, description="承诺响应时间（小时）")
    min_case_amount: float | None = Field(None, ge=0, description="最低接案金额")


class VerifyCertificationRequest(BaseModel):
    approved: bool = Field(..., description="是否通过")
    rejection_reason: str | None = Field(None, max_length=500, description="驳回原因")


# ===== 律师端接口 =====


@router.post("/onboarding/profile")
async def create_or_update_profile(
    req: ProfileRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """创建或更新律师档案"""
    service = LawyerOnboardingService(db)
    try:
        data = await service.create_or_update_profile(
            user_id=user.id,
            data=req.model_dump(),
        )
        return UnifiedResponse.success(data, message="档案已保存")
    except Exception as e:
        logger.error(f"创建律师档案失败: {e}")
        return UnifiedResponse.error(400, str(e))


@router.post("/onboarding/certification")
async def submit_certification(
    req: CertificationRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """提交执业证认证"""
    service = LawyerOnboardingService(db)

    # 查找用户的 LawyerProfile
    result = await db.execute(select(LawyerProfile).where(LawyerProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        return UnifiedResponse.error(400, "请先创建律师档案")

    try:
        data = await service.submit_certification(
            profile_id=profile.id,
            license_image_url=req.license_image_url,
            issue_date=req.license_issue_date,
            expiry_date=req.license_expiry_date,
            bar_association=req.bar_association,
            id_card_image_url=req.id_card_image_url,
        )
        return UnifiedResponse.success(data, message="认证已提交，等待审核")
    except ValueError as e:
        return UnifiedResponse.error(400, str(e))


@router.get("/onboarding/status")
async def get_onboarding_status(
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """查询入驻进度"""
    service = LawyerOnboardingService(db)
    data = await service.get_onboarding_status(user_id=user.id)
    return UnifiedResponse.success(data)


@router.put("/onboarding/service-config")
async def update_service_config(
    req: ServiceConfigRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """更新接单设置"""
    service = LawyerOnboardingService(db)

    # 查找用户的 LawyerProfile
    result = await db.execute(select(LawyerProfile).where(LawyerProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        return UnifiedResponse.error(400, "请先创建律师档案")

    try:
        data = await service.update_service_config(
            profile_id=profile.id,
            data=req.model_dump(),
        )
        return UnifiedResponse.success(data, message="接单设置已保存")
    except Exception as e:
        logger.error(f"更新接单设置失败: {e}")
        return UnifiedResponse.error(400, str(e))


@router.get("/dashboard")
async def get_lawyer_dashboard(
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """律师仪表板"""
    service = LawyerOnboardingService(db)
    try:
        data = await service.get_lawyer_dashboard(user_id=user.id)
        return UnifiedResponse.success(data)
    except ValueError as e:
        return UnifiedResponse.error(400, str(e))


# ===== 管理端接口 =====


@router.post("/admin/lawyer/{cert_id}/verify")
async def verify_certification(
    cert_id: str,
    req: VerifyCertificationRequest,
    user: User = Depends(require_permission(Permission.VERIFY_LAWYER)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """审核律师认证"""
    service = LawyerOnboardingService(db)
    try:
        data = await service.verify_certification(
            cert_id=cert_id,
            approver_id=user.id,
            approved=req.approved,
            rejection_reason=req.rejection_reason,
        )
        msg = "认证已通过" if req.approved else "认证已驳回"
        return UnifiedResponse.success(data, message=msg)
    except ValueError as e:
        return UnifiedResponse.error(400, str(e))


@router.get("/admin/lawyer/pending")
async def get_pending_certifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_permission(Permission.VERIFY_LAWYER)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """待审核认证列表"""
    service = LawyerOnboardingService(db)
    data = await service.get_pending_certifications(page=page, page_size=page_size)
    return UnifiedResponse.success(data)
