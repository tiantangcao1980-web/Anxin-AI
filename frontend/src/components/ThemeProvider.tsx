import { useEffect } from 'react'
import { useUIStore } from '@/lib/store'

/**
 * ThemeProvider — 集中管理主题初始化和切换
 *
 * 功能：
 * 1. 应用启动时立即同步主题到 DOM
 * 2. system 模式下实时监听系统偏好变化
 * 3. 切换时添加过渡动画，避免闪烁
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useUIStore((s) => s.theme)

  useEffect(() => {
    const root = document.documentElement

    const applyTheme = (prefersDark?: boolean) => {
      const isDark =
        theme === 'dark' ||
        (theme === 'system' && (prefersDark ?? window.matchMedia('(prefers-color-scheme: dark)').matches))

      // 添加过渡类，避免切换闪烁
      root.classList.add('theme-transition')
      root.classList.toggle('dark', isDark)

      // 同步 meta theme-color（移动端浏览器顶部栏颜色）
      const metaThemeColor = document.querySelector('meta[name="theme-color"]')
      if (metaThemeColor) {
        metaThemeColor.setAttribute('content', isDark ? '#171310' : '#ffffff')
      }

      // 过渡结束后移除过渡类
      requestAnimationFrame(() => {
        setTimeout(() => root.classList.remove('theme-transition'), 300)
      })
    }

    applyTheme()

    // system 模式下监听系统偏好变化（如系统从日间切到夜间）
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = (e: MediaQueryListEvent) => {
      if (theme === 'system') {
        applyTheme(e.matches)
      }
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [theme])

  return <>{children}</>
}
