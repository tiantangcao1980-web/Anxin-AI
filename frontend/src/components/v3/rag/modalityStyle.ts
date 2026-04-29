/**
 * Modality 视觉令牌（V3 P13-D 跨组件共享）
 *
 * 5 种 modality 各自一个色系：
 *   - text   → slate / 灰
 *   - image  → blue / 蓝
 *   - table  → emerald / 绿
 *   - formula → violet / 紫
 *   - seal   → red / 红
 *
 * 暴露 hex / token 双套，兼容 Tailwind className 与 react-force-graph 渲染上下文。
 */

import type { Modality } from '@/lib/api/rag'

export interface ModalityVisual {
  label: string
  emoji: string
  /** Tailwind 背景 / 文字 / 边框（用于 SegmentPreview / Badge） */
  bg: string
  text: string
  border: string
  /** 实色 hex（react-force-graph 节点颜色 / SVG / canvas 用） */
  color: string
  /** 较深的辅色（描边 / hover） */
  accent: string
}

export const MODALITY_VISUALS: Record<Modality, ModalityVisual> = {
  text: {
    label: '文本',
    emoji: '📝',
    bg: 'bg-slate-50 dark:bg-slate-900/40',
    text: 'text-slate-700 dark:text-slate-200',
    border: 'border-slate-300 dark:border-slate-700',
    color: '#64748b',
    accent: '#334155',
  },
  image: {
    label: '图像',
    emoji: '🖼️',
    bg: 'bg-blue-50 dark:bg-blue-950/30',
    text: 'text-blue-700 dark:text-blue-200',
    border: 'border-blue-300 dark:border-blue-800',
    color: '#2563eb',
    accent: '#1d4ed8',
  },
  table: {
    label: '表格',
    emoji: '📊',
    bg: 'bg-emerald-50 dark:bg-emerald-950/30',
    text: 'text-emerald-700 dark:text-emerald-200',
    border: 'border-emerald-300 dark:border-emerald-800',
    color: '#059669',
    accent: '#047857',
  },
  formula: {
    label: '公式',
    emoji: '∑',
    bg: 'bg-violet-50 dark:bg-violet-950/30',
    text: 'text-violet-700 dark:text-violet-200',
    border: 'border-violet-300 dark:border-violet-800',
    color: '#7c3aed',
    accent: '#6d28d9',
  },
  seal: {
    label: '印章',
    emoji: '🔴',
    bg: 'bg-red-50 dark:bg-red-950/30',
    text: 'text-red-700 dark:text-red-200',
    border: 'border-red-300 dark:border-red-800',
    color: '#dc2626',
    accent: '#b91c1c',
  },
}

export function modalityVisual(m: Modality): ModalityVisual {
  return MODALITY_VISUALS[m] ?? MODALITY_VISUALS.text
}

export const MODALITIES: Modality[] = ['text', 'image', 'table', 'formula', 'seal']
