# 安心智能助手 · UI 设计规范

> 单一可执行真相源。任何 PR 涉及 UI 必须先读本文。冲突时本文优先于 `DESIGN.md`。
>
> 适用范围：`frontend/` (Web/Desktop) · `mobile/` (Expo RN) · `mini-program/` (Taro)
>
> 关联文档：
> - [`DESIGN.md`](DESIGN.md) — 设计哲学与历史背景
> - [`docs/design/v3-prototype-editorial.html`](docs/design/v3-prototype-editorial.html) — 视觉锚点 prototype
> - [`docs/design/full-page-audit-2026-05-20.md`](docs/design/full-page-audit-2026-05-20.md) — 全谱页面合规审计
> - [`docs/design/ui-audit-and-upgrade-2026-05.md`](docs/design/ui-audit-and-upgrade-2026-05.md) — Reset 决策记录
>
> 守护测试：`frontend/src/brand-consistency.test.ts` + 跨端对应文件（违反规则即 vitest 失败）

---

## 0. 设计哲学 (One-line Spec)

> **像一间被精心整理过的专业法律工作室 — 光线柔和、秩序清晰、层级克制。**

**Aesthetic Direction**: Editorial Luxury（编辑级排版 · 克制的奢华）

### 三条根本约束
1. **不像通用 SaaS 控制台** — 没有 8 色拼盘、没有 dashboard 风格
2. **不强调 AI 感** — 不靠紫色/渐变/脉冲动画展示"AI"
3. **专业 > 友好** — 中信书店 × 律师事务所大堂气质，不是消费级 App

### 三条根本资源
- **颜色**：单一品牌琥珀橙 `--primary` (`hsl(25 95% 53%)`) + 暖灰阶梯
- **字体**：中文系统字体（PingFang/Microsoft YaHei/Noto Sans SC）+ Editorial Serif（Noto Serif SC）
- **图标**：Lucide（Web）/ Ionicons（RN 平台 API）— 全单色线性 1.5px stroke

---

## 1. 颜色规范

### 1.1 唯一彩色锚点：品牌琥珀橙

```css
--primary:       hsl(25 95% 53%);    /* #F08A2A — 唯一彩色，仅 CTA / active / 焦点环 */
--primary-700:   hsl(17 88% 40%);    /* hover / pressed */
--primary-50:    hsl(33 100% 97%);   /* active 微提示底（侧栏 active 行）*/
```

### 1.2 暖灰阶梯（所有非 CTA 元素都从这里取色）

```css
--bg:            hsl(30 14% 98%);   /* #FAF8F5  纸张暖白 - 页面底层 */
--surface-1:     hsl(0 0% 100%);    /* 主面 - 卡片底 */
--surface-2:     hsl(30 14% 96%);   /* hover 面 - 列表 hover / toolbar */
--surface-3:     hsl(32 18% 95%);   /* 分组底 */
--foreground:    hsl(20 14% 10%);   /* #1C1815  主文本（暖墨）*/
--muted-foreground: hsl(20 9% 46%); /* 次文本 */
--text-tertiary: hsl(20 8% 60%);    /* 弱说明 / micro tracker */
--text-disabled: hsl(20 7% 72%);    /* 禁用 */
--border:        hsl(30 13% 91%);   /* 标准发丝边 */
--border-strong: hsl(30 12% 84%);   /* 高对比边 */
--border-subtle: hsl(30 10% 94%);   /* 极弱分隔 */
```

### 1.3 状态色（极低饱和墨色）

```css
--success:       hsl(142 76% 36%);   /* 通过 / 已签约 */
--warning:       hsl(38 92% 50%);    /* 待审 / 中风险 */
--destructive:   hsl(0 72% 51%);     /* 错误 / 高风险 */
--info:          hsl(217 91% 60%);   /* 中性提示（已签约前置） */
```

### 1.4 AI 单独保留（**仅** AI 生成态用）

```css
--ai:            hsl(262 83% 58%);   /* 仅 AI 身份 / 推理流 / 生成态 — 不参与业务流程 */
```

### 1.5 ❌ FORBIDDEN COLORS

