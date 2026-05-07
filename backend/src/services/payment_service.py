"""
支付服务 - Provider-agnostic 支付接口

支持微信支付、支付宝等多种支付渠道，通过工厂模式切换。
开发环境使用 MockPaymentProvider，无需真实商户凭据即可测试完整支付流程。
"""

import base64
import json
import os
import secrets
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from pathlib import Path
from typing import Any, TypeAlias, cast
from urllib.parse import urlencode

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from loguru import logger
from pydantic import BaseModel, Field

from src.core.config import settings
from src.services.official_webhook_security import (
    OfficialWebhookVerificationError,
    verify_alipay_response_body,
    verify_wechat_pay_signature,
)

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
    payment_url: str | None = Field(default=None, description="支付链接")
    qr_code: str | None = Field(default=None, description="二维码数据（Base64或URL）")
    provider: PaymentProviderType = Field(description="支付渠道")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC) + timedelta(minutes=30)
    )


class PaymentStatus(BaseModel):
    """支付状态查询结果"""
    order_id: str
    status: PaymentStatusEnum
    paid_at: datetime | None = None
    transaction_id: str | None = None


class RefundResult(BaseModel):
    """退款结果"""
    refund_id: str
    status: str  # success / pending / failed
    amount: float


class PaymentProviderConfigError(RuntimeError):
    """Raised when an official payment provider lacks required configuration."""


class CreateOrderRequest(BaseModel):
    """创建订单请求"""
    type: OrderType = Field(description="订单类型")
    amount: float = Field(description="金额（元）", gt=0, le=1_000_000)
    description: str = Field(description="订单描述", max_length=256)
    related_id: str | None = Field(default=None, description="关联业务ID（咨询ID/委托ID等）")
    provider: PaymentProviderType = Field(
        default=PaymentProviderType.MOCK,
        description="支付渠道"
    )


