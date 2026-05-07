# 跨平台设计 Token 漂移清单

> 日期：2026-05-07
> 范围：Web/桌面、移动端、微信小程序的颜色、字号、间距、圆角、触控与暗色模式 token 对齐情况。
> 结论：本文件只做审计，不修改 token。当前发现的漂移不会替代真机验收；修复应单独走设计系统变更。

## 1. 审计依据

| 平台 | 事实来源 | 说明 |
|---|---|---|
| Web / 桌面 | `frontend/src/lib/design-tokens.ts`、`frontend/src/index.css`、`frontend/tailwind.config.js` | 桌面 Tauri 当前复用 Web 前端主题，未发现独立 `frontend/src/components/desktop/` token 层 |
| 移动端 | `mobile/src/constants/colors.ts`、`mobile/src/constants/layout.ts`、`mobile/src/lib/theme.ts`、`mobile/app/(tabs)/_layout.tsx` | 已有集中 `Colors` / `Layout`，但仍存在页面级 hardcoded 状态色和旧页面色值 |
| 微信小程序 | `mini-program/src/styles/design-tokens.scss`、`mini-program/src/styles/design-tokens.ts`、`mini-program/src/app.scss`、`mini-program/src/app.config.ts`、`mini-program/src/pages/*/*.scss` | 已补小程序语义 token 层，首页/聊天/个人中心页面样式已迁移；`app.config.ts` 的 tabBar/nav 色值已改为 TS token 常量 |

## 2. P0 漂移

| 项 | 发现 | 风险 | 建议 |
|---|---|---|---|
| 品牌主色不一致 | Web canonical primary 为 `hsl(25 95% 53%)` / `--primary-500`；移动端与小程序主色为 `#D4A574`，小程序深色梯度为 `#B8864E`，移动端 `primaryDark` 为 `#B8895A` | 三端首屏、按钮和 Tab active 态会呈现两个不同品牌：Web 更偏高饱和琥珀橙，移动/小程序更偏低饱和金棕 | 建立跨端 `brand.primary` / `brand.primaryDark` 映射表，由 Web token 导出或显式确认移动端保留金棕作为 platform variant |
| 触控目标口径仍需真机确认 | Web 粗指针模式强制 `44px` 最小触控；移动端已补 `Layout.touchTarget.min=44` 并接入 Tab/EmptyState；小程序已补 `$touch-target-min: 88rpx` 并覆盖 `.action-item`、`.menu-item`、`.send-btn` | 代码级 token 已对齐，但真机上仍需逐项确认小程序/移动局部点击目标是否低于 44pt | 真机验收前继续核对底部 Tab、聊天发送、列表操作、个人中心菜单、首页快捷入口 |

## 3. P1 漂移

| 项 | 发现 | 风险 | 建议 |
|---|---|---|---|
| 文本色层级不一致 | Web 使用 `foreground` / `muted-foreground` / `text-tertiary` HSL 层级；移动端为 `#1C1C1E`、`#8E8E93`、`#AEAEB2`；小程序为 `#333`、`#666`、`#999` | 小程序文本对比与层级显著浅于 Web/移动，弱提示和正文区分不稳定 | 定义 `text.primary`、`text.secondary`、`text.tertiary` 三端对照，避免页面直接写灰阶 |
| 圆角尺度不一致 | Web 组件文档以按钮 `16px`、卡片 `24px` 为主；移动端 `md=12`、`lg=16`、`xl=24`，页面常用 `md/lg`；小程序卡片多为 `16rpx`，标签为 `6rpx` | Web 卡片更圆、更柔和，移动/小程序更紧凑；跨端截图会显得不是同一套系统 | 明确 `card.radius` 在移动/小程序是否采用 compact variant；如果不是，应把核心卡片提升到对应 16/24px 档 |
| 字号层级压缩 | Web h1/h2/h3 为 32/24/20px，body 为 14px；移动端 title 为 28、xxl 为 24、xl 为 20、md 为 16；小程序 page base 为 `28rpx`，section title 多为 `32rpx` | 小程序标题与正文差距偏小，法律智库/个人中心信息层级弱 | 给小程序补 `font-title` / `font-section` / `font-body` 变量，按中文移动端阅读密度做受控映射 |
| 暗色模式覆盖不一致 | Web 暗色 token 完整；移动端只有基础 `DarkColors`，且部分业务页仍硬编码 `#FEE2E2` / `#DC2626` 等浅色错误态；小程序无暗色 token | 夜间模式下移动端局部错误态/状态色可能刺眼，小程序无法跟随系统暗色 | 移动端把错误/成功/info 背景加入 `Colors`；小程序先声明不支持暗色或补一组暗色变量 |
| 状态色命名不统一 | Web 有 `success/warning/info/destructive/risk/ai` 语义色；移动端只有 `success/warning/error/info`，页面另有 `#3B82F6`、`#10B981`、`#EF4444`；小程序缺状态语义变量 | 风险、案件、知识类型在三端颜色含义会漂移 | 把状态色分为 `status.*` 与 `domain.*`，避免业务页直接写 Tailwind palette hex |

## 4. P2 / 平台合理差异

| 项 | 发现 | 判断 |
|---|---|---|
| 桌面无独立 token 文件 | 当前桌面包复用 Web 前端和 CSS 变量；未发现独立 desktop token 层 | 可接受，但应在桌面设计说明里写明“桌面继承 Web token” |
| 移动端 safe-area | `mobile/app/(tabs)/_layout.tsx` 使用 `useSafeAreaInsets()`，Tab 高度为 `56 + paddingBottom` | 合理平台差异；仍需真机验证 iPhone/Android 底部遮挡 |
| 小程序 rpx 单位 | 小程序使用 rpx 而非 px/rem | 合理平台差异；需要在 token 文档中写换算口径，避免误判为数值漂移 |
| 纯白/纯黑别名 | 移动端 `white` / `black` token 存在；Web 也在部分画布 fallback 中保留 hex | 不是立即阻断，但应限制为图标、遮罩、canvas fallback，不用于默认大面积表面 |

## 5. 建议修复顺序

1. 先冻结跨端 token contract：`brand`、`text`、`surface`、`border`、`status`、`radius`、`spacing`、`touchTarget`。
2. 决定 Web `hsl(25 95% 53%)` 与移动/小程序 `#D4A574` 的品牌主色统一方向。
3. 移动端把页面 hardcoded 状态色纳入 `Colors`，同时保留平台合理的 `Layout` spacing/radius。
4. 真机验收前复核触控目标：底部 Tab、聊天发送、列表操作、个人中心菜单、首页快捷入口。
5. 修复后复跑 `bash scripts/mobile-device-smoke.sh`，并在 iOS/Android/微信开发者工具记录截图或 transcript。

## 6. 当前未完成

- 已补小程序语义 token 层和触控目标 token 底座；品牌主色统一方向尚未修复。
- 未进行 iOS/Android 真机截图验证。
- 未进行微信开发者工具视觉验收。
- 小程序 SCSS 与 TS token 仍是双文件映射，后续如需彻底单源可增加构建期 token 生成。
