# ADR 004 — i18n 国际化策略

> **状态**: Accepted (Phase K, 2026-05-14)
> **决策者**: 用户授权 (技术债清零批次)
> **影响范围**: `frontend/src/`

---

## 背景

项目当前阶段是 **PMF 验证** (核心面向中国大陆用户), 全站 UI 文案为简体中文硬编码. 但:

1. **未来海外/港澳台扩展**几乎必然需要 i18n (尤其涉及法律科技场景, 香港 / 新加坡市场有现成商机)
2. **现存文案约 5000+** 处硬编码在 `.tsx` 文件中, 真正上线 i18n 时需大规模迁移, 风险高
3. **新代码**如果不养成 `t()` 习惯, 未来要按文件回扫历史代码, 工作量指数级增长

## 决策

采用 **轻量直通 + react-i18next API 兼容** 的渐进策略, 三步走:

### Step 1 (当前阶段, Phase K 已实施): 骨架 + API 兼容层

- ✅ `frontend/src/i18n/index.ts` 提供 `t()` / `useTranslation()` API, 形状与 react-i18next 完全一致
- ✅ 当前实现是**轻量直通**: `t('xxx')` 返回 `xxx` 自身, 不引入 npm 依赖, 0 bundle 成本
- ✅ `locales/zh-CN.json` + `locales/en-US.json` 已就位 (en-US 含 20+ 常用翻译示例)
- ✅ `i18n.changeLanguage()` 已可工作, 调用 `useTranslation()` 的组件能响应 locale 切换

**新代码规范**: 用户可见文案优先用 `t('文案')` 包裹, 不强制改老代码:
```tsx
import { useTranslation } from '@/i18n'

function MyNewComponent() {
  const { t } = useTranslation()
  return <h1>{t('管理中心')}</h1>  // 当前直接返回 '管理中心', 未来切 react-i18next 不动调用点
}
```

### Step 2 (未来海外扩张时启动): 切换到 react-i18next

触发条件: **有明确港澳台 / 海外客户合同** 或 **产品决策要做多语言**。

步骤 (估算 1-2 天):
1. `pnpm add react-i18next i18next i18next-browser-languagedetector`
2. 替换 `frontend/src/i18n/index.ts` 的实现 (API 形状保持不变)
3. 跑脚本扫全仓 `t('xxx')` 调用, 把 key/value 同步到 `locales/zh-CN.json`
4. 用 AI 批量翻译生成 `locales/en-US.json` / 其他语言
5. 在 `main.tsx` 引入 i18n init

### Step 3 (语言落地后): 历史代码渐进迁移

不要求一次性迁全, 按页面优先级:
1. 主路径页面 (Chat / Settings / Auth) — 上线前必须
2. 营销页 (Pricing / 落地页) — 多语言 SEO
3. 管理后台 (Admin*) — 内部用户, 可延后

## 不采纳的方案

- ❌ **现在就接 react-i18next** — 0 个海外客户的情况下增加 90KB+ bundle + 配置复杂度
- ❌ **不写任何 i18n 骨架, 等启动时再说** — 未来迁移阻力指数级增长, "新代码就是技术债"
- ❌ **用 React Intl** — API 形状与 react-i18next 差异较大, 业界 React 项目 i18n 主流是 react-i18next, 切换风险低

## 落地清单

- ✅ `frontend/src/i18n/index.ts` (轻量直通 t/useTranslation)
- ✅ `frontend/src/i18n/locales/zh-CN.json` (空骨架)
- ✅ `frontend/src/i18n/locales/en-US.json` (20+ 常用文案示例)
- ✅ `frontend/src/i18n/i18n.test.ts` (vitest 7 项)
- ✅ ADR 004 (本文件)

## 引用

- [react-i18next 官网](https://react.i18next.com/)
- [i18next API 参考](https://www.i18next.com/overview/api)
- [docs/standards/frontend-standard.md §10 国际化](../standards/frontend-standard.md)
