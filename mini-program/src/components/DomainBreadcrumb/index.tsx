// -*- coding: utf-8 -*-
/**
 * DomainBreadcrumb (Taro · V3 · Editorial Luxury · Reset)
 *
 * 2026-05 Reset 说明：
 *   旧版用域色 + emoji iconbox，违反 ui-design skill 硬性禁令，已删除。
 *   新版纯文字 micro UPPERCASE tracking。
 *
 * 用法：
 *   <DomainBreadcrumb domain='legal' />
 *   <DomainBreadcrumb domain='legal' moduleName='合同审查' />
 */

import { Text, View } from '@tarojs/components'
import { domainMeta, type DomainId } from '@/styles/design-tokens'
import './index.scss'

interface DomainBreadcrumbProps {
  domain: DomainId
  moduleName?: string
  /** 兼容旧 API；Reset 后 compact 等同默认 */
  compact?: boolean
  className?: string
}

export default function DomainBreadcrumb(props: DomainBreadcrumbProps) {
  const { domain: domainId, moduleName, className = '' } = props
  const meta = domainMeta[domainId]
  return (
    <View className={`domain-breadcrumb ${className}`}>
      <Text className='domain-breadcrumb__en'>{meta.labelEn}</Text>
      <Text className='domain-breadcrumb__sep'> · </Text>
      <Text className='domain-breadcrumb__zh'>{meta.labelZh}</Text>
      {moduleName ? (
        <>
          <Text className='domain-breadcrumb__sep'> · </Text>
          <Text className='domain-breadcrumb__module'>{moduleName}</Text>
        </>
      ) : null}
    </View>
  )
}
