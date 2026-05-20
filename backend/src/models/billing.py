"""计费系统模型"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import GUID, Base, TimestampMixin


class BillingPlan(Base, TimestampMixin):
    """计费方案/套餐"""

    __tablename__ = "billing_plans"

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="方案名称")
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="方案代码: basic/professional/enterprise"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="方案描述")
    billing_mode: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="计费模式: per_consultation/monthly/yearly/hourly"
    )

    # 价格
    base_price: Mapped[float] = mapped_column(Float, nullable=False, comment="基础价格")
    original_price: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="原价（用于显示划线价）"
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CNY", comment="币种")

    # V2 架构：适用客户端 (needer / provider / both)
    client_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="needer",
        server_default="needer",
        comment="适用客户端: needer / provider / both",
    )

    # 功能配额
    features: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, default=list, comment='功能列表: [{"name":"AI咨询","quota":100}, ...]'
    )
    ai_quota: Mapped[int] = mapped_column(
        Integer, default=100, nullable=False, comment="AI对话次数/月"
    )
    storage_gb: Mapped[int] = mapped_column(
        Integer, default=5, nullable=False, comment="存储空间GB"
    )
    max_team_members: Mapped[int] = mapped_column(
        Integer, default=5, nullable=False, comment="团队成员数上限"
    )

    # 状态
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="是否上架"
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序权重")

    # 显示
    badge: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment='角标: "推荐"/"限时优惠"'
    )
    highlight: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否高亮推荐"
    )

    __table_args__ = (
        Index("ix_billing_plans_code", "code"),
        Index("ix_billing_plans_is_active", "is_active"),
        Index("ix_billing_plans_sort_order", "sort_order"),
    )


class Subscription(Base, TimestampMixin):
    """用户订阅（V2 架构：支持双端独立计费）"""

    __tablename__ = "subscriptions"

    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID"
    )
    plan_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("billing_plans.id", ondelete="CASCADE"),
        nullable=False,
        comment="计费方案ID",
    )
    org_id: Mapped[str | None] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        comment="企业订阅关联组织",
    )

    # V2 架构：适用客户端（needer/provider），同一用户可有两端各一个活跃订阅
    client_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="needer",
        server_default="needer",
        comment="适用客户端: needer(需求方) / provider(服务方)",
    )

    # V2 架构：允许的运行模式（JSON 列表），从 plan.features.modes 继承
    allowed_modes: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment='允许的运行模式: ["local","hybrid","cloud"]'
    )

    # V2 架构：功能权限覆盖（管理员可逐用户定制）
    features_override: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="管理员覆盖的功能权限（优先于 plan.features）"
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        comment="订阅状态: pending/active/trial/past_due/cancelled/expired",
    )

    # V2 架构：试用期
    trial_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="试用期结束时间"
    )

    current_period_start: Mapped[date] = mapped_column(
        Date, nullable=False, comment="当前周期开始日期"
    )
    current_period_end: Mapped[date] = mapped_column(
        Date, nullable=False, comment="当前周期结束日期"
    )

    auto_renew: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="是否自动续费"
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="取消时间"
    )
    cancellation_reason: Mapped[str | None] = mapped_column(
        String(256), nullable=True, comment="取消原因"
    )

    # 支付记录
    last_payment_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="最近一次支付订单ID"
    )
    next_billing_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="下次扣费日期"
    )

    # Relationships
    user = relationship("User", backref="subscriptions")
    plan = relationship("BillingPlan")

    __table_args__ = (
        Index("ix_subscriptions_user_id", "user_id"),
        Index("ix_subscriptions_plan_id", "plan_id"),
        Index("ix_subscriptions_org_id", "org_id"),
        Index("ix_subscriptions_status", "status"),
        Index("ix_subscriptions_next_billing", "next_billing_date"),
    )


class SubscriptionEvent(Base, TimestampMixin):
    """订阅状态变更事件"""

    __tablename__ = "subscription_events"

    subscription_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, comment="订阅ID"
    )
    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID"
    )
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="变更前状态")
    to_status: Mapped[str] = mapped_column(String(20), nullable=False, comment="变更后状态")
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="事件类型")
    reason: Mapped[str | None] = mapped_column(String(256), nullable=True, comment="事件原因")
    payment_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="关联支付订单ID"
    )
    event_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="事件扩展数据"
    )

    subscription = relationship("Subscription", backref="events")
    user = relationship("User")

    __table_args__ = (
        Index("ix_subscription_events_subscription_id", "subscription_id"),
        Index("ix_subscription_events_user_id", "user_id"),
        Index("ix_subscription_events_event_type", "event_type"),
    )


class Refund(Base, TimestampMixin):
    """退款单"""

    __tablename__ = "refunds"

    order_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("payment_orders.id", ondelete="CASCADE"),
        nullable=False,
        comment="支付订单ID",
    )
    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="申请人ID"
    )

    amount: Mapped[float] = mapped_column(Float, nullable=False, comment="退款金额")
    reason: Mapped[str] = mapped_column(String(500), nullable=False, comment="退款原因")
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="退款幂等键"
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="退款状态: pending/approved/rejected/processed",
    )

    approved_by: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="审批人ID"
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="审批时间"
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        String(256), nullable=True, comment="驳回原因"
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="处理完成时间"
    )
    processor_transaction_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="支付渠道退款流水号"
    )

    # Relationships
    order = relationship("PaymentOrder", backref="refunds")
    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])

    __table_args__ = (
        Index("ix_refunds_order_id", "order_id"),
        Index("ix_refunds_user_id", "user_id"),
        Index("ix_refunds_status", "status"),
        Index("ix_refunds_idempotency_key", "idempotency_key", unique=True),
    )
