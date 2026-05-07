import subprocess
from pathlib import Path


def test_desktop_network_surface_gate_passes_current_desktop_profile():
    repo_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        ["bash", str(repo_root / "scripts" / "desktop-network-surface-gate.sh")],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Desktop network surface gate: PASS" in result.stdout