按 `ui-design` skill 硬性禁令：
| 色族 | 禁用值 | 例外 |
|---|---|---|
| 紫色 | `text-violet-*` / `bg-violet-*` / `text-purple-*` / `bg-purple-*` / `text-indigo-*` / hsl hue 260-290 | 仅 `--ai` 变量（AI 生成态） |
| 高饱和 8 域色 | 任何 `--domain-*` 变量回归 | 无 |
| 域名色 | 8 业务域不用色彩区分 | 详见 §5.8 |

### 1.6 Do / Don't · 颜色使用示例

#### ✅ Do
```tsx
{/* CTA 按钮：单一品牌色 */}
<button className="bg-primary hover:bg-primary-700 text-primary-foreground">登 录</button>

{/* 状态徽章：墨色 tone-only，无背景色块 */}
<span className="text-success">✓ 已通过</span>
<span className="text-destructive">! 高风险</span>

{/* 次要文本：muted-foreground */}
<p className="text-muted-foreground">说明文字</p>

{/* hover：暖灰阶（surface-2） */}
<div className="hover:bg-surface-2/40 transition-colors">列表行</div>
```

#### ❌ Don't
```tsx
{/* 业务域 8 色块 — 已删除 */}
<span className="bg-domain-legal text-domain-legal-foreground">法务</span>  ❌

{/* 紫色族 */}
<button className="bg-violet-500 hover:bg-purple-600">操作</button>  ❌

{/* 散落硬编码 hex */}
<div style={{ backgroundColor: '#FBF3E8', color: '#1D2129' }}>...</div>  ❌

{/* 状态色用背景色块 */}
<span className="bg-green-50 text-green-700 px-2 py-0.5 rounded-full">成功</span>  ❌
{/* 应改为 */}
<span className="text-success">✓ 成功</span>  ✅
```

### 1.7 业务域 ≠ 颜色

**业务域用以下手段区分（不用色彩）**：
- 序号 `01`–`08`（serif tabular-nums）
- 衬线域名（H2/H3 字号层次）
- Lucide 单色线性图标
- 1px hairline 边界

详见 §5.8 业务域可视化规范。

---

## 2. 字体规范

### 2.1 三个字体栈

```ts
// frontend/tailwind.config.js
sans:  ["PingFang SC", "Microsoft YaHei", "Noto Sans SC", "Hiragino Sans GB", "WenQuanYi Micro Hei", "sans-serif"]
serif: ["Noto Serif SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", "serif"]
mono:  ["JetBrains Mono", "SF Mono", "Menlo", "Monaco", "Consolas", "monospace"]
```

### 2.2 ❌ FORBIDDEN FONTS

`ui-design` skill 明令禁止：`Inter` / `Roboto` / `Arial` / `Helvetica` / `Helvetica Neue` / `system-ui` / `-apple-system` / `BlinkMacSystemFont`

**唯一例外**：`mobile/src/theme/typography.ts` 的 `'System'` / `'Roboto'` 是 React Native `fontFamily` prop 的平台 API 字面值（OS 选系统字体），不是 Web CSS — 已加注释保留。

### 2.3 字号层级（Editorial 大跨度）

| Role | Font | Size | Line-Height | Letter-Spacing | Weight | 用途 |
|---|---|---|---|---|---|---|
| Display | **Serif** | 48px | 1.1 | -0.04em | 500 | Login / DomainHomePage / WelcomeGuide 主标题 |
| H1 | **Serif** | 32px | 1.2 | -0.02em | 500 | 业务子页主标题、业务域名 |
| H2 | Sans | 24px | 1.3 | -0.01em | 500 | 区块标题 |
| H3 | Sans | 18px | 1.4 | -0.005em | 600 | 卡片/面板标题 |
| Body | Sans | 15px | 1.65 | 0 | 400 | 标准正文 |
| Caption | Sans | 13px | 1.5 | 0.01em | 400 | 次要说明、列表 meta |
| **Micro** | **Sans** | **11px** | **1.4** | **0.16em** UPPERCASE | **500** | **Editorial 标志细节** — tracker / 元信息 |

