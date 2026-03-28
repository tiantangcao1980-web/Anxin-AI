# -*- coding: utf-8 -*-
"""
支付服务 - Provider-agnostic 支付接口

支持微信支付、支付宝等多种支付渠道，通过工厂模式切换。
开发环境使用 MockPaymentProvider，无需真实商户凭据即可测试完整支付流程。
"""

import os
import uuid
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from loguru import logger


# ========== 枚举 ==========


class OrderType(str, Enum):
    """订单类型"""
    CONSULTATION_FEE = "consultation_fee"        # 咨询费
    DELEGATION_DEPOSIT = "delegation_deposit"    # 委托保证金
    SUBSCRIPTION = "subscription"                # 订阅费
    CONTRACT_SIGNING = "contract_signing"        # 合同签署费


class PaymentStatusEnum(str, Enum):
    """支付状态"""
    PENDING = "pending"      # 待支付
    PAID = "paid"            # 已支付
    FAILED = "failed"        # 支付失败
    REFUNDED = "refunded"    # 已退款
    CLOSED = "closed"        # 已关闭


class PaymentProviderType(str, Enum):
    """支付渠道"""
    MOCK = "mock"
    WECHAT_PAY = "wechat_pay"
    ALIPAY = "alipay"


# ========== Pydantic 数据模型 ==========


class PaymentOrder(BaseModel):
    """支付订单"""
    order_id: str = Field(description="订单号")
    amount: float = Field(description="金额（元）", gt=0)
    status: PaymentStatusEnum = Field(default=PaymentStatusEnum.PENDING)
    payment_url: Optional[str] = Field(default=None, description="支付链接")
    qr_code: Optional[str] = Field(default=None, description="二维码数据（Base64或URL）")
    provider: PaymentProviderType = Field(description="支付渠道")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=30)
    )


class PaymentStatus(BaseModel):
    """支付状态查询结果"""
    order_id: str
    status: PaymentStatusEnum
    paid_at: Optional[datetime] = None
    transaction_id: Optional[str] = None


class RefundResult(BaseModel):
    """退款结果"""
    refund_id: str
    status: str  # success / pending / failed
    amount: float


class CreateOrderRequest(BaseModel):
    """创建订单请求"""
    type: OrderType = Field(description="订单类型")
    amount: float = Field(description="金额（元）", gt=0, le=1_000_000)
    description: str = Field(description="订单描述", max_length=256)
    related_id: Optional[str] = Field(default=None, description="关联业务ID（咨询ID/委托ID等）")
    provider: PaymentProviderType = Field(
        default=PaymentProviderType.MOCK,
        description="支付渠道"
    )


class RefundRequest(BaseModel):
    """退款请求"""
    amount: Optional[float] = Field(default=None, description="退款金额，为空则全额退款", gt=0)
    reason: str = Field(default="用户申请退款", description="退款原因", max_length=256)


# ========== 抽象支付接口 ==========


class PaymentProvider(ABC):
    """支付渠道抽象基类"""

    @abstractmethod
    async def create_order(
        self,
        order_id: str,
        amount: float,
        description: str,
        notify_url: str,
    ) -> PaymentOrder:
        """创建支付订单"""
        ...

    @abstractmethod
    async def query_order(self, order_id: str) -> PaymentStatus:
        """查询订单状态"""
        ...

    @abstractmethod
    async def refund(
        self,
        order_id: str,
        amount: float,
        reason: str,
    ) -> RefundResult:
        """发起退款"""
        ...

    @abstractmethod
    async def close_order(self, order_id: str) -> bool:
        """关闭订单"""
        ...


# ========== Mock 实现（开发环境） ==========


