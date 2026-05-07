import json
import subprocess
from pathlib import Path


def _inventory(
    repo_root: Path,
    fixture: Path,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "python3",
            str(repo_root / "scripts" / "release-worktree-inventory.py"),
            "--status-file",
            str(fixture),
            "--json",
            *extra,
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def test_release_worktree_inventory_classifies_dirty_paths(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    fixture = tmp_path / "status.txt"
    fixture.write_text(
        "\n".join(
            [
                " M backend/src/services/payment_service.py",
                "?? docs/release/evidence/payment-sandbox.md",
                "?? scripts/validate-release-artifacts.py",
                "?? docker-compose.yml",
                "?? desktop/Entitlements.plist",
                "?? docs/DEPLOYMENT_DESKTOP.md",
                "?? docs/design/cross-platform-token-drift.md",
                "?? frontend/package-lock.json",
                "?? .env",
                "?? desktop/target/debug/app",
                "?? scratch.txt",
            ]
        ),
        encoding="utf-8",
    )

    result = _inventory(repo_root, fixture)

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["tracked_changes"] == 1
    assert payload["untracked_files"] == 10
    assert "backend/src/services/payment_service.py" in payload["categories"]["release_delivery"]
    assert "docs/release/evidence/payment-sandbox.md" in payload["categories"]["release_delivery"]
    assert "docker-compose.yml" in payload["categories"]["release_delivery"]
    assert "desktop/Entitlements.plist" in payload["categories"]["release_delivery"]
    assert "docs/DEPLOYMENT_DESKTOP.md" in payload["categories"]["release_delivery"]
    assert "docs/design/cross-platform-token-drift.md" in payload["categories"]["release_delivery"]
    assert "frontend/package-lock.json" in payload["categories"]["release_delivery"]
    assert ".env" in payload["categories"]["local_secret"]
    assert "desktop/target/debug/app" in payload["categories"]["generated_or_runtime"]
    assert "scratch.txt" in payload["categories"]["unknown"]


def test_release_worktree_inventory_can_fail_on_unknown_paths(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    fixture = tmp_path / "status.txt"
    fixture.write_text("?? scratch.txt\n", encoding="utf-8")

    result = _inventory(repo_root, fixture, "--fail-on-unknown")

    assert result.returncode == 1
    assert "scratch.txt" in result.stdout
