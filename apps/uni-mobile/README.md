# Anxin uni-mobile

`apps/uni-mobile` is the new uni-app base for both the mobile App and WeChat Mini Program. The old `mobile/` Expo app and `mini-program/` Taro app stay as legacy references until each module has equivalent uni-app capability, tests, and device or DevTools evidence.

## Scope

- Unified API client with bearer token, refresh-token retry, `X-Privacy-Mode`, and route-token extension points.
- Fail-closed privacy model for `local` and `top-secret` before data network calls or WeChat login.
- WeChat login adapter using `uni.login` and backend `code2session`.
- Desktop-control safe-probe gate model without claiming high-risk execution.
- Cross-platform design tokens for touch target, safe area, spacing, status colors, and card radius.

## Commands

```bash
npm install
npm run typecheck
npm test
npm run build:h5
npm run build:mp-weixin
```

App cloud build, iOS signing, Android signing, official WeChat AppID, and device evidence remain external release inputs.
