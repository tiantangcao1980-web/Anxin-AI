"""
获客分析服务
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.lawyer_matching import Consultation, Delegation, LawyerProfile
from src.models.lead import Lead


class AcquisitionAnalyticsService:
    """获客分析服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_lead_funnel(
        self,
        org_id: str | None = None,
        days: int = 30,
    ) -> list[dict[str, int | str]]:
        """获取线索漏斗各阶段数量"""
        since = datetime.now(UTC) - timedelta(days=days)
        stages = ["new", "contacted", "qualified", "proposal", "won", "lost"]

        query = select(
            Lead.stage,
            func.count(Lead.id).label("count_value"),
        ).where(Lead.created_at >= since)

        if org_id:
            query = query.where(Lead.org_id == org_id)

        query = query.group_by(Lead.stage)
        result = await self.db.execute(query)
        stage_counts: dict[str, int] = {
            str(row["stage"]): int(row["count_value"])
            for row in result.mappings()
            if row["stage"] is not None
        }

        return [
            {"stage": s, "count": stage_counts.get(s, 0)}
            for s in stages
        ]

    async def get_conversion_rates(
        self,
        org_id: str | None = None,
        days: int = 30,
    ) -> list[dict[str, float | int | str]]:
        """获取各阶段转化率"""
        funnel = await self.get_lead_funnel(org_id=org_id, days=days)
        stage_map = {str(item["stage"]): int(item["count"]) for item in funnel}

        stages_order = ["new", "contacted", "qualified", "proposal", "won"]
        conversions: list[dict[str, float | int | str]] = []
        for i in range(len(stages_order) - 1):
            from_stage = stages_order[i]
            to_stage = stages_order[i + 1]
            from_count = stage_map.get(from_stage, 0)
            to_count = stage_map.get(to_stage, 0)
            rate = round(to_count / from_count, 4) if from_count > 0 else 0.0
            conversions.append({
                "from_stage": from_stage,
                "to_stage": to_stage,
                "from_count": from_count,
                "to_count": to_count,
                "rate": rate,
            })

        return conversions

    async def get_lead_sources(
        self,
        org_id: str | None = None,
        days: int = 30,
    ) -> list[dict[str, int | str]]:
        """获取线索来源分布"""
        since = datetime.now(UTC) - timedelta(days=days)

        query = select(
            Lead.source,
            func.count(Lead.id).label("count_value"),
        ).where(
            and_(
                Lead.created_at >= since,
                Lead.source.isnot(None),
            )
        )

        if org_id:
            query = query.where(Lead.org_id == org_id)

        query = query.group_by(Lead.source).order_by(func.count(Lead.id).desc())
        result = await self.db.execute(query)

        return [
            {"source": str(row["source"] or "未知"), "count": int(row["count_value"])}
            for row in result.mappings()
        ]

    async def get_lawyer_performance(
        self,
        org_id: str | None = None,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """获取律师业绩排名"""
        since = datetime.now(UTC) - timedelta(days=days)

        # 查询所有已认证律师档案
        profiles_q = select(LawyerProfile).where(LawyerProfile.is_verified == True)
        profiles_result = await self.db.execute(profiles_q)
        profiles = profiles_result.scalars().all()

        performances: list[dict[str, Any]] = []
        for profile in profiles:
            # 统计该律师在时间范围内的咨询量
            consult_q = select(func.count(Consultation.id)).where(
                and_(
                    Consultation.matched_lawyer_id == profile.user_id,
                    Consultation.created_at >= since,
                )
            )
            total_consultations = (await self.db.execute(consult_q)).scalar() or 0

            # 统计委托量
            deleg_q = select(func.count(Delegation.id)).where(
                and_(
                    Delegation.lawyer_id == profile.user_id,
                    Delegation.created_at >= since,
                )
            )
            total_delegations = (await self.db.execute(deleg_q)).scalar() or 0

            # 统计收入
            revenue_q = select(func.coalesce(func.sum(Delegation.paid_amount), 0)).where(
                and_(
                    Delegation.lawyer_id == profile.user_id,
                    Delegation.created_at >= since,
                    Delegation.paid_amount.isnot(None),
                )
            )
            revenue = float((await self.db.execute(revenue_q)).scalar() or 0)

            performances.append({
                "lawyer_profile_id": profile.id,
                "lawyer_name": profile.real_name,
                "law_firm": profile.law_firm,
                "total_consultations": total_consultations,
                "total_delegations": total_delegations,
                "revenue": revenue,
                "avg_rating": profile.rating,
            })

        # 按委托量降序排序
        performances.sort(key=lambda x: int(x["total_delegations"]), reverse=True)
        return performances[:20]
