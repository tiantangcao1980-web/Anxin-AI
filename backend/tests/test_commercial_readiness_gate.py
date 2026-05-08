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


def test_commercial_gate_runs_workstation_settings_e2e():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "frontend workstation settings e2e"' in script
    assert "e2e/settings-workstation.spec.ts --project=chromium --project=mobile" in script


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


def test_commercial_gate_runs_cli_route_governance_tests():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "CLI route governance tests"' in script
    assert "tests/test_cli_route.py" in script


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


def test_commercial_gate_runs_approval_authorization_guard_tests():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "approval authorization guard tests"' in script
    assert "tests/test_business_authorization_guards.py -k 'approval or template'" in script
