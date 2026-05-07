"""
律师入驻服务

覆盖入驻全生命周期：创建档案 -> 提交认证 -> 审核 -> 配置接单 -> 上线
"""

from datetime import UTC, date, datetime
from typing import Any

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.lawyer_certification import LawyerCertification, LawyerServiceConfig
from src.models.lawyer_matching import Consultation, Delegation, LawyerProfile
from src.models.user import User


class LawyerOnboardingService:
    """律师入驻服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 档案管理
    # ------------------------------------------------------------------

    async def create_or_update_profile(
        self, user_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """创建或更新律师档案，自动将 user.role 设为 platform_lawyer"""

        result = await self.db.execute(
            select(LawyerProfile).where(LawyerProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if profile is None:
            profile = LawyerProfile(
                user_id=user_id,
                real_name=data["real_name"],
                license_number=data["license_number"],
            )
            self.db.add(profile)

        # 可更新字段
        updatable = [
            "real_name", "license_number", "law_firm", "years_of_practice",
            "city", "province", "specializations", "bio",
            "hourly_rate_min", "hourly_rate_max",
        ]
        for field in updatable:
            if field in data:
                setattr(profile, field, data[field])

        # 自动升级角色为 platform_lawyer
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if user and user.role not in ("platform_lawyer", "admin", "super_admin"):
            user.role = "platform_lawyer"

        await self.db.commit()
        await self.db.refresh(profile)

        return profile.to_dict()

    # ------------------------------------------------------------------
    # 认证管理
    # ------------------------------------------------------------------

    async def submit_certification(
        self,
        profile_id: str,
        license_image_url: str,
        issue_date: date,
        expiry_date: date,
        bar_association: str | None = None,
        id_card_image_url: str | None = None,
    ) -> dict[str, Any]:
        """提交或重新提交执业证认证"""

        # 查找已有认证记录
        result = await self.db.execute(
            select(LawyerCertification).where(
                LawyerCertification.lawyer_profile_id == profile_id
            )
        )
        cert = result.scalar_one_or_none()

        if cert is not None:
            # 仅 pending / rejected 可重新提交
            if cert.status not in ("pending", "rejected"):
                raise ValueError(f"当前认证状态为 {cert.status}，无法重新提交")
            cert.license_image_url = license_image_url
            cert.id_card_image_url = id_card_image_url
            cert.license_issue_date = issue_date
            cert.license_expiry_date = expiry_date
            cert.bar_association = bar_association
            cert.status = "pending"
            cert.rejection_reason = None
            cert.verified_by = None
            cert.verified_at = None
        else:
            cert = LawyerCertification(
                lawyer_profile_id=profile_id,
                license_image_url=license_image_url,
                id_card_image_url=id_card_image_url,
                license_issue_date=issue_date,
                license_expiry_date=expiry_date,
                bar_association=bar_association,
                status="pending",
            )
            self.db.add(cert)

        await self.db.commit()
        await self.db.refresh(cert)

        logger.info(f"律师 profile={profile_id} 提交认证 cert={cert.id}")
        return cert.to_dict()

    # ------------------------------------------------------------------
    # 入驻进度
    # ------------------------------------------------------------------

    async def get_onboarding_status(self, user_id: str) -> dict[str, Any]:
        """
        返回入驻进度:
        step 1: profile  — 是否已创建档案
        step 2: certification — 认证状态
        step 3: service_config — 是否已配置接单设置
        step 4: active — 是否已上线
        """

        # 查找 profile
        result = await self.db.execute(
            select(LawyerProfile).where(LawyerProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        steps: list[dict[str, Any]] = [
            {"name": "profile", "status": "pending", "detail": None},
            {"name": "certification", "status": "pending", "detail": None},
            {"name": "service_config", "status": "pending", "detail": None},
            {"name": "active", "status": "pending", "detail": None},
        ]

        current_step = 1

        if profile:
            steps[0]["status"] = "completed"
            steps[0]["detail"] = {"profile_id": profile.id, "real_name": profile.real_name}
            current_step = 2

            # 查认证
            cert_result = await self.db.execute(
                select(LawyerCertification).where(
                    LawyerCertification.lawyer_profile_id == profile.id
                )
            )
            cert = cert_result.scalar_one_or_none()
            if cert:
                steps[1]["status"] = cert.status  # pending/approved/rejected
                steps[1]["detail"] = {
                    "cert_id": cert.id,
                    "status": cert.status,
                    "rejection_reason": cert.rejection_reason,
                }
                if cert.status == "approved":
                    current_step = 3

            # 查接单设置
            config_result = await self.db.execute(
                select(LawyerServiceConfig).where(
                    LawyerServiceConfig.lawyer_profile_id == profile.id
                )
            )
            config = config_result.scalar_one_or_none()
            if config:
                steps[2]["status"] = "completed"
                steps[2]["detail"] = {"config_id": config.id}
                if cert and cert.status == "approved":
                    current_step = 4

            # 上线状态
            if profile.is_verified and profile.is_accepting:
                steps[3]["status"] = "completed"
                steps[3]["detail"] = {"is_online": profile.is_online}

        return {
            "current_step": current_step,
            "steps": steps,
        }

    # ------------------------------------------------------------------
    # 审核
    # ------------------------------------------------------------------

    async def verify_certification(
        self,
        cert_id: str,
        approver_id: str,
        approved: bool,
        rejection_reason: str | None = None,
    ) -> dict[str, Any]:
        """管理员审核认证"""

        cert = await self.db.get(LawyerCertification, cert_id)
        if not cert:
            raise ValueError("认证记录不存在")
        if cert.status != "pending":
            raise ValueError(f"认证状态为 {cert.status}，无法审核")

        now = datetime.now(UTC)

        if approved:
            cert.status = "approved"
            cert.verified_by = approver_id
            cert.verified_at = now

            # 更新 LawyerProfile
            result = await self.db.execute(
                select(LawyerProfile).where(
                    LawyerProfile.id == cert.lawyer_profile_id
                )
            )
            profile = result.scalar_one_or_none()
            if profile:
                profile.is_verified = True
                profile.verified_at = now
        else:
            cert.status = "rejected"
            cert.rejection_reason = rejection_reason
            cert.verified_by = approver_id
            cert.verified_at = now

        await self.db.commit()
        await self.db.refresh(cert)

        logger.info(
            f"认证审核: cert={cert_id}, approved={approved}, "
            f"approver={approver_id}"
        )
        return cert.to_dict()

    async def get_pending_certifications(
        self, page: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        """管理员查询待审核列表"""

        base_query = (
            select(LawyerCertification)
            .join(LawyerProfile, LawyerCertification.lawyer_profile_id == LawyerProfile.id)
            .where(LawyerCertification.status == "pending")
            .order_by(LawyerCertification.created_at.asc())
        )

        # 总数
        count_q = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        # 分页
        rows = (
            await self.db.execute(
                base_query.offset((page - 1) * page_size).limit(page_size)
            )
        ).scalars().all()

        items: list[dict[str, Any]] = []
        for cert in rows:
            # 加载关联的 profile
            profile_result = await self.db.execute(
                select(LawyerProfile).where(LawyerProfile.id == cert.lawyer_profile_id)
            )
            profile = profile_result.scalar_one_or_none()

            user_result = await self.db.execute(
                select(User).where(User.id == profile.user_id)
            ) if profile else None
            user = user_result.scalar_one_or_none() if user_result else None

            items.append({
                **cert.to_dict(),
                "lawyer_name": profile.real_name if profile else None,
                "license_number": profile.license_number if profile else None,
                "law_firm": profile.law_firm if profile else None,
                "specializations": profile.specializations if profile else [],
                "years_of_practice": profile.years_of_practice if profile else None,
                "province": profile.province if profile else None,
                "city": profile.city if profile else None,
                "user_email": user.email if user else None,
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ------------------------------------------------------------------
    # 接单设置
    # ------------------------------------------------------------------

    async def update_service_config(
        self, profile_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """创建或更新接单设置"""

        result = await self.db.execute(
            select(LawyerServiceConfig).where(
                LawyerServiceConfig.lawyer_profile_id == profile_id
            )
        )
        config = result.scalar_one_or_none()

        if config is None:
            config = LawyerServiceConfig(lawyer_profile_id=profile_id)
            self.db.add(config)

        updatable = [
            "service_types", "auto_accept", "max_concurrent_cases",
            "response_time_hours", "working_hours", "min_case_amount",
        ]
        for field in updatable:
            if field in data:
                setattr(config, field, data[field])

        await self.db.commit()
        await self.db.refresh(config)

        return config.to_dict()

    # ------------------------------------------------------------------
    # 律师仪表板
    # ------------------------------------------------------------------

    async def get_lawyer_dashboard(self, user_id: str) -> dict[str, Any]:
        """
        律师工作台数据:
        1. 基本统计: 本月收入、接单数、评分
        2. 待处理咨询数量
        3. 近6个月收入趋势
        4. 近6个月评分趋势
        """

        # 查找 profile
        result = await self.db.execute(
            select(LawyerProfile).where(LawyerProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise ValueError("律师档案不存在")

        now = datetime.now(UTC)
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # 1. 本月接单数（已匹配给该律师的咨询）
        month_cases_q = select(func.count()).select_from(
            select(Consultation).where(
                and_(
                    Consultation.matched_lawyer_id == user_id,
                    Consultation.matched_at >= current_month_start,
                )
            ).subquery()
        )
        month_cases = (await self.db.execute(month_cases_q)).scalar() or 0

        # 2. 本月收入（已支付委托的总金额）
        month_revenue_q = select(func.coalesce(func.sum(Delegation.paid_amount), 0)).where(
            and_(
                Delegation.lawyer_id == user_id,
                Delegation.paid_at >= current_month_start,
                Delegation.status.in_(["paid", "in_progress", "completed"]),
            )
        )
        month_revenue = float((await self.db.execute(month_revenue_q)).scalar() or 0)

        # 3. 待处理咨询数量
        pending_q = select(func.count()).select_from(
            select(Consultation).where(
                and_(
                    Consultation.matched_lawyer_id == user_id,
                    Consultation.status == "in_progress",
                )
            ).subquery()
        )
        pending_count = (await self.db.execute(pending_q)).scalar() or 0

        # 4. 近6个月收入趋势（简化实现）
        revenue_trend: list[dict[str, Any]] = []
        for i in range(5, -1, -1):
            month = now.month - i
            year = now.year
            if month <= 0:
                month += 12
                year -= 1
            revenue_trend.append({"month": f"{year}-{month:02d}", "revenue": 0})

        # 5. 近6个月评分趋势（简化实现）
        rating_trend: list[dict[str, Any]] = []
        for i in range(5, -1, -1):
            month = now.month - i
            year = now.year
            if month <= 0:
                month += 12
                year -= 1
            rating_trend.append({"month": f"{year}-{month:02d}", "avg_rating": profile.rating})

        return {
            "profile": {
                "id": profile.id,
                "real_name": profile.real_name,
                "rating": profile.rating,
                "total_cases": profile.total_cases,
                "is_verified": profile.is_verified,
                "is_online": profile.is_online,
            },
            "stats": {
                "month_revenue": month_revenue,
                "month_cases": month_cases,
                "rating": profile.rating,
                "pending_count": pending_count,
            },
            "revenue_trend": revenue_trend,
            "rating_trend": rating_trend,
        }
