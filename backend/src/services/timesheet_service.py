"""
工时管理服务
"""

from datetime import UTC, date, datetime
from typing import Any

from loguru import logger
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.firm_management import TimeEntry


class TimesheetService:
    """工时管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_entry(
        self,
        user_id: str,
        entry_date: date,
        minutes: int,
        description: str | None = None,
        billable: bool = True,
        rate: float | None = None,
        case_id: str | None = None,
    ) -> dict[str, Any]:
        """创建工时记录"""
        entry = TimeEntry(
            user_id=user_id,
            date=entry_date,
            minutes=minutes,
            description=description,
            billable=billable,
            rate=rate,
            case_id=case_id,
            status="draft",
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        logger.info(f"创建工时记录: user={user_id}, date={entry_date}, minutes={minutes}")
        return entry.to_dict()

    async def list_entries(
        self,
        user_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        status: str | None = None,
        case_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """查询工时记录"""
        stmt = select(TimeEntry)

        conditions = []
        if user_id:
            conditions.append(TimeEntry.user_id == user_id)
        if date_from:
            conditions.append(TimeEntry.date >= date_from)
        if date_to:
            conditions.append(TimeEntry.date <= date_to)
        if status:
            conditions.append(TimeEntry.status == status)
        if case_id:
            conditions.append(TimeEntry.case_id == case_id)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(TimeEntry.date.desc(), TimeEntry.created_at.desc())
        result = await self.db.execute(stmt)
        entries = result.scalars().all()
        return [e.to_dict() for e in entries]

    async def submit_entries(self, entry_ids: list[str], user_id: str) -> int:
        """批量提交工时记录: draft -> submitted"""
        stmt = select(TimeEntry).where(
            TimeEntry.id.in_(entry_ids),
            TimeEntry.user_id == user_id,
            TimeEntry.status == "draft",
        )
        result = await self.db.execute(stmt)
        entries = result.scalars().all()

        count = 0
        for entry in entries:
            entry.status = "submitted"
            count += 1

        await self.db.commit()
        logger.info(f"提交工时记录: user={user_id}, count={count}")
        return count

    async def approve_entries(self, entry_ids: list[str], approver_id: str) -> int:
        """批量审批工时记录: submitted -> approved"""
        stmt = select(TimeEntry).where(
            TimeEntry.id.in_(entry_ids),
            TimeEntry.status == "submitted",
        )
        result = await self.db.execute(stmt)
        entries = result.scalars().all()

        now = datetime.now(UTC)
        count = 0
        for entry in entries:
            entry.status = "approved"
            entry.approved_by = approver_id
            entry.approved_at = now
            count += 1

        await self.db.commit()
        logger.info(f"审批工时记录: approver={approver_id}, count={count}")
        return count

    async def reject_entries(self, entry_ids: list[str], approver_id: str) -> int:
        """批量拒绝工时记录: submitted -> rejected"""
        stmt = select(TimeEntry).where(
            TimeEntry.id.in_(entry_ids),
            TimeEntry.status == "submitted",
        )
        result = await self.db.execute(stmt)
        entries = result.scalars().all()

        count = 0
        for entry in entries:
            entry.status = "rejected"
            entry.approved_by = approver_id
            count += 1

        await self.db.commit()
        logger.info(f"拒绝工时记录: approver={approver_id}, count={count}")
        return count

    async def get_summary(
        self,
        user_id: str | None = None,
        org_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, Any]:
        """
        获取工时汇总
        返回 { total_minutes, billable_minutes, total_amount, by_user: [...] }
        """
        stmt = select(
            TimeEntry.user_id,
            func.sum(TimeEntry.minutes).label("total_minutes"),
            func.sum(
                case(
                    (TimeEntry.billable == True, TimeEntry.minutes),
                    else_=0,
                )
            ).label("billable_minutes"),
            func.sum(
                case(
                    (
                        and_(TimeEntry.billable == True, TimeEntry.rate.isnot(None)),
                        TimeEntry.minutes / 60.0 * TimeEntry.rate,
                    ),
                    else_=0,
                )
            ).label("total_amount"),
        )

        conditions = []
        if user_id:
            conditions.append(TimeEntry.user_id == user_id)
        if date_from:
            conditions.append(TimeEntry.date >= date_from)
        if date_to:
            conditions.append(TimeEntry.date <= date_to)
        # 只统计已审批的记录
        conditions.append(TimeEntry.status == "approved")

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.group_by(TimeEntry.user_id)
        result = await self.db.execute(stmt)
        rows = result.all()

        total_minutes = 0
        billable_minutes = 0
        total_amount = 0.0
        by_user: list[dict[str, Any]] = []

        for row in rows:
            user_minutes = int(row.total_minutes or 0)
            user_billable = int(row.billable_minutes or 0)
            user_amount = float(row.total_amount or 0)
            total_minutes += user_minutes
            billable_minutes += user_billable
            total_amount += user_amount
            by_user.append({
                "user_id": row.user_id,
                "minutes": user_minutes,
                "billable_minutes": user_billable,
                "amount": round(user_amount, 2),
            })

        return {
            "total_minutes": total_minutes,
            "billable_minutes": billable_minutes,
            "total_amount": round(total_amount, 2),
            "by_user": by_user,
        }