class RefundRequest(BaseModel):
    """退款请求"""
    amount: float | None = Field(default=None, description="退款金额，为空则全额退款", gt=0)
    reason: str = Field(default="用户申请退款", description="退款原因", max_length=256)
    idempotency_key: str | None = Field(
        default=None,
        max_length=128,
        description="退款幂等键；同一 key 的重复请求返回同一退款结果",
    )


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
        total_amount: float | None = None,
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
            elapsed = (datetime.now(UTC) - order.created_at).total_seconds()
            if elapsed > 5:
                order.status = PaymentStatusEnum.PAID
                return PaymentStatus(
                    order_id=order_id,
                    status=PaymentStatusEnum.PAID,
                    paid_at=datetime.now(UTC),
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
        total_amount: float | None = None,
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


def _amount_to_cents(amount: float) -> int:
    return int((Decimal(str(amount)) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _provider_order_id(order_id: str) -> str:
    return order_id.replace("-", "")


def _resolve_notify_url(notify_url: str) -> str:
    if notify_url.startswith(("http://", "https://")):
        return notify_url
    base_url = (settings.PAYMENT_NOTIFY_BASE_URL or "").rstrip("/")
    if not base_url:
        raise PaymentProviderConfigError("请配置 PAYMENT_NOTIFY_BASE_URL 为公网可访问的回调域名。")
    return f"{base_url}{notify_url if notify_url.startswith('/') else f'/{notify_url}'}"


def _load_private_key(*, value: str | None, path: str | None) -> Any:
    if path:
        raw = Path(path).read_bytes()
    elif value:
        raw = value.replace("\\n", "\n").encode("utf-8")
    else:
        raise PaymentProviderConfigError("支付渠道私钥未配置。")
    try:
        return serialization.load_pem_private_key(raw, password=None)
    except Exception as exc:
        raise PaymentProviderConfigError("支付渠道私钥格式无效。") from exc


def _parse_wechat_status(raw: str | None) -> PaymentStatusEnum:
    state = (raw or "").upper()
    if state == "SUCCESS":
        return PaymentStatusEnum.PAID
    if state in {"CLOSED", "REVOKED"}:
        return PaymentStatusEnum.CLOSED
    if state in {"PAYERROR"}:
        return PaymentStatusEnum.FAILED
    if state in {"REFUND"}:
        return PaymentStatusEnum.REFUNDED
    return PaymentStatusEnum.PENDING


def _parse_alipay_status(raw: str | None) -> PaymentStatusEnum:
    state = (raw or "").upper()
    if state in {"TRADE_SUCCESS", "TRADE_FINISHED"}:
        return PaymentStatusEnum.PAID
    if state == "TRADE_CLOSED":
        return PaymentStatusEnum.CLOSED
    return PaymentStatusEnum.PENDING


# ========== 微信支付 ==========


class WeChatPayProvider(PaymentProvider):
    """
    微信支付渠道 - 需要配置商户凭据

    环境变量：
    - WECHAT_PAY_APP_ID: 公众号/应用 ID
    - WECHAT_PAY_MCH_ID: 商户号
    - WECHAT_PAY_MERCHANT_SERIAL_NO: 商户 API 证书序列号
    - WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH 或 WECHAT_PAY_MERCHANT_PRIVATE_KEY: 商户私钥
    - WECHAT_PAY_PLATFORM_PUBLIC_KEY_PATH 或 WECHAT_PAY_PLATFORM_PUBLIC_KEY: 微信支付平台公钥/证书
    - WECHAT_PAY_PLATFORM_SERIAL: 平台公钥 ID 或平台证书序列号
    - PAYMENT_NOTIFY_BASE_URL: 公网回调域名
    """

    def __init__(self) -> None:
        self.app_id = settings.WECHAT_PAY_APP_ID
        self.mch_id = settings.WECHAT_PAY_MCH_ID
        self.serial_no = settings.WECHAT_PAY_MERCHANT_SERIAL_NO
        self.private_key = _load_private_key(
            value=settings.WECHAT_PAY_MERCHANT_PRIVATE_KEY,
            path=settings.WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH,
        )
        self.platform_serial = settings.WECHAT_PAY_PLATFORM_SERIAL
        self.platform_public_key = settings.WECHAT_PAY_PLATFORM_PUBLIC_KEY
        self.platform_public_key_path = settings.WECHAT_PAY_PLATFORM_PUBLIC_KEY_PATH
        self.api_base_url = settings.WECHAT_PAY_API_BASE_URL.rstrip("/")

    def _check_config(self) -> None:
        missing = [
            name
            for name, value in {
                "WECHAT_PAY_APP_ID": self.app_id,
                "WECHAT_PAY_MCH_ID": self.mch_id,
                "WECHAT_PAY_MERCHANT_SERIAL_NO": self.serial_no,
                "WECHAT_PAY_PLATFORM_SERIAL": self.platform_serial,
            }.items()
            if not value
        ]
        if not self.platform_public_key and not self.platform_public_key_path:
            missing.append("WECHAT_PAY_PLATFORM_PUBLIC_KEY(_PATH)")
        if missing:
            raise PaymentProviderConfigError(f"微信支付配置缺失: {', '.join(missing)}")

    def _authorization(self, method: str, path_with_query: str, body: bytes) -> str:
        timestamp = str(int(datetime.now(UTC).timestamp()))
        nonce = secrets.token_hex(16)
        message = b"\n".join(
            [
                method.upper().encode("utf-8"),
                path_with_query.encode("utf-8"),
                timestamp.encode("utf-8"),
                nonce.encode("utf-8"),
                body,
            ]
        ) + b"\n"
        signature = self.private_key.sign(
            message,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        signature_b64 = base64.b64encode(signature).decode("ascii")
        return (
            'WECHATPAY2-SHA256-RSA2048 '
            f'mchid="{self.mch_id}",nonce_str="{nonce}",signature="{signature_b64}",'
            f'timestamp="{timestamp}",serial_no="{self.serial_no}"'
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        expect_empty: bool = False,
    ) -> dict[str, Any]:
        self._check_config()
        query_string = f"?{urlencode(query)}" if query else ""
        path_with_query = f"{path}{query_string}"
        body = (
            json.dumps(json_body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            if json_body is not None
            else b""
        )
        headers = {
            "Accept": "application/json",
            "Authorization": self._authorization(method, path_with_query, body),
            "Content-Type": "application/json",
        }
        if self.platform_serial:
            headers["Wechatpay-Serial"] = self.platform_serial
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(
                method,
                f"{self.api_base_url}{path_with_query}",
                content=body if body else None,
                headers=headers,
            )
        if response.content:
            try:
                verify_wechat_pay_signature(
                    headers=response.headers,
                    body=response.content,
                    public_key=self.platform_public_key,
                    public_key_path=self.platform_public_key_path,
                    expected_serial=self.platform_serial,
                    max_age_seconds=settings.WEBHOOK_SIGNATURE_MAX_AGE_SECONDS,
                )
            except OfficialWebhookVerificationError as exc:
                raise RuntimeError(f"微信支付 API 响应验签失败: {exc}") from exc
        if response.status_code >= 400:
            raise RuntimeError(f"微信支付 API 调用失败: {response.status_code} {response.text}")
        if expect_empty or not response.content:
            return {}
        return cast(dict[str, Any], response.json())

    async def create_order(
        self,
        order_id: str,
        amount: float,
        description: str,
        notify_url: str,
    ) -> PaymentOrder:
        provider_order_id = _provider_order_id(order_id)
        data = await self._request(
            "POST",
            "/v3/pay/transactions/native",
            json_body={
                "appid": self.app_id,
                "mchid": self.mch_id,
                "description": description[:127],
                "out_trade_no": provider_order_id,
                "notify_url": _resolve_notify_url(notify_url),
                "amount": {"total": _amount_to_cents(amount), "currency": "CNY"},
            },
        )
        code_url = data.get("code_url")
        if not code_url:
            raise RuntimeError("微信支付下单响应缺少 code_url。")
        return PaymentOrder(
            order_id=order_id,
            amount=amount,
            status=PaymentStatusEnum.PENDING,
            payment_url=code_url,
            qr_code=code_url,
            provider=PaymentProviderType.WECHAT_PAY,
        )

    async def query_order(self, order_id: str) -> PaymentStatus:
        if not self.mch_id:
            raise PaymentProviderConfigError("微信支付配置缺失: WECHAT_PAY_MCH_ID")
        data = await self._request(
            "GET",
            f"/v3/pay/transactions/out-trade-no/{_provider_order_id(order_id)}",
            query={"mchid": self.mch_id},
        )
        status = _parse_wechat_status(data.get("trade_state"))
        paid_at = None
        if data.get("success_time"):
            try:
                paid_at = datetime.fromisoformat(str(data["success_time"]).replace("Z", "+00:00"))
            except ValueError:
                paid_at = None
        return PaymentStatus(
            order_id=order_id,
            status=status,
            paid_at=paid_at,
            transaction_id=data.get("transaction_id"),
        )

    async def refund(
        self,
        order_id: str,
        amount: float,
        reason: str,
        total_amount: float | None = None,
    ) -> RefundResult:
        provider_order_id = _provider_order_id(order_id)
        original_amount = total_amount if total_amount is not None else amount
        data = await self._request(
            "POST",
            "/v3/refund/domestic/refunds",
            json_body={
                "out_trade_no": provider_order_id,
                "out_refund_no": f"rf_{provider_order_id[:29]}",
                "reason": reason[:80],
                "amount": {
                    "refund": _amount_to_cents(amount),
                    "total": _amount_to_cents(original_amount),
                    "currency": "CNY",
                },
            },
        )
        raw_status = str(data.get("status") or "").upper()
        status = "success" if raw_status == "SUCCESS" else "pending"
        return RefundResult(
            refund_id=str(data.get("refund_id") or data.get("out_refund_no") or f"rf_{provider_order_id[:29]}"),
            status=status,
            amount=amount,
        )

    async def close_order(self, order_id: str) -> bool:
        await self._request(
            "POST",
            f"/v3/pay/transactions/out-trade-no/{_provider_order_id(order_id)}/close",
            json_body={"mchid": self.mch_id},
            expect_empty=True,
        )
        return True


# ========== 支付宝 ==========


class AlipayProvider(PaymentProvider):
    """
    支付宝渠道 - 需要配置应用凭据

    环境变量：
    - ALIPAY_APP_ID: 应用 ID
    - ALIPAY_PRIVATE_KEY 或 ALIPAY_PRIVATE_KEY_PATH: 应用私钥
    - ALIPAY_PUBLIC_KEY 或 ALIPAY_PUBLIC_KEY_PATH: 支付宝公钥
    - PAYMENT_NOTIFY_BASE_URL: 公网回调域名
    """

    def __init__(self) -> None:
        self.app_id = settings.ALIPAY_APP_ID
        self.private_key = _load_private_key(
            value=settings.ALIPAY_PRIVATE_KEY,
            path=settings.ALIPAY_PRIVATE_KEY_PATH,
        )
        self.public_key = settings.ALIPAY_PUBLIC_KEY
        self.public_key_path = settings.ALIPAY_PUBLIC_KEY_PATH
        self.gateway_url = settings.ALIPAY_GATEWAY_URL

    def _check_config(self) -> None:
        if not self.app_id:
            raise PaymentProviderConfigError("支付宝配置缺失: ALIPAY_APP_ID")

    def _check_response_verification_config(self) -> None:
        if not self.public_key and not self.public_key_path:
            raise PaymentProviderConfigError("支付宝配置缺失: ALIPAY_PUBLIC_KEY(_PATH)")

    def _signed_params(
        self,
        method: str,
        biz_content: dict[str, Any],
        *,
        notify_url: str | None = None,
    ) -> dict[str, str]:
        if not self.app_id:
            raise PaymentProviderConfigError("支付宝配置缺失: ALIPAY_APP_ID")
        params = {
            "app_id": self.app_id,
            "method": method,
            "format": "JSON",
            "charset": "UTF-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "biz_content": json.dumps(biz_content, ensure_ascii=False, separators=(",", ":")),
        }
        if notify_url:
            params["notify_url"] = _resolve_notify_url(notify_url)
        content = "&".join(f"{key}={params[key]}" for key in sorted(params))
        signature = self.private_key.sign(
            content.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        params["sign"] = base64.b64encode(signature).decode("ascii")
        return params

    async def _call(self, method: str, biz_content: dict[str, Any]) -> dict[str, Any]:
        params = self._signed_params(method, biz_content)
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(self.gateway_url, data=params)
        if response.status_code >= 400:
            raise RuntimeError(f"支付宝 API 调用失败: {response.status_code} {response.text}")
        response_key = method.replace(".", "_") + "_response"
        self._check_response_verification_config()
        try:
            verify_alipay_response_body(
                raw_body=response.content,
                response_key=response_key,
                public_key=self.public_key,
                public_key_path=self.public_key_path,
            )
        except OfficialWebhookVerificationError as exc:
            raise RuntimeError(f"支付宝 API 响应验签失败: {exc}") from exc
        data = response.json()
        result = data.get(response_key)
        if not isinstance(result, dict):
            raise RuntimeError(f"支付宝响应缺少 {response_key}。")
        if result.get("code") != "10000":
            raise RuntimeError(f"支付宝 API 业务失败: {result.get('sub_msg') or result.get('msg')}")
        return result

    async def create_order(
        self,
        order_id: str,
        amount: float,
        description: str,
        notify_url: str,
    ) -> PaymentOrder:
        provider_order_id = _provider_order_id(order_id)
        params = self._signed_params(
            "alipay.trade.page.pay",
            {
                "out_trade_no": provider_order_id,
                "product_code": "FAST_INSTANT_TRADE_PAY",
                "total_amount": f"{Decimal(str(amount)).quantize(Decimal('0.01'))}",
                "subject": description[:256],
            },
            notify_url=notify_url,
        )
        payment_url = f"{self.gateway_url}?{urlencode(params)}"
        return PaymentOrder(
            order_id=order_id,
            amount=amount,
            status=PaymentStatusEnum.PENDING,
            payment_url=payment_url,
            qr_code=None,
            provider=PaymentProviderType.ALIPAY,
        )

    async def query_order(self, order_id: str) -> PaymentStatus:
        data = await self._call("alipay.trade.query", {"out_trade_no": _provider_order_id(order_id)})
        status = _parse_alipay_status(data.get("trade_status"))
        return PaymentStatus(
            order_id=order_id,
            status=status,
            paid_at=datetime.now(UTC) if status == PaymentStatusEnum.PAID else None,
            transaction_id=data.get("trade_no"),
        )

    async def refund(
        self,
        order_id: str,
        amount: float,
        reason: str,
        total_amount: float | None = None,
    ) -> RefundResult:
        data = await self._call(
            "alipay.trade.refund",
            {
                "out_trade_no": _provider_order_id(order_id),
                "refund_amount": f"{Decimal(str(amount)).quantize(Decimal('0.01'))}",
                "refund_reason": reason[:256],
                "out_request_no": f"rf_{_provider_order_id(order_id)[:29]}",
            },
        )
        return RefundResult(
            refund_id=str(data.get("trade_no") or data.get("out_trade_no") or order_id),
            status="success",
            amount=amount,
        )

    async def close_order(self, order_id: str) -> bool:
        await self._call("alipay.trade.close", {"out_trade_no": _provider_order_id(order_id)})
        return True


# ========== 工厂函数 ==========


ProviderClass: TypeAlias = type[MockPaymentProvider] | type[WeChatPayProvider] | type[AlipayProvider]

_provider_instances: dict[str, PaymentProvider] = {}


def get_payment_provider(provider_name: str | None = None) -> PaymentProvider:
    """
    根据环境变量 PAYMENT_PROVIDER 返回对应的支付渠道实例。

    - "mock"       → MockPaymentProvider（默认）
    - "wechat_pay" → WeChatPayProvider
    - "alipay"     → AlipayProvider
    """
    raw_provider_name = provider_name or os.getenv("PAYMENT_PROVIDER")
    provider_name = (raw_provider_name or "mock").lower()
    if settings.ENVIRONMENT.lower() in {"production", "staging"} and provider_name == "mock":
        raise PaymentProviderConfigError("staging/production 环境必须配置真实 PAYMENT_PROVIDER，禁止使用 Mock 支付渠道。")

    # 单例模式：同一进程内复用实例
    if provider_name in _provider_instances:
        return _provider_instances[provider_name]

    providers: dict[str, ProviderClass] = {
        "mock": MockPaymentProvider,
        "wechat_pay": WeChatPayProvider,
        "alipay": AlipayProvider,
    }

    provider_cls = providers.get(provider_name)
    if provider_cls is None:
        raise PaymentProviderConfigError(f"未知支付渠道 '{provider_name}'，请配置 wechat_pay 或 alipay。")

    _provider_instances[provider_name] = provider_cls()
    logger.info(f"支付渠道已初始化: {provider_cls.__name__}")
    return _provider_instances[provider_name]


def reset_payment_providers() -> None:
    """Reset provider cache for tests and config reloads."""
    _provider_instances.clear()
