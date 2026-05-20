/**
 * Center Tabs — I2 (2026-05-14, ADR 003)
 *
 * 这 5 个组件原本在 src/pages/ 下, 看起来像顶级 routed pages, 但实际从未被 App.tsx
 * 直接路由 — 它们是 CaseCenter / ManagementCenter 的 tab 内容子组件:
 *
 *   CaseCenter (路由 /case-center)
 *   ├── Leads  ← 案源线索 tab
 *   └── Tasks  ← 任务与审批 tab
 *
 *   ManagementCenter (路由 /management-center)
 *   ├── Contracts        ← 合同管理 tab
 *   ├── ComplianceCheck  ← 合规自检 tab
 *   └── RiskAlertPanel   ← 风险预警 tab
 *
 * 之前放 pages/ 命名误导 (会被下一接手 AI 误读为活跃顶级页面 + 误改重定向链).
 * 本目录把它们集中, 命名明确"中心型 tab 内容子组件".
 *
 * 注: Cases.tsx 是 5 行 shim 已删除 (Phase H4), 真实 CaseManagement 在
 * components/case-management/ 下, 是更早就规范放置的版本.
 */

export { default as Leads } from './Leads'
export { default as Tasks } from './Tasks'
export { default as Contracts } from './Contracts'
export { default as ComplianceCheck } from './ComplianceCheck'
export { RiskAlertPanel } from './RiskAlertPanel'