### 2.4 衬线 Display + Micro tracker：Editorial 标志组合

```tsx
{/* 标准业务页头部 — 使用 EditorialPageHeader */}
<EditorialPageHeader
  tracker={["Legal", "案件中心"]}        // → "LEGAL · 案件中心" (micro UPPERCASE)
  title="案件中心"                       // → serif 32px
  description="案件全生命周期 · 团队协作" // → serif italic 副标
/>
```

### 2.5 ❌ 字号违规模式

```tsx
{/* 散落使用 Tailwind 默认字号 */}
<h1 className="text-4xl font-bold">标题</h1>  ❌
<h2 className="text-3xl font-semibold">区块</h2>  ❌

{/* 字重违规：font-bold 不在 Editorial Luxury 体系内 */}
<span className="font-bold">强调</span>  ❌
<span className="font-extrabold">很重要</span>  ❌
```

#### ✅ 正确写法
```tsx
{/* 优先用 EditorialPageHeader */}
<EditorialPageHeader title="标题" size="display" />

{/* 不在模板内时使用 token */}
<h1 className="font-serif text-[32px] leading-[1.2] tracking-[-0.02em] font-medium text-foreground">
  标题
</h1>

{/* 强调用 font-medium，不用 font-bold */}
<span className="font-medium">强调</span>
```

### 2.6 数字必用 tabular-nums

```tsx
{/* 金额 / 计数 / 序号 必须 */}
<span className="tabular-nums">{amount.toLocaleString()}</span>
<span className="tabular-nums">{String(index + 1).padStart(3, '0')}</span>
```

---

## 3. 布局规范

### 3.1 容器选择决策表

| 页面类型 | 用哪个容器 |
|---|---|
| 列表页（Cases / Contracts / Leads / Documents）| `<ListPageTemplate>` |
| 详情页（CaseDetail / LawyerProfile） | `<DetailPageTemplate>` |
| 表单页（Settings / Onboarding） | `<FormPageTemplate>` |
| Dashboard（LawyerDashboard / Monitoring） | `<DashboardTemplate>` + `<PanelSection>` |
| 后台表格（AdminBilling / AdminConfig） | `<AdminTableTemplate>` |
| 复杂特殊页（Chat / KnowledgeGraph） | 自定义但必须有 `<EditorialPageHeader>` 头部 |
| **禁止** | 完全自定义、无标准头部、无 hairline |

模板源码：`frontend/src/components/ui/{ListPage,DetailPage,FormPage,Dashboard,AdminTable}Template.tsx`

### 3.2 间距规范（Editorial 大留白）

```ts
// 通用间距
section gap:  64px (page sections)
card padding: 32px (Editorial cards / PanelSection)
field gap:    16px (form fields)
inline gap:   8px / 12px (chip / icon + text)

// 模板内置默认
ListPageTemplate header → toolbar:   32px (mb-8)
ListPageTemplate toolbar → body:     none (toolbar 自带 mb-6)
DetailPageTemplate header → body:    40px (mb-10)
```

### 3.3 容器最大宽度

```ts
list / dashboard / admin:  1400-1600px
detail:                    1400px
form:                       960px  (聚焦)
chat:                       全宽
```

### 3.4 分隔手段：hairline 优先

```tsx
{/* ✅ hairline 1px border 分隔 — Editorial */}
<div className="border-b border-border/60">
  ...
</div>

{/* ❌ 卡片阴影分隔 — V2 SaaS 风格 */}
<div className="shadow-lg rounded-2xl">
  ...
</div>
```

### 3.5 移动端

| 断点 | Tailwind | 含义 |
|---|---|---|
| `sm:` | ≥ 640px | 大手机 |
| `md:` | ≥ 768px | 平板 |
| `lg:` | ≥ 1024px | 桌面 — Editorial 双栏 grid 在此切换 |
| `xl:` | ≥ 1280px | 大桌面 — 边距增加到 px-16/24 |

所有 PageTemplate 在 `lg:` 以下退化为单列 + 单一向滚动。

---

## 4. 组件规范

### 4.1 按钮

