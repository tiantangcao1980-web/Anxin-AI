// -*- coding: utf-8 -*-
/**
 * DomainBreadcrumb — 业务域面包屑（Mini Program / Taro 受限版）
 *
 * 与 frontend / mobile DomainBreadcrumb 视觉对齐 — 同一套 8 域元数据。
 * 小程序受限：不能用 SVG 图标库，用 emoji 替代（与 DomainBadge 同样模式）。
 *
 * 用法：
 *   import DomainBreadcrumb from '@/components/DomainBreadcrumb'
 *   <DomainBreadcrumb domain='legal' />
 *   <DomainBreadcrumb domain='legal' moduleName='合同审查' />
 *   <DomainBreadcrumb domain='legal' compact />
 */

import { Text, View } from '@tarojs/components'
import { domain, type DomainId } from '@/styles/design-tokens'
import './index.scss'

// 域 → emoji（与 DomainBadge 共用同一映射 — 任何修改必须同步两处）
const DOMAIN_EMOJI: Record<DomainId, string> = {
  legal: '⚖️',
  finance: '💰',
  tax: '🏛️',
  compliance: '🛡️',
  operations: '📊',
  growth: '🧭',
  content: '✍️',
  global: '🌐',
}

interface DomainBreadcrumbProps {
  domain: DomainId
  /** 可选：当前模块/子页名称，显示在域名之后 */
  moduleName?: string
  /** 紧凑变体：仅显示 6rpx 圆点 + 域名 */
  compact?: boolean
  /** 容器自定义类名 */
  className?: string
}

export default function DomainBreadcrumb(props: DomainBreadcrumbProps) {
  const { domain: domainId, moduleName, compact = false, className = '' } = props
  const meta = domain[domainId]

  if (compact) {
    return (
      <View className={`domain-breadcrumb domain-breadcrumb--compact ${className}`}>
        <View
          className='domain-breadcrumb__dot'
          style={{ backgroundColor: meta.color }}
        />
        <Text
          className='domain-breadcrumb__label'
          style={{ color: meta.color }}
        >
          {meta.labelZh}
        </Text>
      </View>
    )
  }

  return (
    <View className={`domain-breadcrumb ${className}`}>
      <View
        className='domain-breadcrumb__iconbox'
        style={{ backgroundColor: meta.surface }}
      >
        <Text className='domain-breadcrumb__icon'>{DOMAIN_EMOJI[domainId]}</Text>
      </View>
      <Text
        className='domain-breadcrumb__label'
        style={{ color: meta.color }}
      >
        {meta.labelZh}
      </Text>
      {moduleName ? (
        <>
          <Text className='domain-breadcrumb__sep'>·</Text>
          <Text className='domain-breadcrumb__module'>{moduleName}</Text>
        </>
      ) : null}
    </View>
  )
}
