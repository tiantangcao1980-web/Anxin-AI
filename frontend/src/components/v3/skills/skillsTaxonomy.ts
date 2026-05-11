/**
 * skillsTaxonomy — 13 域 + type 的中文 label / 配色 / icon 表
 *
 * 与 docs/v3/SKILLS_INVENTORY.md 对齐，避免在每个组件里重复硬编码。
 */

import type { SkillCategory, SkillType } from '@/lib/api/skills'

export const CATEGORY_ORDER: SkillCategory[] = [
  'legal',
  'tax_finance',
  'operations',
  'research',
  'marketing',
  'content',
  'design',
  'office',
  'ecommerce',
  'sales',
  'intelligence',
  'decision',
  'system',
]

export const CATEGORY_LABEL: Record<SkillCategory, string> = {
  legal: '法律',
  tax_finance: '税务财务',
  operations: '运营流程',
  research: '调研',
  marketing: '营销',
  content: '内容',
  design: '设计',
  office: '办公文档',
  ecommerce: '跨境电商',
  sales: '销售',
  intelligence: '情报采集',
  decision: '决策',
  system: '系统 / 元能力',
}

export const CATEGORY_ICON: Record<SkillCategory, string> = {
  legal: '⚖️',
  tax_finance: '🧾',
  operations: '🔁',
  research: '🔬',
  marketing: '📣',
  content: '✍️',
  design: '🎨',
  office: '📄',
  ecommerce: '🛒',
  sales: '🤝',
  intelligence: '🛰️',
  decision: '🧭',
  system: '🛠️',
}

export const CATEGORY_BADGE_CLASS: Record<SkillCategory, string> = {
  legal: 'border-amber-300 bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300',
  tax_finance:
    'border-yellow-300 bg-yellow-50 text-yellow-700 dark:bg-yellow-500/10 dark:text-yellow-300',
  operations:
    'border-sky-300 bg-sky-50 text-sky-700 dark:bg-sky-500/10 dark:text-sky-300',
  research:
    'border-violet-300 bg-violet-50 text-violet-700 dark:bg-violet-500/10 dark:text-violet-300',
  marketing:
    'border-pink-300 bg-pink-50 text-pink-700 dark:bg-pink-500/10 dark:text-pink-300',
  content:
    'border-rose-300 bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300',
  design:
    'border-fuchsia-300 bg-fuchsia-50 text-fuchsia-700 dark:bg-fuchsia-500/10 dark:text-fuchsia-300',
  office:
    'border-blue-300 bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-300',
  ecommerce:
    'border-orange-300 bg-orange-50 text-orange-700 dark:bg-orange-500/10 dark:text-orange-300',
  sales:
    'border-teal-300 bg-teal-50 text-teal-700 dark:bg-teal-500/10 dark:text-teal-300',
  intelligence:
    'border-indigo-300 bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300',
  decision:
    'border-emerald-300 bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300',
  system:
    'border-slate-300 bg-slate-50 text-slate-700 dark:bg-slate-500/10 dark:text-slate-300',
}

export const TYPE_LABEL: Record<SkillType, string> = {
  tool: '工具',
  workflow: '工作流',
  agent: '智能体',
}

/** 已知的 user-facing personas（来自 docs/v3/AGENT_PERSONAS.md） */
export const KNOWN_PERSONAS = [
  '安心助理',
  '法律顾问',
  '合同管家',
  '财税顾问',
  '流程管家',
  '市场研究员',
  '尽调专家',
  '获客猎手',
  '内容总监',
  '跨境电商助手',
] as const
