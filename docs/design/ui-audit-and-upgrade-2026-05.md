# UI 全景审计 & 升级方案 — 2026-05

> 日期：2026-05-15（首版） · 2026-05-15 Round-2（UniApp 终止后重审）
> 范围：Web (frontend) · Mobile (Expo RN) · Mini Program (Taro) · Desktop (Tauri)
> 单一真相源：`DESIGN.md` (V3) · `docs/design/cross-platform-token-drift.md` (2026-05-07)
> 本文是后续升级 PR 的执行依据，每条改动都对应一个 patch。
>
> **Round-1 范围注**：首版曾包含 `apps/uni-mobile/` 端。UniApp 路线 2026-05 终止，该端的所有 token 文件与组件已随目录一并删除；本文相应章节已更新。

---

## 1. 现状速查（Round-2 — UniApp 终止后）

| 端 | 框架 | 主色 | 暗色 | AI 语义色 | 业务域色 | 评价 |
|----|------|------|------|-----------|---------|------|
| Web (`frontend`) | React 18 + Vite + Tailwind + shadcn | 琥珀橙 `hsl(25 95% 53%)` ✓ | ✅ 完整 | ✅ 完整 | ✅ Round-1 已补 | 🟢 成熟 |
| Mobile (`mobile`) | Expo / RN 0.76 | 古铜驼 `#D4A574` | 🟡 基础 | ✅ Round-1 已补 | ✅ Round-1 已补 | 🟡 中等 |
| Mini Program (`mini-program`) | Taro 3.6 | 古铜驼 `#D4A574` | ❌ 无 | ✅ Round-1 已补 | ✅ Round-1 已补 | 🟡 中等 |
| Desktop (`desktop`) | Tauri 2 + 复用 Web | 同 Web | 同 Web | 同 Web | 同 Web | 🟢 继承 |
| ~~UniApp~~ | ~~UniApp 3 + Vue 3~~ | — | — | — | — | ❌ 2026-05 终止，目录已删 |

## 2. 行业 / 产品定位回顾

**安心 AI 智能助手** 是「面向中国成长型制造企业的全链路 AI 经营助理」，覆盖 **8 大业务域**：

| 编号 | 业务域 | 用户场景 | 视觉语义建议 |
|----|------|---------|------------|
| 01 | 法务 Legal | 合同审查、案件管理、找律师 | 暖橄榄绿 — 沉稳、克制、可信 |
| 02 | 财务 Finance | 记账、对账、报销 | 稳重蓝 — 数字精确感 |
| 03 | 税务 Tax | 申报、税务筹划 | 金箔黄 — 价值、合规 |
| 04 | 合规 Compliance | 风控、审计、监管 | 警示橙红 — 红线意识 |
| 05 | 经营管理 Operations | 数据看板、KPI、决策 | 王者紫 — 战略、统筹 |
| 06 | 调研获客 Growth | 客户调查、线索、舆情 | 青蓝 — 情报、洞察 |
| 07 | 内容产出 Content | 文案、营销素材 | 桃红 — 创作、活力 |
| 08 | 出海跨境 Global | 国际化、合规、本地化 | 深海蓝 — 远洋、全球 |

**核心矛盾**：当前设计系统是 V2「安心法务」时期定型的（专业法律工作室气质 — 琥珀橙 + 暖灰），但 V3 已扩展为 8 大业务域。**用户在导航/Dashboard 上无法快速区分自己处在哪个业务域**。

→ 必须新增**业务域色彩 token**。琥珀橙仍是品牌主色（保留品牌识别），业务域色用于辅助标识、卡片角标、模块入口。

---

## 3. 关键漂移（按优先级）

### P0（必修，影响品牌识别）— Round-2 已全部完成

| 编号 | 文件 | 问题 | 修复 | 状态 |
|----|------|------|------|----|
| ~~P0-1~~ | `apps/uni-mobile/src/styles/tokens.ts:30` | 主色 `#2563EB` 与品牌琥珀橙不符 | UniApp 路线终止，文件已删除 | ✅ Round-2 删除整个目录 |
| ~~P0-2~~ | `apps/uni-mobile/src/styles/tokens.scss:9` | 同上 | 同上 | ✅ Round-2 删除 |
| P0-3 | `frontend/src/index.css:7` | 注释残留旧品牌「安心法务」 | 改为「安心智能助手」| ✅ Round-1 完成 |

### P1（必修，影响多端一致性）

| 编号 | 涉及端 | 问题 | 修复 |
|----|------|------|------|
| P1-1 | Web | 缺 8 大业务域 token | `index.css` 新增 `--domain-*`，`tailwind.config.js` 暴露，`design-tokens.ts` 增 `domainColor` |
| P1-2 | Mobile | 缺 AI 语义色（thinking / suggestion / citation）+ 风险三档 | `colors.ts` 扩展 |
| P1-3 | Mini Program | 缺 AI 语义色 + 风险三档 + 暗色 | `design-tokens.scss` 扩展 |
| P1-4 | Web | 缺统一 `DomainBadge` / `DomainCard` 组件 | `frontend/src/components/ui/domain.tsx` 新建 |

