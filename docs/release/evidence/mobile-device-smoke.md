# Mobile And Mini-Program Device Smoke Evidence

> **2026-05 路线调整脚注**：原 2026-05-09 决定"未来移动端/小程序开发统一进入 uni-app（`apps/uni-mobile/`）"已在 2026-05 终止。本文件中所有涉及 `apps/uni-mobile/`、`scripts/uni-mobile-*.sh`、`docs/mobile/uni-app-migration-plan.md`、DCloud 的段落均不再适用 — 现有移动能力回到 `mobile/`（Expo + RN），小程序回到 `mini-program/`（Taro），两端独立演进。下文 uni-app 行保留为历史记录。

Status: pending
Owner: TBD
Environment: code-level mobile/mini smoke complete for the current Expo/Taro clients; Expo config, SDK dependency guard, Expo Metro config, Expo doctor, mobile result surface guard, mobile remote-control safe-probe enqueue/status/cancel/audit timeline visibility, mini-program privacy and navigation boundary guards, WeChat DevTools CLI project smoke, and iOS Simulator Expo Go supporting app-run complete; cross-platform token drift audit complete; Android, interactive WeChat DevTools / real device, and real cross-device continuation pending
Date range: 2026-05-06 to 2026-05-09 local collection

> Simulator/unit tests are useful but insufficient. This evidence requires real or official-device-tool runs for the critical user stories.

## Required Scope

| Platform | Required evidence | Status | Artifact reference |
|---|---|---|---|
| iOS | Login, approval detail, chat continuation, settings error state | pending | TBD |
| iOS Simulator | Expo Go opens local app and completes iOS JS bundle | supporting complete; official/real-device verification pending | `docs/release/evidence/artifacts/mobile-ios-simulator-expo-go-smoke-20260508.json`; `docs/release/evidence/artifacts/mobile-ios-simulator-expo-go-smoke-20260508.log` |
| Android | Login, approval detail, chat continuation, settings error state | pending | TBD |
| WeChat Mini Program | `wx.login -> code2session -> JWT` without leaking `session_key` | pending | TBD |
| WeChat Mini Program | News/empty-state path shows no fake fallback content | pending | TBD |
| Mobile UI | Bottom tabs, safe area, and 44px touch target token baseline | code-level complete; device verification pending | `mobile/src/constants/layout.ts`, `mini-program/src/app.scss` |
| Design system | Cross-platform token drift audit across Web/desktop, mobile, and mini-program | code-level complete; fixes pending | `docs/design/cross-platform-token-drift.md` |
| uni-app migration | Future mobile App and Mini Program development uses one uni-app base; old Expo/Taro clients are legacy references until equivalent evidence exists | code-level base complete; device/cloud build evidence pending | `docs/mobile/uni-app-migration-plan.md`; `docs/release/evidence/artifacts/uni-mobile-base-smoke-20260509.json`; `mobile/README.md`; `mini-program/README.md` |
| Release communication | Error-state release notes explain removal of silent fallback | draft complete; final notes pending | `docs/release/mobile-error-state-release-notes.md` |
| Mobile security | `npm audit --omit=dev` has no production vulnerabilities after targeted Expo SDK 52 toolchain overrides plus `@babel/plugin-transform-modules-systemjs` / `fast-uri` overrides | code-level complete; device verification pending | `docs/release/evidence/artifacts/mobile-mini-code-smoke-20260509.json` -> `mobile_npm_audit.status=passed,total=0` |
| Mobile remote control | Confirmed-pairing state can request a short-lived `desktop:control` route token and enqueue only `desktop.status_probe`; local mode blocks before network I/O; queued/claimed safe probes can be refreshed and cancelled from mobile; the page now shows a redacted remote-control audit timeline without rendering raw payload/metadata; desktop execution still requires host callback evidence | code-level complete; cross-device/device verification pending | `mobile/app/desktop-control.tsx`, `mobile/src/services/api.test.ts`, `mobile/src/features/desktop-control/model.test.ts` |
| Cross-device | Web/desktop/mobile conversation continuation verified | code-level complete; device/shared staging verification pending | `docs/release/evidence/artifacts/cross-device-continuation-code-smoke-20260509.json`; proves backend SyncService desktop/web/mobile flow, desktop sync adapter, and uni-app sync client contract with `release_evidence_complete=false` |
| Error semantics | Backend/network failures show explicit empty/error state, not mock success | pending | TBD |

