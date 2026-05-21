# 前端开发规范

> 强制规范。覆盖 React Web（`frontend/`）+ 移动 RN（`mobile/`）+ 小程序（`mini-program/`）。
>
> 2026-05 调整：原 `apps/uni-mobile/` UniApp 端已终止，相关规范条目（§17）保留为历史段落，但**不再适用**于当前开发。

## 1. 工具链

| 端 | 技术栈 | Lint | Type | Test | Build |
|---|---|---|---|---|---|
| Web | React 18 + Vite 7 + TS 5 + Tailwind 3 | eslint | tsc | vitest + playwright | vite |
| 桌面（共用 Web） | Tauri 2 | 同上 | 同上 | 同上 | tauri build |
| 移动 | RN 0.76 + Expo 52 | eslint | tsc | vitest | expo |
| 小程序 | Taro 3.6 + React | eslint | tsc | — | taro |

## 2. 组件命名

| 类型 | 规则 | 示例 |
|---|---|---|
| 组件文件 | `PascalCase.tsx` | `ChatCanvas.tsx` |
| 组件目录 | `kebab-case/` | `components/document-workbench/` |
| Hook | `useXxx.ts` | `useChatHistory.ts` |
| Store | `useXxxStore.ts` | `useAuthStore.ts` |
| 工具函数 | `camelCase.ts` | `formatCurrency.ts` |
| 类型定义 | `Xxx.types.ts` 或就近写在 `.tsx` | `chat.types.ts` |
| 样式 | 优先 Tailwind；CSS Modules 时 `xxx.module.css` | — |

## 3. 目录组织

```
frontend/src/
├── pages/                         路由级页面（PascalCase.tsx）
│   ├── Chat.tsx
│   ├── admin/                     后台
│   └── v3/                        V3 智能助手专属
├── components/                    可复用组件
│   ├── ui/                        shadcn 基础（Button / Card / Dialog）
│   ├── chat/                      域：对话
│   ├── document-workbench/        域：文档工作台
│   ├── case-management/           域：案件
│   ├── ...                        其他业务域
│   ├── layout/                    布局
│   └── auth/                      鉴权守卫
├── hooks/                         自定义 Hook
├── lib/                           工具与服务
│   ├── api.ts                     API 客户端（唯一）
│   ├── api-adapter.ts             离线适配
│   ├── design-tokens.ts           设计令牌
│   └── tauri-bridge.ts            Tauri 桥接
├── context/                       全局 Context（仅 Privacy / Theme）
├── store/                         Zustand store
├── router/                        路由配置
└── styles/                        全局样式
```

## 4. 组件实现规则

### 4.1 函数组件（强制）

```tsx
// ✅ 正确
import { useState } from 'react';

interface ChatBubbleProps {
  message: ChatMessage;
  onRetry?: () => void;
}

export function ChatBubble({ message, onRetry }: ChatBubbleProps) {
  const [expanded, setExpanded] = useState(false);
  return <div>...</div>;
}

// ❌ 禁止 Class 组件
class ChatBubble extends React.Component { ... }
```

### 4.2 Props

- **必须**用 TypeScript interface 定义 Props
- 可选 props 用 `?` 标记
- 复杂 props 拆出独立 type

### 4.3 Hook 规则

- 仅在组件顶层 / 其他 hook 内调用
- 禁止在条件 / 循环内调用
- 自定义 hook 必须 `use` 开头

### 4.4 状态管理

| 场景 | 用什么 |
|---|---|
| 组件内状态 | `useState` |
| 跨组件浅依赖 | props |
| 跨树深依赖 | Zustand store（`useXxxStore`） |
| 全局主题 / 隐私 / 鉴权 | React Context |
| 服务端数据 | `@tanstack/react-query` 或 `lib/api.ts` 包装 |
| 表单 | 简单：`useState`；复杂：考虑 `react-hook-form` + zod |

**禁止**：滥用 Context、过度 lift state。

## 5. API 调用

### 5.1 唯一入口

**所有后端调用必须走 `frontend/src/lib/api.ts`**。

```ts
// ❌ 禁止
const res = await fetch('/api/v1/chat/send', { ... });

// ✅ 正确
import { api } from '@/lib/api';
const res = await api.chat.send({ ... });
```

### 5.2 错误处理

```ts
const { code, data, message } = await api.contracts.create({ ... });
if (code !== 0) {
  toast.error(message);
  return;
}
// 使用 data
```

### 5.3 类型同步

后端 schema 变更必须同步更新 `api.ts` 中对应方法签名与类型。

## 6. 样式规则

### 6.1 Tailwind 优先

```tsx
// ✅ 语义类
<div className="bg-primary text-primary-foreground rounded-md p-4">

// ❌ 硬编码颜色
<div className="bg-[#1a2b3c] text-[white]">
```

### 6.2 设计令牌唯一源

- `frontend/src/lib/design-tokens.ts` 是唯一真相源
- `tailwind.config.ts` 从 design-tokens 派生
- 修改色彩 / 字号 / 间距必须先改 design-tokens

### 6.3 禁用清单

| ❌ 禁止 | ✅ 改为 |
|---|---|
| `text-white` 硬编码 | `text-primary-foreground` 等语义 token |
| `transition-all` | 具体属性 `transition-colors` / `transition-transform` |
| `bg-[#xxx]` 任意值 | 用 design-tokens 或加 token 后用语义类 |
| `font-bold` 滥用 | 按设计层级用 `font-semibold` / `font-bold` |
| 内联 style 颜色 | className 语义类 |

