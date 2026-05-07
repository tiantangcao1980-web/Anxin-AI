# Payment Sandbox Evidence

Status: pending
Owner: TBD
Environment: staging/sandbox
Date range: TBD

> Do not paste merchant private keys, API v3 keys, platform certificates, access tokens, or raw customer PII into this file. Store secrets only in the approved secret manager and reference redacted log/artifact IDs here.

## Required Scope

This evidence file can be marked `Status: complete` only after both WeChat Pay and Alipay have been exercised against real sandbox or pre-production merchant channels.

| Channel | Required evidence | Status | Artifact reference |
|---|---|---|---|
| WeChat Pay | Native/order creation succeeds with signed request | pending | TBD |
| WeChat Pay | Query order response signature verified | pending | TBD |
| WeChat Pay | Close order succeeds or returns documented terminal state | pending | TBD |
| WeChat Pay | Refund succeeds with idempotency key | pending | TBD |
| WeChat Pay | Official payment success callback verifies RSA-SHA256 signature and decrypts resource | pending | TBD |
| WeChat Pay | Duplicate payment notification is idempotent and does not create duplicate business effects | pending | TBD |
| WeChat Pay | Platform certificate/public key rotation path verified | pending | TBD |
| WeChat Pay | Failed callback enters retry/failed path without fake success | pending | TBD |
| Alipay | `alipay.trade.page.pay` request signs and redirects in sandbox | pending | TBD |
| Alipay | `alipay.trade.query` response signature verified | pending | TBD |
| Alipay | `alipay.trade.refund` succeeds with idempotency | pending | TBD |
| Alipay | `alipay.trade.close` succeeds or returns documented terminal state | pending | TBD |
| Alipay | Async notification verifies RSA2 signature and `notify_id` idempotency | pending | TBD |
| Alipay | Failed notification enters retry/failed path without fake success | pending | TBD |

## Verification Commands

```bash
python3 scripts/sandbox-evidence-runner.py --scope payment --out docs/release/evidence/artifacts/payment-sandbox-preflight-YYYYMMDD.json

# Live provider calls are side-effectful and require real sandbox/pre-production credentials.
python3 scripts/sandbox-evidence-runner.py --scope wechat_pay --live --confirm-live-side-effects \
  --wechat-refund-order-id <paid-sandbox-order-id> \
  --refund-amount 0.01 \
  --refund-total-amount <original-order-amount> \
  --out docs/release/evidence/artifacts/wechat-pay-live-YYYYMMDD.json
python3 scripts/sandbox-evidence-runner.py --scope alipay --live --confirm-live-side-effects \
  --alipay-query-order-id <existing-sandbox-order-id> \
  --alipay-refund-order-id <paid-sandbox-order-id> \
  --alipay-close-order-id <open-sandbox-order-id> \
  --refund-amount 0.01 \
  --out docs/release/evidence/artifacts/alipay-live-YYYYMMDD.json

cd backend && ./.venv/bin/pytest -q tests/test_payment_provider_clients.py tests/test_official_webhook_security.py tests/test_webhook_business_events.py tests/test_refund_idempotency.py
```

The sandbox evidence runner emits redacted JSON only. It does not make this file complete by itself; provider dashboards, callback logs, retry evidence, and redacted artifact IDs must cover every row above.

## Latest Configuration Preflight

Command:

```bash
python3 scripts/sandbox-evidence-runner.py --scope payment --out docs/release/evidence/artifacts/payment-sandbox-preflight-20260507.json
```

Result: preflight artifact written to `docs/release/evidence/artifacts/payment-sandbox-preflight-20260507.json`; live checks were not run.

Current missing configuration:

- WeChat Pay: public callback base URL, app ID, merchant ID, merchant serial number, merchant private key, platform serial, platform public key, API v3 key for official callback decrypt, official webhook enabled.
- Alipay: public callback base URL, app ID, app private key, Alipay public key, official webhook enabled.

This confirms the remaining blocker is missing real sandbox/pre-production merchant configuration and live provider evidence, not a missing local evidence runner.

## Completion Notes

- Record sandbox merchant IDs in redacted form.
- Record event IDs / notify IDs in redacted form.
- Attach or link sanitized request/response logs.
- Record retry worker evidence for failed notifications.
