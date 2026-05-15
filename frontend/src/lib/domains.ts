/**
 * domains.ts — 8 大业务域元数据中心 (V3)
 *
 * 安心 AI 智能助手覆盖 8 大业务域（法务/财务/税务/合规/经营管理/调研获客/内容产出/出海跨境）。
 * 本文件是唯一的「业务域真相源」，所有 Dashboard 入口、面包屑徽章、模块顶栏
 * 都应从此读取，避免散落硬编码。
 *
 * 设计原则：
 * - 业务域色 ≠ 品牌色：主行动按钮 / 链接 / 焦点环仍走 `--primary`（琥珀橙）
 * - 业务域色用于「分类标识」：模块入口卡片、面包屑、Tab 角标、域内强调
 * - 与 risk-* / status-* token 互不重叠：风险是「状态」，域是「分类」
 *
 * 单一真相源：DESIGN.md §业务域 + docs/design/ui-audit-and-upgrade-2026-05.md §5
 */

import type { LucideIcon } from 'lucide-react'
import {
  Scale,         // 法务
  Calculator,    // 财务
  Landmark,      // 税务
  ShieldCheck,   // 合规
  LineChart,     // 经营管理
  Compass,       // 调研获客
  PenLine,       // 内容产出
  Globe2,        // 出海跨境
} from 'lucide-react'

export type DomainId =
  | 'legal'
  | 'finance'
  | 'tax'
  | 'compliance'
  | 'operations'
  | 'growth'
  | 'content'
  | 'global'

export interface DomainMeta {
  id: DomainId
  /** 中文短名（导航/徽章用） */
  label: string
  /** 英文短名（dev tools / a11y label / 国际化兜底） */
  labelEn: string
  /** 一句话定位 */
  tagline: string
  /** 默认入口路径 */
  defaultPath: string
  /** Lucide 图标组件 */
  icon: LucideIcon
  /** 业务域色 Tailwind class —— 文本/边框/图标用 */
  colorClass: string
  /** 业务域低饱和底色 class —— 卡片背景 / hover 面用 */
  surfaceClass: string
  /** 业务域色对应的 CSS 变量名（不含 `--`） */
  cssVar: string
}

/**
 * 8 大业务域注册表。
 * 新增业务域时同步更新：
 *   1. `frontend/src/index.css`           — `--domain-<id>` CSS 变量（浅/深双模式）
 *   2. `frontend/tailwind.config.js`      — `colors.domain.<id>` 暴露
 *   3. 本文件                              — 这里追加一项
 *   4. `mobile/src/theme/colors.ts`        — `domain.<id>` 字段
 *   5. `mini-program/src/styles/design-tokens.scss` — `$color-domain-<id>`
 */
export const DOMAINS: readonly DomainMeta[] = [
  {
    id: 'legal',
    label: '法务',
    labelEn: 'Legal',
    tagline: '合同审查 · 案件管理 · 法律顾问',
    defaultPath: '/case-center',
    icon: Scale,
    colorClass: 'text-domain-legal',
    surfaceClass: 'bg-domain-legal-surface',
    cssVar: 'domain-legal',
  },
  {
    id: 'finance',
    label: '财务',
    labelEn: 'Finance',
    tagline: '记账 · 对账 · 报销 · 资金看板',
    defaultPath: '/finance',
    icon: Calculator,
    colorClass: 'text-domain-finance',
    surfaceClass: 'bg-domain-finance-surface',
    cssVar: 'domain-finance',
  },
  {
    id: 'tax',
    label: '税务',
    labelEn: 'Tax',
    tagline: '申报 · 税务筹划 · 政策跟踪',
    defaultPath: '/tax',
    icon: Landmark,
    colorClass: 'text-domain-tax',
    surfaceClass: 'bg-domain-tax-surface',
    cssVar: 'domain-tax',
  },
  {
    id: 'compliance',
    label: '合规',
    labelEn: 'Compliance',
    tagline: '风控 · 内审 · 监管红线',
    defaultPath: '/compliance-check',
    icon: ShieldCheck,
    colorClass: 'text-domain-compliance',
    surfaceClass: 'bg-domain-compliance-surface',
    cssVar: 'domain-compliance',
  },
  {
    id: 'operations',
    label: '经营管理',
    labelEn: 'Operations',
    tagline: 'KPI · 决策驾驶舱 · 战略推演',
    defaultPath: '/dashboard',
    icon: LineChart,
    colorClass: 'text-domain-operations',
    surfaceClass: 'bg-domain-operations-surface',
    cssVar: 'domain-operations',
  },
  {
    id: 'growth',
    label: '调研获客',
    labelEn: 'Growth',
    tagline: '市场调研 · 线索挖掘 · 舆情监测',
    defaultPath: '/investigation',
    icon: Compass,
    colorClass: 'text-domain-growth',
    surfaceClass: 'bg-domain-growth-surface',
    cssVar: 'domain-growth',
  },
  {
    id: 'content',
    label: '内容产出',
    labelEn: 'Content',
    tagline: '文案 · 视频脚本 · 营销素材',
    defaultPath: '/content',
    icon: PenLine,
    colorClass: 'text-domain-content',
    surfaceClass: 'bg-domain-content-surface',
    cssVar: 'domain-content',
  },
  {
    id: 'global',
    label: '出海跨境',
    labelEn: 'Global',
    tagline: '国际化 · 海外合规 · 本地化',
    defaultPath: '/global',
    icon: Globe2,
    colorClass: 'text-domain-global',
    surfaceClass: 'bg-domain-global-surface',
    cssVar: 'domain-global',
  },
] as const

/** 按 id 快速查询 */
export const DOMAIN_BY_ID: Record<DomainId, DomainMeta> = DOMAINS.reduce(
  (acc, d) => {
    acc[d.id] = d
    return acc
  },
  {} as Record<DomainId, DomainMeta>,
)

/**
 * 从路径推断所属业务域（用于面包屑 / 状态栏 / DomainBreadcrumb）。
 *
 * 匹配优先级：
 *   1) 直接前缀命中 DOMAINS[].defaultPath
 *   2) Layout ModuleSidebar 已声明的 V2→V3 过渡映射（与 Layout.tsx moduleSidebarConfig 同步）
 *   3) 兜底返回 null（页面应当 fallback 到不显示域指示器）
 */
export function inferDomainFromPath(pathname: string): DomainMeta | null {
  // (1) 直接前缀匹配
  const direct = DOMAINS.find((d) => pathname.startsWith(d.defaultPath))
  if (direct) return direct

  // (2) 与 Layout.tsx moduleSidebarConfig 的 9 个二级导航入口对齐
  //     —— 任何此处的修改必须同步 Layout.tsx 中的 item.domain 字段
  if (
    pathname.startsWith('/contract') ||
    pathname.startsWith('/find-lawyer') ||
    pathname.startsWith('/management') ||
    pathname.startsWith('/cases') ||
    pathname.startsWith('/firm') ||
    pathname.startsWith('/lawyer-dashboard')
  ) {
    return DOMAIN_BY_ID.legal
  }
  if (pathname.startsWith('/knowledge')) return DOMAIN_BY_ID.legal
  if (pathname.startsWith('/monitoring')) return DOMAIN_BY_ID.growth
  if (pathname.startsWith('/agent-approvals')) return DOMAIN_BY_ID.compliance
  if (pathname.startsWith('/documents')) return DOMAIN_BY_ID.content
  if (pathname.startsWith('/acquisition')) return DOMAIN_BY_ID.growth
  return null
}
