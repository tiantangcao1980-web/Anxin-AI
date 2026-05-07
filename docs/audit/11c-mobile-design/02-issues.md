# TASK-11c 剩余问题

| ID | 问题 | 严重度 | 证据 | 处理建议 |
|---|---|---|---|---|
| MOB-DESIGN-01 | Web 与移动/小程序品牌主色不一致 | P0 | `docs/design/cross-platform-token-drift.md` | 冻结跨端 `brand.primary` contract 后再修 |
| MOB-DESIGN-02 | 小程序语义 token 层已补，仍缺真机视觉确认和 SCSS/TS token 单源生成 | P1 | `mini-program/src/styles/design-tokens.scss`、`design-tokens.ts`、`pages/*/*.scss`、`app.config.ts` 已迁移 | 真机视觉验收；必要时再做构建期 token 生成 |
| MOB-A11Y-01 | 触控目标已有统一 token 底座，但缺真机逐项验证 | P0 | Web 有 `44px`，移动端 `Layout.touchTarget.min=44`，小程序 `$touch-target-min=88rpx` | 真机逐项验收底部 Tab、聊天发送、列表操作、个人中心菜单、首页快捷入口 |
| MOB-RUNTIME-01 | iOS/Android/WeChat DevTools 真机证据缺失 | P0 | `mobile-device-smoke.md` 仍 pending | 补设备、OS、build、截图/日志 |
| MOB-SYNC-01 | 跨设备会话延续缺移动 runtime 证据 | P0 | 仅有同步底座和桌面证据 | 桌面发起会话，移动 pull 后验 `last_message` / draft |
| MOB-COMMS-01 | 移除静默 fallback 的 release notes 未写 | P1 | TASK-11c DoD 未完成 | 发布说明中解释错误页代表真实后端/网络失败 |
| MOB-DOC-01 | 经验沉淀到 memory 尚未完成 | P2 | 当前会话无 memory 写入证据 | 后续用项目知识库/团队流程沉淀 |
