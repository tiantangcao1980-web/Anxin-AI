import json
import subprocess
from pathlib import Path


def _validate(repo_root: Path, target: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = ["python3", str(repo_root / "scripts" / "validate-release-artifacts.py")]
    if target is not None:
        command.append(str(target))
    return subprocess.run(
        command,
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def test_release_artifact_validation_accepts_current_artifacts():
    repo_root = Path(__file__).resolve().parents[2]

    result = _validate(repo_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_release_artifact_validation_rejects_missing_shape(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "bad.json"
    artifact.write_text(json.dumps({"mode": "preflight"}), encoding="utf-8")

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "missing generated_at" in result.stdout


def test_release_artifact_validation_rejects_raw_sensitive_values(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "bad-secret.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "live",
                "access_token": "live_token_value_that_should_fail",
                "signer_phone": "13800138000",
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "access_token" in result.stdout
    assert "raw secret/PII-looking value" in result.stdout


def test_release_artifact_validation_warns_for_non_final_artifact_without_note(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "rag-preflight.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "rag_full50_preflight",
                "status": "passed",
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 0
    assert "non-final artifact should clearly say it is not final release evidence" in result.stdout


def test_release_artifact_validation_rejects_rag_live_without_provenance(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "rag-live.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "live_qdrant_full50",
                "golden": {"question_count": 50},
                "predictions": [{"question_id": f"Q-{index:04d}"} for index in range(50)],
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "missing commercial_provenance" in result.stdout


def test_release_artifact_validation_rejects_rag_metrics_with_overrides(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "rag-metrics.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "full",
                "status": "live_predictions_export",
                "commercial_provenance": {
                    "non_commercial_overrides": {"allow_smoke_golden": True},
                    "non_commercial_override_count": 1,
                    "smoke_question_count": 0,
                },
                "summary": {"question_count": 50},
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "non-commercial overrides" in result.stdout


def _rag_failure_diagnostic() -> dict:
    return {
        "generated_at": "2026-05-07T00:00:00Z",
        "run_label": "rag-live-qdrant-full50",
        "mode": "rag_full50_preflight_failure",
        "status": "failed",
        "error": {
            "type": "ValueError",
            "message": "Corpus looks like a fixture/smoke/demo export.",
        },
        "corpus": {
            "path": "eval/citation_documents_smoke.json",
            "sha256": "0" * 64,
            "chunk_count": 3,
            "available_chunk_count": 3,
        },
        "golden": {
            "path": "eval/rag_golden_set.jsonl",
            "sha256": "1" * 64,
            "question_count": 50,
            "min_questions": 50,
            "smoke_question_count": 10,
            "smoke_question_sample": ["Q-0001"],
        },
        "diagnostics": {
            "required_chunk_count": 60,
            "missing_chunk_count": 57,
            "missing_chunk_sample": ["civil_code_490_0"],
            "law_ref_gap_sample": [{"question_id": "Q-0001", "missing_law_refs": "民法典:第490条"}],
        },
        "commercial_provenance": {
            "artifact_kind": "preflight_failure",
            "commercial_baseline_candidate": False,
            "non_commercial_overrides": {"allow_fixture_corpus": True},
            "non_commercial_override_count": 1,
            "smoke_question_count": 10,
        },
        "completion_note": (
            "Failure diagnostics only. Keep release evidence Status: pending until "
            "commercial golden/corpus coverage and live Qdrant metrics pass."
        ),
    }


def test_release_artifact_validation_accepts_rag_failure_diagnostic(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "rag-full50-preflight-failure.json"
    artifact.write_text(json.dumps(_rag_failure_diagnostic()), encoding="utf-8")

    result = _validate(repo_root, artifact)

    assert result.returncode == 0, result.stdout


def test_release_artifact_validation_rejects_incomplete_rag_failure_diagnostic(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "rag-full50-preflight-failure-bad.json"
    payload = _rag_failure_diagnostic()
    payload["status"] = "passed"
    payload["error"] = {}
    payload["golden"]["min_questions"] = 10
    payload["diagnostics"]["missing_chunk_sample"] = "civil_code_490_0"
    payload["commercial_provenance"]["commercial_baseline_candidate"] = True
    payload["completion_note"] = "Complete."
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "status=failed" in result.stdout
    assert "error.type must be non-empty" in result.stdout
    assert "golden.min_questions must be at least 50" in result.stdout
    assert "diagnostics.missing_chunk_sample must be an array" in result.stdout
    assert "commercial_baseline_candidate=false" in result.stdout
    assert "release evidence remains pending" in result.stdout


def test_release_artifact_validation_accepts_mobile_manual_template(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "mobile-template.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "mobile_device_manual_template",
                "status": "template",
                "release_evidence_complete": False,
                "redaction_required": True,
                "platforms": [
                    {
                        "platform": "ios",
                        "device_model": "",
                        "os_version": "",
                        "build_hash": "",
                        "backend_environment": "",
                        "tester_role": "",
                        "tested_at": "",
                    },
                    {
                        "platform": "android",
                        "device_model": "",
                        "os_version": "",
                        "build_hash": "",
                        "backend_environment": "",
                        "tester_role": "",
                        "tested_at": "",
                    },
                    {
                        "platform": "wechat_mini_program",
                        "device_model": "",
                        "os_version": "",
                        "build_hash": "",
                        "backend_environment": "",
                        "tester_role": "",
                        "tested_at": "",
                    },
                ],
                "scenarios": [
                    {"id": "login", "status": "pending", "screenshot_refs": [], "log_refs": []},
                    {"id": "approval_detail", "status": "pending", "screenshot_refs": [], "log_refs": []},
                    {"id": "message_detail", "status": "pending", "screenshot_refs": [], "log_refs": []},
                    {"id": "task_detail", "status": "pending", "screenshot_refs": [], "log_refs": []},
                    {"id": "chat_continuation", "status": "pending", "screenshot_refs": [], "log_refs": []},
                    {"id": "settings_error_state", "status": "pending", "screenshot_refs": [], "log_refs": []},
                    {
                        "id": "mini_program_wx_login_code2session",
                        "status": "pending",
                        "screenshot_refs": [],
                        "log_refs": [],
                    },
                    {
                        "id": "mini_program_no_fake_fallback",
                        "status": "pending",
                        "screenshot_refs": [],
                        "log_refs": [],
                    },
                    {
                        "id": "cross_device_continuation",
                        "status": "pending",
                        "screenshot_refs": [],
                        "log_refs": [],
                    },
                    {
                        "id": "explicit_error_semantics",
                        "status": "pending",
                        "screenshot_refs": [],
                        "log_refs": [],
                    },
                ],
                "cross_device_result": {
                    "status": "pending",
                    "web_session_ref": "",
                    "desktop_session_ref": "",
                    "mobile_session_ref": "",
                },
                "completion_note": "Template only; Status: pending until real device evidence is attached.",
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 0, result.stdout


def test_release_artifact_validation_rejects_incomplete_mobile_manual_template(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "mobile-template-bad.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "mobile_device_manual_template",
                "status": "complete",
                "release_evidence_complete": True,
                "platforms": [{"platform": "ios"}],
                "scenarios": [],
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "release_evidence_complete=false" in result.stdout
    assert "missing platform android" in result.stdout
    assert "missing scenario login" in result.stdout
    assert "platform ios must include device_model" in result.stdout
    assert "must include cross_device_result" in result.stdout


def _mobile_mini_code_checks() -> dict:
    return {
        "mobile_vitest": "passed",
        "mobile_typescript": "passed",
        "mobile_result_surface_guard": "passed",
        "mobile_lawyer_conversion_guard": "passed",
        "mobile_expo_config_guard": "passed",
        "mobile_expo_metro_config": "passed",
        "mobile_expo_doctor": "passed",
        "mini_program_typescript": "passed",
        "mini_program_wechat_build": "passed",
        "mini_program_wechat_devtools_cli": "passed",
        "mobile_refresh_auth_guard": "passed",
        "mini_program_refresh_auth_guard": "passed",
        "fake_fallback_guard": "passed",
        "mini_program_design_token_guard": "passed",
    }


def _mobile_npm_audit(status: str = "residual_known") -> dict:
    if status == "passed":
        return {
            "status": "passed",
            "command": "cd mobile && npm audit --omit=dev --json",
            "critical": 0,
            "high": 0,
            "moderate": 0,
            "total": 0,
            "residual_vulnerabilities": [],
            "remediated_by_override": [
                "@xmldom/xmldom@0.8.13",
                "@babel/plugin-transform-modules-systemjs@7.29.4",
                "fast-uri@3.1.2",
                "@expo/cli -> tar@7.5.14",
                "@expo/metro-config -> postcss@8.5.14",
                "cacache -> tar@7.5.14",
            ],
            "remaining_note": "No production npm audit vulnerabilities remain.",
        }
    return {
        "status": "residual_known",
        "command": "cd mobile && npm audit --omit=dev --json",
        "critical": 0,
        "high": 4,
        "moderate": 2,
        "total": 6,
        "residual_vulnerabilities": [
            "@expo/cli",
            "@expo/metro-config",
            "cacache",
            "expo",
            "postcss",
            "tar",
        ],
        "remediated_by_override": ["@xmldom/xmldom@0.8.13"],
        "remaining_note": "Residual Expo CLI/Metro findings require SDK/CLI fix or exception.",
    }


def test_release_artifact_validation_accepts_mobile_mini_code_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "mobile-mini-code-smoke.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "mobile_mini_code_smoke",
                "status": "passed",
                "release_evidence_complete": False,
                "checks": _mobile_mini_code_checks(),
                "mobile_npm_audit": _mobile_npm_audit("passed"),
                "completion_note": "Code-level supporting evidence only; mobile-device evidence remains pending.",
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 0, result.stdout


def test_release_artifact_validation_accepts_external_unavailable_wechat_devtools(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "mobile-mini-code-smoke-wechat-external.json"
    checks = _mobile_mini_code_checks()
    checks["mini_program_wechat_devtools_cli"] = "external_unavailable"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-09T00:00:00Z",
                "mode": "mobile_mini_code_smoke",
                "status": "passed",
                "release_evidence_complete": False,
                "checks": checks,
                "mobile_npm_audit": _mobile_npm_audit("passed"),
                "completion_note": "Code-level supporting evidence only; interactive WeChat evidence remains pending.",
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 0, result.stdout


def test_release_artifact_validation_accepts_cross_device_continuation_code_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "cross-device-continuation-code-smoke.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-09T00:00:00Z",
                "mode": "cross_device_continuation_code_smoke",
                "status": "passed",
                "release_evidence_complete": False,
                "runtime_evidence_complete": False,
                "checks": {
                    "backend_sync_service_continuation": "passed",
                    "frontend_desktop_sync_adapter": "passed",
                },
                "covered_flow": [
                    "desktop pushes conversation and first message to backend SyncService",
                    "web and mobile pull the same conversation/message set without duplicate entity ids",
                    "desktop pulls subsequent replies incrementally without lost rows",
                ],
                "scope": {
                    "backend": "backend/src/services/sync_service.py",
                    "desktop": "frontend/src/lib/api-adapter.ts",
                    "mobile": "mobile/src/lib/api.ts",
                    "mini_program": "mini-program/src/services/api.ts",
                    "evidence_level": "code_level_rehearsal",
                },
                "pending_external_evidence": [
                    "signed_notarized_desktop_package",
                    "real_ios_device_or_official_app_build",
                    "real_android_device_or_official_app_build",
                    "interactive_wechat_devtools_or_real_mini_program_device",
                    "shared_staging_account_cross_device_session",
                ],
                "completion_note": (
                    "Supporting code-level rehearsal only; real shared staging account "
                    "cross-device evidence remains pending."
                ),
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 0, result.stdout


def test_release_artifact_validation_rejects_incomplete_cross_device_continuation_code_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "cross-device-continuation-code-smoke-bad.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-09T00:00:00Z",
                "mode": "cross_device_continuation_code_smoke",
                "status": "passed",
                "release_evidence_complete": True,
                "runtime_evidence_complete": True,
                "checks": {
                    "backend_sync_service_continuation": "passed",
                    "frontend_desktop_sync_adapter": "failed",
                },
                "covered_flow": ["desktop push"],
                "scope": {
                    "evidence_level": "runtime_complete",
                },
                "pending_external_evidence": ["signed_notarized_desktop_package"],
                "completion_note": "complete",
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "release_evidence_complete=false" in result.stdout
    assert "runtime_evidence_complete=false" in result.stdout
    assert "frontend_desktop_sync_adapter must be passed" in result.stdout
    assert "must include covered_flow steps" in result.stdout
    assert "missing pending external evidence markers" in result.stdout


def test_release_artifact_validation_accepts_agent_governance_code_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "agent-governance-code-smoke.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-09T00:00:00Z",
                "mode": "agent_governance_code_smoke",
                "status": "passed",
                "release_evidence_complete": False,
                "runtime_evidence_complete": False,
                "checks": {
                    "governance_docs_scan": "passed",
                    "agent_capability_policy": "passed",
                    "backend_governance_regressions": "passed",
                    "local_runtime_control_rehearsal": "passed",
                    "approval_authorization_guard": "passed",
                    "mcp_connection_config_policy": "passed",
                    "approved_connector_local_rehearsal": "passed",
                    "cross_process_revocation_local_rehearsal": "passed",
                    "desktop_remote_control_host": "passed",
                    "frontend_skill_connector_credentials_model": "passed",
                    "frontend_agent_workspace_e2e": "passed",
                },
                "scope": {"enterprise_agent_governance": "code_level"},
                "pending_runtime_evidence": [
                    "real_approved_connector_runtime",
                    "commercial_cross_process_revocation_runtime_evidence",
                    "real_pause_takeover_terminate_runtime",
                    "signed_packaged_runtime_outbound_evidence",
                ],
                "completion_note": "Code-level supporting evidence only; runtime evidence remains pending.",
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 0, result.stdout


def test_release_artifact_validation_rejects_incomplete_agent_governance_code_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "agent-governance-code-smoke-bad.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-09T00:00:00Z",
                "mode": "agent_governance_code_smoke",
                "status": "passed",
                "release_evidence_complete": True,
                "runtime_evidence_complete": True,
                "checks": {
                    "governance_docs_scan": "passed",
                    "agent_capability_policy": "failed",
                    "backend_governance_regressions": "passed",
                    "approval_authorization_guard": "passed",
                    "mcp_connection_config_policy": "passed",
                    "approved_connector_local_rehearsal": "passed",
                    "cross_process_revocation_local_rehearsal": "failed",
                    "desktop_remote_control_host": "passed",
                    "frontend_skill_connector_credentials_model": "passed",
                    "frontend_agent_workspace_e2e": "passed",
                },
                "scope": {"enterprise_agent_governance": "runtime_complete"},
                "pending_runtime_evidence": ["approved_connector_rehearsal"],
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "release_evidence_complete=false" in result.stdout
    assert "runtime_evidence_complete=false" in result.stdout
    assert "agent_capability_policy must be passed" in result.stdout
    assert "cross_process_revocation_local_rehearsal must be passed" in result.stdout
    assert "scope.enterprise_agent_governance must be code_level" in result.stdout
    assert "missing pending runtime evidence markers" in result.stdout


def test_release_artifact_validation_accepts_agent_connector_local_rehearsal(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "agent-connector-local-rehearsal.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-09T00:00:00Z",
                "mode": "agent_connector_local_rehearsal",
                "status": "passed",
                "release_evidence_complete": False,
                "runtime_evidence_complete": False,
                "provider_mode": "local_mock_mcp",
                "checks": {
                    "route_token_issued": "passed",
                    "connector_bound_tool_call": "passed",
                    "route_revocation": "passed",
                    "revoked_token_fail_closed": "passed",
                    "audit_trail": "passed",
                    "raw_secret_redaction": "passed",
                },
                "scope": {
                    "connector": "approved-materials",
                    "route_scope": "mcp:call",
                    "evidence_level": "local_mock_runtime_rehearsal",
                },
                "pending_external_evidence": [
                    "real_provider_credentials",
                    "provider_dashboard_logs",
                    "signed_packaged_runtime_outbound_evidence",
                    "commercial_cross_process_revocation_runtime_evidence",
                ],
                "completion_note": (
                    "Supporting local rehearsal only; real approved connector evidence remains pending."
                ),
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 0, result.stdout


def test_release_artifact_validation_rejects_incomplete_agent_connector_local_rehearsal(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "agent-connector-local-rehearsal-bad.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-09T00:00:00Z",
                "mode": "agent_connector_local_rehearsal",
                "status": "passed",
                "release_evidence_complete": True,
                "runtime_evidence_complete": True,
                "provider_mode": "live",
                "checks": {
                    "route_token_issued": "passed",
                    "connector_bound_tool_call": "failed",
                    "route_revocation": "passed",
                    "revoked_token_fail_closed": "passed",
                    "audit_trail": "passed",
                    "raw_secret_redaction": "passed",
                },
                "scope": {
                    "connector": "",
                    "route_scope": "browser:fetch",
                    "evidence_level": "live",
                },
                "pending_external_evidence": ["real_provider_credentials"],
                "completion_note": "done",
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "release_evidence_complete=false" in result.stdout
    assert "runtime_evidence_complete=false" in result.stdout
    assert "provider_mode must be local_mock_mcp" in result.stdout
    assert "connector_bound_tool_call must be passed" in result.stdout
    assert "scope.connector must be non-empty" in result.stdout
    assert "scope.route_scope must be mcp:call" in result.stdout
    assert "missing pending external evidence markers" in result.stdout


def test_release_artifact_validation_accepts_agent_cross_process_revocation_rehearsal(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "agent-cross-process-revocation-rehearsal.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-09T00:00:00Z",
                "mode": "agent_cross_process_revocation_rehearsal",
                "status": "passed",
                "release_evidence_complete": False,
                "runtime_evidence_complete": False,
                "database_mode": "sqlite_file_local_rehearsal",
                "checks": {
                    "independent_issuer_worker_admin_sessions": "passed",
                    "worker_session_cache_refresh": "passed",
                    "admin_revokes_active_route_and_lease": "passed",
                    "next_worker_call_fail_closed": "passed",
                    "audit_trail": "passed",
                    "raw_token_hash_only": "passed",
                },
                "scope": {
                    "route_key": "approved-materials",
                    "route_scope": "mcp:call",
                    "consumer": "legal-advisor-worker",
                    "evidence_level": "local_cross_process_rehearsal",
                },
                "pending_external_evidence": [
                    "signed_packaged_runtime_outbound_evidence",
                    "commercial_cross_process_revocation_runtime_evidence",
                    "real_approved_connector_provider_runtime",
                    "production_database_observability_logs",
                ],
                "completion_note": (
                    "Supporting local cross-process route-token revocation rehearsal only; "
                    "commercial multi-process evidence remains pending."
                ),
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 0, result.stdout


def test_release_artifact_validation_rejects_incomplete_agent_cross_process_revocation_rehearsal(
    tmp_path,
):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "agent-cross-process-revocation-rehearsal-bad.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-09T00:00:00Z",
                "mode": "agent_cross_process_revocation_rehearsal",
                "status": "passed",
                "release_evidence_complete": True,
                "runtime_evidence_complete": True,
                "database_mode": "production",
                "checks": {
                    "independent_issuer_worker_admin_sessions": "passed",
                    "worker_session_cache_refresh": "failed",
                    "admin_revokes_active_route_and_lease": "passed",
                    "next_worker_call_fail_closed": "passed",
                    "audit_trail": "passed",
                    "raw_token_hash_only": "passed",
                },
                "scope": {
                    "route_scope": "browser:fetch",
                    "evidence_level": "runtime_complete",
                },
                "pending_external_evidence": ["signed_packaged_runtime_outbound_evidence"],
                "completion_note": "done",
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "release_evidence_complete=false" in result.stdout
    assert "runtime_evidence_complete=false" in result.stdout
    assert "database_mode must be sqlite_file_local_rehearsal" in result.stdout
    assert "worker_session_cache_refresh must be passed" in result.stdout
    assert "scope.route_scope must be mcp:call" in result.stdout
    assert "scope.evidence_level must be local_cross_process_rehearsal" in result.stdout
    assert "missing pending external evidence markers" in result.stdout


def test_release_artifact_validation_rejects_incomplete_mobile_mini_code_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "mobile-mini-code-smoke-bad.json"
    checks = _mobile_mini_code_checks()
    checks["mini_program_wechat_build"] = "skipped"
    checks["mini_program_wechat_devtools_cli"] = "skipped"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "mobile_mini_code_smoke",
                "status": "passed",
                "release_evidence_complete": True,
                "checks": checks,
                "mobile_npm_audit": {
                    **_mobile_npm_audit(),
                    "critical": 1,
                    "residual_vulnerabilities": ["@xmldom/xmldom"],
                    "remediated_by_override": [],
                },
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "release_evidence_complete=false" in result.stdout
    assert "mini_program_wechat_build must be passed" in result.stdout
    assert "mini_program_wechat_devtools_cli must be passed or external_unavailable" in result.stdout
    assert "zero critical vulnerabilities" in result.stdout
    assert "must not leave xmldom/plist residuals" in result.stdout
    assert "must record xmldom override remediation" in result.stdout


def test_release_artifact_validation_accepts_mobile_ios_simulator_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "mobile-ios-simulator-smoke.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-08T00:00:00Z",
                "mode": "mobile_ios_simulator_expo_go_smoke",
                "status": "passed",
                "release_evidence_complete": False,
                "device": {
                    "platform": "ios_simulator",
                    "name": "iPhone 17",
                    "udid": "simulator-udid",
                },
                "checks": {
                    "simulator_boot": "passed",
                    "expo_asset_resolvable": "passed",
                    "expo_metro_config": "passed",
                    "expo_go_container": "present",
                    "ios_bundle": "passed",
                },
                "artifacts": {"log": "docs/release/evidence/artifacts/mobile-ios-simulator.log"},
                "transcript_excerpt": ["iOS Bundled 581ms node_modules/expo-router/entry.js"],
                "notes": [
                    "Supporting iOS Simulator evidence only; real-device release evidence remains pending.",
                ],
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 0, result.stdout


def test_release_artifact_validation_rejects_incomplete_mobile_ios_simulator_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "mobile-ios-simulator-bad.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-08T00:00:00Z",
                "mode": "mobile_ios_simulator_expo_go_smoke",
                "status": "failed",
                "release_evidence_complete": True,
                "device": {"platform": "ios"},
                "checks": {
                    "simulator_boot": "passed",
                    "expo_asset_resolvable": "missing",
                    "expo_metro_config": "passed",
                    "expo_go_container": "missing",
                    "ios_bundle": "failed",
                },
                "artifacts": {},
                "transcript_excerpt": ["Waiting on http://localhost:19001"],
                "notes": ["complete"],
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "release_evidence_complete=false" in result.stdout
    assert "status=passed" in result.stdout
    assert "device.platform must be ios_simulator" in result.stdout
    assert "expo_asset_resolvable must be passed" in result.stdout
    assert "transcript must include iOS Bundled" in result.stdout


def test_release_artifact_validation_accepts_desktop_installed_profile_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "desktop-installed-profile.json"
    launch = {
        "keyringRoundTrip": True,
        "encryptedReopen": True,
        "plaintextBackupPresent": True,
        "plaintextOpenBlocked": True,
    }
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "desktop_installed_profile_smoke",
                "status": "passed",
                "release_evidence_complete": False,
                "firstLaunch": launch,
                "secondLaunch": launch,
                "completion_note": "Supporting evidence only; desktop runtime evidence remains pending.",
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 0, result.stdout


def test_release_artifact_validation_rejects_incomplete_desktop_installed_profile_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "desktop-installed-profile-bad.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "desktop_installed_profile_smoke",
                "status": "passed",
                "release_evidence_complete": True,
                "firstLaunch": {
                    "keyringRoundTrip": True,
                    "encryptedReopen": True,
                    "plaintextBackupPresent": True,
                    "plaintextOpenBlocked": False,
                },
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "release_evidence_complete=false" in result.stdout
    assert "firstLaunch.plaintextOpenBlocked must be true" in result.stdout
    assert "missing secondLaunch" in result.stdout


def _desktop_runtime_checks() -> dict:
    return {
        "frontend_desktop_sync_vitest": "passed",
        "desktop_cargo_test": "passed",
        "desktop_cargo_check": "passed",
        "sqlite_migration_sql_smoke": "passed",
        "sqlite_sync_performance_smoke": {
            "status": "passed",
            "push_100_rows_p95_ms": 20,
            "pull_500_rows_p95_ms": 30,
            "push_threshold_ms": 2000,
            "pull_threshold_ms": 3000,
        },
        "tauri_debug_build": "passed",
        "debug_binary_or_bundle_self_test": "passed",
        "debug_app_bundle_runtime_startup": "passed",
        "debug_app_bundle_ui_load": "passed",
    }


def test_release_artifact_validation_accepts_desktop_runtime_code_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "desktop-runtime-code-smoke.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "desktop_runtime_code_smoke",
                "status": "passed",
                "release_evidence_complete": False,
                "checks": _desktop_runtime_checks(),
                "completion_note": "Supporting evidence only; desktop runtime evidence remains pending.",
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 0, result.stdout


def test_release_artifact_validation_rejects_incomplete_desktop_runtime_code_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "desktop-runtime-code-smoke-bad.json"
    checks = _desktop_runtime_checks()
    checks["debug_app_bundle_ui_load"] = "skipped"
    checks["sqlite_sync_performance_smoke"]["push_100_rows_p95_ms"] = 2500
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "desktop_runtime_code_smoke",
                "status": "passed",
                "release_evidence_complete": True,
                "checks": checks,
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "release_evidence_complete=false" in result.stdout
    assert "debug_app_bundle_ui_load must be passed" in result.stdout
    assert "push P95 must be below threshold" in result.stdout


def _desktop_release_runtime_unsigned_payload() -> dict:
    return {
        "generated_at": "2026-05-07T00:00:00Z",
        "mode": "desktop_release_runtime_unsigned_smoke",
        "status": "passed",
        "release_evidence_complete": False,
        "signed_or_notarized": False,
        "checks": {
            "release_app_exists": "passed",
            "release_dmg_exists": "passed",
            "release_binary_self_test": "passed",
            "release_sync_code_smoke": "passed",
            "release_sync_loopback_smoke": "passed",
            "release_runtime_startup": "passed",
            "release_webview_ui_load": "passed",
            "sync_code_smoke": {
                "sync_log_migration": "passed",
                "pending_rows_decoded": 2,
                "push_payload_records": 2,
                "accepted_after_conflict": 1,
                "conflict_rows": 1,
                "retry_needs_human": True,
                "pull_records_decoded": 1,
            },
            "sync_loopback_smoke": {
                "loopback_backend": "passed",
                "auth_header_received": True,
                "pending_rows_decoded": 2,
                "push_payload_records": 2,
                "backend_received_records": 2,
                "accepted_after_conflict": 1,
                "conflict_rows": 1,
                "rows_synced": 1,
                "rows_conflicted": 1,
                "pull_records_written": 1,
                "cursor_advanced_to": 13,
                "retry_needs_human": True,
            },
            "sqlite_security": {
                "status": "passed",
                "encrypted": True,
                "keyring_backed": True,
                "release_blocking": False,
            },
        },
        "artifacts": {
            "release_app": "desktop/target/release/bundle/macos/安心智能助手.app",
            "release_binary": "desktop/target/release/bundle/macos/安心智能助手.app/Contents/MacOS/anxin-legal-desktop",
            "release_dmg": "desktop/target/release/bundle/dmg/安心智能助手_1.0.0_aarch64.dmg",
            "ui_log": "docs/release/evidence/artifacts/desktop-release-runtime-ui-smoke-unsigned-20260509.log",
        },
        "completion_note": (
            "Unsigned release packaged-runtime supporting evidence only. "
            "Keep desktop runtime evidence Status: pending until signed/notarized evidence exists."
        ),
    }


def test_release_artifact_validation_accepts_desktop_release_runtime_unsigned_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "desktop-release-runtime-unsigned.json"
    artifact.write_text(json.dumps(_desktop_release_runtime_unsigned_payload()), encoding="utf-8")

    result = _validate(repo_root, artifact)

    assert result.returncode == 0, result.stdout


def test_release_artifact_validation_rejects_incomplete_desktop_release_runtime_unsigned_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "desktop-release-runtime-unsigned-bad.json"
    payload = _desktop_release_runtime_unsigned_payload()
    payload["release_evidence_complete"] = True
    payload["signed_or_notarized"] = True
    payload["checks"]["release_webview_ui_load"] = "failed"
    payload["checks"]["release_sync_code_smoke"] = "failed"
    payload["checks"]["release_sync_loopback_smoke"] = "failed"
    payload["checks"]["sync_code_smoke"]["push_payload_records"] = 0
    payload["checks"]["sync_loopback_smoke"]["auth_header_received"] = False
    payload["checks"]["sync_loopback_smoke"]["backend_received_records"] = 0
    payload["checks"]["sqlite_security"]["encrypted"] = False
    payload["artifacts"]["release_dmg"] = ""
    payload["completion_note"] = "Complete."
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "release_evidence_complete=false" in result.stdout
    assert "signed_or_notarized=false" in result.stdout
    assert "release_webview_ui_load must be passed" in result.stdout
    assert "release_sync_loopback_smoke must be passed" in result.stdout
    assert "sync_loopback_smoke.auth_header_received must be true" in result.stdout
    assert "sqlite_security.encrypted must be true" in result.stdout
    assert "artifacts.release_dmg must be non-empty" in result.stdout
    assert "signed/notarized evidence remains pending" in result.stdout


def _desktop_release_packaged_profile_payload() -> dict:
    launch = {
        "keyringRoundTrip": True,
        "encryptedReopen": True,
        "plaintextBackupPresent": True,
        "plaintextOpenBlocked": True,
    }
    return {
        "generated_at": "2026-05-07T00:00:00Z",
        "mode": "desktop_release_packaged_profile_smoke",
        "status": "passed",
        "release_evidence_complete": False,
        "signed_or_notarized": False,
        "checks": {
            "release_app_exists": "passed",
            "release_binary_exists": "passed",
            "plaintext_profile_seeded": "passed",
            "first_launch_plaintext_to_sqlcipher_migration": "passed",
            "second_launch_keyring_reopen": "passed",
            "release_sqlcipher_performance": "passed",
            "ordinary_sqlite_plaintext_read_blocked": "passed",
        },
        "artifacts": {
            "release_app": "desktop/target/release/bundle/macos/安心智能助手.app",
            "release_binary": "desktop/target/release/bundle/macos/安心智能助手.app/Contents/MacOS/anxin-legal-desktop",
        },
        "firstLaunch": launch,
        "secondLaunch": launch,
        "performance": {
            "status": "passed",
            "keyringRoundTrip": True,
            "encryptedReopen": True,
            "push100RowsP95Ms": 25,
            "pull500RowsP95Ms": 40,
            "pushThresholdMs": 2000,
            "pullThresholdMs": 3000,
        },
        "completion_note": (
            "Unsigned release packaged-profile supporting evidence only. "
            "Keep desktop runtime evidence Status: pending until signed/notarized evidence exists."
        ),
    }


def test_release_artifact_validation_accepts_desktop_release_packaged_profile_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "desktop-release-profile.json"
    artifact.write_text(json.dumps(_desktop_release_packaged_profile_payload()), encoding="utf-8")

    result = _validate(repo_root, artifact)

    assert result.returncode == 0, result.stdout


def test_release_artifact_validation_rejects_incomplete_desktop_release_packaged_profile_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "desktop-release-profile-bad.json"
    payload = _desktop_release_packaged_profile_payload()
    payload["release_evidence_complete"] = True
    payload["signed_or_notarized"] = True
    payload["checks"]["second_launch_keyring_reopen"] = "failed"
    payload["checks"]["release_sqlcipher_performance"] = "failed"
    payload["firstLaunch"]["plaintextOpenBlocked"] = False
    payload["performance"]["push100RowsP95Ms"] = 3000
    payload["performance"]["encryptedReopen"] = False
    payload["artifacts"]["release_binary"] = ""
    payload["completion_note"] = "Complete."
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "release_evidence_complete=false" in result.stdout
    assert "signed_or_notarized=false" in result.stdout
    assert "second_launch_keyring_reopen must be passed" in result.stdout
    assert "release_sqlcipher_performance must be passed" in result.stdout
    assert "firstLaunch.plaintextOpenBlocked must be true" in result.stdout
    assert "performance.encryptedReopen must be true" in result.stdout
    assert "push P95 must be below threshold" in result.stdout
    assert "artifacts.release_binary must be non-empty" in result.stdout
    assert "signed/notarized evidence remains pending" in result.stdout


def _desktop_preflight_checks() -> list[dict]:
    blocking = [
        ("platform", "pass"),
        ("command.xcodebuild", "pass"),
        ("command.xcrun", "pass"),
        ("command.codesign", "pass"),
        ("command.security", "pass"),
        ("command.spctl", "pass"),
        ("command.hdiutil", "pass"),
        ("dmg.hdiutil_create_probe", "fail"),
        ("tauri.signing_identity", "fail"),
        ("tauri.entitlements", "pass"),
        ("tauri.entitlements.aps_environment", "fail"),
        ("codesign.identities", "fail"),
        ("notary.credentials", "fail"),
        ("notary.tool", "pass"),
        ("stapler.tool", "pass"),
        ("release.app.exists", "fail"),
        ("release.dmg.exists", "fail"),
    ]
    supporting = [
        ("support.debug_app.exists", "pass"),
        ("support.debug_runtime_transcript", "pass"),
        ("support.installed_profile_report", "pass"),
    ]
    return [
        {"id": check_id, "label": check_id, "status": status, "release_blocking": True}
        for check_id, status in blocking
    ] + [
        {"id": check_id, "label": check_id, "status": status, "release_blocking": False}
        for check_id, status in supporting
    ]


def test_release_artifact_validation_accepts_desktop_release_preflight(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "desktop-release-preflight.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "preflight",
                "release_ready": False,
                "release_blockers": [
                    "tauri.signing_identity",
                    "tauri.entitlements.aps_environment",
                    "dmg.hdiutil_create_probe",
                    "codesign.identities",
                    "notary.credentials",
                    "release.app.exists",
                    "release.dmg.exists",
                ],
                "inputs": {
                    "release_app": "desktop/target/release/bundle/macos/安心智能助手.app",
                    "debug_app": "desktop/target/debug/bundle/macos/安心智能助手.app",
                    "installed_profile_report": "docs/release/evidence/artifacts/desktop-installed-profile-smoke-20260507.json",
                    "runtime_transcript": "docs/release/evidence/artifacts/desktop-runtime-ui-smoke-20260507.log",
                    "runtime_structured_artifact": "docs/release/evidence/artifacts/desktop-runtime-code-smoke-20260507.json",
                },
                "checks": _desktop_preflight_checks(),
                "completion_note": "Supporting evidence only; desktop runtime evidence remains pending.",
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 0, result.stdout


def test_release_artifact_validation_rejects_incomplete_desktop_release_preflight(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "desktop-release-preflight-bad.json"
    checks = _desktop_preflight_checks()
    checks = [check for check in checks if check["id"] != "release.dmg.exists"]
    checks[-1]["status"] = "warn"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "preflight",
                "release_ready": True,
                "release_blockers": [],
                "inputs": {
                    "release_app": "desktop/target/release/bundle/macos/安心智能助手.app",
                    "debug_app": "desktop/target/debug/bundle/macos/安心智能助手.app",
                    "installed_profile_report": "docs/release/evidence/artifacts/missing-installed-profile.json",
                    "runtime_transcript": "docs/release/evidence/artifacts/desktop-runtime-ui-smoke-20260507.log",
                    "runtime_structured_artifact": "docs/release/evidence/artifacts/desktop-runtime-code-smoke-20260507.json",
                },
                "checks": checks,
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "inputs.installed_profile_report does not exist" in result.stdout
    assert "missing check release.dmg.exists" in result.stdout
    assert "release_blockers must match failing release-blocking checks" in result.stdout
    assert "support.installed_profile_report must be pass" in result.stdout


def _desktop_release_package_checks() -> list[dict]:
    return [
        {"id": "platform", "label": "platform", "status": "pass", "release_blocking": True},
        {"id": "command.cargo", "label": "cargo", "status": "pass", "release_blocking": True},
        {"id": "command.xcrun", "label": "xcrun", "status": "pass", "release_blocking": True},
        {"id": "command.codesign", "label": "codesign", "status": "pass", "release_blocking": True},
        {"id": "command.hdiutil", "label": "hdiutil", "status": "pass", "release_blocking": True},
        {"id": "dmg.hdiutil_create_probe", "label": "hdiutil probe", "status": "fail", "release_blocking": True},
        {"id": "signing.identity", "label": "signing identity", "status": "fail", "release_blocking": True},
        {"id": "notary.credentials", "label": "notary", "status": "fail", "release_blocking": True},
        {
            "id": "entitlements.aps_environment",
            "label": "entitlements",
            "status": "fail",
            "release_blocking": True,
        },
    ]


def test_release_artifact_validation_accepts_desktop_release_package_dry_run(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "desktop-release-package-dry-run.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "desktop_release_package",
                "status": "dry_run",
                "release_evidence_complete": False,
                "release_ready": False,
                "release_blockers": [
                    "signing.identity",
                    "dmg.hdiutil_create_probe",
                    "notary.credentials",
                    "entitlements.aps_environment",
                ],
                "inputs": {
                    "dry_run": True,
                    "skip_build": False,
                    "skip_stapling": False,
                    "bundles": "app,dmg",
                    "signing_identity_configured": False,
                },
                "checks": _desktop_release_package_checks(),
                "preflight_artifact": None,
                "completion_note": "Supporting evidence only; desktop runtime evidence remains pending.",
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 0, result.stdout


def test_release_artifact_validation_rejects_incomplete_desktop_release_package(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "desktop-release-package-bad.json"
    checks = _desktop_release_package_checks()
    checks = [check for check in checks if check["id"] != "command.codesign"]
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "desktop_release_package",
                "status": "dry_run",
                "release_evidence_complete": True,
                "release_ready": True,
                "release_blockers": ["notary.credentials"],
                "inputs": {
                    "dry_run": True,
                    "skip_build": False,
                    "skip_stapling": False,
                    "bundles": "dmg",
                    "signing_identity_configured": False,
                },
                "checks": checks,
                "preflight_artifact": "docs/release/evidence/artifacts/missing-preflight.json",
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "release_evidence_complete=false" in result.stdout
    assert "inputs.bundles must include app" in result.stdout
    assert "missing check command.codesign" in result.stdout
    assert "release_blockers missing local blocker signing.identity" in result.stdout
    assert "cannot be release_ready=true with blockers" in result.stdout
    assert "preflight_artifact does not exist" in result.stdout


def _sandbox_provider(runtime_args: list[str]) -> dict:
    return {
        "configured": False,
        "fields": [
            {
                "label": "app ID",
                "name": "APP_ID",
                "present": False,
                "redacted": "missing",
            }
        ],
        "missing": ["app ID"],
        "runtime_prerequisites": [
            {
                "argument": argument,
                "label": f"{argument} evidence input",
                "note": "Required before live evidence collection.",
                "present": False,
                "status": "missing",
            }
            for argument in runtime_args
        ],
        "external_evidence_requirements": [
            {
                "id": requirement_id,
                "label": f"{requirement_id} evidence",
                "status": "pending_external_input",
                "release_blocking": True,
                "artifact_ref": "TBD",
                "collection_method": "Attach redacted provider callback/dashboard/retry evidence.",
            }
            for requirement_id in (
                "official_success_callback",
                "official_success_notification",
                "official_callback",
                "duplicate_callback_idempotency",
                "duplicate_notification_idempotency",
                "failed_callback_retry",
                "failed_notification_retry",
                "platform_key_rotation",
            )
        ],
        "warnings": [],
    }


def test_release_artifact_validation_accepts_sandbox_preflight(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "payment-preflight.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "preflight",
                "environment": "staging/sandbox",
                "selected_scope": "payment",
                "loaded_env_files": [".env", "backend/.env"],
                "live_checks": {},
                "providers": {
                    "wechat_pay": _sandbox_provider(["--wechat-refund-order-id"]),
                    "alipay": _sandbox_provider(
                        [
                            "--alipay-query-order-id",
                            "--alipay-refund-order-id",
                            "--alipay-close-order-id",
                        ]
                    ),
                },
                "completion_note": "Supporting evidence only; payment release evidence remains pending.",
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 0, result.stdout


def test_release_artifact_validation_rejects_incomplete_sandbox_preflight(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "esign-preflight-bad.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "preflight",
                "environment": "prod",
                "selected_scope": "esign",
                "loaded_env_files": [],
                "live_checks": [],
                "providers": {
                    "esignbao": {
                        "configured": True,
                        "fields": [{"label": "app ID", "name": "ESIGN_BAO_APP_ID", "present": True}],
                        "missing": ["app secret"],
                        "runtime_prerequisites": [
                            {
                                "argument": "--esign-document-url",
                                "label": "document URL",
                                "note": "Required before live evidence collection.",
                                "present": False,
                                "status": "missing",
                            }
                        ],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "environment=staging/sandbox" in result.stdout
    assert "must include live_checks object" in result.stdout
    assert "missing provider fadada" in result.stdout
    assert "configured but still lists missing fields" in result.stdout
    assert "field missing redacted" in result.stdout
    assert "missing runtime prerequisite --esignbao-completed-flow-id" in result.stdout
    assert "must include external_evidence_requirements" in result.stdout


def _sandbox_live_provider(runtime_args: list[str]) -> dict:
    provider = _sandbox_provider(runtime_args)
    provider["configured"] = True
    provider["missing"] = []
    for field in provider["fields"]:
        field["present"] = True
        field["redacted"] = "set"
    for prereq in provider["runtime_prerequisites"]:
        prereq["present"] = True
        prereq["status"] = "ready"
    return provider


def test_release_artifact_validation_accepts_sandbox_live_artifact(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "payment-live.json"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "live",
                "environment": "staging/sandbox",
                "selected_scope": "payment",
                "loaded_env_files": [".env", "backend/.env"],
                "providers": {
                    "wechat_pay": _sandbox_live_provider(["--wechat-refund-order-id"]),
                    "alipay": _sandbox_live_provider(
                        [
                            "--alipay-query-order-id",
                            "--alipay-refund-order-id",
                            "--alipay-close-order-id",
                        ]
                    ),
                },
                "live_checks": {
                    "wechat_pay": [
                        {"step": "wechat native order creation", "status": "pass"},
                        {"step": "wechat query order", "status": "pass"},
                        {"step": "wechat close order", "status": "pass"},
                        {"step": "wechat refund paid order", "status": "pass"},
                    ],
                    "alipay": [
                        {"step": "alipay page.pay signed URL creation", "status": "pass"},
                        {"step": "alipay query order", "status": "pass"},
                        {"step": "alipay refund paid order", "status": "pass"},
                        {"step": "alipay close order", "status": "pass"},
                    ],
                },
                "completion_note": "Supporting evidence only; payment release evidence remains pending.",
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 0, result.stdout


def test_release_artifact_validation_rejects_incomplete_sandbox_live_artifact(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = tmp_path / "esignbao-live-bad.json"
    provider = _sandbox_live_provider(["--esign-document-url", "--esignbao-completed-flow-id"])
    provider["configured"] = False
    provider["missing"] = ["app secret"]
    provider["runtime_prerequisites"][1]["present"] = False
    provider["runtime_prerequisites"][1]["status"] = "missing"
    artifact.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-07T00:00:00Z",
                "mode": "live",
                "environment": "staging/sandbox",
                "selected_scope": "esignbao",
                "providers": {"esignbao": provider},
                "live_checks": {
                    "esignbao": [
                        {"step": "esignbao create/start/get sign URL", "status": "pass"},
                        {"step": "esignbao download completed signed document", "status": "skipped"},
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, artifact)

    assert result.returncode == 1
    assert "provider esignbao must be configured=true" in result.stdout
    assert "provider esignbao must not list missing fields" in result.stdout
    assert "runtime prerequisite --esignbao-completed-flow-id must be present" in result.stdout
    assert "runtime prerequisite --esignbao-completed-flow-id must be ready" in result.stdout
    assert "live check esignbao download completed signed document must be pass" in result.stdout