## Verification Commands

```bash
bash scripts/mobile-device-smoke.sh \
  --out docs/release/evidence/artifacts/mobile-mini-code-smoke-YYYYMMDD.json \
  --manual-template-out docs/release/evidence/artifacts/mobile-device-manual-template-YYYYMMDD.json
bash scripts/mobile-ios-simulator-smoke.sh \
  --out docs/release/evidence/artifacts/mobile-ios-simulator-expo-go-smoke-YYYYMMDD.json \
  --log-out docs/release/evidence/artifacts/mobile-ios-simulator-expo-go-smoke-YYYYMMDD.log
bash scripts/uni-mobile-smoke.sh \
  --out docs/release/evidence/artifacts/uni-mobile-base-smoke-YYYYMMDD.json
bash scripts/cross-device-continuation-smoke.sh \
  --out docs/release/evidence/artifacts/cross-device-continuation-code-smoke-YYYYMMDD.json
cd mobile && npm test
cd mobile && npx tsc --noEmit --module esnext
cd mobile && npx expo-doctor
cd mini-program && npx tsc --noEmit --skipLibCheck --noUnusedLocals false
cd mini-program && npm run check-privacy-boundary
cd mini-program && npm run check-navigation-boundary
cd mini-program && npm run build:weapp
cd apps/uni-mobile && npm run typecheck
cd apps/uni-mobile && npm test
cd apps/uni-mobile && npm run audit:prod
cd apps/uni-mobile && npm run build:mp-weixin
cd apps/uni-mobile && npm run build:h5
```

## Latest Local Collection

Command:

```bash
bash scripts/mobile-device-smoke.sh \
  --out docs/release/evidence/artifacts/mobile-mini-code-smoke-20260509.json \
  --manual-template-out docs/release/evidence/artifacts/mobile-device-manual-template-20260508.json
bash scripts/uni-mobile-smoke.sh \
  --out docs/release/evidence/artifacts/uni-mobile-base-smoke-20260509.json
```

Result refreshed on 2026-05-09 local time:

