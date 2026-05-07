# 安心法务 — 设计系统规范

> 版本：1.0 | 日期：2026-03-26 | 状态：生效中

## 1. 设计原则

| 原则 | 说明 |
|------|------|
| **语义化** | 使用 CSS 变量定义颜色，禁止硬编码 `zinc-*`/`gray-*` |
| **一致性** | 所有页面使用 `PageContainer` 统一布局 |
| **可访问** | 遵循 WCAG 2.1 AA 标准，最小触控区 44px |
| **跨端统一** | 设计令牌在 Web/小程序/Desktop/Mobile 统一映射 |
| **深浅色** | 所有组件必须支持深浅色模式切换 |

## 2. 色彩系统

### 2.1 语义色（CSS 变量）

**浅色模式（`:root`）：**
| 变量 | 用途 | HSL值 |
|------|------|-------|
| `--background` | 页面背景 | `0 0% 100%` |
| `--foreground` | 主文本 | `220 14% 10%` |
| `--primary` | 品牌主色 | `216 98% 52%` |
| `--secondary` | 次要操作 | `220 14% 96%` |
| `--muted` | 弱化背景 | `220 14% 96%` |
| `--muted-foreground` | 弱化文本 | `220 9% 46%` |
| `--accent` | 强调色 | `220 14% 96%` |
| `--destructive` | 危险/删除 | `0 84% 60%` |
| `--border` | 边框 | `220 13% 91%` |
| `--ring` | 焦点环 | `216 98% 52%` |
| `--card` | 卡片背景 | `0 0% 100%` |

**深色模式（`.dark`）：**
| 变量 | HSL值 |
|------|-------|
| `--background` | `220 16% 8%` |
| `--foreground` | `220 13% 91%` |
| `--primary` | `217 80% 56%` |
| `--card` | `220 15% 11%` |
| `--muted` | `220 14% 15%` |
| `--border` | `220 13% 18%` |

### 2.2 状态色

| 状态 | 浅色 | 深色 | 用途 |
|------|------|------|------|
| Success | `emerald-500` | `emerald-400` | 成功、通过 |
| Warning | `amber-500` | `amber-400` | 警告、待处理 |
| Error | `red-500` | `red-400` | 错误、拒绝 |
| Info | `blue-500` | `blue-400` | 提示、信息 |

### 2.3 颜色迁移规则（必须遵守）

| 禁止使用 | 替换为 |
|---------|--------|
| `bg-white` / `bg-zinc-50` | `bg-background` |
| `bg-zinc-100` / `bg-gray-100` | `bg-muted` |
| `text-zinc-700` / `text-gray-700` | `text-foreground` |
| `text-zinc-500` / `text-gray-500` | `text-muted-foreground` |
| `border-zinc-200` / `border-gray-200` | `border-border` |
| `hover:bg-zinc-100` | `hover:bg-muted` |
| `ring-zinc-300` | `ring-ring` |

## 3. 排版系统

| 级别 | Tailwind | 用途 |
|------|----------|------|
| H1 | `text-2xl font-semibold` | 页面标题 |
| H2 | `text-xl font-semibold` | 区段标题 |
| H3 | `text-lg font-medium` | 卡片标题 |
| H4 | `text-base font-medium` | 子标题 |
| Body | `text-sm` | 正文内容 |
| Caption | `text-xs text-muted-foreground` | 辅助说明 |

**字体栈**：`system-ui, -apple-system, sans-serif`

## 4. 间距系统

| 场景 | Desktop | Mobile |
|------|---------|--------|
| 页面内边距 | `px-6 py-6` | `px-4 py-4` |
| 卡片内边距 | `p-5` | `p-4` |
| 区段间距 | `space-y-6` | `space-y-4` |
| 元素间距 | `gap-4` | `gap-3` |
| 紧凑模式 | `p-3 gap-2` | `p-2 gap-2` |

## 5. 圆角系统

| 组件 | 圆角 |
|------|------|
| 按钮 | `rounded-lg` (8px) |
| 卡片 | `rounded-xl` (12px) |
| 对话框 | `rounded-2xl` (16px) |
| 头像 | `rounded-full` |
| 输入框 | `rounded-md` (6px) |
| 气泡 | `rounded-2xl` (16px) |
| 标签 | `rounded-full` |

## 6. 阴影系统

| 级别 | Tailwind | 用途 |
|------|----------|------|
| 卡片 | `shadow-sm hover:shadow-md` | 内容卡片 |
| 下拉 | `shadow-lg` | 下拉菜单、Popover |
| 对话框 | `shadow-xl` | Modal、Sheet |
| 浮动 | `shadow-md` | FAB、浮动按钮 |

## 7. 图标系统

**唯一图标库**：`lucide-react` (1000+ SVG 图标)

| 尺寸 | Tailwind | 像素 | 用途 |
|------|----------|------|------|
| xs | `w-3 h-3` | 12px | 标签内、状态指示 |
| sm | `w-4 h-4` | 16px | 内联文本、按钮图标 |
| md | `w-5 h-5` | 20px | 导航项、操作按钮 |
| lg | `w-6 h-6` | 24px | 标题装饰、空状态 |
| xl | `w-8 h-8` | 32px | 功能入口 |
| 2xl | `w-12 h-12` | 48px | 首屏装饰 |

