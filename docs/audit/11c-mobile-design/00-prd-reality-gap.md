# TASK-11c PRD vs 代码现实差分

> 日期：2026-05-07
> 范围：移动端、小程序、跨平台设计 token、移动错误态和真机验收。

## 1. 当前已落地

| PRD 要求 | 当前代码/证据 | 状态 |
|---|---|---|
| 移动端失败不再渲染假数据 | `mobile/app/approvals/[id].tsx`、`mobile/app/cases.tsx`、`mobile/app/messages/[id].tsx`、`mobile/app/tasks/[id].tsx` 已改为 loading/empty/error；`detail-model.test.ts` 覆盖错误文案 | 代码级完成 |
| 小程序登录不使用 mock token | `mini-program/src/pages/profile/index.tsx` 走 `wx.login -> code2session`；后端测试确认不返回 `session_key` | 代码级完成 |
| 小程序资讯无假新闻 fallback | `mini-program/src/pages/index/index.tsx` 失败/空列表显示空态 | 代码级完成 |
| 移动/小程序本地 smoke | `bash scripts/mobile-device-smoke.sh`：mobile Vitest `7 files / 19 tests passed`、mobile tsc、Expo doctor `17/17`、mobile production npm audit、mini tsc、Taro build、WeChat DevTools CLI project smoke、refresh auth guard、mobile privacy network guard、fake fallback guard、mini-program design token guard 通过 | 代码级完成；小程序本地/绝密模式边界仍需单独补齐或明确不支持 |
| 跨平台 token 漂移清单 | `docs/design/cross-platform-token-drift.md` 已产出 P0/P1/P2 | 审计完成，修复未做 |
| 小程序语义 token 层 | `mini-program/src/styles/design-tokens.scss` 和 `design-tokens.ts` 已新增；首页、聊天、个人中心 SCSS 与 `app.config.ts` 已迁移到 token；`bash scripts/mobile-device-smoke.sh` 的 design token guard 已通过 | 代码级完成 |

## 2. 当前缺口

| 缺口 | 影响 | 发布口径 |
|---|---|---|
| iOS/Android/微信开发者工具真机证据缺失 | 本地测试不能证明真实设备安全区、键盘、登录和网络失败体验 | 阻断商业完成 |
| 跨设备会话延续未证明 | 桌面开始、移动继续的 `last_message` / draft / unread 还缺 runtime 证据 | 阻断商业完成 |
| token 漂移未完全修复 | Web、移动、小程序品牌主色仍未统一；移动端业务状态色仍有页面级 hardcoded | 发布前设计风险 |
| 触控目标未全面验证 | 移动端与小程序已补最小触控 token 底座，但缺真机逐项验证 | 真机验收风险 |
| release notes 未写 | 用户可能把真实错误页误解为 app 退化 | 发布沟通风险 |

## 3. 结论

TASK-11c 的代码级 fallback 清理和本地 smoke 已完成大半；商业完成仍取决于真机/微信开发者工具证据、跨设备连续会话、设计漂移修复和 release notes。
