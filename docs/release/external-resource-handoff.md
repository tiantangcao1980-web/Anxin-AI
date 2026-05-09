# External Resource Handoff

> Date: 2026-05-09
> Status: ready for external input collection. Do not paste secrets, account passwords, phone numbers, ID numbers, private keys, or contract originals into this file.

This is the operator handoff for the remaining commercial-release blockers. Store secrets in the approved secret manager or a local untracked `.env`; store screenshots, videos, and provider logs as redacted release artifacts.

## Payment

Required inputs:

| Provider | Input | Env or runner field |
|---|---|---|
| Common | Public callback base URL | `PAYMENT_NOTIFY_BASE_URL` |
| WeChat Pay | App ID | `WECHAT_PAY_APP_ID` |
| WeChat Pay | Merchant ID | `WECHAT_PAY_MCH_ID` |
| WeChat Pay | Merchant cert serial | `WECHAT_PAY_MERCHANT_SERIAL_NO` |
| WeChat Pay | Merchant private key or file path | `WECHAT_PAY_MERCHANT_PRIVATE_KEY` / `WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH` |
| WeChat Pay | Platform serial | `WECHAT_PAY_PLATFORM_SERIAL` |
| WeChat Pay | Platform public key or file path | `WECHAT_PAY_PLATFORM_PUBLIC_KEY` / `WECHAT_PAY_PLATFORM_PUBLIC_KEY_PATH` |
| WeChat Pay | API v3 key | `WECHAT_PAY_API_V3_KEY` |
| WeChat Pay | Official webhook enable flag | `WECHAT_PAY_OFFICIAL_WEBHOOK_ENABLED=true` |
| WeChat Pay | Paid sandbox order ID for refund evidence | `--wechat-refund-order-id` |
| WeChat Pay | Original paid order amount | `--refund-total-amount` |
| Alipay | App ID | `ALIPAY_APP_ID` |
| Alipay | App private key or file path | `ALIPAY_PRIVATE_KEY` / `ALIPAY_PRIVATE_KEY_PATH` |
| Alipay | Alipay public key or file path | `ALIPAY_PUBLIC_KEY` / `ALIPAY_PUBLIC_KEY_PATH` |
| Alipay | Sandbox/preprod gateway | `ALIPAY_GATEWAY_URL` |
| Alipay | Official webhook enable flag | `ALIPAY_OFFICIAL_WEBHOOK_ENABLED=true` |
| Alipay | Existing sandbox order ID for query | `--alipay-query-order-id` |
| Alipay | Paid sandbox order ID for refund | `--alipay-refund-order-id` |
| Alipay | Open sandbox order ID for close | `--alipay-close-order-id` |

After receipt:

```bash
python3 scripts/sandbox-evidence-runner.py --scope payment \
  --out docs/release/evidence/artifacts/payment-sandbox-preflight-YYYYMMDD.json

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
```

Completion evidence:

- successful payment
- failed payment
- refund
- close order
- official async notification
- idempotent duplicate notification
- cert/key rotation or platform-key refresh proof

Fill the generated `external_evidence_requirements[].artifact_ref` fields with redacted provider dashboard, callback delivery, retry, and rotation artifact paths before marking payment evidence complete.

## E-Sign

Required inputs:

| Provider | Input | Env or runner field |
|---|---|---|
| e签宝 | App ID | `ESIGN_BAO_APP_ID` |
| e签宝 | App secret | `ESIGN_BAO_APP_SECRET` |
| e签宝 | Sandbox/preprod API URL | `ESIGN_BAO_API_URL` |
| 法大大 | App ID | `FADADA_APP_ID` |
| 法大大 | App secret | `FADADA_APP_SECRET` |
| 法大大 | Sandbox/preprod API URL | `FADADA_API_URL` |
| Common | Official webhook enable flag | `ESIGN_OFFICIAL_WEBHOOK_ENABLED=true` |
| Common | Redacted sandbox test contract or file ID | `--esign-document-url` |
| Common | Completed sandbox flow ID for download test | `--esignbao-completed-flow-id` / `--fadada-completed-flow-id` |

After receipt:

```bash
python3 scripts/sandbox-evidence-runner.py --scope esign \
  --out docs/release/evidence/artifacts/esign-sandbox-preflight-YYYYMMDD.json

python3 scripts/sandbox-evidence-runner.py --scope esignbao --live --confirm-live-side-effects \
  --esign-document-url <sandbox-file-id-or-doc-url> \
  --esignbao-completed-flow-id <completed-sandbox-flow-id> \
  --out docs/release/evidence/artifacts/esignbao-live-YYYYMMDD.json

python3 scripts/sandbox-evidence-runner.py --scope fadada --live --confirm-live-side-effects \
  --esign-document-url <sandbox-doc-id-or-url> \
  --fadada-completed-flow-id <completed-sandbox-flow-id> \
  --out docs/release/evidence/artifacts/fadada-live-YYYYMMDD.json
```

