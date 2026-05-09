import json
import subprocess
from pathlib import Path


def _run_validator(
    repo_root: Path, manifest: Path | None = None
) -> subprocess.CompletedProcess[str]:
    command = ["node", "scripts/validate-external-resource-requirements.cjs"]
    if manifest is not None:
        command.append(str(manifest))
    return subprocess.run(
        command,
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def test_external_resource_requirements_manifest_is_valid():
    repo_root = Path(__file__).resolve().parents[2]

    result = _run_validator(repo_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "External resource requirements: OK" in result.stdout


def test_external_resource_requirements_rejects_real_value_fields(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    source = repo_root / "docs/release/external-resource-requirements.json"
    manifest = json.loads(source.read_text(encoding="utf-8"))
    manifest["resources"][0]["items"][0]["value"] = "do-not-store-real-values"
    target = tmp_path / "external-resource-requirements.json"
    target.write_text(json.dumps(manifest), encoding="utf-8")

    result = _run_validator(repo_root, target)

    assert result.returncode == 1
    assert "is forbidden" in result.stderr


def test_external_resource_requirements_rejects_missing_required_p0_env(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    source = repo_root / "docs/release/external-resource-requirements.json"
    manifest = json.loads(source.read_text(encoding="utf-8"))
    for resource in manifest["resources"]:
        for item in resource["items"]:
            if item.get("env_names") == ["WECHAT_PAY_API_V3_KEY"]:
                item["env_names"] = ["WECHAT_PAY_API_V3_KEY_MISSING"]
    target = tmp_path / "external-resource-requirements.json"
    target.write_text(json.dumps(manifest), encoding="utf-8")

    result = _run_validator(repo_root, target)

    assert result.returncode == 1
    assert "WECHAT_PAY_API_V3_KEY" in result.stderr
