# ADR 003 — 前端组件目录三层架构

> **状态**: Accepted (2026-05-14)
> **决策者**: UI 审计 (Phase D agent) + 用户授权 (Phase I)
> **影响范围**: `frontend/src/components/`

---

## 背景

前端组件目前散布在三个目录, 职责重叠引起接手者困惑:

| 目录 | 当前内容 | 来源 |
|---|---|---|
| `components/ui/` | shadcn/ui 53 个原子组件 (button / dialog / tabs / select / ...) | shadcn 官方模板 |
| `components/common/` | EmptyState / ErrorState / LoadingState / PagePlaceholder | 早期共享组件 |
| `components/ui-unified/` | StatCard / StatGrid / StateView / Guidance / Motion | V2 → V3 升级时新增的"统一"层 |

**问题**:
- `EmptyState` 在 `common/` 和 `ui-unified/StateView` 中都有实现 (重复)
- `Skeleton` 在 `ui/skeleton.tsx` + `common/LoadingState` + `ui-unified/StateView` 中三重定义
- 三层命名没有约定的职责边界, 新组件不知该放哪里

## 决策

采用**三层职责分离**约定:

### 层 1: `components/ui/` (atoms, shadcn 原子层)

- **职责**: shadcn/ui 原子组件 (button / input / dialog / popover / select / tabs / table / ...), **不含任何业务语义**
- **来源**: shadcn CLI 生成或人工维护的 shadcn 风格组件
- **依赖**: lucide-react (允许直接 import, 是 shadcn 原版行为, ESLint allow-list 已配置)
- **能改吗**: 谨慎 — 改动会影响所有上层。如要新增, 优先用 shadcn CLI

### 层 2: `components/ui-unified/` (molecules + organisms, 业务复合层)

- **职责**: 业务复合组件 (StatCard / StatGrid / StateView / Guidance / Motion / EmptyState 等), **可有业务语义但与具体路由解耦**
- **依赖**: `ui/` 原子层 + `@/lib/design-tokens`
- **特点**: 跨页面复用, 设计 token 驱动, 可包含动画 / 状态机
- **新增组件优先放这里**

### 层 3: `components/common/` (deprecated, 渐进迁出)

- **职责**: ⚠️ **deprecated** — 历史遗留的共享组件
- **政策**:
  - 新组件**不再放 common/**
  - 现有 `EmptyState` / `ErrorState` / `LoadingState` / `PagePlaceholder` 继续可用 (向后兼容)
  - 下一个里程碑 PR 把这 4 个组件:
    - `EmptyState` → 收口到 `ui-unified/StateView` 的 preset (或迁到 `ui-unified/EmptyState.tsx`)
    - `LoadingState` skeleton variant → 收口到 `ui/skeleton`
    - `ErrorState` → `ui-unified/ErrorState.tsx`
    - `PagePlaceholder` → `ui-unified/PagePlaceholder.tsx`
  - 迁移后 `components/common/` 目录整体删除

## 实施

### 本 ADR 落地 (Phase I, 2026-05-14)

- ✅ 写明三层职责约定 (本文件)
- ✅ 在 `components/common/index.ts` 顶部加 deprecation 注释
- ✅ 在 `components/ui-unified/index.ts` 顶部加新增组件归属说明
- 🚧 **不**移动现有文件 — 避免大规模 import 变更引入回归

### 下一里程碑 PR (待业务里程碑)

1. 把 `common/EmptyState.tsx` 内容迁到 `ui-unified/EmptyState.tsx`
2. 全仓 `grep "from '@/components/common'"` 改为 `from '@/components/ui-unified'`
3. 删除 `common/EmptyState.tsx` (保留 1 个 deprecation alias 1 个 release 后再删)
4. 同步处理 ErrorState / LoadingState / PagePlaceholder
5. 删除 `components/common/` 目录

## 不采纳的方案

- ❌ **一次性大重构** — 数十个文件 import 改动, 风险高, 不值得
- ❌ **保持现状不立约定** — 下一接手 AI 仍会重复添 component 到 common/

## 引用

- UI 审计报告 (Phase D, general-purpose agent)
- 上游 [shadcn/ui 目录约定](https://ui.shadcn.com/docs/installation)
- [docs/standards/frontend-standard.md](../standards/frontend-standard.md)
