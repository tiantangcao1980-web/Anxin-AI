/**
 * useBreakpoint — 多断点响应式 hook
 *
 * 与 Tailwind 默认断点对齐：
 *   sm: 640  md: 768  lg: 1024  xl: 1280  2xl: 1536
 *
 * 使用示例：
 *   const { isMobile, isTablet, isDesktop, breakpoint } = useBreakpoint()
 *   if (isMobile) return <MobileView />
 *
 * 或精确查询：
 *   const isAtLeastLg = useMediaQuery('(min-width: 1024px)')
 *
 * 对比 useIsMobile（保留用于向后兼容）：本 hook 提供多层级与命名断点。
 */

import { useEffect, useState } from 'react'

export type BreakpointKey = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl'

/** 与 tailwind.config.js 的 screens 对齐 */
export const BREAKPOINTS: Record<Exclude<BreakpointKey, 'xs'>, number> = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
}

export interface BreakpointState {
  /** 当前命中的最大断点 */
  breakpoint: BreakpointKey
  /** < 768px（按 Tailwind md 以下） */
  isMobile: boolean
  /** 768 – 1023px */
  isTablet: boolean
  /** >= 1024px */
  isDesktop: boolean
  /** >= 1280px */
  isWide: boolean
  /** 当前视口宽度（px），SSR 时为 undefined */
  width: number | undefined
}

function resolveBreakpoint(width: number): BreakpointKey {
  if (width >= BREAKPOINTS['2xl']) return '2xl'
  if (width >= BREAKPOINTS.xl) return 'xl'
  if (width >= BREAKPOINTS.lg) return 'lg'
  if (width >= BREAKPOINTS.md) return 'md'
  if (width >= BREAKPOINTS.sm) return 'sm'
  return 'xs'
}

function readInitialState(): BreakpointState {
  if (typeof window === 'undefined') {
    // SSR 默认桌面，避免首屏闪烁抽屉
    return {
      breakpoint: 'lg',
      isMobile: false,
      isTablet: false,
      isDesktop: true,
      isWide: false,
      width: undefined,
    }
  }
  const w = window.innerWidth
  const bp = resolveBreakpoint(w)
  return {
    breakpoint: bp,
    isMobile: w < BREAKPOINTS.md,
    isTablet: w >= BREAKPOINTS.md && w < BREAKPOINTS.lg,
    isDesktop: w >= BREAKPOINTS.lg,
    isWide: w >= BREAKPOINTS.xl,
    width: w,
  }
}

export function useBreakpoint(): BreakpointState {
  const [state, setState] = useState<BreakpointState>(readInitialState)

  useEffect(() => {
    const onResize = () => setState(readInitialState())
    // 初次挂载同步一次（SSR/hydration 场景）
    onResize()
    window.addEventListener('resize', onResize, { passive: true })
    window.addEventListener('orientationchange', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      window.removeEventListener('orientationchange', onResize)
    }
  }, [])

  return state
}

/**
 * useMediaQuery — 任意 CSS 媒体查询
 *
 * 示例：
 *   const prefersDark = useMediaQuery('(prefers-color-scheme: dark)')
 *   const isRetina = useMediaQuery('(min-resolution: 2dppx)')
 */
export function useMediaQuery(query: string): boolean {
  const getSnapshot = () =>
    typeof window !== 'undefined' ? window.matchMedia(query).matches : false

  const [matches, setMatches] = useState<boolean>(getSnapshot)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const mql = window.matchMedia(query)
    const handler = () => setMatches(mql.matches)
    handler()
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [query])

  return matches
}

/**
 * useBreakpointMatches — 精确匹配某个断点的最小阈值
 *
 * @example useBreakpointMatches('lg') → 当 viewport >= 1024px 时返回 true
 */
export function useBreakpointMatches(key: Exclude<BreakpointKey, 'xs'>): boolean {
  return useMediaQuery(`(min-width: ${BREAKPOINTS[key]}px)`)
}
