"""E-sign webhook business writeback helpers."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit import AuditAction, ResourceType
from src.models.contract import Contract, ContractStatus
from src.services.audit_service import AuditService
from src.services.contract_lifecycle_service import (
    ContractLifecycleStateMachine,
    IllegalStateTransition,
)
from src.services.webhook_events import ESignWebhookEvent


class ESignWebhookError(ValueError):
    """Raised when an e-sign webhook cannot be applied safely."""


_CONTRACT_ID_KEYS = (
    "contract_id",
    "contractId",
    "contract_no",
    "contractNo",
    "business_id",
    "businessId",
    "biz_id",
    "bizId",
    "transReferenceId",
)
_FLOW_ID_KEYS = (
    "flow_id",
    "flowId",
    "sign_flow_id",
    "signFlowId",
    "flowNo",
    "flow_no",
    "signTaskId",
    "taskId",
)
_STATE_KEYS = (
    "status",
    "flow_status",
    "flowStatus",
    "action",
    "event",
    "event_type",
    "eventType",
    "action_type",
    "actionType",
    "signResult",
    "signTaskStatus",
    "taskStatus",
    "eventStatus",
)
_DATE_KEYS = (
    "signed_at",
    "signedAt",
    "completed_at",
    "completedAt",
    "finish_time",
    "finishTime",
    "sign_time",
    "signTime",
    "eventTime",
)

_SIGNED_STATES = {
    "2",
    "all_signed",
    "complete",
    "completed",
    "done",
    "finish",
    "finished",
    "flow_finish",
    "sign_completed",
    "signed",
    "success",
    "sign_flow_finish",
    "sign_flow_finished",
    "sign_flow_complete",
    "sign_flow_completed",
    "sign_flow_archive",
    "sign_task_signed",
    "sign_task_completed",
    "sign_task_finished",
    "task_finished",
}
_TERMINATED_STATES = {
    "3",
    "cancel",
    "cancelled",
    "canceled",
    "closed",
    "declined",
    "expired",
    "failed",
    "failure",
    "reject",
    "rejected",
    "refused",
    "terminated",
    "abolished",
    "revoked",
    "sign_flow_cancel",
    "sign_flow_revoke",
    "sign_flow_terminate",
    "sign_task_cancel",
    "sign_task_abolish",
    "sign_task_rejected",
}
_IN_PROGRESS_STATES = {
    "created",
    "pending",
    "process",
    "processing",
    "signing",
    "started",
    "signer_signed",
    "signer_read",
    "sign_task_started",
}


def _candidate_dicts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [payload]
    for key in ("extra", "data", "event", "payload", "resource"):
        value = payload.get(key)
        if isinstance(value, dict):
            candidates.append(value)
    return candidates


def _first_string(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for source in _candidate_dicts(payload):
        for key in keys:
            value = source.get(key)
            if value is not None:
                text = str(value).strip()
                if text:
                    return text
    return None


def _parse_signed_date(payload: dict[str, Any]) -> date:
    raw = _first_string(payload, _DATE_KEYS)
    if not raw:
        return date.today()
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return date.today()


def _extract_event_id(payload: dict[str, Any]) -> str | None:
    return _first_string(
        payload,
        (
            "event_id",
            "eventId",
            "notify_id",
            "notifyId",
            "eventTime",
            "id",
        ),
    )


def _extract_event_type(payload: dict[str, Any]) -> str | None:
    return _first_string(
        payload,
        (
            "event_type",
            "eventType",
            "event",
            "action",
            "action_type",
            "actionType",
            "status",
            "X-FASC-Event",
            "signTaskStatus",
            "signResult",
        ),
    )


def _map_contract_status(payload: dict[str, Any]) -> tuple[ContractStatus | None, str]:
    state = (_first_string(payload, _STATE_KEYS) or "").lower()
    normalized = state.replace("-", "_").replace(" ", "_")
    if normalized in _SIGNED_STATES:
        return ContractStatus.SIGNED, normalized
    if normalized in _TERMINATED_STATES:
        return ContractStatus.TERMINATED, normalized
    if normalized in _IN_PROGRESS_STATES:
        return None, normalized
    raise ESignWebhookError(f"Unsupported e-sign webhook status: {state or '<missing>'}")


def parse_esign_webhook_event(payload: dict[str, Any]) -> ESignWebhookEvent:
    """Normalize a verified provider payload into a stable e-sign event."""

    contract_id = _first_string(payload, _CONTRACT_ID_KEYS)
    flow_id = _first_string(payload, _FLOW_ID_KEYS)
    if not contract_id and not flow_id:
        raise ESignWebhookError("Missing contract_id or flow_id in e-sign webhook")

    target_status, provider_status = _map_contract_status(payload)
    signed_date = _parse_signed_date(payload) if target_status == ContractStatus.SIGNED else None
    return ESignWebhookEvent(
        contract_id=contract_id,
        flow_id=flow_id,
        target_status=target_status,
        provider_status=provider_status,
        signed_date=signed_date,
        event_id=_extract_event_id(payload),
        event_type=_extract_event_type(payload),
    )


async def apply_esign_webhook(
    db: AsyncSession,
    *,
    payload: dict[str, Any],
    event: ESignWebhookEvent | None = None,
) -> dict[str, Any]:
    """Apply a verified e-sign webhook to the local contract when possible."""

    event = event or parse_esign_webhook_event(payload)
    contract_id = event.contract_id
    flow_id = event.flow_id

    if contract_id:
        result = await db.execute(select(Contract).where(Contract.id == contract_id))
    else:
        result = await db.execute(select(Contract).where(Contract.esign_flow_id == flow_id))
    contract = result.scalar_one_or_none()
    if contract is None:
        identifier = contract_id or flow_id
        raise ESignWebhookError(f"Contract not found for e-sign webhook: {identifier}")
    if flow_id and contract.esign_flow_id and contract.esign_flow_id != flow_id:
        raise ESignWebhookError("E-sign webhook flow_id does not match contract mapping")
    if flow_id and contract.esign_flow_id is None:
        contract.esign_flow_id = flow_id

    next_status = event.target_status
    if next_status is None:
        return {
            "contract_id": contract.id,
            "flow_id": contract.esign_flow_id,
            "status": (
                contract.status.value
                if isinstance(contract.status, ContractStatus)
                else contract.status
            ),
            "provider_status": event.provider_status,
            "updated": False,
        }

    try:
        ContractLifecycleStateMachine.transition(
            contract,
            next_status,
            actor_id="esign_webhook",
            reason=event.provider_status,
        )
    except IllegalStateTransition as exc:
        raise ESignWebhookError(str(exc)) from exc

    if next_status == ContractStatus.SIGNED and contract.sign_date is None:
        contract.sign_date = event.signed_date or date.today()

    await AuditService(db).log(
        action=(
            AuditAction.CONTRACT_SIGN.value
            if next_status == ContractStatus.SIGNED
            else AuditAction.CONTRACT_STATUS_CHANGE.value
        ),
        resource_type=ResourceType.CONTRACT.value,
        resource_id=contract.id,
        user=None,
        old_value={"status": event.provider_status},
        new_value={
            "status": next_status.value,
            "flow_id": contract.esign_flow_id,
            "event_id": event.event_id,
            "event_type": event.event_type,
            "archive_requested": next_status == ContractStatus.SIGNED,
        },
        extra_data={
            "source": "esign_webhook",
            "provider_status": event.provider_status,
            "flow_id": contract.esign_flow_id,
        },
    )

    await db.flush()
    return {
        "contract_id": contract.id,
        "flow_id": contract.esign_flow_id,
        "status": next_status.value,
        "provider_status": event.provider_status,
        "updated": True,
    }
