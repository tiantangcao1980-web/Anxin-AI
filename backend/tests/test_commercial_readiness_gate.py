from pathlib import Path


def test_commercial_gate_surfaces_artifact_validator_warnings():
    repo_root = Path(__file__).resolve().parents[2]
    script = (repo_root / "scripts" / "commercial-readiness-gate.sh").read_text(encoding="utf-8")

    assert 'artifact_validation_output="$(python3 scripts/validate-release-artifacts.py 2>&1)"' in script
    assert 'add_warning "${line#WARN: }"' in script
    assert 'FAIL:\\ *)' in script
