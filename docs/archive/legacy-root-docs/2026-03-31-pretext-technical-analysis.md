# Pretext 技术分析与性能优化借鉴

> 基于 [chenglou/pretext](https://github.com/chenglou/pretext) 项目的深度分析，评估其技术思想对安心法务项目的适用性。

---

## 一、Pretext 项目概述

| 属性 | 值 |
|------|-----|
| 仓库 | `chenglou/pretext` |
| Stars | 21.4k |
| 语言 | TypeScript (89.8%) |
| 作者 | Cheng Lou (React/ReasonML 核心贡献者) |
| 依赖 | **零运行时依赖** |
| 源码量 | ~3,000 行 TypeScript |
| 定位 | 纯前端文本测量与布局引擎 |

**核心能力**：绕开 DOM 测量（`getBoundingClientRect`/`offsetHeight`），使用 Canvas `measureText()` 直接访问浏览器字体引擎，然后用纯算术完成布局计算，实现零回流的文本排版。

---

## 二、核心架构：两阶段分离

### Phase 1: `prepare(text, font)` — 一次性预处理（重活）

1. CSS `white-space: normal` 语义的空白符归一化
2. `Intl.Segmenter` 分词（天然支持 CJK 逐字断行）
3. 标点合并（"better." 作为一个测量单位）
4. CJK 禁则处理（日文 Kinsoku 规则）
5. Canvas `measureText()` 测量每个段宽度
6. 缓存结构：`Map<font, Map<segment, SegmentMetrics>>`

### Phase 2: `layout(prepared, maxWidth, lineHeight)` — 纯算术热路径

- **零 DOM 读取、零 Canvas 调用、零字符串操作、零内存分配**
- 贪心行折断：遍历缓存宽度数组，溢出前断行
- 约 **0.0002ms/文本块**

---

## 三、性能数据验证（已验证属实）

### 批量测试（500 文本块）

| 操作 | Chrome | Safari |
|------|--------|--------|
| `prepare()` (冷启动) | 18.85ms | 18.0ms |
| `layout()` (热路径) | **0.093ms** | **0.115ms** |
| DOM 批量 (写完再读) | 4.05ms | 87.0ms |
| DOM 交叉 (逐个写读) | 43.5ms | 149.0ms |

### 提升倍数

| 场景 | Chrome | Safari |
|------|--------|--------|
| vs DOM 交叉读写 | **468x** | **1,296x** |
| vs DOM 批量读写 | **44x** | **757x** |

### CJK 长文本测试

| 语言 | 字符数 | `prepare()` | `layout()` | 提升倍数 |
|------|--------|-------------|------------|---------|
| 日文（罗生门） | 5,702 | 12.6ms | 0.034ms | **370x** |
| 中文（祝福） | 9,428 | 19.2ms | 0.053ms | **362x** |
| 韩文 | 10,272 | 11.4ms | 0.043ms | **265x** |
| 阿拉伯文 | 106,857 | 63.5ms | 0.169ms | **376x** |

**结论："几百倍性能提升"的说法保守且属实。Safari 上甚至超过千倍。**

准确率：三大浏览器 7,680/7,680 = **100%** 匹配。

---

## 四、关键优化技术拆解

### 4.1 简单路径快速分支

`simpleLineWalkFastPath` 布尔标记：普通文本（无制表符、无软连字符、无 pre-wrap）走极简计数器 `countPreparedLinesSimple`，避免不必要的状态跟踪。

**启发**：80%场景走快速路径，仅复杂场景走完整引擎。

### 4.2 分层缓存策略

```
段落指标缓存: Map<font, Map<segment, SegmentMetrics>>
├─ width: number           — 段宽度
├─ containsCJK: boolean    — CJK 标记
├─ emojiCount?: number     — 懒计算
├─ graphemeWidths?: number[] — 懒计算（仅 break-word 场景）
└─ graphemePrefixWidths?: number[] — Safari 专用

Emoji 校正缓存: Map<font, number>
└─ 一次 DOM 读取检测 Canvas/DOM emoji 宽度差异，永久缓存

Segmenter 实例: 模块级单例复用
```

**启发**：昂贵计算一次完成、结果永久缓存、懒计算非必需字段。

### 4.3 浏览器引擎 Profile

根据 UA 检测 Safari/Chrome/Firefox，微调参数：
- `lineFitEpsilon`: Safari 用 `1/64`，其他用 `0.005`
- `carryCJKAfterClosingQuote`: 仅 Chromium
- `preferPrefixWidthsForBreakableRuns`: 仅 Safari

**启发**：正视浏览器差异，用 profile 而非通用方案处理。

### 4.4 API 分层设计

| 层级 | API | 用途 | 性能 |
|------|-----|------|------|
| L1 | `prepare()` + `layout()` | 仅需高度/行数 | 最快 |
| L2 | `prepareWithSegments()` + `layoutWithLines()` | 需要行文本 | 中等 |
| L3 | `walkLineRanges()` | 试探性布局（二分搜索） | 零分配 |
| L4 | `layoutNextLine()` | 逐行不同宽度（文字环绕图片） | 迭代器式 |

**启发**：按需提供不同精度的 API，避免过度计算。

---

## 五、安心法务项目适用性分析

### 5.1 高适用场景

#### 知识图谱 Canvas 文本渲染（优先级：高）

**当前问题**（`ForceGraphCanvas.tsx`、`KnowledgeGraphExplorer.tsx`）：
- 每帧对每个节点调用 `ctx.font = ...` + `ctx.fillText()`，字体切换开销大
- 节点标签截断使用朴素字符计数（`slice(0, 10)`），中英文宽度不同导致截断不一致
- 60fps * N 节点 * 2(节点+边) 次文本操作

**Pretext 优化方案**：
1. 用 `prepare()` 预处理所有节点/边标签（图数据变更时一次性完成）
2. 用 `layout()` 在每帧快速判断标签是否溢出，决定截断位置
3. 缓存字体指标，避免每帧重复测量
4. 预期收益：Canvas 文本操作减少 90%+，图谱交互流畅度显著提升

#### 未来消息列表虚拟化（优先级：中，前置依赖）

**当前问题**：
- 聊天消息列表渲染全部 DOM 节点，无虚拟化
- 长对话（100+ 消息）性能退化

**Pretext 价值**：
- 虚拟滚动最难的问题是变高度行的高度预估
- Pretext 可在不插入 DOM 的情况下精确预测 Markdown 渲染后的消息高度
- 为后续引入 react-virtuoso 等方案提供高度预估引擎

### 5.2 中等适用场景

#### Textarea 自动高度（优先级：低-中）

**当前问题**（4 处）：
```javascript
// useChatInput.ts:127-132
textarea.style.height = 'auto';
textarea.style.height = `${textarea.scrollHeight}px`;
// 每次按键触发强制同步布局
```

**Pretext 方案**：用预测量替代 `scrollHeight` 读取，避免布局回流。但实际收益有限（短文本场景）。

### 5.3 不适用场景

| 场景 | 原因 |
|------|------|
| ReactMarkdown 渲染 | DOM 渲染，非 Canvas |
| TipTap/ProseMirror 编辑器 | 自有 contenteditable 布局 |
| CSS 截断 (truncate/line-clamp) | 纯 CSS，无 JS 测量 |
| 弹窗定位 (getBoundingClientRect) | 容器定位，非文本测量 |
| 滚动检测 (scrollHeight/clientHeight) | 容器几何，非文本 |

---

## 六、架构思想对后端 AI 管线的启发

虽然 Pretext 是前端库，但其架构思想对后端 AI 生成管线同样有价值：

### 6.1 两阶段分离 → 减少串行 LLM 调用

| Pretext 思想 | 对应到 AI 管线 |
|-------------|--------------|
| `prepare()` 一次性重活 | 意图识别+需求分析合并为一次 LLM 调用 |
| `layout()` 纯算术热路径 | 关键词规则引擎快速路由（0ms） |
| 简单路径快速分支 | 简单消息跳过 LLM 意图识别 |

**当前问题**：复杂消息路径 = 需求分析(LLM) → 意图识别(LLM) → Agent执行(LLM) = 3 次串行调用

**优化目标**：
```
快速路径: 关键词匹配(0ms) → 直接Agent执行(1次LLM)     [80%场景]
完整路径: 合并意图+需求(1次LLM) → Agent执行(1次LLM)   [20%场景]
```

### 6.2 分层缓存 → LLM 配置缓存

| Pretext 缓存 | 对应到 AI 管线 |
|-------------|--------------|
| `Map<font, Map<segment, Metrics>>` 跨文本共享 | LLM Config 带 TTL 内存缓存 |
| Emoji 校正一次检测永久缓存 | 意图识别 5min TTL 缓存（已有，扩展） |
| Segmenter 单例复用 | httpx.AsyncClient 连接池复用（已有） |

### 6.3 按需精度 → 动态响应策略

| Pretext API 层级 | 对应到 AI 管线 |
|-----------------|--------------|
| L1 仅高度/行数 | 简单问候 → 直接回复，无 Agent |
| L2 行文本 | 单 Agent 流式回复 |
| L3 试探性布局 | 多 Agent DAG，首个 Agent 立即流式 |
| L4 逐行自定义 | 工作台模式，分步展示 |

---

## 七、实施建议

### 短期（1-2 周）

1. **知识图谱 Canvas 优化** — 引入 Pretext 或实现类似的文本测量缓存
2. **后端 AI 管线 P0 优化**（借鉴两阶段分离思想）：
   - LLM Config 加内存缓存
   - 合并意图识别+需求分析
   - WebSocket 路径补对话历史

### 中期（2-4 周）

3. **消息列表虚拟化预研** — 评估 Pretext 作为高度预估引擎的可行性
4. **后端 AI 管线 P1 优化**：
   - 动态 max_tokens
   - Prompt 模板化管理

### 长期（1-2 月）

5. **完整虚拟化实施** — react-virtuoso + Pretext 高度预估
6. **后端 AI 管线 P2 优化**：
   - 拆分 WebSocket handler
   - 消除三重重复代码

---

## 八、参考资料

- [Pretext 源码](https://github.com/chenglou/pretext)
- [Pretext NPM](https://www.npmjs.com/package/@chenglou/pretext)
- Pretext thoughts.md — 作者对 CSS 复杂性和 AI 辅助 UI 开发的思考
- Pretext benchmarks/ — Chrome 和 Safari 的完整基准测试数据
