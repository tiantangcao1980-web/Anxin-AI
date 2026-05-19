// -*- coding: utf-8 -*-
/**
 * DomainBadge — 业务域可视化原子组件 (Taro · V3 · Editorial Luxury · Reset)
 *
 * 2026-05 Reset 说明：
 *   旧版用 8 个高饱和域色 + emoji 作图标（⚖️💰🏛️🛡️📊🧭✍️🌐）。
 *   emoji 作产品图标违反 ui-design skill 硬性禁令；域色违反 DESIGN.md §1 哲学。
 *   新版完全删除 emoji 和域色，仅 micro UPPERCASE tracking 文字。
 *
 * 用法：
 *   <DomainBadge domain='legal' />            // 「LEGAL · 法务」
 *   <DomainBadge domain='legal' showEnglish={false} /> // 「法务」
 *
 * Stripe 已废除（业务子页头部用 DomainBadge 即可）；保留默认导出兼容老调用方
 */

import { Text, View } from '@tarojs/components'
import { domainMeta, type DomainId } from '@/styles/design-tokens'
import './index.scss'

interface DomainBadgeProps {
  domain: DomainId
  /** 是否前置 labelEn（默认 true 显示「LEGAL · 法务」） */
  showEnglish?: boolean
  className?: string
}

export default function DomainBadge(props: DomainBadgeProps) {
  const { domain: domainId, showEnglish = true, className = '' } = props
  const meta = domainMeta[domainId]
  return (
    <View className={`domain-badge ${className}`}>
      {showEnglish ? (
        <>
          <Text className='domain-badge__en'>{meta.labelEn}</Text>
          <Text className='domain-badge__sep'> · </Text>
        </>
      ) : null}
      <Text className='domain-badge__zh'>{meta.labelZh}</Text>
    </View>
  )
}

/** DomainStripe — Reset 后 no-op，兼容旧调用方（renders nothing） */
export function DomainStripe(_props: { domain: DomainId; className?: string }) {
  return null
}
