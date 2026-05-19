/**
 * domains.ts — 8 大业务域元数据中心 (V3 · Editorial Luxury)
 *
 * 2026-05 Reset 说明：
 *   早期版本在此处暴露了 color / colorClass / surfaceClass / cssVar 字段，
 *   配套 8 个高饱和度业务域色 (含违禁紫色 #7D4FCC)。该方案违反 ui-design skill
 *   多条硬性禁令 + 项目 DESIGN.md「不像 SaaS 控制台 / 不强调 AI 感」原则，
 *   已在 Reset 中全量删除。
 *
 *   新方向：业务域不用颜色区分，改用：
 *     - 衬线域名（Noto Serif SC）+ 字号 / 字距层次
 *     - 序号 01–08（serif num display）
 *     - Lucide 单色线性图标（1.5px stroke）
 *
 *   详见：docs/design/v3-prototype-editorial.html
 *
 * 单一真相源：DESIGN.md §业务域
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
  /** 中文短名（导航 / 序号目录 / 衬线大字） */
  label: string
  /** 英文短名（dev tools / a11y / micro UPPERCASE tracking） */
  labelEn: string
  /** 一句话定位（衬线副标 / 列表 caption） */
  tagline: string
  /** 默认入口路径 */
  defaultPath: string
  /** Lucide 图标（单色 1.5px stroke）— 不上品牌色 / 不上业务域色 */
  icon: LucideIcon
}

/**
 * 8 大业务域注册表。
 *
 * 新增业务域时同步更新：
 *   1. 本文件追加一项
 *   2. mobile/src/theme/colors.ts 的 domainMeta
 *   3. mini-program/src/styles/design-tokens.ts 的 domainMeta
 */
export const DOMAINS: readonly DomainMeta[] = [
  { id: 'legal',      label: '法务',     labelEn: 'Legal',      tagline: '合同审查 · 案件管理 · 法律顾问',     defaultPath: '/case-center',      icon: Scale },
  { id: 'finance',    label: '财务',     labelEn: 'Finance',    tagline: '记账 · 对账 · 报销 · 资金看板',        defaultPath: '/finance',          icon: Calculator },
  { id: 'tax',        label: '税务',     labelEn: 'Tax',        tagline: '申报 · 税务筹划 · 政策跟踪',          defaultPath: '/tax',              icon: Landmark },
  { id: 'compliance', label: '合规',     labelEn: 'Compliance', tagline: '风控 · 内审 · 监管红线',              defaultPath: '/compliance-check', icon: ShieldCheck },
  { id: 'operations', label: '经营管理', labelEn: 'Operations', tagline: 'KPI · 决策驾驶舱 · 战略推演',          defaultPath: '/dashboard',        icon: LineChart },
  { id: 'growth',     label: '调研获客', labelEn: 'Growth',     tagline: '市场调研 · 线索挖掘 · 舆情监测',       defaultPath: '/investigation',    icon: Compass },
  { id: 'content',    label: '内容产出', labelEn: 'Content',    tagline: '文案 · 视频脚本 · 营销素材',           defaultPath: '/content',          icon: PenLine },
  { id: 'global',     label: '出海跨境', labelEn: 'Global',     tagline: '国际化 · 海外合规 · 本地化',           defaultPath: '/global',           icon: Globe2 },
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
 * 从路径推断所属业务域（用于 DomainBreadcrumb / 顶栏标记）。
 *
 * 仅返回元数据 — 不返回颜色相关字段（Reset 后已删除）。
 *
 * 路径映射必须与 Layout.tsx moduleSidebarConfig 的 item.domain 字段同步。
 */
export function inferDomainFromPath(pathname: string): DomainMeta | null {
  // (1) 直接前缀匹配
  const direct = DOMAINS.find((d) => pathname.startsWith(d.defaultPath))
  if (direct) return direct

  // (2) Layout moduleSidebarConfig 9 个二级导航入口映射
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