Completion evidence:

- create/start signing flow
- signer link or signing task
- status query
- revoke/cancel
- completed-document download
- official callback
- duplicate callback idempotency
- failed callback retry

Fill the generated `external_evidence_requirements[].artifact_ref` fields with redacted provider dashboard, callback delivery, idempotency, and retry artifact paths before marking e-sign evidence complete.

## Desktop Release

Required inputs:

| Input | Env, config, or artifact |
|---|---|
| Tauri signing identity | `desktop/tauri.conf.json` -> `bundle.macOS.signingIdentity` |
| Apple code signing identity | local Keychain identity visible to `security find-identity -v -p codesigning` |
| Notary credential | `NOTARYTOOL_KEYCHAIN_PROFILE` or Apple ID / App Store Connect API flow |
| Production APNs entitlement | already configured in `desktop/Entitlements.plist` as `com.apple.developer.aps-environment=production` |
| Signed release `.app` | `ANXIN_DESKTOP_RELEASE_APP` |
| Release DMG | `desktop/target/release/bundle/dmg` or release artifact path |

After receipt:

```bash
bash scripts/desktop-release-package.sh --dry-run \
  --out docs/release/evidence/artifacts/desktop-release-package-dry-run-YYYYMMDD.json \
  --preflight-out docs/release/evidence/artifacts/desktop-release-preflight-YYYYMMDD.json

bash scripts/desktop-release-preflight.sh \
  --out docs/release/evidence/artifacts/desktop-release-preflight-YYYYMMDD.json

bash scripts/desktop-release-profile-smoke.sh \
  --out docs/release/evidence/artifacts/desktop-release-profile-unsigned-smoke-YYYYMMDD.json
```

When `release_ready=true`, collect packaged evidence:

- signed/notarized installer verification
- packaged UI interaction transcript
- signed packaged-profile plaintext-to-SQLCipher migration transcript
- signed packaged runtime 100 push / 500 pull performance transcript
- push/pull/conflict/retry/backoff runtime transcript
- desktop/web/mobile cross-device continuation transcript

## Mobile And Mini-Program

Required inputs:

| Input | Artifact field |
|---|---|
| DCloud/uni-app account, application AppID, cloud build access | uni-app migration/build transcript |
| iOS build or TestFlight run | `platforms[].platform=ios`, `build_hash`, device transcript |
| Android build and device run | `platforms[].platform=android`, `build_hash`, device transcript |
| WeChat DevTools interactive run or real-device run | `platforms[].platform=wechat_mini_program`, DevTools/device transcript |
| WeChat Mini Program AppID/AppSecret and legal domain admin access | code2session and request/upload/download/web-view domain evidence |
| Staging backend environment | `backend_environment` |
| Redacted test account role | `tester_role` |
| Screenshot/video/log index | `screenshot_refs`, `log_refs` |
| Mobile npm audit fix/exception | official SDK/CLI fix evidence or security owner exception artifact |

2026-05-09 routing decision: future mobile App and Mini Program feature work moves to a uni-app client. Keep `mobile/` and `mini-program/` as legacy reference surfaces until the uni-app replacement has equivalent auth, privacy, approval, desktop-control, and device evidence. See `docs/mobile/uni-app-migration-plan.md`.

Code-level preflight:

```bash
bash scripts/mobile-device-smoke.sh \
  --out docs/release/evidence/artifacts/mobile-mini-code-smoke-YYYYMMDD.json \
  --manual-template-out docs/release/evidence/artifacts/mobile-device-manual-template-YYYYMMDD.json

bash scripts/uni-mobile-migration-guard.sh

bash scripts/uni-mobile-smoke.sh \
  --out docs/release/evidence/artifacts/uni-mobile-base-smoke-YYYYMMDD.json
```

Completion evidence:

- iOS login, approval detail, chat continuation, settings error state
- Android login, approval detail, chat continuation, settings error state
- DCloud/uni-app App cloud build or official package transcript
- WeChat `wx.login -> code2session -> JWT` with no `session_key` leak
- WeChat news/empty-state path with no fake fallback content
- explicit backend/network error states
- desktop/web/mobile cross-device continuation
- npm audit remains `0` after any SDK/package changes, or a named security exception is attached

## Final Gate

After all lane evidence is complete:

```bash
python3 scripts/validate-release-artifacts.py
bash scripts/release-evidence-secret-scan.sh
GITNEXUS_BIN=/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus \
  bash scripts/commercial-readiness-gate.sh --quick
GITNEXUS_BIN=/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus \
  bash scripts/commercial-readiness-gate.sh --with-local-tests
```

Only update release evidence files to `Status: complete` after every Required Scope row has a real artifact reference and the evidence secret scan passes.
