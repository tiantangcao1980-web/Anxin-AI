# Mobile And Mini-Program Device Smoke Evidence

Status: pending
Owner: TBD
Environment: code-level mobile/mini smoke complete; Expo config, SDK dependency guard, and Expo doctor complete; WeChat DevTools CLI project smoke complete; cross-platform token drift audit complete; iOS, Android, interactive WeChat DevTools / real device pending
Date range: 2026-05-06 to 2026-05-08 local collection

> Simulator/unit tests are useful but insufficient. This evidence requires real or official-device-tool runs for the critical user stories.

## Required Scope

| Platform | Required evidence | Status | Artifact reference |
|---|---|---|---|
| iOS | Login, approval detail, chat continuation, settings error state | pending | TBD |
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
cd mobile && npm test
cd mobile && npx tsc --noEmit --module esnext
cd mobile && npx expo-doctor
cd mini-program && npx tsc --noEmit --skipLibCheck --noUnusedLocals false
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
| mobile Vitest suite | `7 files / 17 tests passed` |
| mobile TypeScript check | exit `0` |
| mobile Expo config/dependency guard | exit `0`; `expo-notifications`, `expo-device`, and `expo-font` are installed and aligned with `mobile/app.json`; `npx expo config --json --full` and `npx expo install --check` pass |
| mobile Expo doctor | exit `0`; `17/17 checks passed` |
| mobile npm audit security summary | exit `0`; `critical=0`, `high=0`, `total=0`; `@xmldom/xmldom`, `@expo/plist`, Expo CLI `tar`, and Metro `postcss` findings are remediated by targeted overrides; `tar@7.5.14` crosses Expo CLI's declared semver range, so Expo doctor and real-device smoke remain required release verification |
| mini-program TypeScript check | exit `0` |
| mini-program WeChat build | exit `0`; Taro compiled successfully |
| mini-program WeChat DevTools CLI smoke | exit `0`; `/Applications/wechatwebdevtools.app/Contents/MacOS/cli auto --project <repo>/mini-program --trust-project` accepted `touristappid` |
| mobile and mini fake fallback guard | exit `0`; guards against `fallbackMessages`, `fallbackTask`, `mock_token`, leaked `session_key`, fake success markers; confirms `wx.login/code2session` path and no fake news fallback |
| mobile and mini refresh auth guard | exit `0`; mobile Vitest covers network refresh failure preserving auth; script guard verifies mobile/mini separate auth expiry from transient refresh failure |
| cross-platform token drift audit | `docs/design/cross-platform-token-drift.md` created; mini-program semantic token layer and touch-target baseline are code-level complete; remaining P0 items are brand primary direction and real-device touch-target verification |
| code-level JSON artifact | `docs/release/evidence/artifacts/mobile-mini-code-smoke-20260508.json`; `status=passed`, `release_evidence_complete=false`, includes Expo guard and `mobile_npm_audit.status=passed,total=0` |
| manual device template | `docs/release/evidence/artifacts/mobile-device-manual-template-20260508.json`; `status=template`, `release_evidence_complete=false` |
| host device probe | `docs/release/evidence/artifacts/mobile-device-host-probe-20260507.json`; iOS simulator has no available device, ADB has no connected devices, Android emulator CLI is missing, WeChat DevTools app is present |

Code-level hardening added in this collection:

- `mobile/app/messages/[id].tsx` no longer renders fallback conversation content when message loading fails; it now shows loading, empty, or explicit error states.
- `mobile/app/tasks/[id].tsx` no longer creates a synthetic fallback task; it uses server data or route-provided real summary and surfaces load errors explicitly.
- `mobile/src/features/workflow/detail-model.ts` now maps string transport errors such as timeout or failed fetch to the explicit network failure copy, and tests status precedence over misleading backend text.
- `mobile/src/constants/layout.ts` now exposes `touchTarget.min=44`; the bottom Tab and EmptyState action use the token, and `mobile/src/constants/layout.test.ts` guards it.
- `mobile/src/services/api.ts` now keeps the stored session when refresh-token retry fails due to weak network/timeout; it clears auth only when the refresh endpoint confirms 401/403, with `mobile/src/services/api.test.ts` covering both paths.
- `mobile/package.json` now declares Expo SDK 52-compatible `expo-notifications`, `expo-device`, `expo-font`, `@expo/vector-icons`, `@react-native-async-storage/async-storage`, `react-native`, and `react-native-safe-area-context` versions so `mobile/app.json` config plugins and native peer dependencies resolve before device smoke.
- `mini-program/src/services/api.ts` now mirrors that refresh-token distinction so transient refresh failure does not silently erase `token`/`refresh_token`.
- `mini-program/project.config.json` now uses `touristappid` for local WeChat DevTools CLI smoke; real upload still requires the official appid in the release environment.
- `mini-program/src/app.scss` now exposes `$touch-target-min: 88rpx` and applies it to homepage actions, profile menu items, and chat send actions.
- `mini-program/src/styles/design-tokens.scss` and `design-tokens.ts` now hold mini-program semantic tokens; the homepage, chat, profile SCSS files, and `app.config.ts` import those tokens instead of hardcoding page colors.
- `docs/design/cross-platform-token-drift.md` records Web/desktop, mobile, and mini-program token drift without changing design tokens; fixes remain separate release work.
- `docs/release/mobile-error-state-release-notes.md` drafts the user/support explanation for explicit error states after silent fallback removal.

This file remains `Status: pending` because the release requirement still needs iOS, Android, interactive WeChat DevTools or real-device evidence, and cross-device continuation. Mobile production npm audit is now fixed in the code-level artifact, but runtime device evidence is still required before release Go.

## Completion Notes

- Record device model, OS version, app build, backend environment, and tester.
- Store screenshots/video clips with secrets and PII redacted.
- Link to interactive WeChat DevTools or real-device logs.
- Use the manual template artifact fields for iOS, Android, WeChat Mini Program, explicit error states, and cross-device continuation before changing this file to `Status: complete`.
- Keep the mobile npm audit fix evidence attached and rerun it after any Expo SDK/package changes before changing this file to `Status: complete`.