### P2（次要，可后续）

| 编号 | 端 | 问题 | 修复 |
|----|------|------|------|
| P2-1 | Mobile | 字体未显式声明 PingFang | `theme/typography.ts` 新增 |
| P2-2 | Mini Program | 字号层级压缩 | `design-tokens.scss` 增 `$font-title/$font-section/$font-body` |
| ~~P2-3~~ | ~~UniApp~~ | 业务页面色彩硬编码风险 | UniApp 已终止，此项不再适用 |

---

## 4. 升级落地清单（本次 PR 范围）

```
[品牌一致性]
✏️  frontend/src/index.css           — 注释品牌名修正
🆕  frontend/src/index.css           — 新增 8 大业务域 CSS 变量 (浅/深双模式)
🆕  frontend/tailwind.config.js      — 暴露 domain-* utility
🆕  frontend/src/lib/design-tokens.ts — 新增 domainColor 配置
🆕  frontend/src/lib/domains.ts      — 业务域元数据中心 (icon/label/path/color)
🆕  frontend/src/components/ui/domain.tsx — DomainBadge / DomainCard

[多端对齐]
✏️  mobile/src/theme/colors.ts       — 增 AI 语义色 / 风险三档 / domain.*
✏️  mini-program/src/styles/design-tokens.scss — 增 AI 语义 / 风险三档 / domain.* / 暗色
✏️  mini-program/src/styles/design-tokens.ts   — 同步导出新 token
```

> Round-1 中曾对 `apps/uni-mobile/` 同步修改了 token；Round-2 该端整目录已删除，所有相关产出物已随之失效。

## 5. 业务域色板规范（V3 新增）

| Domain | 浅色 (HSL) | 深色 (HSL) | Hex 等效 | 用途 |
|----|---|---|---|---|
| Legal 法务 | `100 32% 38%` | `100 28% 60%` | `#5C7F3E` | 模块徽章、入口图标 |
| Finance 财务 | `217 78% 48%` | `217 70% 65%` | `#1F6FD4` | 同 |
| Tax 税务 | `42 88% 48%` | `42 80% 62%` | `#E2A311` | 同 |
| Compliance 合规 | `8 80% 52%` | `8 75% 65%` | `#E84F2E` | 同 |
| Operations 经营 | `270 60% 52%` | `270 55% 68%` | `#7D4FCC` | 同 |
| Growth 获客 | `188 78% 42%` | `188 70% 58%` | `#17AAC3` | 同 |
| Content 内容 | `335 75% 56%` | `335 68% 68%` | `#DE3F88` | 同 |
| Global 出海 | `205 80% 35%` | `205 70% 58%` | `#1768A1` | 同 |

**约束**：
1. 业务域色 **不替代** 品牌琥珀橙 — 主行动按钮、激活态、品牌识别仍用 `--primary`。
2. 域色仅用于：模块入口卡片角标、Dashboard 业务域分区、面包屑徽章、域内子页面的辅助强调（如折线图、tag bar）。
3. **禁止** 把域色用于按钮主色、链接默认色、表单聚焦色。
4. 与现有 `--risk-high / medium / low` 不冲突 — 风险色是「状态」，域色是「分类」。

## 6. 验证步骤

| 步骤 | 操作 | 期望 |
|----|---|---|
| 1 | `pnpm --filter @anxin/frontend dev` 启动 | 端口正常监听 |
| 2 | 打开任意页面 | 视觉零回归（仅新增 token，未改业务样式） |
| 3 | DevTools → Console 执行 `getComputedStyle(document.documentElement).getPropertyValue('--domain-legal')` | 输出 `100 32% 38%` |
| 4 | 切换深色 | 域色阶按 `.dark` 块切换 |
| 5 | 引入示例 `<DomainBadge domain="legal" />` | 渲染暖橄榄绿小徽章 |

## 7. 不在本次范围（留下次）

- 全量业务页迁移到域色（800+ tsx）— 仅在 Layout 模块入口/Dashboard 做示范
- Mobile/Mini Program 暗色全覆盖（需要逐页验证）
- UniApp 业务页 hex 替换（先把 tokens 改对，再扫页面）
- 桌面 Tauri 独立 token 层（目前继承 Web 即可）
- 删除/合并旧 `mobile/src/constants/colors.ts`（避免影响 V2 老页面）

## 8. 风险

| 风险 | 概率 | 缓解 |
|----|----|----|
| Tailwind 引入新 utility 增大 CSS 体积 | 低 | 新 token 总计 < 80 行，gzip 后 < 1 KB |
| UniApp 主色切换导致测试快照失效 | 中 | 改完检查 `tokens.test.ts`，期望值同步更新 |
| 业务域色在长文本背景下对比度不足 | 中 | 仅用于 badge/icon/strip，禁止用作大面积底 |
