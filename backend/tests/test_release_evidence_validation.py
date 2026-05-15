import json
import subprocess
from pathlib import Path


def _validate(repo_root: Path, *items: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(repo_root / "scripts" / "validate-release-evidence.py"), *items],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def test_release_evidence_validation_accepts_closed_complete_file(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    evidence = tmp_path / "static-quality.md"
    evidence.write_text(
        "\n".join(
            [
                "Status: complete",
                "Owner: Codex release owner",
                "Environment: local",
                "Date range: 2026-05-07 local collection",
                "",
                "| Area | Required evidence | Status | Artifact reference |",
                "|---|---|---|---|",
                "| Backend mypy | zero errors | pass | static-quality-baseline.md |",
                "| Secret scan | release evidence scan | pass | scan transcript |",
            ]
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, f"{evidence}|static quality")

    assert result.returncode == 0, result.stdout + result.stderr


def test_release_evidence_validation_rejects_pending_status(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    evidence = tmp_path / "payment.md"
    evidence.write_text("Status: pending\n", encoding="utf-8")

    result = _validate(repo_root, f"{evidence}|payment sandbox")

    assert result.returncode == 1
    assert "Status: pending" in result.stdout
    assert "payment sandbox" in result.stdout


def test_release_evidence_validation_rejects_complete_with_unresolved_rows(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    evidence = tmp_path / "mobile.md"
    evidence.write_text(
        "\n".join(
            [
                "Status: complete",
                "Owner: Codex release owner",
                "Environment: device lab",
                "Date range: 2026-05-07 device run",
                "",
                "| Platform | Required evidence | Status | Artifact reference |",
                "|---|---|---|---|",
                "| iOS | Login and approval detail | pending | TBD |",
            ]
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, f"{evidence}|mobile device")

    assert result.returncode == 1
    assert "marked complete" in result.stdout
    assert "WARN:" in result.stdout
    assert "pending" in result.stdout


def test_release_evidence_validation_rejects_complete_with_tbd_metadata(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    evidence = tmp_path / "payment.md"
    evidence.write_text(
        "\n".join(
            [
                "Status: complete",
                "Owner: TBD",
                "Environment: sandbox",
                "Date range: TBD",
                "",
                "| Area | Required evidence | Status | Artifact reference |",
                "|---|---|---|---|",
                "| WeChat Pay | order creation | pass | artifact-001 |",
            ]
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, f"{evidence}|payment sandbox")

    assert result.returncode == 1
    assert "unresolved metadata" in result.stdout
    assert "Owner: TBD" in result.stdout
    assert "Date range: TBD" in result.stdout


def test_release_evidence_validation_rejects_complete_with_empty_artifact_reference(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    evidence = tmp_path / "rag.md"
    evidence.write_text(
        "\n".join(
            [
                "Status: complete",
                "Owner: RAG release owner",
                "Environment: staging/live vector database",
                "Date range: 2026-05-07 live baseline",
                "",
                "| Area | Required evidence | Status | Artifact reference |",
                "|---|---|---|---|",
                "| Recall | recall@10 recorded | code-level complete | |",
            ]
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, f"{evidence}|rag full50")

    assert result.returncode == 1
    assert "marked complete" in result.stdout
    assert "Recall" in result.stdout


def test_release_evidence_validation_accepts_existing_artifact_reference(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    artifact = (
        repo_root
        / "docs"
        / "release"
        / "evidence"
        / "artifacts"
        / "validator-existing-artifact-test.json"
    )
    artifact.write_text('{"ok": true}\n', encoding="utf-8")
    evidence = tmp_path / "payment.md"
    try:
        evidence.write_text(
            "\n".join(
                [
                    "Status: complete",
                    "Owner: Payment release owner",
                    "Environment: sandbox",
                    "Date range: 2026-05-07 live run",
                    "",
                    "| Area | Required evidence | Status | Artifact reference |",
                    "|---|---|---|---|",
                    (
                        "| WeChat Pay | order creation | pass | "
                        "docs/release/evidence/artifacts/validator-existing-artifact-test.json |"
                    ),
                ]
            ),
            encoding="utf-8",
        )

        result = _validate(repo_root, f"{evidence}|payment sandbox")

        assert result.returncode == 0, result.stdout + result.stderr
    finally:
        artifact.unlink(missing_ok=True)


def test_release_evidence_validation_rejects_missing_artifact_reference(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    evidence = tmp_path / "payment.md"
    evidence.write_text(
        "\n".join(
            [
                "Status: complete",
                "Owner: Payment release owner",
                "Environment: sandbox",
                "Date range: 2026-05-07 live run",
                "",
                "| Area | Required evidence | Status | Artifact reference |",
                "|---|---|---|---|",
                (
                    "| WeChat Pay | order creation | pass | "
                    "docs/release/evidence/artifacts/missing-payment-artifact.json |"
                ),
            ]
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, f"{evidence}|payment sandbox")

    assert result.returncode == 1
    assert "references missing artifact files" in result.stdout
    assert "missing-payment-artifact.json" in result.stdout


def test_release_evidence_validation_rejects_complete_with_pending_prose(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    evidence = tmp_path / "desktop.md"
    evidence.write_text(
        "\n".join(
            [
                "Status: complete",
                "Owner: Desktop release owner",
                "Environment: signed package smoke",
                "Date range: 2026-05-07 packaged run",
                "",
                "This file remains `Status: pending` because signed packaging was not exercised.",
                "",
                "| Area | Required evidence | Status | Artifact reference |",
                "|---|---|---|---|",
                "| Signing | notarized DMG | pass | artifact-001 |",
            ]
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, f"{evidence}|desktop runtime")

    assert result.returncode == 1
    assert "conflicting pending/not-ready prose" in result.stdout
    assert "Status: pending" in result.stdout


def test_release_evidence_validation_json_output_is_machine_readable(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    evidence = tmp_path / "payment.md"
    evidence.write_text(
        "\n".join(
            [
                "Status: complete",
                "Owner: TBD",
                "Environment: sandbox",
                "Date range: 2026-05-07 live run",
                "",
                "| Area | Required evidence | Status | Artifact reference |",
                "|---|---|---|---|",
                "| WeChat Pay | order creation | pass | artifact-001 |",
            ]
        ),
        encoding="utf-8",
    )

    result = _validate(repo_root, "--json", f"{evidence}|payment sandbox")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["failures"]
    assert payload["warnings"]
    assert any("Owner: TBD" in warning for warning in payload["warnings"])
