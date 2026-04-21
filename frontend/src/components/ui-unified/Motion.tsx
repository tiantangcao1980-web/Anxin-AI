import { useEffect, useRef, useState, type ReactNode } from 'react'
import { motion, type MotionProps } from 'framer-motion'
import { cn } from '@/lib/utils'

const STANDARD_EASE: [number, number, number, number] = [0.2, 0, 0, 1]

interface FadeInUpProps extends Omit<MotionProps, 'initial' | 'animate' | 'exit'> {
  children: ReactNode
  delay?: number
  duration?: number
  distance?: number
  className?: string
}

/**
 * FadeInUp — 统一的"淡入 + 上移"入场
 *
 * 与 `.fade-in-up` CSS 工具类功能等同，但支持 JS 动态 delay/distance/stagger 场景。
 */
export function FadeInUp({
  children,
  delay = 0,
  duration = 0.25,
  distance = 8,
  className,
  ...rest
}: FadeInUpProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: distance }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration, delay, ease: STANDARD_EASE }}
      className={className}
      {...rest}
    >
      {children}
    </motion.div>
  )
}

interface StaggeredListProps {
  children: ReactNode[]
  /** 每个子元素延迟步进（秒），默认 0.05 */
  step?: number
  /** 整体入场延迟 */
  initialDelay?: number
  /** 子元素位移距离（px） */
  distance?: number
  /** 容器的额外 className */
  className?: string
  /** 子元素的 wrapper className（会包住每个 child） */
  itemClassName?: string
  /** 垂直间距（padding/gap 用途） */
  as?: keyof React.JSX.IntrinsicElements
}

/**
 * StaggeredList — 列表/网格的错峰入场
 *
 * 每个子元素依次淡入 + 上移，符合 Notion / Linear 列表出现的节奏感。
 *
 * 建议 step 值：
 * - 短列表（< 6 项）: 0.06
 * - 中长列表（6-15 项）: 0.035
 * - 超长列表（> 15 项）: 改用 ScrollReveal（避免首屏等待过久）
 */
export function StaggeredList({
  children,
  step = 0.05,
  initialDelay = 0,
  distance = 8,
  className,
  itemClassName,
  as = 'div',
}: StaggeredListProps) {
  const Tag = as as keyof React.JSX.IntrinsicElements
  return (
    <Tag className={className as string}>
      {children.map((child, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: distance }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            duration: 0.3,
            delay: initialDelay + i * step,
            ease: STANDARD_EASE,
          }}
          className={itemClassName}
        >
          {child}
        </motion.div>
      ))}
    </Tag>
  )
}

interface ScrollRevealProps {
  children: ReactNode
  /** 交集阈值（0-1），默认 0.15 */
  threshold?: number
  /** 仅首次进入视口时触发（默认 true） */
  once?: boolean
  /** 位移距离（px） */
  distance?: number
  /** 延迟（秒） */
  delay?: number
  className?: string
}

/**
 * ScrollReveal — 滚动进入视口时淡入（IntersectionObserver）
 *
 * 业务场景：
 * - 长表单/长文档分段渐显
 * - 列表滚动加载的新元素自然出现
 * - 登录/营销页的区块依次呈现
 *
 * 注意：对 prefers-reduced-motion 的用户会降级为直接显示（由全局 CSS 兜底）。
 */
export function ScrollReveal({
  children,
  threshold = 0.15,
  once = true,
  distance = 16,
  delay = 0,
  className,
}: ScrollRevealProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el || typeof IntersectionObserver === 'undefined') {
      setVisible(true)
      return
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setVisible(true)
            if (once) io.unobserve(entry.target)
          } else if (!once) {
            setVisible(false)
          }
        })
      },
      { threshold },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [threshold, once])

  return (
    <motion.div
      ref={ref}
      initial={false}
      animate={visible ? { opacity: 1, y: 0 } : { opacity: 0, y: distance }}
      transition={{ duration: 0.4, delay, ease: STANDARD_EASE }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

interface InteractivePressProps {
  children: ReactNode
  /** 按下缩放比，默认 0.97 */
  scale?: number
  className?: string
  onClick?: () => void
}

/**
 * InteractivePress — 轻按反馈包装（给任意卡片 / 图标按钮即时手感）
 *
 * 150ms 缩放 + hover 轻抬升。与 Button 组件的原生交互互补，
 * 用于非 Button 语义但可交互的元素（卡片、头像、徽章）。
 */
export function InteractivePress({
  children,
  scale = 0.97,
  className,
  onClick,
}: InteractivePressProps) {
  return (
    <motion.div
      whileTap={{ scale }}
      whileHover={{ y: -1 }}
      transition={{ duration: 0.15, ease: STANDARD_EASE }}
      className={cn('cursor-pointer', className)}
      onClick={onClick}
    >
      {children}
    </motion.div>
  )
}
