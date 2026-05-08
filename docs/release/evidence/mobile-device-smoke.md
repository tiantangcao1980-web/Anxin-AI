# Mobile And Mini-Program Device Smoke Evidence

Status: pending
Owner: TBD
Environment: code-level mobile/mini smoke complete; Expo config, SDK dependency guard, Expo Metro config, Expo doctor, mobile result surface guard, mini-program privacy and navigation boundary guards, WeChat DevTools CLI project smoke, and iOS Simulator Expo Go supporting app-run complete; cross-platform token drift audit complete; Android, interactive WeChat DevTools / real device, and cross-device continuation pending
Date range: 2026-05-06 to 2026-05-08 local collection

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
| Release communication | Error-state release notes explain removal of silent fallback | draft complete; final notes pending | `docs/release/mobile-error-state-release-notes.md` |
| Mobile security | `npm audit --omit=dev` has no production vulnerabilities after targeted Expo SDK 52 toolchain overrides | code-level complete; device verification pending | `docs/release/evidence/artifacts/mobile-mini-code-smoke-20260508.json` -> `mobile_npm_audit.status=passed,total=0` |
| Cross-device | Web/desktop/mobile conversation continuation verified | pending | TBD |
| Error semantics | Backend/network failures show explicit empty/error state, not mock success | pending | TBD |

## Verification Commands

```bash
bash scripts/mobile-device-smoke.sh \
  --out docs/release/evidence/artifacts/mobile-mini-code-smoke-YYYYMMDD.json \
  --manual-template-out docs/release/evidence/artifacts/mobile-device-manual-template-YYYYMMDD.json
bash scripts/mobile-ios-simulator-smoke.sh \
  --out docs/release/evidence/artifacts/mobile-ios-simulator-expo-go-smoke-YYYYMMDD.json \
  --log-out docs/release/evidence/artifacts/mobile-ios-simulator-expo-go-smoke-YYYYMMDD.log
cd mobile && npm test
cd mobile && npx tsc --noEmit --module esnext
cd mobile && npx expo-doctor
cd mini-program && npx tsc --noEmit --skipLibCheck --noUnusedLocals false
cd mini-program && npm run check-privacy-boundary
cd mini-program && npm run check-navigation-boundary
cd mini-program && npm run build:weapp
```

## Latest Local Collection

Command:

```bash
bash scripts/mobile-device-smoke.sh \
  --out docs/release/evidence/artifacts/mobile-mini-code-smoke-20260508.json \
  --manual-template-out docs/release/evidence/artifacts/mobile-device-manual-template-20260508.json
```

Result refreshed on 2026-05-08 local time:

| Check | Result |
|---|---|
| mobile Vitest suite | `8 files / 27 tests passed` |
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
| mobile and mini refresh auth guard | exit `0`; mobile Vitest covers network refresh failure preserving auth, desktop-control status endpoint routing, local-mode desktop-control no-network state, and privacy guard `X-Privacy-Mode` propagation; script guard verifies mobile/mini separate auth expiry from transient refresh failure and mini-program privacy fail-closed markers |
| cross-platform token drift audit | `docs/design/cross-platform-token-drift.md` created; mini-program semantic token layer and touch-target baseline are code-level complete; remaining P0 items are brand primary direction and real-device touch-target verification |
| code-level JSON artifact | `docs/release/evidence/artifacts/mobile-mini-code-smoke-20260508.json`; `status=passed`, `release_evidence_complete=false`, includes Expo guard and `mobile_npm_audit.status=passed,total=0` |
| manual device template | `docs/release/evidence/artifacts/mobile-device-manual-template-20260508.json`; `status=template`, `release_evidence_complete=false` |
| host device probe | `docs/release/evidence/artifacts/mobile-device-host-probe-20260508.json`; iOS Simulator is available with iOS 26.4 devices, ADB has no connected devices, Android emulator CLI is missing, WeChat DevTools and WeChat apps are present |
| iOS Simulator Expo Go smoke | `bash scripts/mobile-ios-simulator-smoke.sh --out docs/release/evidence/artifacts/mobile-ios-simulator-expo-go-smoke-20260508.json --log-out docs/release/evidence/artifacts/mobile-ios-simulator-expo-go-smoke-20260508.log --timeout 90` -> exit `0`; boots iPhone 17 simulator, verifies `expo-asset` and Expo Metro config, opens Expo Go on the local Expo URL, and records `iOS Bundled`; artifact has `release_evidence_complete=false` |

