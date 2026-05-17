# V3 UI 升级 · 视觉评审清单

> 对应 PR [#9](https://github.com/tiantangcao1980-web/Anxin-AI/pull/9)
> 日期：2026-05-17
> 范围：所有 V3 8 大业务域可视化产出（5 个原子组件 + 4 个落地页面）
>
> 设计师按表勾选 / 提改进意见。每项含「验收标准」+「如需改动的工程估时」让协作决策有依据。

## 0. 评审入口（推荐顺序）

| 步骤 | 看哪里 | 怎么看 |
|---|---|---|
| 0.1 | 8 域色板 | `frontend/src/index.css` `--domain-*` CSS 变量 + 本文 §1 swatches |
| 0.2 | Login 8 域徽章网格 | `npm run dev` → `http://localhost:3001/login` |
| 0.3 | DomainHomePage 永久索引 | 登录后访问 `/domains` |
| 0.4 | WelcomeGuide 首登 modal | 登录后清 localStorage 重登触发 |
| 0.5 | Layout 顶栏 + 侧栏视觉锚点 | 登录后随便点导航看 active 态 |
| 0.6 | 业务子页 DomainStripe + DomainBreadcrumb | 进入 `/find-lawyer` / `/case-center` 等 |

---

## 1. 8 大业务域色板（核心决策）

每个色值都是 HSL，浅色 / 深色双模式。Hex 是用 [hsl-to-hex](https://hslpicker.com) 转换的等效值，供设计师直观比对。

| Domain | 浅色 HSL | 浅色 Hex | 深色 HSL | 深色 Hex | 语义建议 | □ 验收 |
|---|---|---|---|---|---|---|
| 法务 Legal | `100 32% 38%` | `#5C7F3E` | `100 28% 60%` | `#85B477` | 暖橄榄绿 / 沉稳·克制·可信 | ☐ |
| 财务 Finance | `217 78% 48%` | `#1F6FD4` | `217 70% 65%` | `#5C95E4` | 稳重蓝 / 数字精确感 | ☐ |
| 税务 Tax | `42 88% 48%` | `#E2A311` | `42 80% 62%` | `#EBC459` | 金箔黄 / 价值·合规 | ☐ |
| 合规 Compliance | `8 80% 52%` | `#E84F2E` | `8 75% 65%` | `#EE8166` | 警示橙红 / 红线意识 | ☐ |
| 经营管理 Operations | `270 60% 52%` | `#7D4FCC` | `270 55% 68%` | `#A688D9` | 王者紫 / 战略·统筹 | ☐ |
| 调研获客 Growth | `188 78% 42%` | `#17AAC3` | `188 70% 58%` | `#48C2D5` | 情报青 / 调研·洞察 | ☐ |
| 内容产出 Content | `335 75% 56%` | `#DE3F88` | `335 68% 68%` | `#E677A6` | 桃红 / 创作·活力 | ☐ |
| 出海跨境 Global | `205 80% 35%` | `#1768A1` | `205 70% 58%` | `#418FCB` | 深海蓝 / 远洋·全球 | ☐ |

### 设计师必答
- [ ] **每个域的色相**是否符合业务语义？（若不符 → 改 `frontend/src/index.css` 即可全端生效，估时 5 min/域）
- [ ] **浅色饱和度**在卡片底色场景对比度够吗？（若不够 → 调浅一档，估时 5 min/域）
- [ ] **深色模式**亮度提升够吗？文本可读吗？
- [ ] **8 个域之间的色相区分度**是否足够？（特别是 Finance 蓝 vs Global 深海蓝、Compliance 红橙 vs Tax 金黄）

---

## 2. 设计约束（已硬编码到 token 注释 + 测试守护）

| 约束 | 实施 | □ 设计师确认 |
|---|---|---|
| 业务域色 **不替代** 品牌琥珀橙 | `--primary` (hsl 25 95% 53%) 保留 | ☐ |
| 主行动按钮 / 链接 / 焦点环走 `--primary` | Login 登录按钮、所有 active 文字 | ☐ |
| 业务域色仅做「分类标识」 | Badge / Stripe / Card / Grid / Breadcrumb / underline / dot | ☐ |
| 与风险三档（`--risk-high/medium/low`）不重叠 | 风险是「状态」，域是「分类」 | ☐ |

---

## 3. 5 个原子组件视觉决策点

### 3.1 DomainBadge（最高频复用）
| 决策点 | 当前 | 改动估时 |
|---|---|---|
| 圆角 | `9999px`（pill 全圆角）| 改 `rounded-full` → `rounded-md`，10 min |
| 内边距 | sm: `2px 8px` / md: `4px 10px` | 各端独立调，30 min |
| 字号 | sm: 11px / md: 12px | 三端 token 调，15 min |
| Icon 字号 | sm: 12px / md: 14px | 三端独立，15 min |
| 是否始终带 icon | 默认带，可关 | 默认值改 `showIcon=false`，5 min |

### 3.2 DomainStripe（顶部 4pt 彩条）
| 决策点 | 当前 | 改动估时 |
|---|---|---|
| 高度 | 4px（web）/ 4pt（mobile）/ 6rpx（mini）| 三端独立调，15 min |
| 颜色 | 100% 域色饱和 | 改半透明 `opacity: 0.85`，5 min |

### 3.3 DomainCard（仅 Web）
| 决策点 | 当前 | 改动估时 |
|---|---|---|
| 高度 | 自适应（含 title + tagline + count + chevron）| 改固定高度，15 min |
| Hover 态 | `translate-y -0.5 + shadow-elev-3` | 调整 hover 抬升幅度，10 min |
| 圆角 | `rounded-2xl` (16px) | 调整圆角，5 min |

### 3.4 DomainGrid（仅 Web · DomainCard 4 列响应式）
| 决策点 | 当前 | 改动估时 |
|---|---|---|
| 列数断点 | `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4` | 调整断点，5 min |
| 卡片间距 | `gap-3` (12px) | 三端独立调，10 min |

### 3.5 DomainBreadcrumb
| 决策点 | 当前 | 改动估时 |
|---|---|---|
| 默认模式 icon 框 | `5×5 rounded-md`（web）/ `20×20 rounded-md`（mobile）| 三端独立调，15 min |
| compact 模式圆点 | 1.5×1.5（web）/ 6pt（mobile）/ 10rpx（mini）| 三端独立调，15 min |
| moduleName 分隔符 | `·`（中点）| 改 `›` 或 `›`，3 min |

---

## 4. 4 个落地页面视觉决策点

### 4.1 Login 页 — 左侧 8 域徽章网格
**位置**：`frontend/src/pages/Login.tsx:472-501`

| 决策点 | 当前 | 改动估时 |
|---|---|---|
| 网格布局 | 4×2 | 改 2×4 或 8×1，5 min |
| 卡片样式 | 域 surface 底色 + icon + label | 加 hover 态，10 min |
| 入口区文案 | "一个 App，搞定企业 8 大业务" | 改文案，2 min |

### 4.2 WelcomeGuide modal — 首登 8 域引导
**位置**：`frontend/src/components/WelcomeGuide.tsx`

| 决策点 | 当前 | 改动估时 |
|---|---|---|
| 触发时机 | 登录后 600ms 延迟弹出 | 改延迟 / 改触发条件（如首次进 /domains），10 min |
| 关闭行为 | 关闭后 `hasSeenWelcome=true` 持久化 | 增加"以后不再提示"checkbox，15 min |
| 标题文案 | "欢迎使用安心智能助手" | — |
| 副标 | "全链路 AI 经营助理 · 一个 App 搞定企业 8 大业务" | — |
| 推荐域徽章 | operations 标 "推荐入口" | 改默认推荐域，2 min |

### 4.3 DomainHomePage `/domains` — 永久 8 域索引
**位置**：`frontend/src/pages/DomainHomePage.tsx`

| 决策点 | 当前 | 改动估时 |
|---|---|---|
| 顶部 | `<DomainGrid />` 全 8 域 | — |
| 中部"常用模块" | 按域分组，每域列 1-5 个子页 link | 调整每域子页列表，10 min |
| 占位域（finance/tax/global）| 显示"敬请期待" + 60% opacity | 改占位文案 / 加 mock placeholder，10 min |
| 底部 | 品牌定位字符串 | — |

### 4.4 Layout 顶栏 + 侧栏
**位置**：`frontend/src/components/Layout.tsx`

| 决策点 | 当前 | 改动估时 |
|---|---|---|
| 顶栏 `/domains` 入口按钮 | LayoutGrid 图标 + active 态 primary 高亮 | 改图标 / 位置，5 min |
| 4 大 nav active underline | 2px 域色 rounded-full 紧贴底部 | 改高度 / 偏移，5 min |
| 侧栏 active stripe | 2px 域色 rounded-r 紧贴左边 | 改宽度 / 颜色饱和，5 min |
| 侧栏 inactive dot | 1×1 域色 70% opacity 右侧 | 改大小 / 位置，5 min |
| 侧栏标题区 DomainBreadcrumb | compact 模式（圆点 + 域名）| 改默认变体，5 min |

---

## 5. Mobile / Mini Program 端视觉差异

| 端 | DomainBadge 实现 | 与 Web 视觉差异 |
|---|---|---|
| Web | lucide-react SVG | 基准 |
| Mobile (Expo) | Ionicons | 图标风格略不同（Outline vs lucide stroke）|
| Mini Program (Taro) | **Emoji** | 受小程序限制无 SVG，emoji 颜色由 OS 主题决定，不受域色控制 |

### 设计师必答
- [ ] Mini Program emoji 版本可接受吗？还是要换成 Taro 内置图标库（部分覆盖 8 域）？
- [ ] Mobile Ionicons 图标在 Light / Dark 模式下颜色都正常吗？

---

## 6. 验收签字栏

设计师评审完成后填写：

| 项 | 设计师姓名 | 日期 | 状态 |
|---|---|---|---|
| 8 域色板 | ☐ | YYYY-MM-DD | ☐ Pass / ☐ Need rework |
| 5 原子组件 | ☐ | YYYY-MM-DD | ☐ Pass / ☐ Need rework |
| 4 落地页面 | ☐ | YYYY-MM-DD | ☐ Pass / ☐ Need rework |
| 跨端视觉一致性 | ☐ | YYYY-MM-DD | ☐ Pass / ☐ Need rework |

如有 "Need rework" 项，请在 PR #9 留 review comment + 具体改动建议。
