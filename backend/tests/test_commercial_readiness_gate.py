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


def test_commercial_gate_runs_agent_governance_policy_tests():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'require_command "agent governance policy tests"' in script
    assert "tests/test_agent_governance_policy.py" in script
