# TASK-11c 后续计划

## P0

1. 冻结跨端品牌主色 contract，决定 Web `hsl(25 95% 53%)` 与移动/小程序 `#D4A574` 的统一方向。
2. 用 iOS、Android、微信开发者工具或真机跑登录、审批、消息/任务详情、网络失败、资讯空态和触控目标核对。
3. 做桌面到移动的跨设备会话延续 runtime 验收。
4. 新建 `apps/uni-mobile/` uni-app 基座，先迁移 API client、auth store、privacy mode、审批工作台和桌面远控 safe-probe 安全闸。
5. 旧 `mobile/` 与 `mini-program/` 进入 legacy 后，只做安全修复和迁移提取；每个模块达到 uni-app 同等能力与真机/DevTools 证据后再删除或归档。

## P1

1. 新增移动错误分支测试，覆盖消息详情和任务详情失败态。
2. 补 release notes，说明移除静默 fallback 后错误页代表真实网络/后端失败。
3. 为移动 hardcoded 业务状态色建立 `status.*` 与 `domain.*` 映射。
4. 评估小程序 SCSS/TS token 是否需要构建期单源生成。
5. 评估 uni-app x / UTS 插件是否只用于推送、文件、扫码、原生 SDK 等必须原生能力，避免 P0 阶段引入过多平台差异。

## P2

1. 将 TASK-11c 经验沉淀到项目知识库。
2. 在移动设计文档中声明桌面继承 Web token，不维护独立 desktop token。
