# E-Sign Sandbox Evidence

Status: deferred
Deferred-Reason: 产品方向调整 (2026-05-14) — 商业化电签 (e签宝/法大大) 不作为核心功能 PMF 验证阻断项; 签约场景优先接入广东省政务签章 (GDCA / 粤企签), 见 docs/integrations/guangdong-gov-signature.md
Deferred-Until: 政务签章接入完成或 PMF 后启动商业化电签 (预计 2026 Q3)
Owner: TBD
Environment: staging/sandbox
Date range: TBD

> **降级说明**: 见 [docs/DEVELOPMENT_PLAN.md §2.1 P8.D](../../DEVELOPMENT_PLAN.md) + [docs/integrations/guangdong-gov-signature.md](../../integrations/guangdong-gov-signature.md). 当前 ESIGN_PROVIDER 支持 5 渠道 (mock / gdca / yueqishang / esignbao / fadada); 商业化 e签宝/法大大降为 P3, 政务签章 GDCA/粤企签 仅框架占位🟡（未接入·调用即 raise ESignProviderConfigError，待商务对接凭据后推动）。

> Do not paste app secrets, access tokens, signing credentials, contract contents, signer phone numbers, or identity numbers into this file. Use redacted artifact references.

## Required Scope

This evidence file can be marked `Status: complete` only after both e签宝 and 法大大 have been exercised against real sandbox or pre-production accounts.

| Provider | Required evidence | Status | Artifact reference |
|---|---|---|---|
| e签宝 | Create flow with official signed request | pending | TBD |
| e签宝 | Start flow succeeds | pending | TBD |
| e签宝 | Generate signer URL succeeds | pending | TBD |
| e签宝 | Query flow status succeeds | pending | TBD |
| e签宝 | Signed document download succeeds | pending | TBD |
| e签宝 | Cancel/revoke succeeds or returns documented terminal state | pending | TBD |
| e签宝 | Official callback verifies `X-Tsign-Open-*` HMAC and writes audit | pending | TBD |
| e签宝 | Duplicate callback is idempotent and does not duplicate flow state transitions | pending | TBD |
| e签宝 | Failed callback enters retry/failed path without fake success | pending | TBD |
| 法大大 | Access token acquisition succeeds | pending | TBD |
| 法大大 | Sign task creation succeeds | pending | TBD |
| 法大大 | Actor URL succeeds | pending | TBD |
| 法大大 | Detail/status query succeeds | pending | TBD |
| 法大大 | Download URL succeeds | pending | TBD |
| 法大大 | Cancel succeeds or returns documented terminal state | pending | TBD |
| 法大大 | FASC callback verifies headers/body and writes audit | pending | TBD |
| 法大大 | Duplicate callback is idempotent and does not duplicate flow state transitions | pending | TBD |
| 法大大 | Failed callback enters retry/failed path without fake success | pending | TBD |

## Verification Commands

```bash
python3 scripts/sandbox-evidence-runner.py --scope esign --out docs/release/evidence/artifacts/esign-sandbox-preflight-YYYYMMDD.json

# Live provider calls are side-effectful and require real sandbox/pre-production accounts.
python3 scripts/sandbox-evidence-runner.py --scope esignbao --live --confirm-live-side-effects \
  --esign-document-url <sandbox-file-id-or-doc-url> \
  --esignbao-completed-flow-id <completed-sandbox-flow-id> \
  --out docs/release/evidence/artifacts/esignbao-live-YYYYMMDD.json
python3 scripts/sandbox-evidence-runner.py --scope fadada --live --confirm-live-side-effects \
  --esign-document-url <sandbox-doc-id-or-url> \
  --fadada-completed-flow-id <completed-sandbox-flow-id> \
  --out docs/release/evidence/artifacts/fadada-live-YYYYMMDD.json

cd backend && ./.venv/bin/pytest -q tests/test_esign_provider_clients.py tests/test_official_webhook_security.py tests/test_webhook_business_events.py tests/test_external_surface_guards.py
```

The sandbox evidence runner emits redacted JSON only. It does not make this file complete by itself; provider dashboards, callback logs, retry evidence, completed-flow download proof, and redacted artifact IDs must cover every row above.

## Latest Configuration Preflight

Command:

```bash
python3 scripts/sandbox-evidence-runner.py --scope esign --out docs/release/evidence/artifacts/esign-sandbox-preflight-20260507.json
```

Result: preflight artifact written to `docs/release/evidence/artifacts/esign-sandbox-preflight-20260507.json`; live checks were not run.

Current missing configuration:

- e签宝: app ID, app secret, official webhook enabled.
- 法大大: app ID, app secret, official webhook enabled.

This confirms the remaining blocker is missing real sandbox/pre-production e-sign account configuration and live provider evidence, not a missing local evidence runner.

## Completion Notes

- Record sandbox account IDs in redacted form.
- Record flow/task IDs in redacted form.
- Attach sanitized provider dashboards or logs.
- Confirm repeated callback idempotency and failed callback retry.
