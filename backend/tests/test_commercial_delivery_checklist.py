import json
import subprocess
from pathlib import Path


def _validate(repo_root: Path, checklist: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = [
        "node",
        str(repo_root / "scripts" / "validate-commercial-delivery-checklist.cjs"),
    ]
    if checklist is not None:
        command.append(str(checklist))
    return subprocess.run(
        command,
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def _manifest(status: str, criteria: list[dict]) -> dict:
    return {
        "generated_at": "2026-05-07",
        "objective": "commercial delivery checklist test",
        "status": status,
        "status_reason": "test fixture",
        "success_criteria": criteria,
    }


def _criterion(
    *,
    status: str = "complete",
    evidence: list[str] | None = None,
    item_id: str = "criterion-1",
) -> dict:
    return {
        "id": item_id,
        "prompt_requirement": "test requirement",
        "status": status,
        "evidence": evidence or ["docs/release/evidence/static-quality-baseline.md"],
        "verification": ["test -s docs/release/evidence/static-quality-baseline.md"],
        "current_result": "test current result",
    }


def _pending_evidence(*items: str) -> list[str]:
    return [*items, "docs/release/external-resource-handoff.md"]


def test_commercial_delivery_checklist_accepts_current_not_ready_manifest():
    repo_root = Path(__file__).resolve().parents[2]

    result = _validate(repo_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "status=not_ready" in result.stdout
    assert "9 criteria" in result.stdout


def test_commercial_delivery_checklist_rejects_missing_evidence(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    checklist = tmp_path / "checklist.json"
    checklist.write_text(
        json.dumps(
            _manifest(
                "ready",
                [_criterion(evidence=["docs/release/evidence/does-not-exist.md"])],
            )
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, checklist)

    assert result.returncode == 1
    assert "missing evidence artifact" in result.stderr


def test_commercial_delivery_checklist_rejects_ready_with_pending_criteria(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    checklist = tmp_path / "checklist.json"
    checklist.write_text(
        json.dumps(
            _manifest(
                "ready",
                [
                    _criterion(
                        status="pending_external_input",
                        evidence=_pending_evidence("docs/release/evidence/payment-sandbox.md"),
                    )
                ],
            )
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, checklist)

    assert result.returncode == 1
    assert "manifest is ready" in result.stderr


def test_commercial_delivery_checklist_rejects_complete_item_with_pending_evidence(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    checklist = tmp_path / "checklist.json"
    checklist.write_text(
        json.dumps(
            _manifest(
                "ready",
                [
                    _criterion(
                        status="complete",
                        evidence=["docs/release/evidence/payment-sandbox.md"],
                    )
                ],
            )
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, checklist)

    assert result.returncode == 1
    assert "Status: pending" in result.stderr


def test_commercial_delivery_checklist_requires_external_handoff_for_pending_items(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    checklist = tmp_path / "checklist.json"
    checklist.write_text(
        json.dumps(
            _manifest(
                "not_ready",
                [
                    _criterion(
                        status="pending_external_input",
                        evidence=["docs/release/evidence/payment-sandbox.md"],
                    )
                ],
            )
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, checklist)

    assert result.returncode == 1
    assert "external-resource-handoff.md" in result.stderr
