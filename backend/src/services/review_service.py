"""
律师评价服务
"""

from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.lawyer_matching import Consultation, Delegation, LawyerProfile
from src.models.review import LawyerReview


class ReviewService:
    """律师评价服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_review(
        self,
        reviewer_id: str,
        lawyer_profile_id: str,
        rating: int,
        content: str | None = None,
        tags: list[str] | None = None,
        is_anonymous: bool = False,
        consultation_id: str | None = None,
        delegation_id: str | None = None,
    ) -> LawyerReview:
        """创建评价，并自动更新律师的平均评分和评价总数"""
        # 校验评分范围
        if not 1 <= rating <= 5:
            raise ValueError("评分必须在 1-5 之间")

        lawyer_profile = await self.db.get(LawyerProfile, lawyer_profile_id)
        if not lawyer_profile:
            raise ValueError("律师档案不存在")

        if not consultation_id and not delegation_id:
            raise ValueError("评价必须关联真实咨询或委托记录")

        if consultation_id:
            consultation = await self.db.get(Consultation, consultation_id)
            if not consultation:
                raise ValueError("咨询记录不存在")
            if consultation.user_id != reviewer_id:
                raise ValueError("无权使用该咨询记录进行评价")
            if consultation.matched_lawyer_id != lawyer_profile.user_id:
                raise ValueError("咨询记录与律师档案不匹配")

        if delegation_id:
            delegation = await self.db.get(Delegation, delegation_id)
            if not delegation:
                raise ValueError("委托记录不存在")
            if delegation.client_id != reviewer_id:
                raise ValueError("无权使用该委托记录进行评价")
            if delegation.lawyer_id != lawyer_profile.user_id:
                raise ValueError("委托记录与律师档案不匹配")

        duplicate_conditions = [
            LawyerReview.reviewer_id == reviewer_id,
            LawyerReview.lawyer_profile_id == lawyer_profile_id,
        ]
        if consultation_id:
            duplicate_conditions.append(LawyerReview.consultation_id == consultation_id)
        if delegation_id:
            duplicate_conditions.append(LawyerReview.delegation_id == delegation_id)

        existing_result = await self.db.execute(
            select(LawyerReview).where(and_(*duplicate_conditions))
        )
        if existing_result.scalar_one_or_none():
            raise ValueError("该服务记录已评价，请勿重复提交")

        review = LawyerReview(
            reviewer_id=reviewer_id,
            lawyer_profile_id=lawyer_profile_id,
            rating=rating,
            content=content,
            tags=tags or [],
            is_anonymous=is_anonymous,
            consultation_id=consultation_id,
            delegation_id=delegation_id,
        )
        self.db.add(review)
        await self.db.flush()

        # 更新 LawyerProfile 的 rating 和 total_reviews（加权平均）
        await self._update_lawyer_rating(lawyer_profile_id)

        await self.db.commit()
        await self.db.refresh(review)

        logger.info(f"用户 {reviewer_id} 对律师档案 {lawyer_profile_id} 提交了 {rating} 星评价")
        return review

    async def list_reviews(
        self,
        lawyer_profile_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any]:
        """分页查询某律师的评价列表（按时间降序）"""
        base_query = select(LawyerReview).where(LawyerReview.lawyer_profile_id == lawyer_profile_id)

        # 总数
        count_q = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        # 分页
        query = base_query.order_by(LawyerReview.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        reviews = result.scalars().all()

        items: list[dict[str, Any]] = []
        for r in reviews:
            item = {
                "id": r.id,
                "rating": r.rating,
                "content": r.content,
                "tags": r.tags or [],
                "is_anonymous": r.is_anonymous,
                "reply_content": r.reply_content,
                "replied_at": r.replied_at.isoformat() if r.replied_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            # 匿名评价不返回 reviewer 信息
            if not r.is_anonymous:
                item["reviewer_id"] = r.reviewer_id
            else:
                item["reviewer_id"] = None
            items.append(item)

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def reply_to_review(
        self,
        review_id: str,
        lawyer_user_id: str,
        content: str,
    ) -> LawyerReview:
        """律师回复评价（验证身份）"""
        review = await self.db.get(LawyerReview, review_id)
        if not review:
            raise ValueError("评价不存在")

        # 验证该律师是否对应这条评价的律师档案
        profile_result = await self.db.execute(
            select(LawyerProfile).where(
                and_(
                    LawyerProfile.id == review.lawyer_profile_id,
                    LawyerProfile.user_id == lawyer_user_id,
                )
            )
        )
        profile = profile_result.scalar_one_or_none()
        if not profile:
            raise PermissionError("只有该律师本人才能回复评价")

        review.reply_content = content
        review.replied_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(review)

        logger.info(f"律师 {lawyer_user_id} 回复了评价 {review_id}")
        return review

    async def get_review_stats(self, lawyer_profile_id: str) -> dict[str, Any]:
        """获取律师的评价统计"""
        # 总数 & 平均分
        stats_q = select(
            func.count(LawyerReview.id).label("total"),
            func.avg(LawyerReview.rating).label("avg_rating"),
        ).where(LawyerReview.lawyer_profile_id == lawyer_profile_id)
        stats_result = await self.db.execute(stats_q)
        row = stats_result.one()
        total_reviews = row.total or 0
        average_rating = round(float(row.avg_rating or 0), 1)

        # 评分分布
        dist_q = (
            select(
                LawyerReview.rating,
                func.count(LawyerReview.id).label("cnt"),
            )
            .where(LawyerReview.lawyer_profile_id == lawyer_profile_id)
            .group_by(LawyerReview.rating)
        )
        dist_result = await self.db.execute(dist_q)
        rating_distribution = dict.fromkeys(range(1, 6), 0)
        for r in dist_result:
            rating_distribution[r.rating] = r.cnt

        # 热门标签统计 — 从 JSON 数组中提取
        all_reviews_q = select(LawyerReview.tags).where(
            and_(
                LawyerReview.lawyer_profile_id == lawyer_profile_id,
                LawyerReview.tags.isnot(None),
            )
        )
        all_reviews_result = await self.db.execute(all_reviews_q)
        tag_counter: dict[str, int] = {}
        for (tags_val,) in all_reviews_result:
            if isinstance(tags_val, list):
                for tag in tags_val:
                    tag_counter[tag] = tag_counter.get(tag, 0) + 1

        # 按出现次数降序取 top 10
        top_tag_counts = sorted(tag_counter.items(), key=lambda x: x[1], reverse=True)[:10]
        top_tags = [{"tag": tag, "count": count} for tag, count in top_tag_counts]

        return {
            "average_rating": average_rating,
            "total_reviews": total_reviews,
            "rating_distribution": rating_distribution,
            "top_tags": top_tags,
        }

    # ===== 内部方法 =====

    async def _update_lawyer_rating(self, lawyer_profile_id: str) -> None:
        """重新计算并更新律师档案的平均评分和评价总数"""
        stats_q = select(
            func.count(LawyerReview.id).label("total"),
            func.avg(LawyerReview.rating).label("avg"),
        ).where(LawyerReview.lawyer_profile_id == lawyer_profile_id)
        result = await self.db.execute(stats_q)
        row = result.one()

        profile = await self.db.get(LawyerProfile, lawyer_profile_id)
        if profile:
            profile.total_reviews = row.total or 0
            profile.rating = round(float(row.avg or 5.0), 1)
