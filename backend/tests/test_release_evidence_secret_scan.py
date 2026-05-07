import subprocess
from pathlib import Path


def _scan(repo_root: Path, target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(repo_root / "scripts" / "release-evidence-secret-scan.sh"), str(target)],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def test_release_evidence_secret_scan_passes_redacted_artifacts(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    target = tmp_path / "evidence"
    target.mkdir()
    (target / "payment.md").write_text(
        "\n".join(
            [
                "Status: complete",
                "merchant_private_key: <redacted>",
                "access_token: <redacted>",
                "signer_phone: 138****8000",
                "identity_number: 110************234",
            ]
        ),
        encoding="utf-8",
    )

    result = _scan(repo_root, target)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Release evidence secret scan: PASS" in result.stdout


def test_release_evidence_secret_scan_fails_on_raw_secret_and_pii(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    target = tmp_path / "evidence"
    target.mkdir()
    private_key_header = "-----BEGIN " + "PRIVATE KEY-----"
    private_key_footer = "-----END " + "PRIVATE KEY-----"
    access_token = "live_token_value_that_should_fail"
    phone = "138" + "0013" + "8000"
    identity_number = "110101" + "19900307" + "1234"
    (target / "bad-provider-log.md").write_text(
        "\n".join(
            [
                private_key_header,
                "secret-material",
                private_key_footer,
                f"ACCESS_TOKEN={access_token}",
                f"signer_phone={phone}",
                f"identity_number={identity_number}",
            ]
        ),
        encoding="utf-8",
    )

    result = _scan(repo_root, target)

    assert result.returncode == 1
    assert "Release evidence secret scan: FAIL" in result.stdout
    assert "bad-provider-log.md" in result.stdout
    assert access_token in result.stdout