| 类型 | 何时用 | Class |
|---|---|---|
| Primary CTA | 页面唯一主行动（新建/确认/登录）| `bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2.5 text-[14px] font-medium` |
| Ghost / Secondary | 次要行动（取消/返回） | `border border-border hover:border-foreground text-foreground/80 hover:text-foreground px-4 py-2 text-[13px]` |
| Destructive | 删除/流失 | `text-destructive border border-destructive/40 hover:bg-destructive/5 px-4 py-2 text-[13px]` |
| Icon-only | 工具栏 / 表头小操作 | `p-1.5 text-muted-foreground hover:text-foreground hover:bg-surface-2 rounded-sm` |

#### ❌ 禁用按钮模式
```tsx
{/* rounded-full pill 按钮 — V2 SaaS 风格 */}
<button className="rounded-full bg-primary px-6 py-3">操作</button>  ❌

{/* shadow 凸起按钮 */}
<button className="shadow-md hover:shadow-xl">点击</button>  ❌
```

### 4.2 表单输入

```tsx
{/* 标准 Editorial input — 下划线风格（参考 Login 表单）*/}
<div>
  <label className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground block mb-2">
    邮箱
  </label>
  <input
    type="email"
    className="w-full bg-transparent border-0 border-b border-border focus:border-primary py-3 text-[15px] text-foreground placeholder:text-text-disabled outline-none transition-colors"
    placeholder="name@company.com"
  />
</div>
```

### 4.3 状态色徽章（无背景色块版）

```tsx
{/* ✅ Editorial tone-only badge */}
<span className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-success">
  <span className="h-1 w-1 rounded-full bg-current" aria-hidden />
  <span>Won</span>
  <span className="text-foreground/30" aria-hidden>·</span>
  <span className="normal-case tracking-normal text-foreground/80">已签约</span>
</span>

{/* ❌ V2 chip 风格 — bg + 圆角胶囊 */}
<span className="bg-green-50 text-green-700 px-2 py-0.5 rounded-full">已签约</span>  ❌
```

### 4.4 表格

走 `<AdminTableTemplate>`。要点：
- 表头 `bg-surface-2`，sticky 时 `z-[1]`
- 行间 `border-b border-border/60`，**不用斑马纹**
- 行 hover `hover:bg-surface-2/40`
- 数字列 `tabular-nums` 右对齐
- 操作列 `sticky right-0 bg-card`

### 4.5 卡片

```tsx
{/* ✅ Editorial 卡片 — 1px 边 + 暖灰底，无 shadow */}
<div className="border border-border bg-card px-5 py-4">...</div>

{/* ✅ KPI 网格（DashboardTemplate 内置）— 0gap 共享 border */}
<div className="grid grid-cols-4 gap-px bg-border border-t border-l border-border">
  <div className="bg-card px-6 py-5 border-r border-b border-border">...</div>
</div>

{/* ❌ V2 圆角卡片 */}
<div className="rounded-2xl shadow-md p-6 bg-white">...</div>  ❌
```

### 4.6 Modal / Drawer

- Modal：`<Dialog>` (Radix) + 内部用 `EditorialPageHeader` 风格头部
- Drawer 仅用于移动端 — 桌面用 modal 或 sticky aside
- 背景 `bg-black/30 backdrop-blur-md`，Editorial 不用模糊高光

### 4.7 Toast 通知

```tsx
import { toast } from 'sonner'

toast.success('已保存')              // ✅
toast.error('网络错误', { description: '请稍后重试' })
```

**禁止**：自定义 Toast 风格、用 alert()、用 emoji 前缀。

### 4.8 状态：Empty / Loading / Error

| 状态 | 推荐组件 |
|---|---|
| Empty (List) | `<ListPageStatus tracker="Empty" title="..." description="..." />` |
| Loading | `<ListPageStatus tracker="Loading" title="正在加载" />` |
| Error | `<ListPageStatus tracker="Error" title="..." tone="error" />` |
| 旧的 `<EmptyState>` `<LoadingState>` `<ErrorState>` | 仍可用但应渐进迁移到上述 |

### 4.9 图标

✅ **唯一图标库**：`lucide-react` (Web) / `@expo/vector-icons` Ionicons (Mobile)

