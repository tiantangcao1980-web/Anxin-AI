/**
 * i18n 骨架 — K2 (2026-05-14)
 *
 * **当前阶段策略**: 项目阶段为 PMF 验证, **仅支持简体中文**, 不引入 react-i18next 等
 * 重型 i18n 框架。但希望:
 *   1. **API 形状**与 react-i18next 一致, 后续迁移只换实现不动调用站点
 *   2. **现在就开始**让新代码养成 `t('文案')` 习惯, 避免上千个硬编码字符串
 *      在未来 i18n 上线时阻塞迁移
 *
 * **当前实现** (轻量直通):
 *   - `t(key)` 直接返回 key 自身 (key 即默认中文文案)
 *   - 可选 2 参数 `t(key, defaultText)`: 显式提供默认文案
 *   - `useTranslation()` hook 返回 `{ t, i18n }` (i18n 是 stub, 暂只暴露 `language` 字段)
 *   - 同时 `i18n.changeLanguage(lang)` 暴露为 no-op (上线 i18n 后绑定 react-i18next)
 *
 * **未来迁移路径** (3 步, 不动调用点):
 *   1. `pnpm add react-i18next i18next i18next-browser-languagedetector`
 *   2. 把 `t()` 替换为 react-i18next 的 useTranslation().t
 *   3. 跑脚本扫 `t('xxx')` 把 key/value 同步到 locales/zh-CN.json
 *
 * **使用示例**:
 *   ```tsx
 *   import { useTranslation } from '@/i18n'
 *   export function ManagementCenter() {
 *     const { t } = useTranslation()
 *     return <h1>{t('管理中心')}</h1>  // 当前直接返回 '管理中心'
 *   }
 *   ```
 *
 * 见 docs/adr/004-i18n-strategy.md
 */

import { useCallback, useMemo, useState } from 'react'

import zhCN from './locales/zh-CN.json'
import enUS from './locales/en-US.json'

type Locale = 'zh-CN' | 'en-US'

interface Resources {
  'zh-CN': Record<string, string>
  'en-US': Record<string, string>
}

const RESOURCES: Resources = {
  'zh-CN': zhCN as Record<string, string>,
  'en-US': enUS as Record<string, string>,
}

// 简单的全局状态 (后续迁 react-i18next 时, 此 module-level state 会被替换)
let currentLocale: Locale = 'zh-CN'
const listeners = new Set<(locale: Locale) => void>()

export const i18n = {
  get language(): Locale {
    return currentLocale
  },
  changeLanguage(locale: Locale): void {
    if (locale === currentLocale) return
    currentLocale = locale
    listeners.forEach(fn => fn(locale))
  },
  /** 暴露给测试: 重置回默认 zh-CN */
  reset(): void {
    currentLocale = 'zh-CN'
    listeners.forEach(fn => fn('zh-CN'))
  },
}

/**
 * 翻译函数 — react-i18next API 兼容。
 *
 * - `t('xxx')`: 返回 RESOURCES[currentLocale][xxx] 或 fallback 到 xxx 自身
 * - `t('xxx', '默认')`: 同上, 但 fallback 改为第二参数
 */
export function t(key: string, defaultValue?: string): string {
  const dict = RESOURCES[currentLocale]
  if (dict && dict[key]) return dict[key]
  return defaultValue ?? key
}

/**
 * React hook — useTranslation API 兼容 react-i18next。
 *
 * 用法: `const { t, i18n } = useTranslation()`
 */
export function useTranslation(): { t: typeof t; i18n: typeof i18n } {
  const [, force] = useState(0)

  // 监听 locale 变更, 触发组件重渲染
  useMemo(() => {
    const fn = () => force(n => n + 1)
    listeners.add(fn)
    return fn
  }, [])

  const tFn = useCallback((key: string, defaultValue?: string) => t(key, defaultValue), [])

  return { t: tFn, i18n }
}

export type { Locale }
