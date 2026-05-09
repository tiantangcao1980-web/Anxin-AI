# 移动端与小程序 uni-app 迁移方案

> 日期：2026-05-09
> 决策：移动 App 与小程序新开发统一转向 uni-app；旧 `mobile/` Expo 与 `mini-program/` Taro 保留为 legacy 参考，按迁移清单逐步清理。
> 目标：减少多端重复适配，沉淀统一 API client、状态模型、隐私模式、设计 token 和发布证据口径。

## 1. 可行性判断

结论：**可行，建议采用“uni-app Vue3 基座先落地，保留评估 uni-app x 的原生性能路线”**。

理由：

- uni-app 官方定位是跨平台应用开发，适合同时覆盖 App、H5、小程序等多端；其 API 命名与小程序兼容，适合当前“移动端 + 微信小程序”统一建设。
- uni-app x 具备更强原生能力：UTS 可在 Android 编译为 Kotlin、iOS 编译为 Swift，且官方文档说明可调用平台原生 API；这对后续推送、文件、扫码、原生 SDK 插件有价值。
- 当前项目核心移动能力是登录、审批、聊天、知识库、桌面远控状态、错误态和跨设备会话，业务复杂度高于原生性能需求；先用成熟 uni-app Vue3 更稳，后续对性能或原生插件要求高的模块再评估 uni-app x/UTS 插件。

边界：

- uni-app 不能让所有平台“零适配”。微信登录、合法域名、App 推送、文件选择、WebView、支付拉起、系统权限、隐私弹窗仍需要平台分支和真机验收。
- 旧 React Native/Expo 与 Taro 代码不能直接平移 UI 组件；可复用的是 API 契约、状态模型、错误处理、隐私模式、测试用例和文案。
- Web 管理端继续保留 React，不纳入本次迁移。

官方参考：

- uni-app API 概述：https://uniapp.dcloud.net.cn/api/index.html
- uni-app x 介绍：https://doc.dcloud.net.cn/uni-app-x/index.html
- uni-app x API 概述：https://doc.dcloud.net.cn/uni-app-x/api/

## 2. 迁移后目录目标

已新增首版基座：

```text
apps/
└── uni-mobile/
    ├── src/
    │   ├── pages/
    │   ├── components/
    │   ├── services/
    │   ├── stores/
    │   ├── styles/
    │   └── platform/
    ├── manifest.json
    ├── pages.json
    ├── package.json
    └── README.md
```

2026-05-09 首版 `apps/uni-mobile/` 已落地为 Vue3 + Vite + uni-app 基座，包含统一 API client、auth/storage、privacy fail-closed、微信 `uni.login` 适配、桌面远控 safe-probe gate model、跨端 token 层，以及 H5/微信小程序本地构建脚本。

旧目录处理：

| 目录 | 当前角色 | 迁移期处理 | 完成后处理 |
|---|---|---|---|
| `mobile/` | Expo/React Native 移动端 | 标为 legacy；提取 API、状态模型、测试用例和设计 token | uni-app 覆盖同等能力并有真机证据后删除或归档到 `docs/archive/legacy-mobile/` |
| `mini-program/` | Taro 微信小程序 | 标为 legacy；提取微信登录、隐私边界、导航 guard、token 样式 | uni-app 微信小程序构建与 DevTools/真机证据通过后删除或归档 |
| `frontend/` | Web/桌面管理端 | 保留 | 保留 |
| `desktop/` | Tauri 桌面端 | 保留 | 保留 |

## 3. 首版 uni-app 功能范围

P0 必须迁移：

| 能力 | 来源 | uni-app 目标 |
|---|---|---|
| 登录/注册/刷新 token | `mobile/src/lib/auth-client.ts`、`mini-program/src/pages/profile/index.tsx` | 统一 auth service；微信小程序走 `uni.login`/平台分支到后端 `code2session` |
| 统一 API client | `mobile/src/services/api.ts`、`mini-program/src/services/api.ts` | 统一 `uni.request` 封装，透传 bearer token、`X-Privacy-Mode`、route-token |
| 隐私模式 fail-closed | 移动/小程序现有 guard | local/top-secret 下登录、数据请求、远控命令发起前拒绝 |
| 首页/聊天/知识库/尽调 | `mobile/app/(tabs)/*`、`mini-program/src/pages/index` | 页面内 loading/error/empty/result，不允许假 fallback |
| 审批工作台 | `mobile/app/approvals*` | 审批列表、详情、批准/驳回/撤销、审计时间线 |
| 桌面远控安全闸 | `mobile/app/desktop-control.tsx` | status、pairing、safe-probe 入队、状态刷新、取消、脱敏审计；高风险真实控制禁用到 runtime 接入 |
| 跨设备会话入口 | 任务 11b sync API | 显示 last_message、draft、unread；不伪造同步成功 |
| 设计 token | `frontend/src/lib/design-tokens.ts` + `docs/design/cross-platform-token-drift.md` | 建立 uni-app token 层，保持触控 44pt/88rpx、安全区和品牌色 contract |

