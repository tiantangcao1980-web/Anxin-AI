"""Stable business event objects produced from verified webhook payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.models.contract import ContractStatus
from src.services.payment_service import PaymentStatusEnum


@dataclass(frozen=True, slots=True)
class PaymentWebhookEvent:
    """Canonical payment event after provider payload normalization."""

    provider: str
    order_id: str
    status: PaymentStatusEnum
    provider_status: str
    transaction_id: str | None = None
    event_id: str | None = None
    event_type: str | None = None


@dataclass(frozen=True, slots=True)
class ESignWebhookEvent:
    """Canonical e-sign event after provider payload normalization."""

    contract_id: str | None
    flow_id: str | None
    target_status: ContractStatus | None
    provider_status: str
    signed_date: date | None = None
    event_id: str | None = None
    event_type: str | None = None