```tsx
import { ArrowRight, FileText, Search } from 'lucide-react'

<ArrowRight className="w-4 h-4 stroke-[1.5] text-muted-foreground" />
```

❌ **禁用**：
- emoji 作 UI 图标（⚖️💰📊 等）
- 业务域图标染色（保持 `text-muted-foreground` 单色）
- 多色 logo 图标
- 自制 SVG 图标（除非 lucide 真没有）

### 4.10 域可视化 5 个原子

| 组件 | 用途 | 文件 |
|---|---|---|
| `<DomainBadge>` | micro UPPERCASE「LEGAL · 法务」 | `components/ui/domain.tsx` |
| `<DomainStripe>` | Reset 后 no-op shim（已废 4pt 彩条） | 同上 |
| `<DomainCard>` | Dashboard 入口卡（序号 + 衬线名 + Lucide） | 同上 |
| `<DomainGrid>` | 编辑级 2 列目录 | 同上 |
| `<DomainBreadcrumb>` | 业务域面包屑 | `components/ui/DomainBreadcrumb.tsx` |

---

## 5. 业务流统一模式

### 5.1 CRUD 模式

| 动作 | 入口 | 验证 | 反馈 |
|---|---|---|---|
| 创建 | 列表页右上角 Primary CTA「新建 + Lucide Plus」 | 表单字段必填 + format | `toast.success('已创建')` + 跳转详情 |
| 编辑 | 详情页右上角 Ghost「编辑」 / 列表行 hover icon | 同上 | `toast.success('已保存')` |
| 删除 | 详情页或 admin 表格右侧 Destructive ghost | `<ConfirmDialog>` 二次确认 | `toast.success('已删除')` |
| 详情 | 列表行 onClick / href | — | — |

### 5.2 列表筛选模式

```tsx
{/* ListPageTemplate.tabs — Editorial underline */}
tabs={[
  { key: 'all',     label: '全部', count: 142 },
  { key: 'pending', label: '待审', count: 23 },
  { key: 'won',     label: '已签约', count: 96 },
]}
activeTab={status}
onTabChange={setStatus}
```

### 5.3 搜索模式

```tsx
<div className="relative">
  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground stroke-[1.5]" />
  <input
    className="pl-8 pr-3 py-1.5 text-[13px] bg-surface-2/60 border border-transparent hover:border-border focus:border-foreground transition-colors outline-none w-48"
    placeholder="搜索合同名 / 客户 / 编号"
  />
</div>
```

### 5.4 分页模式

```tsx
<footer className="mt-12 pt-6 border-t border-border flex items-center justify-between text-[13px] text-muted-foreground">
  <span className="text-[11px] uppercase tracking-[0.16em]">
    显示 {start}–{end} · 共 {total} 条
  </span>
  <div className="flex items-center gap-1">
    <button disabled className="ghost"><ChevronLeft /></button>
    <button className="text-foreground font-medium" aria-current="page">1</button>
    <button>2</button>
    <button><ChevronRight /></button>
  </div>
</footer>
```

### 5.5 错误处理统一

```ts
try {
  await api.someAction()
  toast.success('已完成')
} catch (err) {
  // 1. 业务错误（4xx）：toast.error + 留在原页
  // 2. 网络错误：toast.error('网络错误，请稍后重试')
  // 3. 鉴权错误（401）：刷新 token 或跳登录
  // 4. 服务器错误（5xx）：toast.error + 上报 Sentry
}
```

### 5.6 加载态优先级

1. **页面初始加载**：用 ListPageStatus / Skeleton（不闪烁）
2. **行内动作**：button 内嵌 `<Loader2 className="animate-spin" />` + disabled
3. **后台轮询**：不显示 loading（用户无感）

### 5.7 表单提交模式

```tsx
const [submitting, setSubmitting] = useState(false)
async function onSubmit(values: FormValues) {
  setSubmitting(true)
  try {
    await api.create(values)
    toast.success('已创建')
    navigate('/detail/' + result.id)
  } catch (err) {
    toast.error(err.message || '创建失败')
  } finally {
    setSubmitting(false)
  }
}

<button type="submit" disabled={submitting} className="bg-primary ...">
  {submitting ? '提交中…' : '创建'}
</button>
```

