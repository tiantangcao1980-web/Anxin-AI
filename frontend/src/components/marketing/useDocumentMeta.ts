/**
 * useDocumentMeta —— 极简 per-page SEO meta 钩子
 *
 * 不引入 react-helmet-async 等额外依赖；直接 useEffect 改 document。
 * 路由切换时上一页的 cleanup 会把 title 还原成站点默认。
 *
 * 用法::
 *
 *   useDocumentMeta({
 *     title: '产品功能 · 安心智能助手',
 *     description: '...',
 *     ogImage: '/og/features.png',
 *   })
 */

import { useEffect } from 'react'

interface MetaSpec {
  title: string
  description?: string
  ogImage?: string
  ogUrl?: string
  noindex?: boolean
}

const DEFAULT_TITLE = '安心智能助手 · 企业级多 Persona AI 助手'

function setMeta(name: string, content: string, isProperty = false) {
  const selector = isProperty
    ? `meta[property="${name}"]`
    : `meta[name="${name}"]`
  let el = document.querySelector<HTMLMetaElement>(selector)
  if (!el) {
    el = document.createElement('meta')
    if (isProperty) el.setAttribute('property', name)
    else el.setAttribute('name', name)
    document.head.appendChild(el)
  }
  el.setAttribute('content', content)
}

export function useDocumentMeta(spec: MetaSpec) {
  useEffect(() => {
    const previous = document.title
    document.title = spec.title
    if (spec.description) {
      setMeta('description', spec.description)
      setMeta('og:description', spec.description, true)
      setMeta('twitter:description', spec.description)
    }
    setMeta('og:title', spec.title, true)
    setMeta('twitter:title', spec.title)
    if (spec.ogImage) {
      setMeta('og:image', spec.ogImage, true)
      setMeta('twitter:image', spec.ogImage)
    }
    if (spec.ogUrl) {
      setMeta('og:url', spec.ogUrl, true)
    }
    if (spec.noindex) {
      setMeta('robots', 'noindex,nofollow')
    } else {
      setMeta('robots', 'index,follow')
    }
    return () => {
      document.title = previous || DEFAULT_TITLE
    }
  }, [spec.title, spec.description, spec.ogImage, spec.ogUrl, spec.noindex])
}

export default useDocumentMeta
