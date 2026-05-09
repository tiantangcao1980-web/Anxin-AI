#!/usr/bin/env python3
"""Validate release evidence artifact shape and redaction boundaries."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_ARTIFACT_DIR = Path("docs/release/evidence/artifacts")
SENSITIVE_VALUE_KEYS = {
    "access_token",
    "api_key",
    "api_v3_key",
    "app_secret",
    "authorization",
    "certificate",
    "id_card",
    "id_number",
    "identity_number",
    "jwt",
    "merchant_private_key",
    "password",
    "phone",
    "private_key",
    "refresh_token",
    "secret",
    "token",
}
REDACTED_VALUES = {"", "<redacted>", "redacted", "missing", "not_configured", "false", "true"}
RAW_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN ([A-Z ]+ )?PRIVATE KEY-----"),
    re.compile(r"\b1[3-9][0-9]{9}\b"),
    re.compile(r"\b[0-9]{17}[0-9Xx]\b"),
    re.compile(r"sk-[A-Za-z0-9_-]{24,}"),
)


@dataclass(frozen=True)
class ValidationResult:
    failures: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.failures


def normalized_key(key: str) -> str:
    return key.strip().lower().replace("-", "_")


def is_sensitive_value_key(key: str) -> bool:
    normalized = normalized_key(key)
    return normalized in SENSITIVE_VALUE_KEYS or normalized.endswith("_secret")


def is_redacted_value(value: str) -> bool:
    stripped = value.strip().lower()
    if stripped in REDACTED_VALUES:
        return True
    if "*" in stripped:
        return True
    if stripped.startswith("redacted_"):
        return True
    return False


def raw_secret_findings(path: str, value: str) -> list[str]:
    findings: list[str] = []
    for pattern in RAW_SECRET_PATTERNS:
        if pattern.search(value):
            findings.append(f"{path}: raw secret/PII-looking value")
    return findings


def _as_nonnegative_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)


def _truthy_override_names(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    return [str(key) for key, enabled in value.items() if bool(enabled)]


def _combined_note_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("completion_note", "note"):
        value = payload.get(key)
        if isinstance(value, str):
            parts.append(value)
    notes = payload.get("notes")
    if isinstance(notes, list):
        parts.extend(str(note) for note in notes)
    return " ".join(parts).lower()


def _validate_non_final_note(path: Path, payload: dict[str, Any], warnings: list[str]) -> None:
    mode = str(payload.get("mode", "")).lower()
    if mode != "preflight" and "preflight" not in mode and "code_smoke" not in mode:
        return
    note_text = _combined_note_text(payload)
    if not any(marker in note_text for marker in ("pending", "supporting evidence", "not final", "failure diagnostics", "not a live")):
        warnings.append(f"{path}: non-final artifact should clearly say it is not final release evidence")


def _validate_rag_commercial_provenance(path: Path, payload: dict[str, Any], failures: list[str]) -> None:
    mode = payload.get("mode")
    status = payload.get("status")
    requires_full50_provenance = mode == "live_qdrant_full50" or (
        mode == "full" and status == "live_predictions_export"
    )
    if not requires_full50_provenance:
        return

    provenance = payload.get("commercial_provenance")
    if not isinstance(provenance, dict):
        failures.append(f"{path}: RAG full50 live/metrics artifact missing commercial_provenance")
        return

    overrides = _truthy_override_names(provenance.get("non_commercial_overrides"))
    override_count = _as_nonnegative_int(provenance.get("non_commercial_override_count"))
    smoke_question_count = _as_nonnegative_int(provenance.get("smoke_question_count"))
    if overrides or override_count:
        details = ", ".join(sorted(set(overrides))) or f"count={override_count}"
        failures.append(f"{path}: RAG full50 artifact uses non-commercial overrides: {details}")
    if smoke_question_count:
        failures.append(f"{path}: RAG full50 artifact reports smoke_question_count={smoke_question_count}")

    if mode == "live_qdrant_full50":
        golden = payload.get("golden")
        predictions = payload.get("predictions")
        if not isinstance(golden, dict) or _as_nonnegative_int(golden.get("question_count")) < 50:
            failures.append(f"{path}: RAG live full50 artifact must report at least 50 golden questions")
        if not isinstance(predictions, list) or len(predictions) < 50:
            failures.append(f"{path}: RAG live full50 artifact must contain at least 50 predictions")
    elif mode == "full":
        summary = payload.get("summary")
        if not isinstance(summary, dict) or _as_nonnegative_int(summary.get("question_count")) < 50:
            failures.append(f"{path}: RAG full metrics artifact must report at least 50 questions")


def _validate_rag_failure_diagnostics(path: Path, payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("mode") != "rag_full50_preflight_failure":
        return
    if payload.get("status") != "failed":
        failures.append(f"{path}: RAG full50 failure diagnostic must have status=failed")

    error = payload.get("error")
    if not isinstance(error, dict):
        failures.append(f"{path}: RAG full50 failure diagnostic must include error object")
    else:
        for key in ("type", "message"):
            if not isinstance(error.get(key), str) or not error.get(key).strip():
                failures.append(f"{path}: RAG full50 failure diagnostic error.{key} must be non-empty")

    corpus = payload.get("corpus")
    if not isinstance(corpus, dict):
        failures.append(f"{path}: RAG full50 failure diagnostic must include corpus object")
    else:
        for key in ("path", "sha256"):
            if not isinstance(corpus.get(key), str) or not corpus.get(key).strip():
                failures.append(f"{path}: RAG full50 failure diagnostic corpus.{key} must be non-empty")
        for key in ("chunk_count", "available_chunk_count"):
            if not isinstance(corpus.get(key), int) or corpus.get(key) < 0:
                failures.append(f"{path}: RAG full50 failure diagnostic corpus.{key} must be a non-negative integer")

    golden = payload.get("golden")
    if not isinstance(golden, dict):
        failures.append(f"{path}: RAG full50 failure diagnostic must include golden object")
    else:
        for key in ("path", "sha256"):
            if not isinstance(golden.get(key), str) or not golden.get(key).strip():
                failures.append(f"{path}: RAG full50 failure diagnostic golden.{key} must be non-empty")
        for key in ("question_count", "min_questions", "smoke_question_count"):
            if not isinstance(golden.get(key), int) or golden.get(key) < 0:
                failures.append(f"{path}: RAG full50 failure diagnostic golden.{key} must be a non-negative integer")
        if _as_nonnegative_int(golden.get("min_questions")) < 50:
            failures.append(f"{path}: RAG full50 failure diagnostic golden.min_questions must be at least 50")
        if not isinstance(golden.get("smoke_question_sample"), list):
            failures.append(f"{path}: RAG full50 failure diagnostic golden.smoke_question_sample must be an array")

    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, dict):
        failures.append(f"{path}: RAG full50 failure diagnostic must include diagnostics object")
    else:
        for key in ("required_chunk_count", "missing_chunk_count"):
            if not isinstance(diagnostics.get(key), int) or diagnostics.get(key) < 0:
                failures.append(f"{path}: RAG full50 failure diagnostic diagnostics.{key} must be a non-negative integer")
        for key in ("missing_chunk_sample", "law_ref_gap_sample"):
            if not isinstance(diagnostics.get(key), list):
                failures.append(f"{path}: RAG full50 failure diagnostic diagnostics.{key} must be an array")

    provenance = payload.get("commercial_provenance")
    if not isinstance(provenance, dict):
        failures.append(f"{path}: RAG full50 failure diagnostic must include commercial_provenance")
    else:
        if provenance.get("artifact_kind") != "preflight_failure":
            failures.append(f"{path}: RAG full50 failure diagnostic commercial_provenance.artifact_kind must be preflight_failure")
        if provenance.get("commercial_baseline_candidate") is not False:
            failures.append(f"{path}: RAG full50 failure diagnostic must set commercial_baseline_candidate=false")

    note_text = _combined_note_text(payload)
    if "failure diagnostics" not in note_text or "pending" not in note_text:
        failures.append(f"{path}: RAG full50 failure diagnostic must clearly say release evidence remains pending")


def _validate_mobile_device_manual_template(path: Path, payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("mode") != "mobile_device_manual_template":
        return
    if payload.get("release_evidence_complete") is not False:
        failures.append(f"{path}: mobile manual template must set release_evidence_complete=false")
    if payload.get("status") != "template":
        failures.append(f"{path}: mobile manual template must have status=template")
    if payload.get("redaction_required") is not True:
        failures.append(f"{path}: mobile manual template must require redaction")

    platforms = payload.get("platforms")
    if not isinstance(platforms, list):
        failures.append(f"{path}: mobile manual template must include platforms")
        platforms = []
    platform_ids = {str(item.get("platform")) for item in platforms if isinstance(item, dict)}
    for required in ("ios", "android", "wechat_mini_program"):
        if required not in platform_ids:
            failures.append(f"{path}: mobile manual template missing platform {required}")
    for item in platforms:
        if not isinstance(item, dict):
            continue
        platform = item.get("platform")
        for metadata_key in (
            "device_model",
            "os_version",
            "build_hash",
            "backend_environment",
            "tester_role",
            "tested_at",
        ):
            if metadata_key not in item:
                failures.append(
                    f"{path}: mobile manual template platform {platform} must include {metadata_key}"
                )

    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list):
        failures.append(f"{path}: mobile manual template must include scenarios")
        scenarios = []
    scenario_ids = {str(item.get("id")) for item in scenarios if isinstance(item, dict)}
    for required in (
        "login",
        "approval_detail",
        "message_detail",
        "task_detail",
        "chat_continuation",
        "settings_error_state",
        "mini_program_wx_login_code2session",
        "mini_program_no_fake_fallback",
        "cross_device_continuation",
        "explicit_error_semantics",
    ):
        if required not in scenario_ids:
            failures.append(f"{path}: mobile manual template missing scenario {required}")
    for item in scenarios:
        if not isinstance(item, dict):
            continue
        if item.get("status") != "pending":
            failures.append(f"{path}: mobile manual template scenario {item.get('id')} must start pending")
        for ref_key in ("screenshot_refs", "log_refs"):
            if not isinstance(item.get(ref_key), list):
                failures.append(f"{path}: mobile manual template scenario {item.get('id')} must include {ref_key}")

    cross_device_result = payload.get("cross_device_result")
    if not isinstance(cross_device_result, dict):
        failures.append(f"{path}: mobile manual template must include cross_device_result")
    else:
        if cross_device_result.get("status") != "pending":
            failures.append(f"{path}: mobile manual template cross_device_result must start pending")
        for ref_key in ("web_session_ref", "desktop_session_ref", "mobile_session_ref"):
            if ref_key not in cross_device_result:
                failures.append(f"{path}: mobile manual template cross_device_result must include {ref_key}")


def _validate_mobile_mini_code_smoke(path: Path, payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("mode") != "mobile_mini_code_smoke":
        return
    if payload.get("release_evidence_complete") is not False:
        failures.append(f"{path}: mobile/mini code smoke must set release_evidence_complete=false")
    if payload.get("status") != "passed":
        failures.append(f"{path}: mobile/mini code smoke must have status=passed")

    checks = payload.get("checks")
    if not isinstance(checks, dict):
        failures.append(f"{path}: mobile/mini code smoke must include checks object")
        return
    required_checks = [
        "mobile_vitest",
        "mobile_typescript",
        "mobile_expo_config_guard",
        "mobile_expo_doctor",
        "mini_program_typescript",
        "mini_program_wechat_build",
        "mini_program_wechat_devtools_cli",
        "mobile_refresh_auth_guard",
        "mini_program_refresh_auth_guard",
        "fake_fallback_guard",
        "mini_program_design_token_guard",
    ]
    if str(payload.get("generated_at") or "")[:10] >= "2026-05-08":
        required_checks.extend(
            [
                "mobile_result_surface_guard",
                "mobile_lawyer_conversion_guard",
                "mobile_expo_metro_config",
            ]
        )
    for check_name in required_checks:
        if check_name == "mini_program_wechat_devtools_cli":
            if checks.get(check_name) not in {"passed", "external_unavailable"}:
                failures.append(
                    f"{path}: mobile/mini code smoke {check_name} must be passed or external_unavailable"
                )
            continue
        if checks.get(check_name) != "passed":
            failures.append(f"{path}: mobile/mini code smoke {check_name} must be passed")

    mobile_npm_audit = payload.get("mobile_npm_audit")
    if not isinstance(mobile_npm_audit, dict):
        failures.append(f"{path}: mobile/mini code smoke must include mobile_npm_audit")
        return
    status = mobile_npm_audit.get("status")
    if status not in {"passed", "residual_known"}:
        failures.append(f"{path}: mobile npm audit status must be passed or residual_known")
    if mobile_npm_audit.get("critical") != 0:
        failures.append(f"{path}: mobile npm audit must have zero critical vulnerabilities")
    if not isinstance(mobile_npm_audit.get("residual_vulnerabilities"), list):
        failures.append(f"{path}: mobile npm audit must list residual_vulnerabilities")
    else:
        residual = set(str(item) for item in mobile_npm_audit["residual_vulnerabilities"])
        if "@xmldom/xmldom" in residual or "@expo/plist" in residual:
            failures.append(f"{path}: mobile npm audit must not leave xmldom/plist residuals")
    try:
        total = int(mobile_npm_audit.get("total") or 0)
        high = int(mobile_npm_audit.get("high") or 0)
    except (TypeError, ValueError):
        failures.append(f"{path}: mobile npm audit total/high must be numeric")
        total = high = 999
    if total > 6 or high > 4:
        failures.append(f"{path}: mobile npm audit residual count regressed")
    if status == "passed" and total != 0:
        failures.append(f"{path}: mobile npm audit status=passed requires total=0")
    remediated = mobile_npm_audit.get("remediated_by_override")
    if not isinstance(remediated, list) or "@xmldom/xmldom@0.8.13" not in remediated:
        failures.append(f"{path}: mobile npm audit must record xmldom override remediation")
    if status == "passed":
        required_remediations = {
            "@expo/cli -> tar@7.5.14",
            "@expo/metro-config -> postcss@8.5.14",
            "cacache -> tar@7.5.14",
        }
        missing = required_remediations.difference(set(str(item) for item in remediated))
        if missing:
            failures.append(
                f"{path}: mobile npm audit passed artifact must record Expo toolchain overrides"
            )


def _validate_uni_mobile_base_smoke(path: Path, payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("mode") != "uni_mobile_base_smoke":
        return
    if payload.get("release_evidence_complete") is not False:
        failures.append(f"{path}: uni-mobile base smoke must set release_evidence_complete=false")
    if payload.get("status") != "passed":
        failures.append(f"{path}: uni-mobile base smoke must have status=passed")

    checks = payload.get("checks")
    if not isinstance(checks, dict):
        failures.append(f"{path}: uni-mobile base smoke must include checks object")
        return
    for check_name in (
        "typecheck",
        "contract_tests",
        "production_npm_audit",
        "build_h5",
        "build_mp_weixin",
    ):
        if checks.get(check_name) != "passed":
            failures.append(f"{path}: uni-mobile base smoke {check_name} must be passed")

    scope = payload.get("scope")
    if not isinstance(scope, dict):
        failures.append(f"{path}: uni-mobile base smoke must include scope")
    else:
        if scope.get("base") != "apps/uni-mobile":
            failures.append(f"{path}: uni-mobile base smoke scope.base must be apps/uni-mobile")


def _validate_agent_governance_code_smoke(path: Path, payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("mode") != "agent_governance_code_smoke":
        return
    if payload.get("release_evidence_complete") is not False:
        failures.append(f"{path}: agent governance code smoke must set release_evidence_complete=false")
    if payload.get("runtime_evidence_complete") is not False:
        failures.append(f"{path}: agent governance code smoke must set runtime_evidence_complete=false")
    if payload.get("status") != "passed":
        failures.append(f"{path}: agent governance code smoke must have status=passed")

    checks = payload.get("checks")
    if not isinstance(checks, dict):
        failures.append(f"{path}: agent governance code smoke must include checks object")
        return
    for check_name in (
        "governance_docs_scan",
        "agent_capability_policy",
        "backend_governance_regressions",
        "approval_authorization_guard",
        "mcp_connection_config_policy",
        "desktop_remote_control_host",
        "frontend_agent_workspace_e2e",
    ):
        if checks.get(check_name) != "passed":
            failures.append(f"{path}: agent governance code smoke {check_name} must be passed")

    scope = payload.get("scope")
    if not isinstance(scope, dict):
        failures.append(f"{path}: agent governance code smoke must include scope")
    elif scope.get("enterprise_agent_governance") != "code_level":
        failures.append(
            f"{path}: agent governance code smoke scope.enterprise_agent_governance must be code_level"
        )

    pending_runtime_evidence = payload.get("pending_runtime_evidence")
    if not isinstance(pending_runtime_evidence, list) or not pending_runtime_evidence:
        failures.append(f"{path}: agent governance code smoke must list pending_runtime_evidence")
    else:
        pending = {str(item) for item in pending_runtime_evidence}
        required_pending = {
            "approved_connector_rehearsal",
            "real_cross_process_revocation",
            "pause_takeover_terminate_runtime",
            "signed_packaged_runtime_outbound_evidence",
        }
        missing = required_pending.difference(pending)
        if missing:
            failures.append(
                f"{path}: agent governance code smoke missing pending runtime evidence markers"
            )


def _validate_mobile_ios_simulator_smoke(path: Path, payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("mode") != "mobile_ios_simulator_expo_go_smoke":
        return
    if payload.get("release_evidence_complete") is not False:
        failures.append(f"{path}: iOS simulator smoke must set release_evidence_complete=false")
    if payload.get("status") != "passed":
        failures.append(f"{path}: iOS simulator smoke must have status=passed")

    device = payload.get("device")
    if not isinstance(device, dict):
        failures.append(f"{path}: iOS simulator smoke must include device object")
    else:
        if device.get("platform") != "ios_simulator":
            failures.append(f"{path}: iOS simulator smoke device.platform must be ios_simulator")
        for key in ("name", "udid"):
            if not isinstance(device.get(key), str) or not device.get(key).strip():
                failures.append(f"{path}: iOS simulator smoke device.{key} must be non-empty")

    checks = payload.get("checks")
    if not isinstance(checks, dict):
        failures.append(f"{path}: iOS simulator smoke must include checks object")
    else:
        for check_name in (
            "simulator_boot",
            "expo_asset_resolvable",
            "expo_metro_config",
            "ios_bundle",
        ):
            if checks.get(check_name) != "passed":
                failures.append(f"{path}: iOS simulator smoke {check_name} must be passed")
        if checks.get("expo_go_container") not in {"present", "installed"}:
            failures.append(f"{path}: iOS simulator smoke expo_go_container must be present")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict) or not isinstance(artifacts.get("log"), str) or not artifacts.get("log", "").strip():
        failures.append(f"{path}: iOS simulator smoke must include artifacts.log")
    transcript_excerpt = payload.get("transcript_excerpt")
    if not isinstance(transcript_excerpt, list) or not any("iOS Bundled" in str(line) for line in transcript_excerpt):
        failures.append(f"{path}: iOS simulator smoke transcript must include iOS Bundled")

    note_text = _combined_note_text(payload)
    if "supporting" not in note_text or "pending" not in note_text or "real-device" not in note_text:
        failures.append(
            f"{path}: iOS simulator smoke must clearly say real-device release evidence remains pending"
        )


def _validate_desktop_installed_profile_smoke(path: Path, payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("mode") != "desktop_installed_profile_smoke":
        return
    if payload.get("release_evidence_complete") is not False:
        failures.append(f"{path}: desktop installed-profile smoke must set release_evidence_complete=false")
    if payload.get("status") != "passed":
        failures.append(f"{path}: desktop installed-profile smoke must have status=passed")

    required_fields = (
        "keyringRoundTrip",
        "encryptedReopen",
        "plaintextBackupPresent",
        "plaintextOpenBlocked",
    )
    for launch_key in ("firstLaunch", "secondLaunch"):
        launch = payload.get(launch_key)
        if not isinstance(launch, dict):
            failures.append(f"{path}: desktop installed-profile smoke missing {launch_key}")
            continue
        for field in required_fields:
            if launch.get(field) is not True:
                failures.append(f"{path}: desktop installed-profile smoke {launch_key}.{field} must be true")


def _validate_desktop_runtime_code_smoke(path: Path, payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("mode") != "desktop_runtime_code_smoke":
        return
    if payload.get("release_evidence_complete") is not False:
        failures.append(f"{path}: desktop runtime code smoke must set release_evidence_complete=false")
    if payload.get("status") != "passed":
        failures.append(f"{path}: desktop runtime code smoke must have status=passed")

    checks = payload.get("checks")
    if not isinstance(checks, dict):
        failures.append(f"{path}: desktop runtime code smoke missing checks")
        return

    for check_name in (
        "frontend_desktop_sync_vitest",
        "desktop_cargo_test",
        "desktop_cargo_check",
        "sqlite_migration_sql_smoke",
        "tauri_debug_build",
        "debug_binary_or_bundle_self_test",
        "debug_app_bundle_runtime_startup",
        "debug_app_bundle_ui_load",
    ):
        if checks.get(check_name) != "passed":
            failures.append(f"{path}: desktop runtime code smoke {check_name} must be passed")

    performance = checks.get("sqlite_sync_performance_smoke")
    if not isinstance(performance, dict):
        failures.append(f"{path}: desktop runtime code smoke missing sqlite_sync_performance_smoke")
        return
    if performance.get("status") != "passed":
        failures.append(f"{path}: desktop runtime code smoke sqlite_sync_performance_smoke.status must be passed")
    push_p95 = performance.get("push_100_rows_p95_ms")
    pull_p95 = performance.get("pull_500_rows_p95_ms")
    push_threshold = performance.get("push_threshold_ms")
    pull_threshold = performance.get("pull_threshold_ms")
    if not isinstance(push_p95, (int, float)) or not isinstance(push_threshold, (int, float)) or push_p95 >= push_threshold:
        failures.append(f"{path}: desktop runtime code smoke push P95 must be below threshold")
    if not isinstance(pull_p95, (int, float)) or not isinstance(pull_threshold, (int, float)) or pull_p95 >= pull_threshold:
        failures.append(f"{path}: desktop runtime code smoke pull P95 must be below threshold")


def _validate_desktop_release_runtime_unsigned_smoke(
    path: Path, payload: dict[str, Any], failures: list[str]
) -> None:
    if payload.get("mode") != "desktop_release_runtime_unsigned_smoke":
        return
    if payload.get("release_evidence_complete") is not False:
        failures.append(f"{path}: desktop unsigned release runtime smoke must set release_evidence_complete=false")
    if payload.get("signed_or_notarized") is not False:
        failures.append(f"{path}: desktop unsigned release runtime smoke must set signed_or_notarized=false")
    if payload.get("status") != "passed":
        failures.append(f"{path}: desktop unsigned release runtime smoke must have status=passed")

    checks = payload.get("checks")
    if not isinstance(checks, dict):
        failures.append(f"{path}: desktop unsigned release runtime smoke missing checks")
        return
    for check_name in (
        "release_app_exists",
        "release_dmg_exists",
        "release_binary_self_test",
        "release_runtime_startup",
        "release_webview_ui_load",
    ):
        if checks.get(check_name) != "passed":
            failures.append(f"{path}: desktop unsigned release runtime smoke {check_name} must be passed")

    sqlite_security = checks.get("sqlite_security")
    if not isinstance(sqlite_security, dict):
        failures.append(f"{path}: desktop unsigned release runtime smoke missing sqlite_security")
    else:
        if sqlite_security.get("status") != "passed":
            failures.append(f"{path}: desktop unsigned release runtime smoke sqlite_security.status must be passed")
        if sqlite_security.get("encrypted") is not True:
            failures.append(f"{path}: desktop unsigned release runtime smoke sqlite_security.encrypted must be true")
        if sqlite_security.get("keyring_backed") is not True:
            failures.append(f"{path}: desktop unsigned release runtime smoke sqlite_security.keyring_backed must be true")
        if sqlite_security.get("release_blocking") is not False:
            failures.append(f"{path}: desktop unsigned release runtime smoke sqlite_security.release_blocking must be false")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        failures.append(f"{path}: desktop unsigned release runtime smoke missing artifacts")
        return
    for key in ("release_app", "release_binary", "release_dmg", "ui_log"):
        value = artifacts.get(key)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{path}: desktop unsigned release runtime smoke artifacts.{key} must be non-empty")

    note_text = _combined_note_text(payload)
    if "supporting evidence" not in note_text or "signed/notarized" not in note_text:
        failures.append(
            f"{path}: desktop unsigned release runtime smoke must clearly say signed/notarized evidence remains pending"
        )


def _validate_desktop_release_packaged_profile_smoke(
    path: Path, payload: dict[str, Any], failures: list[str]
) -> None:
    if payload.get("mode") != "desktop_release_packaged_profile_smoke":
        return
    if payload.get("release_evidence_complete") is not False:
        failures.append(
            f"{path}: desktop release packaged-profile smoke must set release_evidence_complete=false"
        )
    if payload.get("signed_or_notarized") is not False:
        failures.append(
            f"{path}: desktop release packaged-profile smoke must set signed_or_notarized=false"
        )
    if payload.get("status") != "passed":
        failures.append(f"{path}: desktop release packaged-profile smoke must have status=passed")

    checks = payload.get("checks")
    if not isinstance(checks, dict):
        failures.append(f"{path}: desktop release packaged-profile smoke missing checks")
    else:
        for check_name in (
            "release_app_exists",
            "release_binary_exists",
            "plaintext_profile_seeded",
            "first_launch_plaintext_to_sqlcipher_migration",
            "second_launch_keyring_reopen",
            "release_sqlcipher_performance",
            "ordinary_sqlite_plaintext_read_blocked",
        ):
            if checks.get(check_name) != "passed":
                failures.append(
                    f"{path}: desktop release packaged-profile smoke {check_name} must be passed"
                )

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        failures.append(f"{path}: desktop release packaged-profile smoke missing artifacts")
    else:
        for key in ("release_app", "release_binary"):
            value = artifacts.get(key)
            if not isinstance(value, str) or not value.strip():
                failures.append(
                    f"{path}: desktop release packaged-profile smoke artifacts.{key} must be non-empty"
                )

    required_fields = (
        "keyringRoundTrip",
        "encryptedReopen",
        "plaintextBackupPresent",
        "plaintextOpenBlocked",
    )
    for launch_key in ("firstLaunch", "secondLaunch"):
        launch = payload.get(launch_key)
        if not isinstance(launch, dict):
            failures.append(f"{path}: desktop release packaged-profile smoke missing {launch_key}")
            continue
        for field in required_fields:
            if launch.get(field) is not True:
                failures.append(
                    f"{path}: desktop release packaged-profile smoke {launch_key}.{field} must be true"
                )

    performance = payload.get("performance")
    if not isinstance(performance, dict):
        failures.append(f"{path}: desktop release packaged-profile smoke missing performance")
    else:
        if performance.get("status") != "passed":
            failures.append(f"{path}: desktop release packaged-profile smoke performance.status must be passed")
        for field in ("keyringRoundTrip", "encryptedReopen"):
            if performance.get(field) is not True:
                failures.append(
                    f"{path}: desktop release packaged-profile smoke performance.{field} must be true"
                )
        push_p95 = performance.get("push100RowsP95Ms")
        pull_p95 = performance.get("pull500RowsP95Ms")
        push_threshold = performance.get("pushThresholdMs")
        pull_threshold = performance.get("pullThresholdMs")
        if (
            not isinstance(push_p95, (int, float))
            or not isinstance(push_threshold, (int, float))
            or push_p95 >= push_threshold
        ):
            failures.append(f"{path}: desktop release packaged-profile smoke push P95 must be below threshold")
        if (
            not isinstance(pull_p95, (int, float))
            or not isinstance(pull_threshold, (int, float))
            or pull_p95 >= pull_threshold
        ):
            failures.append(f"{path}: desktop release packaged-profile smoke pull P95 must be below threshold")

    note_text = _combined_note_text(payload)
    if "supporting evidence" not in note_text or "signed/notarized" not in note_text:
        failures.append(
            f"{path}: desktop release packaged-profile smoke must clearly say signed/notarized evidence remains pending"
        )


def _validate_desktop_release_preflight(path: Path, payload: dict[str, Any], failures: list[str]) -> None:
    inputs = payload.get("inputs")
    if payload.get("mode") != "preflight" or not isinstance(inputs, dict):
        return
    desktop_input_keys = {
        "release_app",
        "debug_app",
        "installed_profile_report",
        "runtime_transcript",
        "runtime_structured_artifact",
    }
    if not desktop_input_keys.issubset(inputs):
        return

    if not isinstance(payload.get("release_ready"), bool):
        failures.append(f"{path}: desktop release preflight must include boolean release_ready")
    blockers = payload.get("release_blockers")
    if not isinstance(blockers, list) or not all(isinstance(item, str) and item for item in blockers):
        failures.append(f"{path}: desktop release preflight must include release_blockers string array")
        blockers = []

    for key in desktop_input_keys:
        value = inputs.get(key)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{path}: desktop release preflight inputs.{key} must be a non-empty path")
            continue
        if key in {"installed_profile_report", "runtime_transcript", "runtime_structured_artifact"}:
            candidate = Path(value)
            if not candidate.is_absolute() and not candidate.exists():
                failures.append(f"{path}: desktop release preflight inputs.{key} does not exist: {value}")

    checks = payload.get("checks")
    if not isinstance(checks, list):
        failures.append(f"{path}: desktop release preflight must include checks array")
        return

    required_check_ids = {
        "platform",
        "command.xcodebuild",
        "command.xcrun",
        "command.codesign",
        "command.security",
        "command.spctl",
        "command.hdiutil",
        "dmg.hdiutil_create_probe",
        "tauri.signing_identity",
        "tauri.entitlements",
        "tauri.entitlements.aps_environment",
        "codesign.identities",
        "notary.credentials",
        "notary.tool",
        "stapler.tool",
        "release.app.exists",
        "release.dmg.exists",
        "support.debug_app.exists",
        "support.debug_runtime_transcript",
        "support.installed_profile_report",
    }
    checks_by_id: dict[str, dict[str, Any]] = {}
    for check in checks:
        if not isinstance(check, dict):
            failures.append(f"{path}: desktop release preflight checks must be objects")
            continue
        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id:
            failures.append(f"{path}: desktop release preflight check missing id")
            continue
        checks_by_id[check_id] = check
        if check.get("status") not in {"pass", "warn", "fail"}:
            failures.append(f"{path}: desktop release preflight check {check_id} has invalid status")
        if not isinstance(check.get("release_blocking"), bool):
            failures.append(f"{path}: desktop release preflight check {check_id} missing release_blocking boolean")

    for check_id in sorted(required_check_ids - checks_by_id.keys()):
        failures.append(f"{path}: desktop release preflight missing check {check_id}")

    blocking_failures = sorted(
        check_id
        for check_id, check in checks_by_id.items()
        if check.get("release_blocking") is True and check.get("status") != "pass"
    )
    if sorted(blockers) != blocking_failures:
        failures.append(f"{path}: desktop release preflight release_blockers must match failing release-blocking checks")
    if payload.get("release_ready") is True and blocking_failures:
        failures.append(f"{path}: desktop release preflight cannot be release_ready=true with blocking failures")
    if payload.get("release_ready") is False and not blocking_failures:
        failures.append(f"{path}: desktop release preflight release_ready=false must list blocking failures")

    for support_check_id in (
        "support.debug_runtime_transcript",
        "support.installed_profile_report",
    ):
        if checks_by_id.get(support_check_id, {}).get("status") != "pass":
            failures.append(f"{path}: desktop release preflight {support_check_id} must be pass")


def _validate_desktop_release_package(path: Path, payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("mode") != "desktop_release_package":
        return
    if payload.get("release_evidence_complete") is not False:
        failures.append(f"{path}: desktop release package artifact must set release_evidence_complete=false")
    if payload.get("status") not in {"dry_run", "blocked", "ready", "built", "failed", "packaged_preflight_passed"}:
        failures.append(f"{path}: desktop release package artifact has invalid status")
    if not isinstance(payload.get("release_ready"), bool):
        failures.append(f"{path}: desktop release package artifact must include boolean release_ready")

    inputs = payload.get("inputs")
    if not isinstance(inputs, dict):
        failures.append(f"{path}: desktop release package artifact must include inputs")
    else:
        for key in ("dry_run", "skip_build", "skip_stapling", "signing_identity_configured"):
            if not isinstance(inputs.get(key), bool):
                failures.append(f"{path}: desktop release package inputs.{key} must be boolean")
        if not isinstance(inputs.get("bundles"), str) or "app" not in inputs.get("bundles", ""):
            failures.append(f"{path}: desktop release package inputs.bundles must include app")

    checks = payload.get("checks")
    if not isinstance(checks, list):
        failures.append(f"{path}: desktop release package artifact must include checks")
        return
    checks_by_id: dict[str, dict[str, Any]] = {}
    for check in checks:
        if not isinstance(check, dict):
            failures.append(f"{path}: desktop release package checks must be objects")
            continue
        check_id = check.get("id")
        if isinstance(check_id, str) and check_id:
            checks_by_id[check_id] = check
        else:
            failures.append(f"{path}: desktop release package check missing id")
        if check.get("status") not in {"pass", "fail"}:
            failures.append(f"{path}: desktop release package check {check_id} has invalid status")
        if not isinstance(check.get("release_blocking"), bool):
            failures.append(f"{path}: desktop release package check {check_id} missing release_blocking boolean")

    required_check_ids = {
        "platform",
        "command.cargo",
        "command.xcrun",
        "command.codesign",
        "command.hdiutil",
        "dmg.hdiutil_create_probe",
        "signing.identity",
        "notary.credentials",
        "entitlements.aps_environment",
    }
    for check_id in sorted(required_check_ids - checks_by_id.keys()):
        failures.append(f"{path}: desktop release package missing check {check_id}")

    blockers = payload.get("release_blockers")
    if not isinstance(blockers, list) or not all(isinstance(item, str) and item for item in blockers):
        failures.append(f"{path}: desktop release package artifact must include release_blockers string array")
        blockers = []
    failed_local_blockers = {
        check_id
        for check_id, check in checks_by_id.items()
        if check.get("release_blocking") is True and check.get("status") != "pass"
    }
    missing_local_blockers = failed_local_blockers - set(blockers)
    for blocker in sorted(missing_local_blockers):
        failures.append(f"{path}: desktop release package release_blockers missing local blocker {blocker}")
    if payload.get("release_ready") is True and blockers:
        failures.append(f"{path}: desktop release package cannot be release_ready=true with blockers")

    preflight_artifact = payload.get("preflight_artifact")
    if preflight_artifact is not None:
        if not isinstance(preflight_artifact, str) or not preflight_artifact.strip():
            failures.append(f"{path}: desktop release package preflight_artifact must be a non-empty string or null")
        elif not Path(preflight_artifact).exists():
            failures.append(f"{path}: desktop release package preflight_artifact does not exist: {preflight_artifact}")


SANDBOX_SCOPE_PROVIDERS = {
    "payment": {"wechat_pay", "alipay"},
    "esign": {"esignbao", "fadada"},
    "all": {"wechat_pay", "alipay", "esignbao", "fadada"},
    "wechat_pay": {"wechat_pay"},
    "alipay": {"alipay"},
    "esignbao": {"esignbao"},
    "fadada": {"fadada"},
}
SANDBOX_PROVIDER_RUNTIME_ARGS = {
    "wechat_pay": {"--wechat-refund-order-id"},
    "alipay": {"--alipay-query-order-id", "--alipay-refund-order-id", "--alipay-close-order-id"},
    "esignbao": {"--esign-document-url", "--esignbao-completed-flow-id"},
    "fadada": {"--esign-document-url", "--fadada-completed-flow-id"},
}
SANDBOX_PROVIDER_EXTERNAL_EVIDENCE = {
    "wechat_pay": {
        "official_success_callback",
        "duplicate_callback_idempotency",
        "failed_callback_retry",
        "platform_key_rotation",
    },
    "alipay": {
        "official_success_notification",
        "duplicate_notification_idempotency",
        "failed_notification_retry",
    },
    "esignbao": {
        "official_callback",
        "duplicate_callback_idempotency",
        "failed_callback_retry",
    },
    "fadada": {
        "official_callback",
        "duplicate_callback_idempotency",
        "failed_callback_retry",
    },
}


def _validate_sandbox_external_evidence_requirements(
    path: Path,
    provider: str,
    provider_payload: dict[str, Any],
    failures: list[str],
) -> None:
    requirements = provider_payload.get("external_evidence_requirements")
    if not isinstance(requirements, list):
        failures.append(f"{path}: sandbox provider {provider} must include external_evidence_requirements")
        return

    requirement_ids: set[str] = set()
    for requirement in requirements:
        if not isinstance(requirement, dict):
            failures.append(f"{path}: sandbox provider {provider} external evidence requirements must be objects")
            continue
        requirement_id = requirement.get("id")
        if isinstance(requirement_id, str) and requirement_id:
            requirement_ids.add(requirement_id)
        else:
            failures.append(f"{path}: sandbox provider {provider} external evidence requirement missing id")
        for key in ("label", "status", "artifact_ref", "collection_method"):
            if not isinstance(requirement.get(key), str) or not requirement.get(key).strip():
                failures.append(f"{path}: sandbox provider {provider} external evidence requirement missing {key}")
        if requirement.get("release_blocking") is not True:
            failures.append(
                f"{path}: sandbox provider {provider} external evidence requirement must be release_blocking=true"
            )
        if requirement.get("status") not in {"pending_external_input", "pending_collection", "ready", "complete"}:
            failures.append(
                f"{path}: sandbox provider {provider} external evidence requirement has invalid status"
            )

    for requirement_id in sorted(SANDBOX_PROVIDER_EXTERNAL_EVIDENCE[provider] - requirement_ids):
        failures.append(f"{path}: sandbox provider {provider} missing external evidence requirement {requirement_id}")


def _validate_sandbox_preflight(path: Path, payload: dict[str, Any], failures: list[str]) -> None:
    selected_scope = payload.get("selected_scope")
    if payload.get("mode") != "preflight" or selected_scope not in SANDBOX_SCOPE_PROVIDERS:
        return
    if payload.get("environment") != "staging/sandbox":
        failures.append(f"{path}: sandbox preflight must have environment=staging/sandbox")
    if not isinstance(payload.get("loaded_env_files"), list):
        failures.append(f"{path}: sandbox preflight must include loaded_env_files")
    if not isinstance(payload.get("live_checks"), dict):
        failures.append(f"{path}: sandbox preflight must include live_checks object")

    providers = payload.get("providers")
    if not isinstance(providers, dict):
        failures.append(f"{path}: sandbox preflight must include providers object")
        return

    expected_providers = SANDBOX_SCOPE_PROVIDERS[str(selected_scope)]
    for provider in sorted(expected_providers):
        provider_payload = providers.get(provider)
        if not isinstance(provider_payload, dict):
            failures.append(f"{path}: sandbox preflight missing provider {provider}")
            continue
        if not isinstance(provider_payload.get("configured"), bool):
            failures.append(f"{path}: sandbox preflight provider {provider}.configured must be boolean")
        fields = provider_payload.get("fields")
        if not isinstance(fields, list) or not fields:
            failures.append(f"{path}: sandbox preflight provider {provider} must include fields")
        else:
            field_names: set[str] = set()
            for field in fields:
                if not isinstance(field, dict):
                    failures.append(f"{path}: sandbox preflight provider {provider} fields must be objects")
                    continue
                for key in ("label", "name", "redacted"):
                    if not isinstance(field.get(key), str) or not field.get(key):
                        failures.append(f"{path}: sandbox preflight provider {provider} field missing {key}")
                if not isinstance(field.get("present"), bool):
                    failures.append(f"{path}: sandbox preflight provider {provider} field present must be boolean")
                if isinstance(field.get("name"), str):
                    field_names.add(field["name"])
            if not field_names:
                failures.append(f"{path}: sandbox preflight provider {provider} must report at least one field name")

        missing = provider_payload.get("missing")
        if not isinstance(missing, list):
            failures.append(f"{path}: sandbox preflight provider {provider}.missing must be an array")
        elif provider_payload.get("configured") is True and missing:
            failures.append(f"{path}: sandbox preflight provider {provider} is configured but still lists missing fields")
        elif provider_payload.get("configured") is False and not missing:
            failures.append(f"{path}: sandbox preflight provider {provider} is not configured but lists no missing fields")

        runtime_prerequisites = provider_payload.get("runtime_prerequisites")
        if not isinstance(runtime_prerequisites, list):
            failures.append(f"{path}: sandbox preflight provider {provider} must include runtime_prerequisites")
            continue
        runtime_args: set[str] = set()
        for prereq in runtime_prerequisites:
            if not isinstance(prereq, dict):
                failures.append(f"{path}: sandbox preflight provider {provider} runtime_prerequisites must be objects")
                continue
            argument = prereq.get("argument")
            if isinstance(argument, str) and argument:
                runtime_args.add(argument)
            else:
                failures.append(f"{path}: sandbox preflight provider {provider} runtime prerequisite missing argument")
            for key in ("label", "note", "status"):
                if not isinstance(prereq.get(key), str) or not prereq.get(key):
                    failures.append(f"{path}: sandbox preflight provider {provider} runtime prerequisite missing {key}")
            if not isinstance(prereq.get("present"), bool):
                failures.append(f"{path}: sandbox preflight provider {provider} runtime prerequisite present must be boolean")
            if prereq.get("status") not in {"ready", "present", "missing"}:
                failures.append(
                    f"{path}: sandbox preflight provider {provider} runtime prerequisite status "
                    "must be ready/present or missing"
                )
        for argument in sorted(SANDBOX_PROVIDER_RUNTIME_ARGS[provider] - runtime_args):
            failures.append(f"{path}: sandbox preflight provider {provider} missing runtime prerequisite {argument}")
        _validate_sandbox_external_evidence_requirements(path, provider, provider_payload, failures)


def _validate_sandbox_live(path: Path, payload: dict[str, Any], failures: list[str]) -> None:
    selected_scope = payload.get("selected_scope")
    if payload.get("mode") != "live" or selected_scope not in SANDBOX_SCOPE_PROVIDERS:
        return
    if payload.get("environment") != "staging/sandbox":
        failures.append(f"{path}: sandbox live artifact must have environment=staging/sandbox")

    providers = payload.get("providers")
    if not isinstance(providers, dict):
        failures.append(f"{path}: sandbox live artifact must include providers object")
        return

    live_checks = payload.get("live_checks")
    if not isinstance(live_checks, dict):
        failures.append(f"{path}: sandbox live artifact must include live_checks object")
        live_checks = {}

    expected_providers = SANDBOX_SCOPE_PROVIDERS[str(selected_scope)]
    for provider in sorted(expected_providers):
        provider_payload = providers.get(provider)
        if not isinstance(provider_payload, dict):
            failures.append(f"{path}: sandbox live artifact missing provider {provider}")
            continue
        if provider_payload.get("configured") is not True:
            failures.append(f"{path}: sandbox live artifact provider {provider} must be configured=true")
        _validate_sandbox_external_evidence_requirements(path, provider, provider_payload, failures)
        missing = provider_payload.get("missing")
        if not isinstance(missing, list):
            failures.append(f"{path}: sandbox live artifact provider {provider}.missing must be an array")
        elif missing:
            failures.append(f"{path}: sandbox live artifact provider {provider} must not list missing fields")

        runtime_prerequisites = provider_payload.get("runtime_prerequisites")
        if not isinstance(runtime_prerequisites, list):
            failures.append(f"{path}: sandbox live artifact provider {provider} must include runtime_prerequisites")
        else:
            runtime_args: set[str] = set()
            for prereq in runtime_prerequisites:
                if not isinstance(prereq, dict):
                    failures.append(f"{path}: sandbox live artifact provider {provider} runtime_prerequisites must be objects")
                    continue
                argument = prereq.get("argument")
                if isinstance(argument, str) and argument:
                    runtime_args.add(argument)
                else:
                    failures.append(f"{path}: sandbox live artifact provider {provider} runtime prerequisite missing argument")
                if prereq.get("present") is not True:
                    failures.append(
                        f"{path}: sandbox live artifact provider {provider} runtime prerequisite "
                        f"{argument} must be present"
                    )
                if prereq.get("status") not in {"ready", "present"}:
                    failures.append(
                        f"{path}: sandbox live artifact provider {provider} runtime prerequisite "
                        f"{argument} must be ready"
                    )
            for argument in sorted(SANDBOX_PROVIDER_RUNTIME_ARGS[provider] - runtime_args):
                failures.append(f"{path}: sandbox live artifact provider {provider} missing runtime prerequisite {argument}")

        checks = live_checks.get(provider)
        if not isinstance(checks, list) or not checks:
            failures.append(f"{path}: sandbox live artifact provider {provider} must include non-empty live_checks")
            continue
        for check in checks:
            if not isinstance(check, dict):
                failures.append(f"{path}: sandbox live artifact provider {provider} live_checks must be objects")
                continue
            if not isinstance(check.get("step"), str) or not check.get("step"):
                failures.append(f"{path}: sandbox live artifact provider {provider} live check missing step")
            if check.get("status") != "pass":
                failures.append(
                    f"{path}: sandbox live artifact provider {provider} live check "
                    f"{check.get('step')} must be pass"
                )


def iter_json_values(value: Any, path: str = "$") -> list[tuple[str, str, str]]:
    values: list[tuple[str, str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if isinstance(child, str):
                values.append((child_path, key, child))
            values.extend(iter_json_values(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            values.extend(iter_json_values(child, f"{path}[{index}]"))
    return values


def validate_json_artifact(path: Path) -> ValidationResult:
    failures: list[str] = []
    warnings: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return ValidationResult(
            failures=(f"{path}: invalid JSON at line {exc.lineno}: {exc.msg}",),
            warnings=(),
        )

    if not isinstance(payload, dict):
        return ValidationResult(
            failures=(f"{path}: artifact JSON must be an object",),
            warnings=(),
        )

    generated_at = payload.get("generated_at")
    if not isinstance(generated_at, str) or not generated_at.strip():
        failures.append(f"{path}: missing generated_at")

    if not any(isinstance(payload.get(key), str) and payload.get(key).strip() for key in ("mode", "type", "artifact_type")):
        failures.append(f"{path}: missing mode/type/artifact_type")

    _validate_non_final_note(path, payload, warnings)
    _validate_rag_commercial_provenance(path, payload, failures)
    _validate_rag_failure_diagnostics(path, payload, failures)
    _validate_mobile_device_manual_template(path, payload, failures)
    _validate_mobile_mini_code_smoke(path, payload, failures)
    _validate_uni_mobile_base_smoke(path, payload, failures)
    _validate_agent_governance_code_smoke(path, payload, failures)
    _validate_mobile_ios_simulator_smoke(path, payload, failures)
    _validate_desktop_installed_profile_smoke(path, payload, failures)
    _validate_desktop_runtime_code_smoke(path, payload, failures)
    _validate_desktop_release_runtime_unsigned_smoke(path, payload, failures)
    _validate_desktop_release_packaged_profile_smoke(path, payload, failures)
    _validate_desktop_release_preflight(path, payload, failures)
    _validate_desktop_release_package(path, payload, failures)
    _validate_sandbox_preflight(path, payload, failures)
    _validate_sandbox_live(path, payload, failures)

    for value_path, key, value in iter_json_values(payload):
        failures.extend(raw_secret_findings(value_path, value))
        if is_sensitive_value_key(key) and not is_redacted_value(value):
            failures.append(f"{path}: {value_path} must be redacted or omitted")

    return ValidationResult(failures=tuple(failures), warnings=tuple(warnings))


def artifact_paths(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if not target.exists():
        return []
    return sorted(path for path in target.glob("*.json") if path.is_file())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target",
        nargs="?",
        default=str(DEFAULT_ARTIFACT_DIR),
        help="JSON artifact file or artifact directory",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON summary")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = Path(args.target)
    paths = artifact_paths(target)
    failures: list[str] = []
    warnings: list[str] = []

    if target.exists() and not paths:
        failures.append(f"{target}: no JSON artifacts found")

    for path in paths:
        result = validate_json_artifact(path)
        failures.extend(result.failures)
        warnings.extend(result.warnings)

    if args.json:
        print(
            json.dumps(
                {
                    "ok": not failures,
                    "checked": [str(path) for path in paths],
                    "failures": failures,
                    "warnings": warnings,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1 if failures else 0

    for warning in warnings:
        print(f"WARN: {warning}")
    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        return 1
    print(f"Release evidence artifact validation: PASS ({len(paths)} JSON artifacts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
