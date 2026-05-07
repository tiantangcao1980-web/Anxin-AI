import json
import subprocess
from pathlib import Path


def _run_validator(repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", "scripts/validate-commercial-delivery-lanes.cjs"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def test_commercial_delivery_lanes_manifest_is_valid():
    repo_root = Path(__file__).resolve().parents[2]

    result = _run_validator(repo_root)

    assert result.returncode == 0, result.stderr
    assert "Commercial delivery lanes: OK" in result.stdout


def test_commercial_delivery_lanes_keep_final_gate_serial():
    repo_root = Path(__file__).resolve().parents[2]
    manifest = json.loads((repo_root / "docs/release/commercial-delivery-lanes.json").read_text(encoding="utf-8"))

    final_lane_id = manifest["parallelization"]["final_lane"]
    lanes = {lane["id"]: lane for lane in manifest["lanes"]}

    assert final_lane_id == "final-commercial-gate"
    assert lanes[final_lane_id]["can_parallelize"] is False
    assert "commercial-readiness-gate.sh --quick" in "\n".join(lanes[final_lane_id]["local_commands"])


def test_external_or_device_lanes_declare_inputs_and_blockers():
    repo_root = Path(__file__).resolve().parents[2]
    manifest = json.loads((repo_root / "docs/release/commercial-delivery-lanes.json").read_text(encoding="utf-8"))
    pending_statuses = {"pending_external_input", "pending_device_evidence", "pending_final_release"}

    pending_lanes = [lane for lane in manifest["lanes"] if lane["status"] in pending_statuses]

    assert pending_lanes
    for lane in pending_lanes:
        assert lane["external_inputs"], lane["id"]
        assert lane["current_blockers"], lane["id"]
        assert "docs/release/external-resource-handoff.md" in lane["evidence"], lane["id"]
