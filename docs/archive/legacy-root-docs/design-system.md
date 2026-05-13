# 安心 AI 法务 - 设计系统规范 v1.0

> 当前项目级设计真相源已升级为仓库根目录 `DESIGN.md`。本文件保留实现规范、平台说明与历史设计背景；当与 `DESIGN.md` 冲突时，以 `DESIGN.md` 为准。

> 适用平台：Web (React + Tailwind) / 移动端 H5 / 小程序
> 基准标准：WCAG 2.2 AA / W3C Design Tokens 2025.10 / 中文排版最佳实践
> 产品定位：多 Agent 智能体法务应用，对话驱动，工作台协作

---

## 1. 设计原则

| 原则 | 说明 | 法务场景体现 |
|------|------|------------|
| **清晰优先** | 法律信息必须准确无歧义 | 引用来源、风险等级、合规状态均有视觉标识 |
| **感知可控** | 用户知道 AI 在做什么 | 流式输出有光标指示，多 Agent 有进度卡片 |
| **渐进呈现** | 复杂功能分层暴露 | 快捷动作→对话→工作台→A2UI 卡片逐步深化 |
| **专业信赖** | 法务产品需要权威感 | 暖灰+琥珀色调，稳重不冰冷 |
| **多端一致** | Token 驱动，一份规范多端适配 | CSS 变量 + Tailwind + 响应式断点 |

### AI 产品专属原则

- **不确定性可见化**：Agent 推理过程、置信度、降级状态必须清晰展示
- **操作可逆**：AI 生成内容支持编辑、重新生成、撤销
- **流式体验**：内容追加时无布局跳变，自动滚动锁定
- **人机协作感**：AI 辅助以非侵入方式出现（如幽灵文本、浮动建议）

---

## 2. 设计令牌 (Design Tokens)

### 2.1 颜色系统

#### 品牌色（琥珀橙，HSL 分离式存储）

| Token | HSL 值 | HEX 近似 | 用途 |
|-------|--------|----------|------|
| `--primary-50` | 36 100% 96% | #FFF8EB | 浅底背景 |
| `--primary-100` | 33 100% 90% | #FFEDCC | 悬停态底色 |
| `--primary-200` | 31 100% 80% | #FFD699 | 选中态底色 |
| `--primary-300` | 29 97% 70% | #FFB85C | 次要按钮 |
| `--primary-400` | 27 96% 61% | #FF9B29 | 活跃指示 |
| `--primary-500` | 25 95% 53% | #F97316 | **主品牌色** |
| `--primary-600` | 22 90% 45% | #DA5E0D | 按钮悬停 |
| `--primary-700` | 20 82% 37% | #AC4A0B | 按钮按下 |
| `--primary-800` | 18 73% 30% | #853A0A | 深色强调 |
| `--primary-900` | 15 75% 20% | #592408 | 极深色 |

#### 语义色

| Token | 亮色值 | 暗色值 | 用途 |
|-------|--------|--------|------|
| `--success` | hsl(142 76% 36%) | hsl(142 69% 58%) | 合规通过、成功状态 |
| `--warning` | hsl(38 92% 50%) | hsl(45 93% 47%) | 风险提醒、待处理 |
| `--destructive` | hsl(0 84% 60%) | hsl(0 63% 31%) | 高风险、错误 |
| `--info` | hsl(217 91% 60%) | hsl(217 91% 75%) | 信息提示、链接 |
| `--ai` | hsl(262 83% 58%) | hsl(262 83% 75%) | AI 生成标识 |

#### 中性色（暖灰调）

亮色模式基底：纯白 + 暖灰
暗色模式基底：`#0D0D0C` → `#141412` → `#1C1C1A` → `#272724`（按层级递增亮度）

### 2.2 Surface 系统（背景层级）

| Token | 亮色 | 暗色 | 用途 |
|-------|------|------|------|
| `--background` | `0 0% 100%` | `20 14.3% 4.1%` | 页面底层 |
| `--card` | `0 0% 100%` | `24 9.8% 10%` | 卡片、面板 |
| `--popover` | `0 0% 100%` | `20 14.3% 4.1%` | 弹窗、下拉 |
| `--muted` | `60 4.8% 95.9%` | `12 6.5% 15.1%` | 次级背景、输入框 |

### 2.3 排版系统

#### 字体栈

