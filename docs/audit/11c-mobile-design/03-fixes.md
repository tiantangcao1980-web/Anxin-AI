# TASK-11c 已完成修复

## 1. 代码级修复

- 移动审批/案件/消息/任务详情不再用 synthetic fallback 伪装成功。
- 移动尽调和知识库搜索提交后不再只弹 Alert，而是在页面内展示结果摘要和下一步提示。
- 小程序 profile 登录链路已移除生产 mock token，改为 `wx.login -> code2session -> JWT`。
- 小程序首页资讯加载失败/空数据改为明确空态。
- 小程序首页和个人中心主入口已移除空路径和“功能开发中”死胡同，统一跳转 AI 助手并预填业务问题。
- 移动端找律师已补匿名咨询创建、AI 匿名摘要、律师选择、匿名聊天室和委托 API 路径，移除跳转不存在律师详情页的死路。
- `scripts/mobile-device-smoke.sh` 固化 mobile/mini 本地 smoke、mobile result surface guard、mobile lawyer conversion guard、mini-program privacy boundary guard、mini-program navigation boundary guard、fake fallback guard 与 mini-program design token guard。
- 移动端 `Layout.touchTarget.min=44`，Tab bar 与 EmptyState action 接入最小触控目标。
- 小程序 `$touch-target-min=88rpx`，首页动作、个人中心菜单和聊天发送按钮获得全局最小触控目标。
- 新增 `mini-program/src/styles/design-tokens.scss` 和 `design-tokens.ts`；首页、聊天、个人中心页面 SCSS 与 `app.config.ts` 已从 hardcoded 色值迁移到语义 token。

## 2. 文档级修复

- 新增 `docs/design/cross-platform-token-drift.md`，列出 Web/桌面、移动、小程序 token P0/P1/P2 漂移。
- 新增 `docs/mobile/error-handling-guidelines.md`，固定移动/小程序错误态、空态和 forbidden fallback 模式。
- 同步 `docs/release/evidence/mobile-device-smoke.md`、`docs/release/test-evidence.md`、`docs/audit/SUMMARY.md` 的移动证据口径。

## 3. 未在本轮修复的内容

- 不修改 `frontend/src/lib/design-tokens.ts`。
- 未做 SCSS/TS token 单源生成；当前是两份小程序 token 映射。
- 不新增后端同步协议字段。
- 不把真机证据 pending 改为 complete。
