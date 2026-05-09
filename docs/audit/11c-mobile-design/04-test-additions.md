# TASK-11c 测试与验证证据

## 已有验证

```bash
bash scripts/mobile-device-smoke.sh
```

最近记录：

- mobile Vitest：`7 files / 19 tests passed`
- mobile TypeScript：exit `0`
- Expo doctor：`17/17 checks passed`
- mobile production npm audit：exit `0`；2026-05-09 通过 `@babel/plugin-transform-modules-systemjs@7.29.4` 与 `fast-uri@3.1.2` 定向 overrides 继续保持 `0`
- mobile result surface guard：`scripts/mobile-device-smoke.sh` 会确认移动端尽调和知识库搜索保留页面内结果卡，且不回退到 Alert-only 反馈。
- mobile lawyer conversion guard：`scripts/mobile-device-smoke.sh` 会确认移动端找律师保留真实咨询创建、AI 匿名摘要、律师选择、匿名聊天室/委托 API 路径，且不回退到不存在的律师详情页跳转。
- mini-program TypeScript：exit `0`
- mini-program `build:weapp`：exit `0`
- WeChat DevTools CLI project smoke：exit `0`
- refresh auth guard：exit `0`
- fake fallback guard：exit `0`
- mini-program privacy boundary guard：`cd mini-program && npm run check-privacy-boundary` 会确认 local/top-secret 在 `Taro.request` 前阻断、登录在 `Taro.login` 前阻断，且首页/聊天有隐私阻断错误态。
- mini-program navigation boundary guard：`cd mini-program && npm run check-navigation-boundary` 会确认首页/个人中心主入口不再使用空路径，也不会回退到“功能开发中”占位。
- mini-program design token guard：`bash scripts/mobile-device-smoke.sh` 会扫描小程序 `*.scss` / `*.ts`，只允许 `mini-program/src/styles/design-tokens.(scss|ts)` 保留原始色值；页面样式和 `app.config.ts` 必须走 token

## 相关单测

- `mobile/src/features/workflow/detail-model.test.ts`：任务/审批动作与错误文案映射。
- `mobile/src/features/workflow/detail-model.test.ts`：新增字符串 transport error 和 status 优先级错误分支。
- `mobile/src/constants/layout.test.ts`：新增 44pt touch target、tab/header 高度和 compact hit slop 常量约束。
- `mobile/src/features/inbox/model.test.ts`：移动工作台卡片顺序与 quick actions。
- `backend/tests/test_auth_surface_hardening.py`：小程序 `code2session` 返回 JWT 且不泄露 `session_key`。

## 本轮文档验证

```bash
git diff --check
bash scripts/release-evidence-secret-scan.sh
GITNEXUS_BIN=/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus \
  bash scripts/commercial-readiness-gate.sh --quick
```

结果：

- `git diff --check` 通过。
- release evidence secret scan 通过。
- commercial readiness gate 仍按预期失败，移动 evidence 仍为 `Status: pending`。

## 尚需补充

- 移动错误分支和触控 token 用例已补到 `15 passed`；后续仍可继续扩展消息/任务详情组件级测试。
- 小程序 lint 或等价静态检查。
- iOS/Android/微信开发者工具真机或官方工具 transcript。
