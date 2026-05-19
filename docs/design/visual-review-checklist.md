# V3 UI 升级 · 视觉评审清单（Reset 版）

> 对应 PR [#9](https://github.com/tiantangcao1980-web/Anxin-AI/pull/9)
> 日期：2026-05-17 首版 → 2026-05-20 Reset 重写
> 设计方向：**Editorial Luxury**（克制的奢华 · 编辑级排版）
> Aesthetic Direction 决策记录见 `docs/design/ui-audit-and-upgrade-2026-05.md` §Reset

---

## ⚠️ 重要 · Reset 公告（先看）

首版 PR 落地了「8 大业务域 × 8 种高饱和色拼盘 + emoji 图标 + Inter 字体」方案，
被用户严厉批评后用 `ui-design` skill 重新做了 Design Specification，
全量 Reset 到 **Editorial Luxury** 方向：

- ❌ 删除 8 域高饱和色（含被 ui-design `FORBIDDEN COLORS` 命中的紫色）
- ❌ 删除所有 emoji 作 UI 图标（ui-design `FORBIDDEN`）
- ❌ 删除 Inter / system-ui / -apple-system / Helvetica Neue 字体（ui-design `FORBIDDEN FONTS`）
- ✅ 业务域改用「序号 + 衬线域名 + 字距层次」区分，不用色彩
- ✅ 单一品牌琥珀橙仅出现在 CTA 按钮 / active 1px 左线
- ✅ 衬线大字（Noto Serif SC）承载 Editorial 气质
- ✅ Lucide 单色线性图标替代所有 emoji

详细 Reset 清单：commit `7a69bd47` (Phase 1-3) + `e55819c3` (Phase 4-6) + `b2436e52` (FORBIDDEN FONTS 残留清理)

---

## 0. 评审入口（按重要性排序）

| 步骤 | 看哪里 | 怎么看 |
|---|---|---|
| 0.1 | **独立 Prototype HTML**（最直观）| `docs/design/v3-prototype-editorial.html` 直接 `open` 或起 http server。三屏切换：Login / 业务域目录 / 业务子页 |
| 0.2 | Login 页实景 | `cd frontend && npm run dev` → `http://localhost:3001/login` |
| 0.3 | DomainHomePage `/domains` | 登录后访问 `/domains`（Layout 顶栏 LayoutGrid 图标也可直达）|
| 0.4 | WelcomeGuide modal | 登录后清 `localStorage.removeItem('auth-storage')` 重登触发 |
| 0.5 | Layout 顶栏 + 侧栏 | 任意登录态页面 |
| 0.6 | 业务子页 | `/find-lawyer` / `/case-center` 等 |

---

## 1. 调色板（核心决策）

✅ **单一品牌锚点 + 暖灰阶梯**（替代上轮 8 色高饱和拼盘）

| 角色 | HSL | Hex | 用途 | □ 验收 |
|---|---|---|---|---|
| 品牌主色 | `25 95% 53%` | `#F08A2A` | CTA / 激活态 / 唯一彩色锚点 | ☐ |
| 品牌深色 | `15 80% 38%` | `#B0501C` | hover / pressed | ☐ |
| 品牌极浅 | `33 100% 97%` | `#FFF8F0` | active 微提示底 | ☐ |
| 纸张暖白 | `30 14% 98%` | `#FAF8F5` | 页面背景 | ☐ |
| Surface 1 | `0 0% 100%` | `#FFFFFF` | 主面 | ☐ |
| 暖墨文本 | `20 14% 10%` | `#1C1815` | 主文本 | ☐ |
| 次墨文本 | `20 14% 30%` | `#524742` | 次文本 | ☐ |
| 弱墨文本 | `20 9% 46%` | `#7A7068` | 弱说明 / micro tracker | ☐ |
| 发丝边 | `30 13% 91%` | `#ECE7E0` | 标准边框 | ☐ |
| 墨绿（success）| `142 30% 38%` | `#4B7C5A` | 通过 / 成功 — 低饱和墨色 | ☐ |
| 降饱和琥珀（warning）| `38 70% 48%` | `#D08A1C` | 提醒 / 中风险 | ☐ |
| 墨红（destructive）| `0 50% 45%` | `#B33A3A` | 错误 / 高风险 | ☐ |
| AI 紫（仅 AI 生成态）| `262 60% 48%` | `#604ECC` | DESIGN.md §2 保留，**不参与业务域分类** | ☐ |

### 设计师必答（调色板）
- [ ] 暖灰 + 单一琥珀橙的 Editorial Luxury 方向是否符合预期？
- [ ] 状态色（success / warning / destructive）的「墨色低饱和」是否够辨识？
- [ ] 字面对比度（暖墨 #1C1815 on 纸张暖白 #FAF8F5 = 12.5:1）是否 WCAG AAA 合格？

---

## 2. 字体系统（核心决策）

✅ **中文系统字体优先 + Editorial Serif**（替代上轮 Inter 等违禁字体）

| 角色 | 字体栈 | 用途 |
|---|---|---|
| Sans（主 UI）| `PingFang SC` / `Microsoft YaHei` / `Noto Sans SC` / `sans-serif` | 正文、按钮、表单 |
| Serif（Editorial）| `Noto Serif SC` / `Source Han Serif SC` / `Songti SC` / `STSong` / `SimSun` / `serif` | Display / H1 大标题、业务域名、文档预览 |
| Mono | `JetBrains Mono` / `SF Mono` / `Menlo` / `monospace` | 合同 diff / 数字 / 代码 |

### 字号层级（Editorial 大跨度）
| 角色 | px | line-height | letter-spacing | family | weight |
|---|---|---|---|---|---|
| Display | 48 | 1.1 | -0.04em | serif | 500 |
| H1 | 32 | 1.2 | -0.02em | serif | 500 |
| H2 | 24 | 1.3 | -0.01em | sans | 500 |
| H3 | 18 | 1.4 | -0.005em | sans | 600 |
| Body | 15 | 1.65 | 0 | sans | 400 |
| Caption | 13 | 1.5 | 0.01em | sans | 400 |
| **Micro** | **11** | **1.4** | **0.16em** | sans | **500** UPPERCASE |

❌ 禁用：`Inter` / `Roboto` / `Arial` / `Helvetica` / `Helvetica Neue` / `system-ui` / `-apple-system` / `BlinkMacSystemFont`

### 设计师必答（字体）
- [ ] 衬线字体（Noto Serif SC）作 Display + H1 + 业务域名 — 是否带出"中信书店 × 律师事务所大堂"的气质？
- [ ] Micro tracker（0.16em UPPERCASE）在中文标签上是否合理？

---

## 3. 业务域可视化（最重要 — 上轮被批评的核心点）

✅ **Editorial 编号目录**（替代上轮 8 色高饱和卡片墙）

### 区分手段（克制）
- 序号 `01`–`08`（serif 数字 tabular-nums）
- 衬线域名（H2/H3 字号层次）
- Lucide 单色线性图标（1.5px stroke）
- 1px hairline 边界（hover 时浅琥珀底）
- active 项 1px primary 左线

### 业务域元数据（无 color/surface 字段）
| 序号 | 域 | English | Lucide 图标 | tagline |
|---|---|---|---|---|
| 01 | 法务 | Legal | `Scale` | 合同审查 · 案件管理 · 法律顾问 |
| 02 | 财务 | Finance | `Calculator` | 记账 · 对账 · 报销 · 资金看板 |
| 03 | 税务 | Tax | `Landmark` | 申报 · 税务筹划 · 政策跟踪 |
| 04 | 合规 | Compliance | `ShieldCheck` | 风控 · 内审 · 监管红线 |
| 05 | 经营管理 | Operations | `LineChart` | KPI · 决策驾驶舱 · 战略推演 |
| 06 | 调研获客 | Growth | `Compass` | 市场调研 · 线索挖掘 · 舆情监测 |
| 07 | 内容产出 | Content | `PenLine` | 文案 · 视频脚本 · 营销素材 |
| 08 | 出海跨境 | Global | `Globe2` | 国际化 · 海外合规 · 本地化 |

### 设计师必答（业务域）
- [ ] **8 域不用色彩区分** — 仅用序号 + 衬线名 + Lucide 图标，是否可接受？
- [ ] Lucide 图标的选择（Scale 法务 / Compass 获客 / Globe2 出海 ...）是否准确？
- [ ] 8 域中文名命名是否准确？

---

## 4. 落地页面（4 个）

### 4.1 Login 页
- 7+5 不对称 grid
- 左：serif Display + H1 + body 引言 + 8 域 serif 编号目录 + 底部 micro tracker
- 右：表单（邮箱/密码 + 单一琥珀橙 CTA + OR + 微信/支付宝 ghost）

### 4.2 `/domains` DomainHomePage
- 编辑部目录式 4+8 双栏
- 左：8 业务域 serif 名录（01–08 序号 + 衬线 H2 + tagline）
- 右：当前选中域的子页列（Lucide + 衬线名 + caption + 进入 CTA）

### 4.3 WelcomeGuide modal（首登）
- 编辑级目录式 modal
- header: serif Display + serif italic 副标
- 主体: 8 行域名录（2 列 grid）
- footer: 单一「打开 AI 对话」CTA

### 4.4 Layout 顶栏 + 侧栏
- 顶栏 4 大 nav active = 1px primary underline（**非 4 种业务域色**）
- 侧栏 active = 1px primary 左线 + primary-50 微底（**非业务域 stripe + dot**）
- 顶栏 `LayoutGrid` 图标按钮直达 `/domains`

### 设计师必答（落地页）
- [ ] Login 7+5 不对称是否合理？是否需要 50/50？
- [ ] DomainHomePage 编辑部目录是否易扫读？
- [ ] WelcomeGuide modal 是否过于"出版物"风格？应不应该更友好？
- [ ] Layout active 态的 1px primary 是否过细难看？

---

## 5. 跨端实现差异

| 端 | DomainBadge 实现 |
|---|---|
| Web | Lucide SVG（与图标同源）|
| Mobile (Expo RN) | 纯文字 micro UPPERCASE（无图标，文字承担识别）|
| Mini Program (Taro) | 纯文字（Taro 受限不便用 SVG，但**不再用 emoji**）|

### 设计师必答（跨端）
- [ ] Mobile / Mini Program 端**仅文字**版本可接受吗？还是要加 SVG 图标？

---

## 6. 验收签字栏

| 项 | 设计师 | 日期 | 状态 |
|---|---|---|---|
| 调色板（暖灰 + 单一琥珀橙）| | YYYY-MM-DD | ☐ Pass / ☐ Need rework |
| 字体（系统字体 + Noto Serif SC）| | YYYY-MM-DD | ☐ Pass / ☐ Need rework |
| 业务域可视化（编号目录式）| | YYYY-MM-DD | ☐ Pass / ☐ Need rework |
| Login / DomainHomePage / WelcomeGuide / Layout | | YYYY-MM-DD | ☐ Pass / ☐ Need rework |
| 跨端一致性 | | YYYY-MM-DD | ☐ Pass / ☐ Need rework |

如有 "Need rework"，请在 PR #9 留 review comment + 具体改动建议。