### 6.4 暗色模式

- 用 Tailwind `dark:` 前缀
- 必须用语义 token（已含明暗双套）
- 禁止 `if (dark) { color = '#fff' }` 这种 JS 判断

## 7. 路由

### 7.1 React Router v6

```tsx
// frontend/src/App.tsx
<Routes>
  <Route path="/login" element={<Login />} />
  <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
    <Route index element={<Navigate to="/chat" replace />} />
    <Route path="chat" element={<Chat />} />
    {/* V3 智能助手专属路由 */}
    <Route path="v3/personas" element={<V3Personas />} />
  </Route>
  <Route path="*" element={<NotFound />} />
</Routes>
```

### 7.2 懒加载

所有页面级路由必须 `React.lazy()`：

```tsx
const Chat = lazy(() => import('@/pages/Chat'));
```

### 7.3 守卫

| 守卫 | 用途 |
|---|---|
| `ProtectedRoute` | 登录守卫 |
| `AdminRoute` | 管理员守卫 |
| `ProtectedRoute feature="xxx"` | 特性开关 |
| `ProtectedRoute requirePrimaryClient="provider"` | V2 双客户端守卫 |
| `ModeGate required="hybrid_or_cloud"` | 三态模式守卫 |

## 8. 错误边界

- 路由级用 `<ErrorBoundary>`
- 组件级用 try/catch + `<ErrorState>` UI
- 网络错误：`<ErrorState onRetry={...}>` 提供重试

## 9. 加载 / 空 / 错误三态

任何数据驱动 UI 必须处理：

```tsx
if (loading) return <LoadingState />;
if (error) return <ErrorState onRetry={refetch} />;
if (!data || data.length === 0) return <EmptyState />;
return <List items={data} />;
```

统一组件：`components/common/{LoadingState,EmptyState,ErrorState}.tsx`

## 10. 国际化

- 当前阶段**仅简体中文**，无 i18n 框架
- 文案直接写中文
- 未来 i18n 时统一抽到 `frontend/src/locales/`
- 写代码时**禁止**在多处复制文案（用常量）

## 11. 可访问性 (a11y)

- 优先使用 Radix UI / shadcn 组件（原生 a11y 支持）
- 自造组件必须有：
  - 语义 HTML（`button` 而非 `div onClick`）
  - 键盘导航（Tab / Enter / Esc）
  - ARIA label（图标按钮）

## 12. 性能

| 规则 | 工具 |
|---|---|
| chunk < 500 KB | vite `chunkSizeWarningLimit` |
| 路由懒加载 | `React.lazy()` |
| 列表虚拟化（> 100 项） | `react-virtuoso` / `@tanstack/react-virtual` |
| 重计算 | `useMemo` `useCallback`（不滥用） |
| 图片 | 懒加载 + 压缩；大图用 CDN |
| `console.log` | 生产构建 terser 自动去除 |

## 13. 测试

### 13.1 单元（Vitest）

- 组件：测渲染 + 关键交互
- Hook：`@testing-library/react-hooks`
- 工具：纯函数 100% 覆盖

文件就近：`<Component>.test.tsx`

### 13.2 E2E（Playwright）

- 关键用户旅程必有
- 配置：`frontend/playwright.config.ts`
- 跑：`npm run test:e2e`

## 14. WebSocket

```ts
// 必须封装到 hook
const { messages, send } = useChatWebSocket(conversationId);
```

- 首包发 token
- 心跳 30s
- 断线指数退避重连
- 实现：`frontend/src/hooks/useChatWebSocket.ts`

## 15. Tauri Bridge（桌面）

```ts
import { isTauri } from '@/lib/tauri-bridge';

if (isTauri()) {
  const { invoke } = await import('@tauri-apps/api/core');
  await invoke('local_command', { ... });
}
```

Feature-detection，禁止 hardcode `window.__TAURI__`。

## 16. Mobile (RN + Expo) 特殊规则

- 用 Expo Router（`mobile/app/`）
- 平台 API 差异用 `Platform.select`
- 推送：`expo-notifications`
- 安全存储：`expo-secure-store`（不用 AsyncStorage 存 token）
- 生物识别：`expo-local-authentication`

## 17. UniApp（已终止 — 历史段落）

> 2026-05 UniApp 跨端方案终止；本节保留以避免历史 PR 引用断链。新代码不应再涉及 UniApp。

## 18. 小程序 (mini-program/) 特殊规则

- Taro `useDidShow` / `useDidHide` 替代 React lifecycle
- 主包 < 2 MB，超过用分包
- 禁止 `eval` / 动态 import 代码字符串
- 网络：`Taro.request`（不用原生 fetch）

## 19. 跨端一致性

| 维度 | 一致性要求 |
|---|---|
| API 调用层 | 所有端实现相同的 `api` 接口签名（Web / 桌面共用 `frontend/src/lib/api.ts`；其他端各自实现） |
| 设计令牌 | 同一份 design-tokens 派生到各端 |
| 错误码 | UnifiedResponse 在所有端处理一致 |
| 隐私模式 Header | 所有端必须传 `X-Privacy-Mode` |

详见 [docs/design/cross-platform-token-drift.md](../design/cross-platform-token-drift.md)。

## 20. 提交前自查

```bash
# Web
cd frontend
npm run lint && npm run typecheck && npm run test && npm run build

# Mobile
cd mobile
npm run typecheck && npm run test

# 小程序
cd mini-program
npm run typecheck && npm run build:weapp
```

任一失败 PR 不能合。