class MockPaymentProvider(PaymentProvider):
    """
    模拟支付渠道 - 开发/测试环境使用

    - create_order: 返回模拟支付链接和二维码数据
    - query_order: 模拟 2 秒延迟后返回支付成功
    - refund: 始终成功
    - close_order: 始终成功
    """

    # 内存存储，模拟订单状态
    _orders: dict[str, PaymentOrder] = {}

    async def create_order(
        self,
        order_id: str,
        amount: float,
        description: str,
        notify_url: str,
    ) -> PaymentOrder:
        logger.info(f"[MockPay] 创建订单: {order_id}, 金额: {amount}, 描述: {description}")

        order = PaymentOrder(
            order_id=order_id,
            amount=amount,
            status=PaymentStatusEnum.PENDING,
            payment_url=f"https://mock-pay.example.com/pay/{order_id}",
            qr_code=f"mock://qr/{order_id}?amount={amount}",
            provider=PaymentProviderType.MOCK,
        )
        self._orders[order_id] = order
        return order

    async def query_order(self, order_id: str) -> PaymentStatus:
        logger.info(f"[MockPay] 查询订单: {order_id}")

        order = self._orders.get(order_id)
        if order and order.status == PaymentStatusEnum.PENDING:
            # 模拟：订单创建超过 5 秒后自动变为"已支付"
            elapsed = (datetime.now(timezone.utc) - order.created_at).total_seconds()
            if elapsed > 5:
                order.status = PaymentStatusEnum.PAID
                return PaymentStatus(
                    order_id=order_id,
                    status=PaymentStatusEnum.PAID,
                    paid_at=datetime.now(timezone.utc),
                    transaction_id=f"MOCK_TXN_{uuid.uuid4().hex[:12].upper()}",
                )

        return PaymentStatus(
            order_id=order_id,
            status=order.status if order else PaymentStatusEnum.PENDING,
            paid_at=None,
            transaction_id=None,
        )

    async def refund(
        self,
        order_id: str,
        amount: float,
        reason: str,
    ) -> RefundResult:
        logger.info(f"[MockPay] 退款: {order_id}, 金额: {amount}, 原因: {reason}")

        order = self._orders.get(order_id)
        if order:
            order.status = PaymentStatusEnum.REFUNDED

        return RefundResult(
            refund_id=f"MOCK_REFUND_{uuid.uuid4().hex[:12].upper()}",
            status="success",
            amount=amount,
        )

    async def close_order(self, order_id: str) -> bool:
        logger.info(f"[MockPay] 关闭订单: {order_id}")

        order = self._orders.get(order_id)
        if order:
            order.status = PaymentStatusEnum.CLOSED
        return True


# ========== 微信支付（占位） ==========


class WeChatPayProvider(PaymentProvider):
    """
    微信支付渠道 - 需要配置商户凭据

    环境变量：
    - WECHAT_PAY_MCH_ID: 商户号
    - WECHAT_PAY_API_KEY: API 密钥
    - WECHAT_PAY_CERT_PATH: 证书路径
    """

    async def create_order(self, order_id, amount, description, notify_url) -> PaymentOrder:
        raise NotImplementedError(
            "微信支付未配置。请设置环境变量 WECHAT_PAY_MCH_ID、WECHAT_PAY_API_KEY 并参考文档完成接入。"
        )

    async def query_order(self, order_id) -> PaymentStatus:
        raise NotImplementedError("微信支付未配置。请设置环境变量 WECHAT_PAY_MCH_ID。")

    async def refund(self, order_id, amount, reason) -> RefundResult:
        raise NotImplementedError("微信支付未配置。请设置环境变量 WECHAT_PAY_MCH_ID。")

    async def close_order(self, order_id) -> bool:
        raise NotImplementedError("微信支付未配置。请设置环境变量 WECHAT_PAY_MCH_ID。")


# ========== 支付宝（占位） ==========


class AlipayProvider(PaymentProvider):
    """
    支付宝渠道 - 需要配置应用凭据

    环境变量：
    - ALIPAY_APP_ID: 应用 ID
    - ALIPAY_PRIVATE_KEY: 应用私钥
    - ALIPAY_PUBLIC_KEY: 支付宝公钥
    """

    async def create_order(self, order_id, amount, description, notify_url) -> PaymentOrder:
        raise NotImplementedError(
            "支付宝未配置。请设置环境变量 ALIPAY_APP_ID、ALIPAY_PRIVATE_KEY 并参考文档完成接入。"
        )

    async def query_order(self, order_id) -> PaymentStatus:
        raise NotImplementedError("支付宝未配置。请设置环境变量 ALIPAY_APP_ID。")

    async def refund(self, order_id, amount, reason) -> RefundResult:
        raise NotImplementedError("支付宝未配置。请设置环境变量 ALIPAY_APP_ID。")

    async def close_order(self, order_id) -> bool:
        raise NotImplementedError("支付宝未配置。请设置环境变量 ALIPAY_APP_ID。")


# ========== 工厂函数 ==========


_provider_instance: Optional[PaymentProvider] = None


def get_payment_provider() -> PaymentProvider:
    """
    根据环境变量 PAYMENT_PROVIDER 返回对应的支付渠道实例。

    - "mock"       → MockPaymentProvider（默认）
    - "wechat_pay" → WeChatPayProvider
    - "alipay"     → AlipayProvider
    """
    global _provider_instance

    provider_name = os.getenv("PAYMENT_PROVIDER", "mock").lower()

    # 单例模式：同一进程内复用实例
    if _provider_instance is not None:
        return _provider_instance

    providers = {
        "mock": MockPaymentProvider,
        "wechat_pay": WeChatPayProvider,
        "alipay": AlipayProvider,
    }

    provider_cls = providers.get(provider_name)
    if provider_cls is None:
        logger.warning(f"未知支付渠道 '{provider_name}'，回退到 MockPaymentProvider")
        provider_cls = MockPaymentProvider

    _provider_instance = provider_cls()
    logger.info(f"支付渠道已初始化: {provider_cls.__name__}")
    return _provider_instance