### 5.8 业务域可视化规范

**核心原则**：8 业务域 **不用色彩区分**。区分手段：序号 + 衬线域名 + Lucide + 字距层次。

#### 元数据真相源
- Web：`frontend/src/lib/domains.ts` 的 `DOMAINS` 数组
- Mobile：`mobile/src/theme/colors.ts` 的 `domainMeta`
- Mini Program：`mini-program/src/styles/design-tokens.ts` 的 `domainMeta`

字段：`id / label / labelEn / tagline / defaultPath / icon`（**无 color / surface / cssVar**）

#### 标准 8 域编号
| # | id | label | labelEn | Icon |
|---|---|---|---|---|
| 01 | `legal` | 法务 | Legal | `Scale` |
| 02 | `finance` | 财务 | Finance | `Calculator` |
| 03 | `tax` | 税务 | Tax | `Landmark` |
| 04 | `compliance` | 合规 | Compliance | `ShieldCheck` |
| 05 | `operations` | 经营管理 | Operations | `LineChart` |
| 06 | `growth` | 调研获客 | Growth | `Compass` |
| 07 | `content` | 内容产出 | Content | `PenLine` |
| 08 | `global` | 出海跨境 | Global | `Globe2` |

---

## 6. 文案与术语

### 6.1 品牌

- ✅ **「安心智能助手」** — 标准名
- ✅ **「全链路 AI 经营助理」** — 标准定位
- ❌ ~~「安心法务」~~ ~~「安心智慧法务」~~（V2 已废）
- ❌ ~~「超级安心智能助手系统」~~（V2 副标）

### 6.2 V3 术语表

| 标准用词 | 禁用 / 不推荐 |
|---|---|
| AI 对话 | ~~智能对话~~（如果共存请统一为「AI 对话」） |
| AI 助手 | ~~智能助理~~ |
| 业务域 | ~~业务模块~~ |
| 案件 | （保留 V2，产品事实）|
| 律师 / 律所 | （保留 V2，产品事实 — 注册角色）|

### 6.3 动作命名

| 中文 | 英文 micro tracker |
|---|---|
| 新建 | NEW |
| 编辑 | EDIT |
| 删除 | DELETE |
| 详情 | DETAIL |
| 提交 / 保存 | SAVE |
| 取消 / 返回 | CANCEL / BACK |
| 加载中 | LOADING |
| 错误 | ERROR |
| 空 | EMPTY |
| 已签约 / 完成 | DONE / WON |
| 失败 / 流失 | LOST / FAILED |

### 6.4 文案要求
- ✅ 所有页面用**简体中文** + 英文 micro tracker
- ✅ 标点：中文用全角（。，：；！？），英文用半角
- ✅ 数字 + 单位之间留半角空格：`5 元` / `100 条`
- ❌ 不用感叹号过度强调（除错误状态）
- ❌ 不用 emoji 表达情绪

---

## 7. 无障碍 (a11y)

| 检查项 | 要求 |
|---|---|
| 焦点环 | 所有交互元素 `focus-visible:ring-2 ring-primary` |
| 颜色对比度 | WCAG AA（4.5:1 正文 / 3:1 大字）— Editorial 暖墨 #1C1815 on 纸张 #FAF8F5 = 12.5:1 AAA |
| aria-label | 图标按钮 / 工具栏 / Tab 必须有 |
| 语义标签 | 用 `<header>` `<main>` `<nav>` `<aside>` `<article>` `<section>` |
| 表单 label | `<label htmlFor>` 关联 `<input id>` |
| 键盘 | Tab / Enter / Esc / Arrow 全支持 |
| 减弱动效 | `prefers-reduced-motion` 媒介查询尊重 |

---

## 8. 反向断链清单（违规即 vitest 失败）

工程守护文件：
- `frontend/src/brand-consistency.test.ts`
- `mobile/src/brand-consistency.test.ts`
- `mini-program/src/styles/design-tokens.test.ts`
- `mobile/src/theme/colors.test.ts`

