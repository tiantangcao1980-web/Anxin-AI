/**
 * A2UI Card - 智能卡片组件
 * 支持多种变体、悬停动画、玻璃态效果
 */

import React, { forwardRef } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../utils/cn';

/**
 * 卡片变体
 */
export type CardVariant = 'default' | 'gradient' | 'glass' | 'elevated' | 'outlined';

/**
 * 卡片属性
 */
export interface A2UICardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onAnimationStart' | 'onAnimationEnd' | 'onDragStart' | 'onDragEnd' | 'onDrag'> {
  variant?: CardVariant;
  hoverable?: boolean;
  hoverScale?: number;
  clickable?: boolean;
  onClick?: () => void;
  header?: React.ReactNode;
  footer?: React.ReactNode;
  title?: string;
  subtitle?: string;
  icon?: React.ReactNode;
  extra?: React.ReactNode;
}

/**
 * 样式配置
 */
const cardStyles = {
  variants: {
    default: 'bg-background border border-border shadow-md',
    gradient: 'bg-primary/5 border-0 shadow-lg',
    glass: 'bg-background/80 backdrop-blur-lg border border-white/20 shadow-xl',
    elevated: 'bg-background shadow-2xl border-0',
    outlined: 'bg-background border-2 border-border shadow-none'
  },

  hoverStyles: {
    default: { y: -4, boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1)' },
    elevated: { y: -8, boxShadow: '0 25px 50px -12px rgb(0 0 0 / 0.25)' },
    glass: {
      y: -4,
      boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)'
    }
  }
};

/**
 * A2UI Card 组件
 */
export const A2UICard = forwardRef<HTMLDivElement, A2UICardProps>(
  (
    {
      variant = 'default',
      hoverable = false,
      hoverScale = 1.02,
      clickable = false,
      onClick,
      header,
      footer,
      title,
      subtitle,
      icon,
      extra,
      children,
      className,
      ...props
    },
    ref
  ) => {
    const baseClassName = cn(
      // 基础样式
      'rounded-2xl',
      'p-6',
      'transition-all',
      'duration-300',

      // 变体样式
      cardStyles.variants[variant],

      // 可点击样式
      clickable && 'cursor-pointer',

      // 可悬停样式
      hoverable && 'hover:shadow-2xl',

      className
    );

    // 悬停动画配置
    const hoverProps = hoverable
      ? {
          whileHover: {
            scale: hoverScale,
            ...(variant === 'glass'
              ? cardStyles.hoverStyles.glass
              : variant === 'elevated'
              ? cardStyles.hoverStyles.elevated
              : cardStyles.hoverStyles.default)
          },
          transition: { type: 'spring', stiffness: 300, damping: 20 }
        }
      : {};

    // 点击动画配置
    const tapProps = clickable
      ? {
          whileTap: { scale: 0.98 }
        }
      : {};

    return (
      <motion.div
        ref={ref}
        className={baseClassName}
        onClick={onClick}
        {...hoverProps}
        {...tapProps}
        {...props}
      >
        {/* 头部 */}
        {(header || title || icon || extra) && (
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              {/* 图标 */}
              {icon && (
                <motion.div
                  className="flex-shrink-0"
                  whileHover={{ rotate: 360 }}
                  transition={{ duration: 0.6, ease: 'easeInOut' }}
                >
                  {icon}
                </motion.div>
              )}

              {/* 标题和副标题 */}
              {(title || subtitle) && (
                <div>
                  {title && (
                    <h3 className="text-lg font-semibold text-foreground">
                      {title}
                    </h3>
                  )}
                  {subtitle && (
                    <p className="text-sm text-muted-foreground">{subtitle}</p>
                  )}
                </div>
              )}
            </div>

            {/* 额外内容 */}
            {extra && <div>{extra}</div>}
          </div>
        )}

        {/* 自定义头部 */}
        {header && !title && <div className="mb-4">{header}</div>}

        {/* 内容 */}
        <div className="flex-1">{children}</div>

        {/* 底部 */}
        {footer && (
          <div className="mt-4 pt-4 border-t border-border/50">
            {footer}
          </div>
        )}
      </motion.div>
    );
  }
);

A2UICard.displayName = 'A2UICard';

/**
 * Card 头部组件
 */
export const A2UICardHeader: React.FC<{
  title?: string;
  subtitle?: string;
  icon?: React.ReactNode;
  extra?: React.ReactNode;
  className?: string;
}> = ({ title, subtitle, icon, extra, className }) => {
  return (
    <div className={cn('flex items-center justify-between mb-4', className)}>
      <div className="flex items-center gap-3">
        {icon && (
          <motion.div
            className="flex-shrink-0"
            whileHover={{ rotate: 360, scale: 1.1 }}
            transition={{ duration: 0.6 }}
          >
            {icon}
          </motion.div>
        )}
        {(title || subtitle) && (
          <div>
            {title && (
              <h3 className="text-lg font-semibold text-foreground">{title}</h3>
            )}
            {subtitle && (
              <p className="text-sm text-muted-foreground">{subtitle}</p>
            )}
          </div>
        )}
      </div>
      {extra && <div>{extra}</div>}
    </div>
  );
};

/**
 * Card 内容组件
 */
export const A2UICardContent: React.FC<{
  children: React.ReactNode;
  className?: string;
}> = ({ children, className }) => {
  return <div className={cn('flex-1', className)}>{children}</div>;
};

/**
 * Card 底部组件
 */
export const A2UICardFooter: React.FC<{
  children: React.ReactNode;
  className?: string;
}> = ({ children, className }) => {
  return (
    <div className={cn('mt-4 pt-4 border-t border-border/50', className)}>
      {children}
    </div>
  );
};

/**
 * 默认导出
 */
export default A2UICard;