```css
--font-sans-cn:
  "PingFang SC",         /* macOS/iOS */
  "HarmonyOS Sans SC",   /* HarmonyOS */
  "Microsoft YaHei UI",  /* Windows */
  "Noto Sans SC",        /* Android / Web */
  system-ui, sans-serif;

--font-mono:
  "JetBrains Mono", "Fira Code", "Cascadia Code",
  "SF Mono", Consolas, monospace;
```

#### 字号比例（基准 1rem = 16px）

| Token | 大小 | 行高 | 字重 | 用途 |
|-------|------|------|------|------|
| `text-display` | 2.5rem (40px) | 1.2 | 500 | 落地页大标题 |
| `text-h1` | 2rem (32px) | 1.25 | 500 | 页面主标题 |
| `text-h2` | 1.5rem (24px) | 1.3 | 500 | 区块标题 |
| `text-h3` | 1.25rem (20px) | 1.35 | 500 | 卡片/面板标题 |
| `text-body-lg` | 1rem (16px) | 1.75 | 400 | AI 对话正文 |
| `text-body` | 0.875rem (14px) | 1.65 | 400 | 普通正文 |
| `text-body-sm` | 0.8125rem (13px) | 1.6 | 400 | 次要信息 |
| `text-caption` | 0.75rem (12px) | 1.5 | 400 | 时间戳、标签 |

#### 中文排版要点

- 标题 `font-weight: 500`（中文 600 偏粗）
- 正文 `line-height: 1.75`（中文字符高度更饱满）
- 中英文混排保留半角空格
- 正文不加 `letter-spacing`，标题 `-0.01em`

### 2.4 间距系统（4px 基准网格）

| Token | 值 | 用途 |
|-------|------|------|
| `spacing-1` | 4px | 极小间距，图标与标签 |
| `spacing-2` | 8px | 小间距，列表项内部 |
| `spacing-3` | 12px | 紧凑间距 |
| `spacing-4` | 16px | 基础间距（基准） |
| `spacing-5` | 20px | 内容区段内部 |
| `spacing-6` | 24px | 卡片内边距 |
| `spacing-8` | 32px | 区块间距 |

**AI 对话特殊间距**：

| Token | 值 | 用途 |
|-------|------|------|
| `chat-bubble-py` | 12px | 消息气泡上下内边距 |
| `chat-bubble-px` | 16px | 消息气泡左右内边距 |
| `chat-bubble-gap` | 12px | 同角色消息间距 |
| `chat-turn-gap` | 24px | 不同角色消息组间距 |

### 2.5 圆角系统

| Token | 值 | 用途 |
|-------|------|------|
| `radius-sm` | 4px | 标签、Badge |
| `radius-md` | 8px | 按钮、输入框 |
| `radius-lg` | 12px | 卡片、面板 |
| `radius-xl` | 16px | 模态框、消息气泡 |
| `radius-2xl` | 24px | 大卡片、移动端底部面板 |
| `radius-full` | 9999px | 头像、胶囊按钮 |

### 2.6 动效令牌

| Token | 值 | 用途 |
|-------|------|------|
| `duration-instant` | 50ms | 焦点环、按钮状态 |
| `duration-fast` | 150ms | 悬停、颜色变化 |
| `duration-normal` | 250ms | 展开、折叠 |
| `duration-slow` | 400ms | 页面切换、抽屉 |

**缓动曲线**：
```css
--ease-standard:   cubic-bezier(0.2, 0, 0, 1);      /* 标准 */
--ease-decelerate: cubic-bezier(0, 0, 0.2, 1);      /* 进入 */
--ease-spring:     cubic-bezier(0.34, 1.56, 0.64, 1); /* 弹性 */
```

### 2.7 阴影系统

| Token | 亮色 | 暗色 | 用途 |
|-------|------|------|------|
| `shadow-sm` | `0 1px 2px rgba(0,0,0,0.06)` | `0 0 0 1px rgba(255,255,255,0.06)` | 卡片 |
| `shadow-md` | `0 4px 6px rgba(0,0,0,0.07)` | `0 0 0 1px rgba(255,255,255,0.08)` | 悬浮面板 |
| `shadow-lg` | `0 10px 15px rgba(0,0,0,0.08)` | `0 0 0 1px rgba(255,255,255,0.10)` | 模态框 |

---

## 3. 组件规范

### 3.1 对话 / 聊天组件

