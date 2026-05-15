"""
账单管理服务
"""

from datetime import UTC, date, datetime
from typing import Any

from loguru import logger
from sqlalchemy import and_, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.firm_management import Invoice


class BillingService:
    """账单管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _generate_invoice_number(self, org_id: str) -> str:
        """生成发票编号: INV-YYYYMM-NNN"""
        now = datetime.now(UTC)
        prefix = f"INV-{now.strftime('%Y%m')}"

        # 查询当月最大序号
        stmt = select(func.count(Invoice.id)).where(
            Invoice.org_id == org_id,
            Invoice.number.like(f"{prefix}-%"),
        )
        result = await self.db.execute(stmt)
        count = result.scalar() or 0

        return f"{prefix}-{count + 1:03d}"

    async def create_invoice(
        self,
        org_id: str,
        client_name: str,
        items: list[dict[str, Any]],
        case_id: str | None = None,
        due_date: date | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """创建发票"""
        number = await self._generate_invoice_number(org_id)
        total_amount = sum(item.get("amount", 0) for item in items)

        invoice = Invoice(
            org_id=org_id,
            case_id=case_id,
            number=number,
            client_name=client_name,
            total_amount=total_amount,
            items=items,
            due_date=due_date,
            notes=notes,
            status="draft",
        )
        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)
        logger.info(f"创建发票: {number}, 金额={total_amount}")
        return invoice.to_dict()

    async def list_invoices(
        self,
        org_id: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """查询发票列表"""
        stmt = select(Invoice).where(Invoice.org_id == org_id)
        if status:
            stmt = stmt.where(Invoice.status == status)
        stmt = stmt.order_by(Invoice.created_at.desc())

        result = await self.db.execute(stmt)
        invoices = result.scalars().all()
        return [inv.to_dict() for inv in invoices]

    async def update_invoice_status(self, invoice_id: str, status: str) -> dict[str, Any] | None:
        """更新发票状态"""
        result = await self.db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = result.scalar_one_or_none()
        if not invoice:
            return None

        invoice.status = status
        if status == "paid":
            invoice.paid_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(invoice)
        logger.info(f"更新发票状态: {invoice.number} -> {status}")
        return invoice.to_dict()

    async def get_revenue_report(
        self,
        org_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, Any]:
        """
        获取收入报表
        返回 { total_revenue, paid_amount, pending_amount,
               by_month: [{month, amount}], by_status: [{status, count, amount}] }
        """
        base_conditions = [Invoice.org_id == org_id]
        if date_from:
            base_conditions.append(
                Invoice.created_at >= datetime.combine(date_from, datetime.min.time())
            )
        if date_to:
            base_conditions.append(
                Invoice.created_at <= datetime.combine(date_to, datetime.max.time())
            )

        # 按状态汇总
        stmt_status = (
            select(
                Invoice.status,
                func.count(Invoice.id).label("count"),
                func.coalesce(func.sum(Invoice.total_amount), 0).label("amount"),
            )
            .where(and_(*base_conditions))
            .group_by(Invoice.status)
        )
        result_status = await self.db.execute(stmt_status)
        status_rows = result_status.all()

        total_revenue = 0.0
        paid_amount = 0.0
        pending_amount = 0.0
        by_status: list[dict[str, Any]] = []
        for status_row in status_rows:
            amount = float(status_row.amount)
            total_revenue += amount
            if status_row.status == "paid":
                paid_amount += amount
            elif status_row.status in ("sent", "overdue"):
                pending_amount += amount
            by_status.append(
                {
                    "status": status_row.status,
                    "count": status_row.count,
                    "amount": round(amount, 2),
                }
            )

        # 按月汇总（仅已支付）
        paid_conditions = base_conditions + [Invoice.status == "paid"]
        stmt_month = (
            select(
                extract("year", Invoice.paid_at).label("year"),
                extract("month", Invoice.paid_at).label("month"),
                func.coalesce(func.sum(Invoice.total_amount), 0).label("amount"),
            )
            .where(and_(*paid_conditions))
            .group_by("year", "month")
            .order_by("year", "month")
        )
        result_month = await self.db.execute(stmt_month)
        month_rows = result_month.all()

        by_month: list[dict[str, Any]] = []
        for month_row in month_rows:
            by_month.append(
                {
                    "month": f"{int(month_row.year)}-{int(month_row.month):02d}",
                    "amount": round(float(month_row.amount), 2),
                }
            )

        return {
            "total_revenue": round(total_revenue, 2),
            "paid_amount": round(paid_amount, 2),
            "pending_amount": round(pending_amount, 2),
            "by_month": by_month,
            "by_status": by_status,
        }