**使用规范**：
```tsx
// 正确：统一从 icons.ts 导入
import { FileText, Search } from '@/lib/icons';

// 禁止：直接从 lucide-react 或 @heroicons 导入
```

## 8. 动效系统

### 8.1 时长标准

| 类型 | 时长 | 用途 |
|------|------|------|
| fast | 150ms | 按钮状态、hover、toggle |
| normal | 200ms | 面板展开、Tab 切换 |
| slow | 300ms | 页面过渡、模态框 |
| spring | `stiffness:300 damping:30` | 卡片入场、列表动画 |

### 8.2 入场动画

```tsx
// 页面入场
const pageVariants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.2 }
};

// 卡片交错入场
const cardVariants = {
  initial: { opacity: 0, y: 12 },
  animate: (i: number) => ({
    opacity: 1, y: 0,
    transition: { delay: i * 0.05 }
  })
};

// 弹出层
const popupVariants = {
  initial: { opacity: 0, scale: 0.95 },
  animate: { opacity: 1, scale: 1 }
};
```

### 8.3 Lottie 动画

存放目录：`frontend/src/assets/animations/`

| 场景 | 文件名 | 用途 |
|------|--------|------|
| 加载中 | `loading.json` | 全局/局部加载态 |
| 空状态 | `empty.json` | 列表无数据 |
| 成功 | `success.json` | 操作完成反馈 |
| 搜索中 | `searching.json` | 搜索等待 |
| AI思考 | `thinking.json` | Agent 处理中 |

## 9. 响应式断点

| 断点 | 宽度 | 布局 |
|------|------|------|
| mobile | < 640px | 单列，汉堡菜单展开全屏 |
| tablet | 640-1023px | 双列，汉堡菜单 |
| desktop | >= 1024px | 多列，顶部导航 + Apple/影石风格全屏下拉面板 |

### 9.1 桌面端导航交互

- **顶部固定导航栏**: 60px 高度，Logo 左置 + 四大业务域下拉菜单居中 + 系统功能右置
- **下拉面板**: hover 触发全屏宽度面板，背景半透明 + 模糊效果（backdrop-blur）
- **子菜单网格**: 2-3 列网格布局，每项带图标背景圆角方块
- **遮罩层**: 面板展开时下方内容覆盖 bg-black/20 + backdrop-blur-sm

## 10. 组件规范

### 10.1 按钮变体

| 变体 | 用途 | 样式 |
|------|------|------|
| default | 主操作 | `bg-primary text-primary-foreground` |
| secondary | 次要操作 | `bg-secondary text-secondary-foreground` |
| outline | 边框按钮 | `border border-input bg-background` |
| ghost | 幽灵按钮 | `hover:bg-accent` |
| destructive | 危险操作 | `bg-destructive text-destructive-foreground` |

### 10.2 卡片变体

| 变体 | 用途 | 样式 |
|------|------|------|
| base | 默认卡片 | `bg-card rounded-xl border shadow-sm` |
| interactive | 可点击 | `base + hover:shadow-md cursor-pointer transition` |
| highlight | 强调卡片 | `base + border-primary/20 bg-primary/5` |
| compact | 紧凑卡片 | `base + p-3` |

### 10.3 页面布局

```
所有业务页面结构：
┌─────────────────────────┐
│ PageContainer           │
│ ┌─────────────────────┐ │
│ │ PageHeader           │ │  标题 + 描述 + 操作按钮
│ ├─────────────────────┤ │
│ │ FilterBar (可选)     │ │  搜索、筛选、排序
│ ├─────────────────────┤ │
│ │ Content Area         │ │  卡片网格 / 列表 / 表格
│ ├─────────────────────┤ │
│ │ Pagination (可选)    │ │  分页控制
│ └─────────────────────┘ │
└─────────────────────────┘
```

## 11. 跨端设计令牌映射

| 维度 | Web | 小程序 | Desktop | Mobile |
|------|-----|--------|---------|--------|
| 色彩 | CSS 变量 | WXSS 变量 | CSS 变量 | StyleSheet |
| 深浅色 | `prefers-color-scheme` | 系统+手动 | 系统+手动 | `Appearance` |
| 图标 | lucide SVG | SVG/font | lucide SVG | vector-icons |
| 动效 | Framer Motion | wx.animate | Framer Motion | Reanimated 3 |
| Lottie | lottie-react | lottie-mp | lottie-react | lottie-rn |

## 12. 深浅色检查清单

- [ ] 所有组件使用 CSS 变量引用颜色
- [ ] 图片/图标使用 `currentColor` SVG 或准备双套
- [ ] 图表（Recharts）使用主题色变量
- [ ] Lottie 动画颜色参数化
- [ ] 3D/地图场景提供暗色皮肤
- [ ] 无硬编码 `zinc-*`/`gray-*`/`white`/`black` 色值