| Check | Result |
|---|---|
| mobile Vitest suite | `8 files / 37 tests passed` in the latest smoke artifact |
| mobile TypeScript check | exit `0` |
| mobile result surface guard | exit `0`; static guard verifies investigation and knowledge submissions render in-page result cards instead of relying on Alert-only feedback |
| mobile lawyer conversion guard | exit `0`; static guard verifies find-lawyer creates real consultation records, renders AI anonymous summaries, selects lawyers in-page, exposes anonymous chat/delegation API paths, and does not route to a missing lawyer detail page |
| mobile Expo config/dependency guard | exit `0`; `expo-asset`, `expo-notifications`, `expo-device`, and `expo-font` are installed and aligned with `mobile/app.json`; `expo/metro-config` can instantiate Metro config; `npx expo config --json --full` and `npx expo install --check` pass |
| mobile Expo doctor | exit `0`; `17/17 checks passed` |
| mobile npm audit security summary | exit `0`; `critical=0`, `high=0`, `total=0`; `@xmldom/xmldom`, `@expo/plist`, Expo CLI `tar`, and Metro `postcss` findings are remediated by targeted overrides; `tar@7.5.14` crosses Expo CLI's declared semver range, so Expo doctor and real-device smoke remain required release verification |
| mini-program TypeScript check | exit `0` |
| mini-program privacy boundary guard | exit `0`; static guard verifies `local` / `top-secret` block before `Taro.request`, login blocks before `Taro.login`, and index/chat render privacy-specific error states |
| mini-program navigation boundary guard | exit `0`; static guard verifies home/profile primary entries do not use empty paths or generic development placeholders |
| mini-program WeChat build | exit `0`; Taro compiled successfully |
| mini-program WeChat DevTools CLI smoke | exit `0`; `/Applications/wechatwebdevtools.app/Contents/MacOS/cli auto --project <repo>/mini-program --trust-project` accepted `touristappid` |
| mobile and mini fake fallback guard | exit `0`; guards against `fallbackMessages`, `fallbackTask`, `mock_token`, leaked `session_key`, fake success markers; confirms `wx.login/code2session` path and no fake news fallback |
| mobile and mini refresh auth guard | exit `0`; mobile Vitest covers network refresh failure preserving auth, desktop-control status endpoint routing, audit-events endpoint routing, local-mode desktop-control no-network state, route-token issuance, safe-probe command enqueue/status/cancel, audit label formatting, and privacy guard `X-Privacy-Mode` propagation; script guard verifies mobile/mini separate auth expiry from transient refresh failure and mini-program privacy fail-closed markers |
| cross-platform token drift audit | `docs/design/cross-platform-token-drift.md` created; mini-program semantic token layer and touch-target baseline are code-level complete; remaining P0 items are brand primary direction and real-device touch-target verification |
| code-level JSON artifact | `docs/release/evidence/artifacts/mobile-mini-code-smoke-20260509.json`; `status=passed`, `release_evidence_complete=false`, includes Expo guard and `mobile_npm_audit.status=passed,total=0` |
| manual device template | `docs/release/evidence/artifacts/mobile-device-manual-template-20260508.json`; `status=template`, `release_evidence_complete=false` |
| host device probe | `docs/release/evidence/artifacts/mobile-device-host-probe-20260508.json`; iOS Simulator is available with iOS 26.4 devices, ADB has no connected devices, Android emulator CLI is missing, WeChat DevTools and WeChat apps are present |
| iOS Simulator Expo Go smoke | `bash scripts/mobile-ios-simulator-smoke.sh --out docs/release/evidence/artifacts/mobile-ios-simulator-expo-go-smoke-20260508.json --log-out docs/release/evidence/artifacts/mobile-ios-simulator-expo-go-smoke-20260508.log --timeout 90` -> exit `0`; boots iPhone 17 simulator, verifies `expo-asset` and Expo Metro config, opens Expo Go on the local Expo URL, and records `iOS Bundled`; artifact has `release_evidence_complete=false` |
| uni-app migration decision | `docs/mobile/uni-app-migration-plan.md` records feasibility, target directory, old-client cleanup plan, P0 feature scope, and evidence gates; `mobile/README.md` and `mini-program/README.md` mark current Expo/Taro clients as legacy |
| uni-app base smoke | `bash scripts/uni-mobile-smoke.sh --out docs/release/evidence/artifacts/uni-mobile-base-smoke-20260509.json` -> exit `0`; migration guard, `apps/uni-mobile` typecheck, `5 files / 12 tests passed`, production npm audit `0`, H5 build, and WeChat Mini Program build pass; artifact has `release_evidence_complete=false` |
| cross-device continuation code smoke | `bash scripts/cross-device-continuation-smoke.sh --out docs/release/evidence/artifacts/cross-device-continuation-code-smoke-20260509.json` -> exit `0`; backend sync continuation `5 passed`, desktop adapter `10 passed`, uni-app sync client `5 passed`; artifact has `release_evidence_complete=false` |

Code-level hardening added in this collection:

