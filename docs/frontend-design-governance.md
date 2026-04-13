# 前端设计治理规则

## 1. 总原则

- 根目录 `DESIGN.md` 是设计系统单一真相源。
- `RESOURCES.md` 是图标、字体、动效与视觉素材的唯一资源目录。
- 新 UI 先复用 `frontend/src/lib/design-tokens.ts`，再考虑补 token。
- 页面和 feature 组件禁止长期保留硬编码视觉值。
- 图标统一通过 `frontend/src/lib/icons.ts` 使用。
- 在做统一升级前，先通过 Cleanup Gate 处理旧页面、旧资源、旧样式热点。

## 2. 允许直接写样式的例外

仅以下场景允许局部硬编码，且必须有注释说明原因：

- 第三方品牌识别图标本体，例如官方 SVG logo
- 文档打印 / 导出场景需要的排版常量
- 临时实验性 A/B 样式，且后续必须迁回 token
- 安全指纹或底层算法绘制所需的非 UI 颜色

## 3. PR 检查清单

- 是否新增了 hex / rgb / hsl 颜色？
- 是否新增了图标库直导或 emoji 图标？
- 是否新增了自定义按钮但没有 `focus-visible`？
- 是否新增了中文 `font-bold` 或 `tracking-wide`？
- 是否新增了不在尺度表内的圆角或间距？
- 是否把品牌橙用于非主行动语义？
- 是否新增了会造成首屏“骨架过强”或状态不明的加载体验？

## 4. 代码评审判定

### 直接拒绝
- 页面里新增长期硬编码主色
- 页面里新增 emoji / text-as-icon / 第二图标库
- 自定义交互控件没有 focus 态
- 同一模块新增第二套按钮/输入风格
- 中文业务标题大量使用 `font-bold` 或 `tracking-wide`
- 明知已有替代实现，却继续往旧页面或旧组件上追加功能/样式

### 可接受但需补债
- 第三方品牌按钮暂时保留官方色，但要抽到语义 token
- 图谱与图表为可读性保留扩展色板，但必须统一来源
- 打印 / 导出可保留独立字体和线条规则，但要归档为“打印态规范”
- 暂时不能删除的旧页面/组件，必须在清理基线里标记 `keep-for-now`

## 5. UI/UX 专项规则

### 图标
- 业务组件禁止直接从 `lucide-react` 导入。
- `frontend/src/components/ui/*` 这类底层基础组件可保留库直导，不纳入业务层图标统一规则。
- 禁止 emoji 图标出现在导航、图谱节点、toast 主视觉、状态提示中。
- 图标按钮最小点击区 44px。

### 字体
- 中文业务标题默认 `500`，强调值最多 `600`。
- `font-bold` 仅用于数字徽章、极小标签、英文缩写。
- `tracking-wide` 仅用于全英文、极小、装饰性标签。

### 间距与圆角
- 新组件必须落在标准 spacing / radius scale 内。
- 不允许常规业务卡片默认使用 `rounded-3xl`。
- 页面布局不允许靠随机 margin 修视觉。

### 体验
- 首屏必须优先显示主任务，而不是装饰和说明。
- 所有重要流程都要有 loading / empty / error / success 的明确设计。
- 移动端优先考虑单手可达与安全区。

## 6. 模块级治理优先级

高优先：
- `components/chat`
- `components/knowledge-center`
- `components/editor`
- `components/dashboard`
- `pages/Login.tsx`
- `pages/Chat.tsx`

中优先：
- `components/im`
- `components/a2ui`
- `pages/admin/*`

低优先：
- 边缘页面、历史兼容页、低频配置页