P1 再迁移：

- 推送通知、订阅消息模板、离线消息。
- 文件上传/合同查看/电签链接跳转。
- 找律师、案件任务、材料包。
- app store / 应用市场适配和埋点。

## 4. 旧端清理计划

### Phase A：冻结和标记 legacy

- 在 `mobile/README.md` 和 `mini-program/README.md` 写明 legacy 状态、禁止新增功能、允许只做安全修复。
- 在任务计划中把新功能写入 `apps/uni-mobile/`，旧端只作为对照样本。
- 跑一次旧端 guard，记录基线，避免迁移期丢掉安全约束。

### Phase B：提取可复用契约

输出到 `apps/uni-mobile/src/`：

- `services/api.ts`：统一请求、错误归一化、隐私 header、route-token。
- `stores/auth.ts`：token、用户、角色、隐私模式。
- `platform/wechat.ts`：微信登录、订阅消息、合法域名错误处理。
- `platform/app.ts`：App 推送、文件、权限、打开外部签署链接。
- `styles/tokens.ts` 与 `styles/tokens.scss`：触控、安全区、颜色、间距。

### Phase C：页面迁移

迁移顺序：

1. Auth shell：登录、注册、忘记密码、微信登录。
2. App shell：Tab、全局错误态、隐私模式提示。
3. 审批与审计：商业治理最关键，先迁。
4. 聊天与知识库：验证流式/长文本/错误态。
5. 桌面远控：只迁 safe-probe 安全闸，不开放高风险真实执行。
6. 首页/任务/案件/合同/找律师：按业务优先级补齐。

### Phase D：双跑与删除

每个模块删除旧代码前必须满足：

- uni-app 同能力页面已通过 App/H5/微信小程序至少两个目标端的本地构建。
- 对应 API、隐私模式、错误态和鉴权测试已覆盖。
- 真机或微信开发者工具证据已写入 release artifact。
- 旧端同模块没有独有能力或已迁移。

删除顺序：

1. 删除旧端 dead assets、无引用组件、旧 mock fixture。
2. 删除已迁移页面。
3. 删除旧端测试和脚本。
4. 删除旧 `mobile/` / `mini-program/` 目录或归档。

## 5. 验收门禁

| 门禁 | 命令或证据 |
|---|---|
| uni-app 类型检查 | `cd apps/uni-mobile && npm run typecheck` |
| uni-app 单测 | `cd apps/uni-mobile && npm test` |
| 微信小程序构建 | `cd apps/uni-mobile && npm run build:mp-weixin` |
| H5 构建 | `cd apps/uni-mobile && npm run build:h5` |
| uni-app 聚合 smoke | `bash scripts/uni-mobile-smoke.sh --out docs/release/evidence/artifacts/uni-mobile-base-smoke-YYYYMMDD.json` |
| App 构建 | HBuilderX / DCloud 云打包 transcript |
| 隐私边界 | local/top-secret 下登录和数据请求 fail-closed |
| 真机证据 | iOS、Android、WeChat DevTools/真机截图或日志 |
| 发布证据 | `docs/release/evidence/mobile-device-smoke.md` 和 JSON artifact 更新 |

## 6. 风险和处理

| 风险 | 处理 |
|---|---|
| uni-app 与现有 React 组件不可复用 | 只复用 API/状态/文案/测试，不承诺 UI 组件平移 |
| 微信小程序能力和 App 能力差异 | 用 `platform/` 分支封装；页面只依赖统一接口 |
| 插件生态质量不一 | P0 不引入复杂插件；推送/文件/签署链接先用官方能力或最小 UTS 插件 |
| 删除旧端过早 | 每个模块先双跑，达到证据门禁后再删 |
| 设计 token 再次漂移 | 新 uni-app token 从 Web contract 映射生成，不允许页面级硬编码品牌色 |

## 7. 第一轮执行清单

- [x] 新建 `apps/uni-mobile/` 基座。证据：`docs/release/evidence/artifacts/uni-mobile-base-smoke-20260509.json`。
- [x] 标记 `mobile/` 和 `mini-program/` 为 legacy。
- [x] 迁移统一 API client、auth store、privacy mode、error model 的代码级契约；完整页面同等能力仍按模块推进。
- [ ] 迁移审批列表/详情/审计时间线。
- [ ] 迁移微信小程序登录与首页空态。
- [x] 跑 H5 + 微信小程序构建。证据：`bash scripts/uni-mobile-smoke.sh --out docs/release/evidence/artifacts/uni-mobile-base-smoke-20260509.json`。
- [ ] 采集 iOS/Android/WeChat 至少一轮真机或开发者工具证据。
- [ ] 对照门禁删除旧端已迁移模块。