- `mobile/app/messages/[id].tsx` no longer renders fallback conversation content when message loading fails; it now shows loading, empty, or explicit error states.
- `mobile/app/tasks/[id].tsx` no longer creates a synthetic fallback task; it uses server data or route-provided real summary and surfaces load errors explicitly.
- `mobile/app/desktop-control.tsx` and `mobile/src/features/desktop-control/model.ts` add a fail-closed desktop-control status, safe-probe surface, and redacted audit timeline; local privacy mode never calls the network, hybrid/cloud mode reads `/sync/remote-control/status` and `/sync/remote-control/audit-events`, and only a confirmed pairing with both `desktop_device_id` and `pairing_id` enables the safe-probe action.
- `mobile/src/services/api.ts` now exposes governed remote-control pairing, route-token, command enqueue, command status, command cancel, audit-event listing, and `desktop.status_probe` helpers; `mobile/src/services/api.test.ts` verifies route-token issuance, safe-probe payload shape, pairing request routing, status/cancel/audit endpoint routing, and local-mode zero network calls before command enqueue.
- `mobile/src/features/workflow/detail-model.ts` now maps string transport errors such as timeout or failed fetch to the explicit network failure copy, and tests status precedence over misleading backend text.
- `mobile/src/constants/layout.ts` now exposes `touchTarget.min=44`; the bottom Tab and EmptyState action use the token, and `mobile/src/constants/layout.test.ts` guards it.
- `mobile/src/services/api.ts` now keeps the stored session when refresh-token retry fails due to weak network/timeout; it clears auth only when the refresh endpoint confirms 401/403, with `mobile/src/services/api.test.ts` covering both paths.
- `mobile/src/services/api.ts` now reads the stored privacy mode before outbound requests, sends `X-Privacy-Mode` in hybrid/cloud modes, and fails closed before `fetch` in local mode; `mobile/src/services/api.test.ts` covers header propagation and zero network calls in local mode.
- `mini-program/src/services/api.ts` now reads the stored privacy mode before outbound requests, sends `X-Privacy-Mode`, and fails closed before `Taro.request` in `local` / `top-secret` modes; `mini-program/src/pages/profile/index.tsx` blocks login before `Taro.login`, and `mini-program/scripts/check-privacy-boundary.js` guards the boundary.
- `apps/uni-mobile/src/services/sync.ts` adds the forward mobile sync client contract for `/sync/push` and `/sync/pull`, with `sync.test.ts` covering conversation continuation record shape and shared backend endpoint routing.
- `mobile/package.json` now declares Expo SDK 52-compatible `expo-notifications`, `expo-device`, `expo-font`, `@expo/vector-icons`, `@react-native-async-storage/async-storage`, `react-native`, and `react-native-safe-area-context` versions so `mobile/app.json` config plugins and native peer dependencies resolve before device smoke.
- `mobile/package.json` now declares `expo-asset` directly because Expo Metro config requires project-level resolution before iOS Simulator app-run can bundle.
- `mini-program/src/services/api.ts` now mirrors that refresh-token distinction so transient refresh failure does not silently erase `token`/`refresh_token`.
- `mini-program/project.config.json` now uses `touristappid` for local WeChat DevTools CLI smoke; real upload still requires the official appid in the release environment.
- `mini-program/src/app.scss` now exposes `$touch-target-min: 88rpx` and applies it to homepage actions, profile menu items, and chat send actions.
- `mini-program/src/styles/design-tokens.scss` and `design-tokens.ts` now hold mini-program semantic tokens; the homepage, chat, profile SCSS files, and `app.config.ts` import those tokens instead of hardcoding page colors.
- `docs/design/cross-platform-token-drift.md` records Web/desktop, mobile, and mini-program token drift without changing design tokens; fixes remain separate release work.
- `docs/release/mobile-error-state-release-notes.md` drafts the user/support explanation for explicit error states after silent fallback removal.

This file remains `Status: pending` because the iOS Simulator Expo Go smoke, uni-app base smoke, and cross-device continuation rehearsal are supporting/code-level evidence only. They do not cover the required signed/official App build, real device user stories, Android, interactive WeChat DevTools or real-device evidence, DCloud cloud build/signing, and shared staging account cross-device continuation. Mobile production npm audit, local iOS bundling, the new uni-app base, and the sync-client contract are now fixed in code-level/supporting artifacts, but runtime device evidence is still required before release Go.

The 2026-05-09 uni-app decision does not make the old device evidence complete. It changes the forward development target and now has a runnable base: new mobile App and Mini Program features should land in `apps/uni-mobile/`, while `mobile/` and `mini-program/` remain legacy references until module-by-module migration, dual-run tests, and device/DevTools evidence allow cleanup.

## Completion Notes

- Record device model, OS version, app build, backend environment, and tester.
- Store screenshots/video clips with secrets and PII redacted.
- Link to interactive WeChat DevTools or real-device logs.
- Use the manual template artifact fields for iOS, Android, WeChat Mini Program, explicit error states, and cross-device continuation before changing this file to `Status: complete`.
- For mobile remote control, capture the full sequence: status ready with confirmed pairing, route-token issuance, safe-probe command queued, redacted audit timeline visible, desktop host callback, cancellation/failure path, and local/top-secret denial.
- Keep the mobile npm audit fix evidence attached and rerun it after any Expo SDK/package changes before changing this file to `Status: complete`.