**消息气泡结构**：
```
ChatThread
  MessageGroup（同角色）
    Avatar（头像，首条显示）
    MessageBubble
      Content（Markdown 渲染）
      ToolCallBlock（工具调用，可折叠）
      ActionBar（复制/重试/反馈，悬停显示）
    Timestamp（时间戳，懒显示）
  StreamingIndicator（AI 思考/生成状态）
```

**气泡最大宽度**：桌面 70%，移动端 85%

**流式输出**：
- 字符级追加，末尾闪烁光标 `|`
- 用户未手动滚动时自动跟随
- 输出完成 500ms 后显示 ActionBar

### 3.2 输入框

```
ChatInput
  TextArea（自动扩展，min 48px，max 200px）
  AttachmentBar（附件预览横滑）
  Toolbar（左：附件/知识库选择；右：模型选择器/发送按钮）
```

**状态**：空态（发送按钮禁用）→ 有内容（品牌色激活）→ AI 响应中（变为停止按钮）

### 3.3 侧栏（ChatSidebar）

```
ChatSidebar
  SearchInput（搜索对话标题）
  FilterTabs（全部 / 收藏）
  ConversationList
    ConversationItem
      Title
      LastMessage（截断）
      StarButton（收藏/取消）
      Timestamp
  NewChatButton
```

### 3.4 模型选择器（ModelSelector）

```
ModelSelector（下拉选择器，位于输入框工具栏）
  CurrentModel（显示当前模型名）
  Dropdown
    ModelOption（名称 + 提供商标签 + 默认标记）
```

---

## 4. 布局系统

### 4.1 响应式断点

| 断点 | 宽度 | 布局 |
|------|------|------|
| `mobile` | < 768px | 单栏，底部 Tab |
| `tablet` | 768-1023px | 双栏（侧栏可收起） |
| `desktop` | >= 1024px | 三栏（侧栏 + 对话 + 工作台） |

### 4.2 三栏布局尺寸

| 区域 | 展开宽度 | 收起宽度 | 最小宽度 |
|------|---------|---------|---------|
| 左侧栏 | 220px | 56px | 56px |
| 对话区 | flex-1 | flex-1 | 320px |
| 工作台 | 400px | 0px | 320px |

### 4.3 Container Queries（组件级响应）

```css
/* 对话消息在窄容器中自适应 */
@container chat-area (max-width: 480px) {
  .message-bubble { max-width: 90%; }
  .action-bar { flex-wrap: wrap; }
}
```

---

## 5. 无障碍规范 (WCAG 2.2 AA)

- **对比度**：正文 >=4.5:1，大文本 >=3:1
- **焦点可见**：所有交互元素有 `focus-visible` 环（3px `--ring` 色）
- **触摸目标**：最小 44x44px（移动端），最小 32x32px（桌面端）
- **减弱动画**：`prefers-reduced-motion: reduce` 时取消所有非必要动画
- **键盘导航**：Tab 顺序、Enter 确认、Esc 取消
- **屏幕阅读器**：`aria-label` / `role` / `aria-live` 用于动态内容

---

## 6. AI 交互规范

### 6.1 Agent 状态可视化

| 状态 | 视觉表现 |
|------|---------|
| 思考中 | 三点脉冲 `...`，`color: var(--ai)` |
| 流式输出 | 末尾闪烁光标 `|`，禁用用户编辑 |
| 工具调用 | 可折叠卡片，显示调用名和结果 |
| 多 Agent 协作 | DAG 进度卡片，每个 Agent 独立状态 |
| 错误/降级 | 红色边框 + 错误说明 + 重新生成按钮 |

### 6.2 A2UI 卡片布局

- **垂直堆叠**：风险评估、详情列表、警示横幅
- **横向滚动**：律师推荐卡片、法规速览
- **流式推送**：卡片逐个生长出现，200ms 间隔

### 6.3 引用来源展示

```
[来源标注] 点击展开
  来源 1: 《民法典》第584条 — 违约损害赔偿 [相关度: 0.92]
  来源 2: 知识库片段 — 合同违约金上限 [相关度: 0.85]
```

---

## 7. Token 到代码映射

### CSS 变量 (index.css)
所有 Token 通过 CSS 自定义属性定义在 `:root` 和 `.dark` 下。

### Tailwind (tailwind.config.ts)
通过 `hsl(var(--*))` 绑定 CSS 变量。

### TypeScript (lib/design-tokens.ts)
导出组件级 Token 常量，供组件直接引用。

---

*最后更新: 2026-04-01*
