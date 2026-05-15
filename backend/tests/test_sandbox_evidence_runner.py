import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace


def _runner(
    repo_root: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "sandbox-evidence-runner.py"), *args],
        cwd=repo_root,
        env=merged_env,
        text=True,
        capture_output=True,
        check=False,
    )


def _load_runner_module(repo_root: Path):
    module_path = repo_root / "scripts" / "sandbox-evidence-runner.py"
    spec = importlib.util.spec_from_file_location("sandbox_evidence_runner", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_live_mode_requires_explicit_side_effect_confirmation():
    repo_root = Path(__file__).resolve().parents[2]

    result = _runner(repo_root, "--scope", "wechat_pay", "--live")

    assert result.returncode == 2
    assert "--live requires --confirm-live-side-effects" in result.stderr


def test_preflight_writes_only_redacted_payment_configuration(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    private_key = tmp_path / "merchant-private.pem"
    platform_key = tmp_path / "platform-public.pem"
    out = tmp_path / "payment-preflight.json"
    private_key.write_text("PRIVATE KEY MATERIAL THAT MUST NOT LEAK", encoding="utf-8")
    platform_key.write_text("PUBLIC KEY MATERIAL", encoding="utf-8")
    secret_api_key = "sk_live_value_that_must_not_appear"
    merchant_private_key = "merchant_private_key_value_that_must_not_appear"
    env = {
        "PAYMENT_NOTIFY_BASE_URL": "https://sandbox-payments.anxin.test/callbacks?token=hidden",
        "WECHAT_PAY_APP_ID": "wx1234567890abcdef",
        "WECHAT_PAY_MCH_ID": "1900000109",
        "WECHAT_PAY_MERCHANT_SERIAL_NO": "SERIAL1234567890",
        "WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH": str(private_key),
        "WECHAT_PAY_MERCHANT_PRIVATE_KEY": merchant_private_key,
        "WECHAT_PAY_PLATFORM_SERIAL": "PLATFORM987654321",
        "WECHAT_PAY_PLATFORM_PUBLIC_KEY_PATH": str(platform_key),
        "WECHAT_PAY_API_V3_KEY": secret_api_key,
        "WECHAT_PAY_OFFICIAL_WEBHOOK_ENABLED": "true",
    }

    result = _runner(repo_root, "--scope", "wechat_pay", "--out", str(out), env=env)

    assert result.returncode == 0, result.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    serialized = json.dumps(report, ensure_ascii=False)
    stdout_and_report = result.stdout + serialized

    assert report["mode"] == "preflight"
    assert report["providers"]["wechat_pay"]["configured"] is True
    assert "token=hidden" not in stdout_and_report
    assert secret_api_key not in stdout_and_report
    assert merchant_private_key not in stdout_and_report
    fields = {field["name"]: field for field in report["providers"]["wechat_pay"]["fields"]}
    assert fields["WECHAT_PAY_API_V3_KEY"]["redacted"] == "set"
    assert fields["WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH"]["redacted"].startswith(
        "path:merchant-private.pem:exists=true"
    )
    assert (
        fields["PAYMENT_NOTIFY_BASE_URL"]["redacted"]
        == "https://sandbox-payments.anxin.test/callbacks"
    )


def test_sandbox_required_env_fields_are_documented_in_templates():
    repo_root = Path(__file__).resolve().parents[2]
    runner = _load_runner_module(repo_root)
    required_names = sorted(
        {
            name
            for provider_requirements in runner.REQUIREMENTS.values()
            for requirement in provider_requirements
            for name in requirement.names
        }
    )

    for template in (repo_root / ".env.example", repo_root / "backend" / ".env.example"):
        text = template.read_text(encoding="utf-8")
        missing = [
            name
            for name in required_names
            if not re.search(rf"^{re.escape(name)}=", text, re.MULTILINE)
        ]
        assert missing == [], f"{template} is missing sandbox evidence fields: {missing}"


def test_preflight_reports_live_runtime_prerequisites(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    out = tmp_path / "sandbox-preflight.json"

    result = _runner(repo_root, "--scope", "all", "--out", str(out))

    assert result.returncode == 0, result.stderr
    report = json.loads(out.read_text(encoding="utf-8"))

    wechat_prereqs = {
        prereq["argument"]: prereq
        for prereq in report["providers"]["wechat_pay"]["runtime_prerequisites"]
    }
    alipay_prereqs = {
        prereq["argument"]: prereq
        for prereq in report["providers"]["alipay"]["runtime_prerequisites"]
    }
    esignbao_prereqs = {
        prereq["argument"]: prereq
        for prereq in report["providers"]["esignbao"]["runtime_prerequisites"]
    }
    fadada_prereqs = {
        prereq["argument"]: prereq
        for prereq in report["providers"]["fadada"]["runtime_prerequisites"]
    }

    assert wechat_prereqs["--wechat-refund-order-id"]["status"] == "missing"
    assert alipay_prereqs["--alipay-query-order-id"]["status"] == "missing"
    assert alipay_prereqs["--alipay-refund-order-id"]["status"] == "missing"
    assert alipay_prereqs["--alipay-close-order-id"]["status"] == "missing"
    assert esignbao_prereqs["--esign-document-url"]["status"] == "missing"
    assert esignbao_prereqs["--esignbao-completed-flow-id"]["status"] == "missing"
    assert fadada_prereqs["--esign-document-url"]["status"] == "missing"
    assert fadada_prereqs["--fadada-completed-flow-id"]["status"] == "missing"

    wechat_external = {
        item["id"]: item
        for item in report["providers"]["wechat_pay"]["external_evidence_requirements"]
    }
    alipay_external = {
        item["id"]: item for item in report["providers"]["alipay"]["external_evidence_requirements"]
    }
    esignbao_external = {
        item["id"]: item
        for item in report["providers"]["esignbao"]["external_evidence_requirements"]
    }
    fadada_external = {
        item["id"]: item for item in report["providers"]["fadada"]["external_evidence_requirements"]
    }

    assert wechat_external["official_success_callback"]["release_blocking"] is True
    assert wechat_external["platform_key_rotation"]["status"] == "pending_external_input"
    assert alipay_external["failed_notification_retry"]["artifact_ref"] == "TBD"
    assert esignbao_external["official_callback"]["collection_method"]
    assert fadada_external["failed_callback_retry"]["release_blocking"] is True


def test_live_probe_validators_preserve_pending_and_failure_states():
    repo_root = Path(__file__).resolve().parents[2]
    runner = _load_runner_module(repo_root)

    refund_status, refund_reason = runner._validate_refund_result(SimpleNamespace(status="pending"))
    assert refund_status == "pending"
    assert "terminal success" in refund_reason

    flow_status, flow_reason = runner._validate_sign_flow_creation(SimpleNamespace(sign_urls={}))
    assert flow_status == "pending"
    assert "no signer URL" in flow_reason

    close_status, close_reason = runner._validate_boolean_result(
        False,
        action="close order",
    )
    assert close_status == "pending"
    assert "documented terminal-state evidence" in close_reason

    download_status, download_reason = runner._validate_download_content(b"")
    assert download_status == "fail"
    assert download_reason == "Downloaded signed document is empty."


def test_release_evidence_templates_list_live_runtime_flags_and_retry_rows():
    repo_root = Path(__file__).resolve().parents[2]
    payment_template = (
        repo_root / "docs" / "release" / "evidence" / "payment-sandbox.md"
    ).read_text(encoding="utf-8")
    esign_template = (repo_root / "docs" / "release" / "evidence" / "esign-sandbox.md").read_text(
        encoding="utf-8"
    )

    for flag in (
        "--wechat-refund-order-id",
        "--alipay-query-order-id",
        "--alipay-refund-order-id",
        "--alipay-close-order-id",
    ):
        assert flag in payment_template
    assert "Duplicate payment notification is idempotent" in payment_template

    for flag in (
        "--esign-document-url",
        "--esignbao-completed-flow-id",
        "--fadada-completed-flow-id",
    ):
        assert flag in esign_template
    assert "Duplicate callback is idempotent" in esign_template
    assert "Failed callback enters retry/failed path without fake success" in esign_template


def test_external_handoff_docs_list_live_runtime_flags():
    repo_root = Path(__file__).resolve().parents[2]
    docs = {
        "handoff": repo_root / "docs" / "release" / "external-resource-handoff.md",
        "runbook": repo_root / "docs" / "release" / "evidence-collection-runbook.md",
        "plan": repo_root / "docs" / "release" / "48-hour-commercial-delivery-plan.md",
        "inputs": repo_root / "docs" / "release" / "external-inputs-checklist.md",
    }
    required_flags = (
        "--wechat-refund-order-id",
        "--refund-total-amount",
        "--alipay-query-order-id",
        "--alipay-refund-order-id",
        "--alipay-close-order-id",
        "--esignbao-completed-flow-id",
        "--fadada-completed-flow-id",
    )

    for name, path in docs.items():
        text = path.read_text(encoding="utf-8")
        missing = [flag for flag in required_flags if flag not in text]
        assert missing == [], f"{name} is missing live runtime flags: {missing}"
