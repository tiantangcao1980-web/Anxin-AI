# TASK-11c PRD 覆盖矩阵

| 能力 | 覆盖证据 | 覆盖结论 |
|---|---|---|
| 审批/任务错误分支 | `mobile/src/features/workflow/detail-model.test.ts`，消息/任务详情页已无 synthetic fallback | 代码级充分 |
| 收件箱/移动工作台 | `mobile/src/features/inbox/model.test.ts`、`engagement-model.test.ts`，本地 smoke 通过 | 代码级充分 |
| 小程序真实登录 | 后端 `test_wechat_mini_code2session_*`、小程序 profile 代码、fake fallback guard | 代码级充分；真机未验 |
| 小程序资讯空态 | 本地 tsc/build + fake fallback guard | 代码级充分；微信开发者工具未验 |
| 跨平台 token | `docs/design/cross-platform-token-drift.md` | 审计充分；修复未做 |
| 小程序语义 token | `mini-program/src/styles/design-tokens.scss`、`mini-program/src/styles/design-tokens.ts`、首页/聊天/个人中心 SCSS imports、`app.config.ts` theme import | 代码级完成；真机视觉未验 |
| 底部 Tab / safe-area | `mobile/app/(tabs)/_layout.tsx` 使用 `useSafeAreaInsets()`，Tab 高度 `56 + paddingBottom` | 代码读取可确认；真机未验 |
| 44pt 触控目标 | Web CSS 有粗指针 `44px` 规则；移动端 `Layout.touchTarget.min=44`，Tab/EmptyState 接入；小程序 `$touch-target-min=88rpx` 覆盖首页动作、个人中心菜单、聊天发送 | 代码级底座完成；真机覆盖不足 |
| 跨设备会话延续 | 依赖 TASK-11b 同步底座；缺移动 runtime 证据 | 覆盖不足 |

## 发布结论

本矩阵不能把 `docs/release/evidence/mobile-device-smoke.md` 改为 complete；该 evidence 仍需真实 iOS、Android、微信开发者工具或真机记录。
