from pathlib import Path


def test_commercial_gate_surfaces_artifact_validator_warnings():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'artifact_validation_output="$(python3 scripts/validate-release-artifacts.py 2>&1)"' in script
    assert 'add_warning "${line#WARN: }"' in script
    assert 'FAIL:\\ *)' in script


def test_commercial_gate_requires_desktop_network_surface_gate():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert '"scripts/desktop-network-surface-gate.sh"' in script
    assert 'desktop_network_output="$(bash scripts/desktop-network-surface-gate.sh 2>&1)"' in script
    assert 'require_command "desktop network surface gate"' in script


def test_commercial_gate_requires_desktop_window_chrome_gate():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert '"scripts/desktop-window-chrome-gate.sh"' in script
    assert 'desktop_window_chrome_output="$(bash scripts/desktop-window-chrome-gate.sh 2>&1)"' in script
    assert 'require_command "desktop window chrome gate"' in script


def test_commercial_gate_requires_desktop_mvp_local_gate():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")
    gate_script = (repo_root / "scripts" / "desktop-mvp-local-gate.sh").read_text(encoding="utf-8")

    assert '"scripts/desktop-mvp-local-gate.sh"' in script
    assert 'desktop_mvp_output="$(bash scripts/desktop-mvp-local-gate.sh 2>&1)"' in script
    assert 'require_command "desktop MVP local gate"' in script
    assert "frontend/src/pages/QuickQuery.tsx" in gate_script
    assert "desktop/src/commands/file_drop.rs" in gate_script
    assert "frontend/src/components/desktop/DesktopWorkstationPanel.tsx" in gate_script


def test_commercial_gate_requires_current_gitnexus_commit():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert "git rev-parse HEAD" in script
    assert "m.lastCommit" in script
    assert "GitNexus metadata is missing lastCommit" in script
    assert "GitNexus metadata is stale" in script
    assert "rerun bash scripts/gitnexus-index.sh after committing release artifacts" in script


def test_commercial_gate_runs_desktop_strict_clippy():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "desktop strict Clippy"' in script
    assert "cargo clippy --all-targets -- -D warnings" in script


def test_commercial_gate_runs_workstation_settings_e2e():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "frontend workstation settings e2e"' in script
    assert "e2e/settings-workstation.spec.ts --project=chromium --project=mobile" in script


def test_commercial_gate_runs_uni_mobile_migration_guard():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")
    smoke_script = (repo_root / "scripts" / "uni-mobile-smoke.sh").read_text(encoding="utf-8")
    guard_script = (repo_root / "scripts" / "uni-mobile-migration-guard.sh").read_text(encoding="utf-8")

    assert "scripts/uni-mobile-migration-guard.sh" in script
    assert 'require_command "uni-mobile migration guard"' in script
    assert 'run_step "uni-mobile migration guard"' in smoke_script
    assert "mobile/README.md" in guard_script
    assert "mini-program/README.md" in guard_script
    assert "apps/uni-mobile/src/services/api.ts" in guard_script


def test_commercial_gate_runs_agent_approval_workspace_e2e():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "frontend agent approval workspace e2e"' in script
    assert "e2e/agent-approval-workspace.spec.ts --project=chromium --project=mobile" in script


def test_commercial_gate_runs_agent_governance_policy_tests():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "agent governance policy tests"' in script
    assert "tests/test_agent_governance_policy.py" in script


def test_commercial_gate_runs_capability_route_token_tests():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "capability route token tests"' in script
    assert "tests/test_capability_routes.py" in script


def test_commercial_gate_runs_agent_governance_model_tests():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "agent governance model tests"' in script
    assert "tests/test_agent_governance_models.py" in script


def test_commercial_gate_runs_agent_governance_service_tests():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "agent governance service tests"' in script
    assert "tests/test_agent_governance_service.py" in script


def test_commercial_gate_runs_agent_approval_service_tests():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "agent approval service tests"' in script
    assert "tests/test_agent_approval_service.py" in script


def test_commercial_gate_runs_agent_approval_api_tests():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "agent approval API tests"' in script
    assert "tests/test_agent_approval_api.py" in script


def test_commercial_gate_runs_mcp_route_governance_tests():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "MCP route governance tests"' in script
    assert "tests/test_mcp_route_governance.py" in script


def test_commercial_gate_runs_approved_connector_local_rehearsal():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert '"scripts/agent-connector-rehearsal.sh"' in script
    assert 'require_command "approved connector local rehearsal"' in script
    assert "scripts/agent-connector-rehearsal.sh --out /tmp/anxin-agent-connector-rehearsal-gate.json" in script


def test_commercial_gate_runs_cross_device_continuation_smoke():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert '"scripts/cross-device-continuation-smoke.sh"' in script
    assert 'require_command "cross-device continuation code smoke"' in script
    assert "scripts/cross-device-continuation-smoke.sh --out /tmp/anxin-cross-device-continuation-gate.json" in script


def test_commercial_gate_runs_cli_route_governance_tests():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "CLI route governance tests"' in script
    assert "tests/test_cli_route.py" in script


def test_commercial_gate_runs_llm_route_governance_tests():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "LLM route governance tests"' in script
    assert "tests/test_llm_route_governance.py" in script


def test_commercial_gate_runs_crawler_browser_route_governance_tests():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "crawler browser route governance tests"' in script
    assert "tests/test_crawler_compliance.py" in script


def test_commercial_gate_runs_skill_governance_gate_tests():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "skill governance gate tests"' in script
    assert "tests/test_skill_evolution_service.py tests/test_skill_service.py" in script
    assert "tests/test_skill_governance_models.py tests/test_skill_governance_service.py" in script
    assert "tests/test_skill_governance_api.py" in script


def test_commercial_gate_requires_agent_governance_release_evidence():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert "docs/release/evidence/agent-governance-smoke.md|enterprise agent governance smoke" in script


def test_commercial_gate_requires_agent_governance_smoke_script():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert '"scripts/agent-governance-smoke.sh"' in script


def test_commercial_gate_runs_approval_authorization_guard_tests():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "approval authorization guard tests"' in script
    assert "tests/test_business_authorization_guards.py -k 'approval or template'" in script
