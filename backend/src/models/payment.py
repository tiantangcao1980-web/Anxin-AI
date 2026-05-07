"""
支付订单模型
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class PaymentOrder(Base, TimestampMixin):
    """支付订单表"""

    __tablename__ = "payment_orders"

    # 业务字段
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, comment="用户ID")
    order_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="订单类型")
    amount: Mapped[float] = mapped_column(Float, nullable=False, comment="金额（元）")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True, comment="支付状态"
    )
    description: Mapped[str] = mapped_column(String(256), nullable=False, default="", comment="订单描述")
    related_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="关联业务ID（咨询/委托/合同等）"
    )
    transaction_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="第三方交易号"
    )
    payment_provider: Mapped[str] = mapped_column(
        String(30), nullable=False, default="mock", comment="支付渠道"
    )
    payment_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="支付链接"
    )
    qr_code: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="二维码数据"
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="支付时间"
    )
    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="退款时间"
    )
    refund_reason: Mapped[str | None] = mapped_column(
        String(256), nullable=True, comment="退款原因"
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="订单过期时间"
    )
