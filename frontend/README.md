# Frontend — 安心智能助手 Web 端

> React 18 + Vite 7 + TypeScript 5 + Tailwind 3 + shadcn/Radix
> 兼用桌面端（Tauri 2）的渲染层

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev                # http://localhost:5173 或 3001

# 构建生产
npm run build              # tsc && vite build

# Lint + 类型
npm run lint               # eslint --max-warnings 0
npm run typecheck          # tsc --noEmit

# 测试
npm run test               # vitest
npm run test:e2e           # playwright

# Tauri 桌面
npm run tauri:dev          # 桌面开发
npm run tauri:build        # 桌面构建
```

## 目录结构

```
src/
├── pages/              52 个页面（含 v3/ 专属）
├── pages/admin/        18 个后台管理页
├── pages/v3/           V3 智能助手专属（agents/capabilities/personas/rag/tasks）
├── components/         按域分组（chat/document-workbench/case-management/...）
├── lib/                api 客户端 / design tokens / Tauri bridge
├── hooks/              17 个自定义 hook
├── context/            Privacy / Theme 两个全局 Context
├── router/             React Router v6 路由表
└── store/              Zustand 状态管理
```

## 关键模块

| 模块 | 入口 |
|---|---|
| API 客户端 | `src/lib/api.ts`（3967 行） |
| 离线适配 | `src/lib/api-adapter.ts` |
| 设计令牌 | `src/lib/design-tokens.ts` |
| Tauri 桥接 | `src/lib/tauri-bridge.ts` |
| 隐私模式 | `src/context/PrivacyContext.tsx` |
| 主题 | `src/components/ThemeProvider.tsx` |
| 鉴权守卫 | `src/components/auth/ProtectedRoute.tsx` `AdminRoute.tsx` |

## 环境变量

`VITE_` 前缀（必须）：

| 变量 | 默认 |
|---|---|
| `VITE_API_TARGET_URL` | `http://localhost:8001` |
| `VITE_WS_URL` | `ws://localhost:8001` |
| `VITE_FEATURE_V3_IA` | `true` |

## 规范

- 代码风格：[docs/standards/code-style.md §2](../docs/standards/code-style.md#2-typescript--react)
- 命名：[docs/standards/naming-convention.md §1](../docs/standards/naming-convention.md#1-文件名)
- 设计系统：[../DESIGN.md](../DESIGN.md) + `src/lib/design-tokens.ts`（唯一真相源）

## 文档

- 当前权威导航：[../docs/00-project-execution-map.md](../docs/00-project-execution-map.md)
- V3 实施细节：[../docs/v3/](../docs/v3/)
- 设计专题：[../docs/design/](../docs/design/)
