#!/usr/bin/env python3
"""Preflight and optional live probes for payment/e-sign release evidence.

The default mode is intentionally read-only: it checks configuration and emits
redacted JSON. Use --live plus --confirm-live-side-effects only when sandbox or
pre-production merchant accounts are available and the side effects are desired.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))


def _load_env_files() -> list[str]:
    loaded: list[str] = []
    try:
        from dotenv import load_dotenv
    except Exception:
        return loaded

    for path in (PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"):
        if path.exists():
            load_dotenv(path, override=False)
            loaded.append(str(path.relative_to(PROJECT_ROOT)))
    return loaded


LOADED_ENV_FILES = _load_env_files()

from src.core.config import settings  # noqa: E402


SECRET_MARKERS = (
    "SECRET",
    "PRIVATE_KEY",
    "API_V3_KEY",
    "ACCESS_TOKEN",
    "WEBHOOK_SECRET",
)
PLACEHOLDER_MARKERS = (
    "your-",
    "change-in-production",
    "change-in-prod",
    "placeholder",
    "example",
    "mock",
    "tbd",
    "<",
)


@dataclass(frozen=True)
class Requirement:
    label: str
    names: tuple[str, ...]
    any_of: bool = False
    secret: bool = False
    must_be_true: bool = False
    path_group: bool = False


REQUIREMENTS: dict[str, list[Requirement]] = {
    "wechat_pay": [
        Requirement("public callback base URL", ("PAYMENT_NOTIFY_BASE_URL",)),
        Requirement("app ID", ("WECHAT_PAY_APP_ID",)),
        Requirement("merchant ID", ("WECHAT_PAY_MCH_ID",)),
        Requirement("merchant serial number", ("WECHAT_PAY_MERCHANT_SERIAL_NO",)),
        Requirement(
            "merchant private key",
            ("WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH", "WECHAT_PAY_MERCHANT_PRIVATE_KEY"),
            any_of=True,
            secret=True,
            path_group=True,
        ),
        Requirement("platform serial", ("WECHAT_PAY_PLATFORM_SERIAL",)),
        Requirement(
            "platform public key",
            ("WECHAT_PAY_PLATFORM_PUBLIC_KEY_PATH", "WECHAT_PAY_PLATFORM_PUBLIC_KEY"),
            any_of=True,
            path_group=True,
        ),
        Requirement("API v3 key for official callback decrypt", ("WECHAT_PAY_API_V3_KEY",), secret=True),
        Requirement("official webhook enabled", ("WECHAT_PAY_OFFICIAL_WEBHOOK_ENABLED",), must_be_true=True),
    ],
    "alipay": [
        Requirement("public callback base URL", ("PAYMENT_NOTIFY_BASE_URL",)),
        Requirement("app ID", ("ALIPAY_APP_ID",)),
        Requirement(
            "app private key",
            ("ALIPAY_PRIVATE_KEY_PATH", "ALIPAY_PRIVATE_KEY"),
            any_of=True,
            secret=True,
            path_group=True,
        ),
        Requirement(
            "Alipay public key",
            ("ALIPAY_PUBLIC_KEY_PATH", "ALIPAY_PUBLIC_KEY"),
            any_of=True,
            path_group=True,
        ),
        Requirement("gateway URL", ("ALIPAY_GATEWAY_URL",)),
        Requirement("official webhook enabled", ("ALIPAY_OFFICIAL_WEBHOOK_ENABLED",), must_be_true=True),
    ],
    "esignbao": [
        Requirement("app ID", ("ESIGN_BAO_APP_ID",)),
        Requirement("app secret", ("ESIGN_BAO_APP_SECRET",), secret=True),
        Requirement("API URL", ("ESIGN_BAO_API_URL",)),
        Requirement("official webhook enabled", ("ESIGN_OFFICIAL_WEBHOOK_ENABLED",), must_be_true=True),
    ],
    "fadada": [
        Requirement("app ID", ("FADADA_APP_ID",)),
        Requirement("app secret", ("FADADA_APP_SECRET",), secret=True),
        Requirement("API URL", ("FADADA_API_URL",)),
        Requirement("official webhook enabled", ("ESIGN_OFFICIAL_WEBHOOK_ENABLED",), must_be_true=True),
    ],
}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _setting_value(name: str) -> Any:
    if name in os.environ and os.environ[name] != "":
        return os.environ[name]
    return getattr(settings, name, None)


def _is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    if not text:
        return True
    lowered = text.lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def _path_exists(value: Any) -> bool:
    if value is None:
        return False
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.is_file() and path.stat().st_size > 0


def _value_present(name: str, *, must_be_true: bool = False) -> bool:
    value = _setting_value(name)
    if must_be_true:
        return value is True or str(value).strip().lower() in {"1", "true", "yes", "on"}
    if name.endswith("_PATH"):
        return bool(value) and _path_exists(value)
    return not _is_placeholder(value)


def _is_secret_name(name: str) -> bool:
    return any(marker in name for marker in SECRET_MARKERS)


def _redact_identifier(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= 8:
        return "***"
    return f"{text[:4]}...{text[-4:]}"


def _redact_url(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parts = urlsplit(text)
    except ValueError:
        return _redact_identifier(text)
    if not parts.scheme or not parts.netloc:
        return _redact_identifier(text)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _redacted_value(name: str) -> str:
    value = _setting_value(name)
    if value is None or value == "":
        return "missing"
    if name.endswith("_PATH"):
        exists = _path_exists(value)
        return f"path:{Path(str(value)).name}:exists={str(exists).lower()}"
    if _is_secret_name(name):
        return "set"
    if name.endswith("_URL") or name in {"PAYMENT_NOTIFY_BASE_URL", "ALIPAY_GATEWAY_URL"}:
        return _redact_url(value)
    if isinstance(value, bool):
        return str(value).lower()
    return _redact_identifier(value)


def _sanitize_text(text: str, *, limit: int = 800) -> str:
    sanitized = text
    for name in {name for reqs in REQUIREMENTS.values() for req in reqs for name in req.names}:
        value = _setting_value(name)
        if value and len(str(value)) >= 6:
            sanitized = sanitized.replace(str(value), f"<redacted:{name}>")
    sanitized = sanitized.replace("\n", " ")
    if len(sanitized) > limit:
        return sanitized[:limit] + "...<truncated>"
    return sanitized


def _safe_payload(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _safe_payload(value.model_dump(mode="json"))
    if isinstance(value, bytes):
        return {
            "byte_length": len(value),
            "sha256_12": hashlib.sha256(value).hexdigest()[:12],
        }
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if "url" in lowered:
                if isinstance(item, dict):
                    safe[key] = {k: _redact_url(v) for k, v in item.items()}
                else:
                    safe[key] = _redact_url(item)
            elif "id" in lowered or "no" in lowered or "token" in lowered:
                safe[key] = _redact_identifier(item)
            elif "key" in lowered or "secret" in lowered or "sign" in lowered:
                safe[key] = "set" if item else "missing"
            else:
                safe[key] = _safe_payload(item)
        return safe
    if isinstance(value, list):
        return [_safe_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_safe_payload(item) for item in value]
    return value


def _provider_requirement_status(provider: str) -> dict[str, Any]:
    fields = []
    missing = []
    warnings = []
    for requirement in REQUIREMENTS[provider]:
        statuses = [
            _value_present(name, must_be_true=requirement.must_be_true)
            for name in requirement.names
        ]
        satisfied = any(statuses) if requirement.any_of else all(statuses)
        if not satisfied:
            missing.append(requirement.label)
        for name, present in zip(requirement.names, statuses, strict=True):
            value = _setting_value(name)
            if name.endswith("_PATH") and value and not _path_exists(value):
                warnings.append(f"{name} points to a missing or empty file")
            fields.append(
                {
                    "name": name,
                    "label": requirement.label,
                    "present": present,
                    "redacted": _redacted_value(name),
                }
            )
    return {
        "configured": not missing,
        "missing": missing,
        "warnings": warnings,
        "fields": fields,
    }


def _runtime_prerequisites(args: argparse.Namespace, provider: str) -> list[dict[str, Any]]:
    prerequisites_by_provider = {
        "wechat_pay": [
            (
                "paid sandbox order ID for refund evidence",
                "--wechat-refund-order-id",
                bool(args.wechat_refund_order_id),
                "Required to exercise the paid-order refund branch.",
            ),
        ],
        "alipay": [
            (
                "existing sandbox order ID for query evidence",
                "--alipay-query-order-id",
                bool(args.alipay_query_order_id),
                "Required to exercise the Alipay query branch.",
            ),
            (
                "paid sandbox order ID for refund evidence",
                "--alipay-refund-order-id",
                bool(args.alipay_refund_order_id),
                "Required to exercise the Alipay refund branch.",
            ),
            (
                "open sandbox order ID for close evidence",
                "--alipay-close-order-id",
                bool(args.alipay_close_order_id),
                "Required to exercise the Alipay close branch.",
            ),
        ],
        "esignbao": [
            (
                "sandbox document URL or file ID",
                "--esign-document-url",
                bool(args.esign_document_url),
                "Required to create/start a signing flow.",
            ),
            (
                "completed sandbox flow ID for download evidence",
                "--esignbao-completed-flow-id",
                bool(args.esignbao_completed_flow_id),
                "Required to exercise completed signed document download.",
            ),
        ],
        "fadada": [
            (
                "sandbox document URL or file ID",
                "--esign-document-url",
                bool(args.esign_document_url),
                "Required to create/start a signing flow.",
            ),
            (
                "completed sandbox flow ID for download evidence",
                "--fadada-completed-flow-id",
                bool(args.fadada_completed_flow_id),
                "Required to exercise completed signed document download.",
            ),
        ],
    }
    return [
        {
            "label": label,
            "argument": argument,
            "present": present,
            "status": "ready" if present else "missing",
            "note": note,
        }
        for label, argument, present, note in prerequisites_by_provider[provider]
    ]


def _external_evidence_requirements(provider: str) -> list[dict[str, Any]]:
    """Release evidence that cannot be proven by local provider API probes alone."""
    common_callback_note = (
        "Attach a redacted provider dashboard or delivery-log artifact after the "
        "official sandbox callback is delivered to the configured public endpoint."
    )
    requirements_by_provider = {
        "wechat_pay": [
            (
                "official_success_callback",
                "Official payment success callback verifies RSA-SHA256 signature and decrypts resource.",
                common_callback_note,
            ),
            (
                "duplicate_callback_idempotency",
                "Duplicate payment notification is idempotent and does not create duplicate business effects.",
                "Attach the redacted callback replay/delivery transcript and backend idempotency/audit log reference.",
            ),
            (
                "failed_callback_retry",
                "Failed callback enters retry or failed path without fake success.",
                "Attach retry worker or provider retry transcript with secrets and PII redacted.",
            ),
            (
                "platform_key_rotation",
                "Platform certificate/public-key rotation or refresh path is verified.",
                "Attach the redacted platform-key/certificate refresh proof from the provider console or key cache.",
            ),
        ],
        "alipay": [
            (
                "official_success_notification",
                "Official payment success notification verifies Alipay RSA2 signature.",
                common_callback_note,
            ),
            (
                "duplicate_notification_idempotency",
                "Duplicate payment notification is idempotent and does not create duplicate business effects.",
                "Attach the redacted callback replay/delivery transcript and backend idempotency/audit log reference.",
            ),
            (
                "failed_notification_retry",
                "Failed notification enters retry or failed path without fake success.",
                "Attach retry worker or provider retry transcript with secrets and PII redacted.",
            ),
        ],
        "esignbao": [
            (
                "official_callback",
                "Official e签宝 callback verifies headers/body and writes audit.",
                common_callback_note,
            ),
            (
                "duplicate_callback_idempotency",
                "Duplicate e签宝 callback is idempotent and does not duplicate flow state transitions.",
                "Attach the redacted callback replay/delivery transcript and backend idempotency/audit log reference.",
            ),
            (
                "failed_callback_retry",
                "Failed e签宝 callback enters retry or failed path without fake success.",
                "Attach retry worker or provider retry transcript with secrets and PII redacted.",
            ),
        ],
        "fadada": [
            (
                "official_callback",
                "Official 法大大 callback verifies headers/body and writes audit.",
                common_callback_note,
            ),
            (
                "duplicate_callback_idempotency",
                "Duplicate 法大大 callback is idempotent and does not duplicate flow state transitions.",
                "Attach the redacted callback replay/delivery transcript and backend idempotency/audit log reference.",
            ),
            (
                "failed_callback_retry",
                "Failed 法大大 callback enters retry or failed path without fake success.",
                "Attach retry worker or provider retry transcript with secrets and PII redacted.",
            ),
        ],
    }
    return [
        {
            "id": requirement_id,
            "label": label,
            "status": "pending_external_input",
            "release_blocking": True,
            "artifact_ref": "TBD",
            "collection_method": note,
        }
        for requirement_id, label, note in requirements_by_provider[provider]
    ]


def _selected_providers(scope: str) -> list[str]:
    mapping = {
        "all": ["wechat_pay", "alipay", "esignbao", "fadada"],
        "payment": ["wechat_pay", "alipay"],
        "esign": ["esignbao", "fadada"],
        "wechat_pay": ["wechat_pay"],
        "alipay": ["alipay"],
        "esignbao": ["esignbao"],
        "fadada": ["fadada"],
    }
    return mapping[scope]


async def _capture_step(label: str, func, validator=None) -> dict[str, Any]:
    started_at = _utc_now()
    try:
        result = await func()
        step = {
            "step": label,
            "status": "pass",
            "started_at": started_at,
            "completed_at": _utc_now(),
            "details": _safe_payload(result),
        }
        if validator is not None:
            validation_status, reason = validator(result)
            step["status"] = validation_status
            if reason:
                step["reason"] = reason
        return step
    except Exception as exc:
        return {
            "step": label,
            "status": "fail",
            "started_at": started_at,
            "completed_at": _utc_now(),
            "error": _sanitize_text(f"{exc.__class__.__name__}: {exc}"),
        }


def _validate_boolean_result(result: Any, *, action: str) -> tuple[str, str | None]:
    if result is True:
        return "pass", None
    if result is False:
        return (
            "pending",
            f"{action} returned false; collect the provider's documented terminal-state evidence before marking complete.",
        )
    return "pass", None


def _validate_refund_result(result: Any) -> tuple[str, str | None]:
    normalized = str(getattr(result, "status", "") or "").strip().lower()
    if normalized == "success":
        return "pass", None
    if normalized == "pending":
        return (
            "pending",
            "Refund request was accepted but the provider has not reported terminal success yet; collect async callback or dashboard confirmation.",
        )
    return "fail", f"Provider returned non-success refund status: {normalized or '<missing>'}"


def _validate_sign_flow_creation(result: Any) -> tuple[str, str | None]:
    sign_urls = getattr(result, "sign_urls", None)
    if isinstance(sign_urls, dict) and sign_urls:
        return "pass", None
    return (
        "pending",
        "Signing flow was created but no signer URL was returned; keep release evidence pending until the signer URL branch succeeds.",
    )


def _validate_download_content(result: Any) -> tuple[str, str | None]:
    if isinstance(result, bytes) and result:
        return "pass", None
    return "fail", "Downloaded signed document is empty."


async def _run_payment_live(args: argparse.Namespace, provider: str) -> list[dict[str, Any]]:
    from src.services.payment_service import AlipayProvider, WeChatPayProvider

    checks: list[dict[str, Any]] = []
    if provider == "wechat_pay":
        client = WeChatPayProvider()
        order_id = args.order_id or str(uuid.uuid4())
        checks.append(
            await _capture_step(
                "wechat native order creation",
                lambda: client.create_order(
                    order_id=order_id,
                    amount=args.amount,
                    description=args.description,
                    notify_url=args.wechat_notify_url,
                ),
            )
        )
        checks.append(
            await _capture_step(
                "wechat query order",
                lambda: client.query_order(order_id),
            )
        )
        checks.append(
            await _capture_step(
                "wechat close order",
                lambda: client.close_order(order_id),
                validator=lambda result: _validate_boolean_result(result, action="close order"),
            )
        )
        if args.wechat_refund_order_id:
            checks.append(
                await _capture_step(
                    "wechat refund paid order",
                    lambda: client.refund(
                        order_id=args.wechat_refund_order_id,
                        amount=args.refund_amount,
                        reason=args.refund_reason,
                        total_amount=args.refund_total_amount,
                    ),
                    validator=_validate_refund_result,
                )
            )
        else:
            checks.append(
                {
                    "step": "wechat refund paid order",
                    "status": "skipped",
                    "reason": "provide --wechat-refund-order-id and amount options after a paid sandbox order exists",
                }
            )
    elif provider == "alipay":
        client = AlipayProvider()
        order_id = args.order_id or str(uuid.uuid4())
        checks.append(
            await _capture_step(
                "alipay page.pay signed URL creation",
                lambda: client.create_order(
                    order_id=order_id,
                    amount=args.amount,
                    description=args.description,
                    notify_url=args.alipay_notify_url,
                ),
            )
        )
        if args.alipay_query_order_id:
            checks.append(
                await _capture_step(
                    "alipay query order",
                    lambda: client.query_order(args.alipay_query_order_id),
                )
            )
        else:
            checks.append({"step": "alipay query order", "status": "skipped", "reason": "provide --alipay-query-order-id"})
        if args.alipay_refund_order_id:
            checks.append(
                await _capture_step(
                    "alipay refund paid order",
                    lambda: client.refund(
                        order_id=args.alipay_refund_order_id,
                        amount=args.refund_amount,
                        reason=args.refund_reason,
                    ),
                    validator=_validate_refund_result,
                )
            )
        else:
            checks.append({"step": "alipay refund paid order", "status": "skipped", "reason": "provide --alipay-refund-order-id"})
        if args.alipay_close_order_id:
            checks.append(
                await _capture_step(
                    "alipay close order",
                    lambda: client.close_order(args.alipay_close_order_id),
                    validator=lambda result: _validate_boolean_result(result, action="close order"),
                )
            )
        else:
            checks.append({"step": "alipay close order", "status": "skipped", "reason": "provide --alipay-close-order-id"})
    return checks


async def _run_esign_live(args: argparse.Namespace, provider: str) -> list[dict[str, Any]]:
    from src.services.esign_service import ESignBaoProvider, FaDaDaProvider, SignerInfo, SignType

    if not args.esign_document_url:
        return [
            {
                "step": f"{provider} create flow",
                "status": "skipped",
                "reason": "provide --esign-document-url for live e-sign flow creation",
            }
        ]

    signer = SignerInfo(
        signer_id=args.signer_id,
        name=args.signer_name,
        mobile=args.signer_mobile,
        email=args.signer_email,
        sign_type=SignType.PERSONAL,
    )
    client = ESignBaoProvider() if provider == "esignbao" else FaDaDaProvider()
    contract_id = args.contract_id or f"sandbox-{uuid.uuid4().hex[:12]}"
    created_flow_id: str | None = None

    async def create_flow():
        nonlocal created_flow_id
        result = await client.create_sign_flow(
            contract_id=contract_id,
            title=args.esign_title,
            signers=[signer],
            document_url=args.esign_document_url,
            expire_hours=args.esign_expire_hours,
        )
        created_flow_id = result.flow_id
        return result

    checks = [
        await _capture_step(
            f"{provider} create/start/get sign URL",
            create_flow,
            validator=_validate_sign_flow_creation,
        )
    ]
    if created_flow_id:
        checks.append(
            await _capture_step(
                f"{provider} query flow status",
                lambda: client.get_flow_status(created_flow_id),
            )
        )
        if not args.skip_cancel:
            checks.append(
                await _capture_step(
                    f"{provider} cancel flow",
                    lambda: client.cancel_flow(created_flow_id, "sandbox evidence cleanup"),
                    validator=lambda result: _validate_boolean_result(result, action="cancel flow"),
                )
            )

    completed_flow_id = args.esignbao_completed_flow_id if provider == "esignbao" else args.fadada_completed_flow_id
    if completed_flow_id:
        checks.append(
            await _capture_step(
                f"{provider} download completed signed document",
                lambda: client.download_signed_doc(completed_flow_id),
                validator=_validate_download_content,
            )
        )
    else:
        checks.append(
            {
                "step": f"{provider} download completed signed document",
                "status": "skipped",
                "reason": f"provide --{provider.replace('_', '-')}-completed-flow-id after a completed sandbox flow exists",
            }
        )
    return checks


def _build_report(args: argparse.Namespace) -> dict[str, Any]:
    providers = _selected_providers(args.scope)
    report = {
        "generated_at": _utc_now(),
        "mode": "live" if args.live else "preflight",
        "environment": args.environment,
        "loaded_env_files": LOADED_ENV_FILES,
        "selected_scope": args.scope,
        "providers": {
            provider: {
                **_provider_requirement_status(provider),
                "runtime_prerequisites": _runtime_prerequisites(args, provider),
                "external_evidence_requirements": _external_evidence_requirements(provider),
            }
            for provider in providers
        },
        "live_checks": {},
        "completion_note": (
            "This artifact is supporting evidence only. Keep release evidence Status: pending "
            "until provider dashboards/logs, callback events, retry evidence, and redacted artifacts "
            "cover every row in docs/release/evidence/payment-sandbox.md and esign-sandbox.md."
        ),
    }
    return report


async def _run_live_checks(args: argparse.Namespace, report: dict[str, Any]) -> None:
    for provider in report["providers"]:
        if not report["providers"][provider]["configured"]:
            report["live_checks"][provider] = [
                {
                    "step": "configuration",
                    "status": "skipped",
                    "reason": "provider configuration is incomplete",
                }
            ]
            continue
        if provider in {"wechat_pay", "alipay"}:
            report["live_checks"][provider] = await _run_payment_live(args, provider)
        else:
            report["live_checks"][provider] = await _run_esign_live(args, provider)


def _write_or_print(report: dict[str, Any], out: str | None) -> None:
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if out:
        path = Path(out)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote redacted sandbox evidence artifact: {path}")
    else:
        print(text)


def _print_summary(report: dict[str, Any]) -> None:
    print("Sandbox evidence runner summary:")
    for provider, status in report["providers"].items():
        configured = "configured" if status["configured"] else "missing config"
        print(f"  - {provider}: {configured}")
        for missing in status["missing"]:
            print(f"    missing: {missing}")
        for warning in status["warnings"]:
            print(f"    warning: {warning}")
    if report["mode"] != "live":
        print("  live checks: not run; pass --live --confirm-live-side-effects to call provider sandboxes")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scope",
        choices=["all", "payment", "esign", "wechat_pay", "alipay", "esignbao", "fadada"],
        default="all",
        help="Provider group to preflight or probe.",
    )
    parser.add_argument("--environment", default=os.getenv("SANDBOX_EVIDENCE_ENVIRONMENT", "staging/sandbox"))
    parser.add_argument("--out", help="Write redacted JSON artifact to this path. Defaults to stdout.")
    parser.add_argument("--live", action="store_true", help="Call real sandbox/pre-production providers.")
    parser.add_argument(
        "--confirm-live-side-effects",
        action="store_true",
        help="Required with --live. Provider calls may create orders or signing flows.",
    )
    parser.add_argument("--amount", type=float, default=0.01, help="Small sandbox payment amount.")
    parser.add_argument("--order-id", help="Override generated payment order ID.")
    parser.add_argument("--description", default="Anxin sandbox evidence probe")
    parser.add_argument("--wechat-notify-url", default="/api/v1/payments/webhook/wechat")
    parser.add_argument("--alipay-notify-url", default="/api/v1/payments/webhook/alipay")
    parser.add_argument("--wechat-refund-order-id")
    parser.add_argument("--refund-amount", type=float, default=0.01)
    parser.add_argument("--refund-total-amount", type=float)
    parser.add_argument("--refund-reason", default="sandbox evidence refund")
    parser.add_argument("--alipay-query-order-id")
    parser.add_argument("--alipay-refund-order-id")
    parser.add_argument("--alipay-close-order-id")
    parser.add_argument("--contract-id")
    parser.add_argument("--esign-title", default="Anxin sandbox evidence contract")
    parser.add_argument("--esign-document-url")
    parser.add_argument("--esign-expire-hours", type=int, default=72)
    parser.add_argument("--signer-id", default="sandbox-signer")
    parser.add_argument("--signer-name", default=os.getenv("SANDBOX_SIGNER_NAME", "Sandbox Signer"))
    parser.add_argument("--signer-mobile", default=os.getenv("SANDBOX_SIGNER_MOBILE"))
    parser.add_argument("--signer-email", default=os.getenv("SANDBOX_SIGNER_EMAIL"))
    parser.add_argument("--skip-cancel", action="store_true")
    parser.add_argument("--esignbao-completed-flow-id")
    parser.add_argument("--fadada-completed-flow-id")
    args = parser.parse_args()
    if args.live and not args.confirm_live_side_effects:
        parser.error("--live requires --confirm-live-side-effects")
    return args


async def _main() -> int:
    args = _parse_args()
    report = _build_report(args)
    if args.live:
        await _run_live_checks(args, report)
    _write_or_print(report, args.out)
    _print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