Code-level hardening added in this collection:

- `mobile/app/messages/[id].tsx` no longer renders fallback conversation content when message loading fails; it now shows loading, empty, or explicit error states.
- `mobile/app/tasks/[id].tsx` no longer creates a synthetic fallback task; it uses server data or route-provided real summary and surfaces load errors explicitly.
- `mobile/app/desktop-control.tsx` and `mobile/src/features/desktop-control/model.ts` add a fail-closed desktop-control status surface; local privacy mode never calls the network, and hybrid/cloud mode only reads `/sync/remote-control/status`.
- `mobile/src/features/workflow/detail-model.ts` now maps string transport errors such as timeout or failed fetch to the explicit network failure copy, and tests status precedence over misleading backend text.
- `mobile/src/constants/layout.ts` now exposes `touchTarget.min=44`; the bottom Tab and EmptyState action use the token, and `mobile/src/constants/layout.test.ts` guards it.
- `mobile/src/services/api.ts` now keeps the stored session when refresh-token retry fails due to weak network/timeout; it clears auth only when the refresh endpoint confirms 401/403, with `mobile/src/services/api.test.ts` covering both paths.
- `mobile/src/services/api.ts` now reads the stored privacy mode before outbound requests, sends `X-Privacy-Mode` in hybrid/cloud modes, and fails closed before `fetch` in local mode; `mobile/src/services/api.test.ts` covers header propagation and zero network calls in local mode.
- `mini-program/src/services/api.ts` now reads the stored privacy mode before outbound requests, sends `X-Privacy-Mode`, and fails closed before `Taro.request` in `local` / `top-secret` modes; `mini-program/src/pages/profile/index.tsx` blocks login before `Taro.login`, and `mini-program/scripts/check-privacy-boundary.js` guards the boundary.
- `mobile/package.json` now declares Expo SDK 52-compatible `expo-notifications`, `expo-device`, `expo-font`, `@expo/vector-icons`, `@react-native-async-storage/async-storage`, `react-native`, and `react-native-safe-area-context` versions so `mobile/app.json` config plugins and native peer dependencies resolve before device smoke.
- `mobile/package.json` now declares `expo-asset` directly because Expo Metro config requires project-level resolution before iOS Simulator app-run can bundle.
- `mini-program/src/services/api.ts` now mirrors that refresh-token distinction so transient refresh failure does not silently erase `token`/`refresh_token`.
- `mini-program/project.config.json` now uses `touristappid` for local WeChat DevTools CLI smoke; real upload still requires the official appid in the release environment.
- `mini-program/src/app.scss` now exposes `$touch-target-min: 88rpx` and applies it to homepage actions, profile menu items, and chat send actions.
- `mini-program/src/styles/design-tokens.scss` and `design-tokens.ts` now hold mini-program semantic tokens; the homepage, chat, profile SCSS files, and `app.config.ts` import those tokens instead of hardcoding page colors.
- `docs/design/cross-platform-token-drift.md` records Web/desktop, mobile, and mini-program token drift without changing design tokens; fixes remain separate release work.
- `docs/release/mobile-error-state-release-notes.md` drafts the user/support explanation for explicit error states after silent fallback removal.

This file remains `Status: pending` because the iOS Simulator Expo Go smoke is supporting evidence only and does not cover the required signed/official app, real device user stories, Android, interactive WeChat DevTools or real-device evidence, and cross-device continuation. Mobile production npm audit and local iOS bundling are now fixed in code-level/supporting artifacts, but runtime device evidence is still required before release Go.

## Completion Notes

- Record device model, OS version, app build, backend environment, and tester.
- Store screenshots/video clips with secrets and PII redacted.
- Link to interactive WeChat DevTools or real-device logs.
- Use the manual template artifact fields for iOS, Android, WeChat Mini Program, explicit error states, and cross-device continuation before changing this file to `Status: complete`.
- Keep the mobile npm audit fix evidence attached and rerun it after any Expo SDK/package changes before changing this file to `Status: complete`.
