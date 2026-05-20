# TASK-11c PRD vs 代码现实差分
> ⚠️ **2026-05-20 路线纠正**：本文档涉及的 uni-app / apps/uni-mobile 技术链路已**彻底放弃**。
> 当前移动端路线 = mobile/ (Expo + RN) + mini-program/ (Taro)，详见 PROJECT_STATUS.md 和 PRODUCT_ROADMAP.md。
> 以下内容保留为历史决策上下文，不代表当前实施方向。

> 日期：2026-05-07
> 范围：移动端、小程序、跨平台设计 token、移动错误态和真机验收。

## 1. 当前已落地

| PRD 要求 | 当前代码/证据 | 状态 |
|---|---|---|
| 移动端失败不再渲染假数据 | `mobile/app/approvals/[id].tsx`、`mobile/app/cases.tsx`、`mobile/app/messages/[id].tsx`、`mobile/app/tasks/[id].tsx` 已改为 loading/empty/error；`detail-model.test.ts` 覆盖错误文案 | 代码级完成 |
| 移动端提交后有结果承接 | `mobile/app/(tabs)/investigation.tsx` 和 `mobile/app/(tabs)/knowledge.tsx` 已从 Alert-only 反馈改为页面内结果摘要卡；`mobile-device-smoke.sh` 的 mobile result surface guard 防回归 | 代码级完成；真机交互证据仍需补 |
| 移动端找律师不是纯列表 | `mobile/app/find-lawyer.tsx` 已补匿名咨询创建、AI 匿名摘要、律师选择、匿名聊天室和委托 API 路径；`mobile-device-smoke.sh` 的 mobile lawyer conversion guard 防止回退到缺闭环列表页 | 代码级完成；真机交互证据仍需补 |
| 小程序登录不使用 mock token | `mini-program/src/pages/profile/index.tsx` 走 `wx.login -> code2session`；后端测试确认不返回 `session_key` | 代码级完成 |
| 小程序资讯无假新闻 fallback | `mini-program/src/pages/index/index.tsx` 失败/空列表显示空态 | 代码级完成 |
| 移动/小程序本地 smoke | `bash scripts/mobile-device-smoke.sh`：mobile Vitest `8 files / 37 tests passed`、mobile tsc、mobile result surface guard、mobile lawyer conversion guard、Expo doctor `17/17`、mobile production npm audit `0`、mini tsc、mini privacy boundary guard、mini navigation boundary guard、Taro build、WeChat DevTools CLI project smoke、refresh auth guard、mobile/mini privacy network guard、fake fallback guard、mini-program design token guard 通过 | 代码级完成；真机/交互式微信开发者工具证据仍需补 |
| 小程序主入口无死胡同 | 首页合同审查/找律师/合规自检与个人中心合同审查/案件协助/联系律师均跳转 AI 助手并预填业务问题；`mini-program/scripts/check-navigation-boundary.js` 阻断空路径和“功能开发中”回归 | 代码级完成；真机点击证据仍需补 |
| 跨平台 token 漂移清单 | `docs/design/cross-platform-token-drift.md` 已产出 P0/P1/P2 | 审计完成，修复未做 |
| 小程序语义 token 层 | `mini-program/src/styles/design-tokens.scss` 和 `design-tokens.ts` 已新增；首页、聊天、个人中心 SCSS 与 `app.config.ts` 已迁移到 token；`bash scripts/mobile-device-smoke.sh` 的 design token guard 已通过 | 代码级完成 |
| uni-app 统一端路线 | 2026-05-09 已产出 `docs/mobile/uni-app-migration-plan.md`；`mobile/README.md`、`mini-program/README.md` 已标记 legacy；`apps/uni-mobile/` 首版基座已通过 typecheck、`5 files / 12 tests`、production npm audit `0`、H5 build 和 WeChat Mini Program build | 代码级基座完成；旧端模块删除待同等能力和真机/DevTools 证据 |

## 2. 当前缺口

| 缺口 | 影响 | 发布口径 |
|---|---|---|
| iOS/Android/微信开发者工具真机证据缺失 | 本地测试不能证明真实设备安全区、键盘、登录和网络失败体验 | 阻断商业完成 |
| 跨设备会话延续未证明 | 桌面开始、移动继续的 `last_message` / draft / unread 还缺 runtime 证据 | 阻断商业完成 |
| token 漂移未完全修复 | Web、移动、小程序品牌主色仍未统一；移动端业务状态色仍有页面级 hardcoded | 发布前设计风险 |
| 触控目标未全面验证 | 移动端与小程序已补最小触控 token 底座，但缺真机逐项验证 | 真机验收风险 |
| release notes 未写 | 用户可能把真实错误页误解为 app 退化 | 发布沟通风险 |
| uni-app App 云打包/真机证据未落地 | 当前已有 `apps/uni-mobile/` 代码级基座，但还没有 DCloud App 云打包/签名、真实 iOS/Android、交互式微信开发者工具和跨设备连续会话证据 | 阻断后续移动/小程序商业发布 |
| 旧端清理未完成 | 旧目录仍包含安全 guard 与业务页面，直接删除会丢回归；不删除又会继续分叉 | 必须按模块迁移、双跑、验收后清理 |

## 3. 结论

TASK-11c 的代码级 fallback 清理、本地 smoke 和 uni-app 首版基座已完成大半；商业完成仍取决于真机/微信开发者工具证据、DCloud App 云打包/签名、跨设备连续会话、设计漂移修复和 release notes。2026-05-09 起，移动 App 与小程序后续新开发切换到 `apps/uni-mobile/`；旧 Expo/Taro 端只作为 legacy 参考，删除必须等 uni-app 同等能力、测试和真实设备证据补齐。