### 8.1 颜色禁令
- ❌ `--domain-*` CSS 变量
- ❌ `colors.domain.*` Tailwind utility
- ❌ 紫色 hue 260-290 在 design token 变量
- ❌ 紫色族 utility (`bg-violet-*` / `text-purple-*` / `bg-indigo-*` / `bg-fuchsia-*`)
- ❌ 8 域专属 hex 字面值（除非在状态色重叠允许列表）

### 8.2 字体禁令
- ❌ `Inter` / `Roboto` / `Arial` / `Helvetica` / `Helvetica Neue` / `system-ui` / `-apple-system` / `BlinkMacSystemFont`
- 例外：Mobile RN `'System'` / `'Roboto'` 是平台 API 字面值，加注释保留

### 8.3 内容禁令
- ❌ emoji 作 UI 图标（Unicode 区段 `1F300-1F9FF` / `2600-26FF` / `2700-27BF`）
- ❌ V2 品牌「安心法务」「安心智慧法务」「让法律服务更简单」
- ❌ UniApp 路线痕迹（`uni-mobile` / `@dcloudio` / `apps/uni-mobile`）

### 8.4 排版反模式（建议加 Lint）
- ⚠️ 散落 `text-2xl` / `text-3xl` / `text-4xl` 出现在业务页（应走模板或 `font-serif text-[Npx]`）
- ⚠️ `font-bold` / `font-extrabold` / `font-black` 出现在业务页（应改 `font-medium`）

---

## 9. 实施路线

### 9.1 已完成（截至 2026-05-20）
- ✅ Token 层 Reset（删 8 域色 / Inter / emoji）
- ✅ 5 个 V3 原子组件三端实现
- ✅ 4 个落地页 Editorial 化（Login / DomainHomePage / WelcomeGuide / Layout）
- ✅ 5 个 PageTemplate（List / Detail / Form / Dashboard / AdminTable）
- ✅ 1 个示范页（Leads）
- ✅ ~95 跨端反向断链守护断言

### 9.2 待推进
按 `docs/design/UI_FIX_ROADMAP.md`（Step 3 产出）执行：
- Phase 2：17 个半合规页迁移
- Phase 3：15 个 List 页接 ListPageTemplate
- Phase 4：12 个 Admin 页接 AdminTableTemplate
- Phase 5：6 个 Form 页接 FormPageTemplate
- Phase 6：7 个 Dashboard 接 DashboardTemplate
- Phase 7：Chat（2796 行）单独重构
- Phase 8：v3/ 14 页评估 + 收尾

---

## 10. PR Review Checklist

提 PR 涉及 UI 时，自检：

```
颜色
[ ] 无 hex 硬编码（除 PDF 模板）
[ ] 无紫色族
[ ] 无 8 域色
[ ] CTA 用 --primary，其他用暖灰阶

字体
[ ] sans 字体栈仅 PingFang / Microsoft YaHei / Noto Sans SC
[ ] 标题 Display/H1 用 font-serif
[ ] 无 Inter / system-ui
[ ] 无 font-bold（用 font-medium）

布局
[ ] 使用了对应的 PageTemplate / EditorialPageHeader
[ ] 间距走 64/32/16/8 阶梯
[ ] 分隔用 hairline border，不用 shadow

组件
[ ] CTA 单一品牌色，非 pill 圆角
[ ] 状态徽章 tone-only，无背景色块
[ ] 图标全 lucide 单色
[ ] 0 emoji 作 UI 图标

业务流
[ ] CRUD/筛选/搜索/分页 走 §5 标准模式
[ ] toast 通知
[ ] Empty/Loading/Error 三态全覆盖

测试
[ ] vitest 通过（含 brand-consistency 守护）
[ ] typecheck 0 新错误
[ ] 浏览器 dev preview 验证页面
```

违反任一项需明确说明理由 + 单独审批。

---

> **Last updated**: 2026-05-20
> **Maintained by**: UI Architecture team
> **Test guardian**: `frontend/src/brand-consistency.test.ts` 等跨端 95+ 反向断链
